"""
anomalias_isolation_forest.py

Detección de anomalías mediante Isolation Forest (Liu et al., 2008).

Diferencia clave respecto al Z-Score:
  - Z-Score analiza cada producto por separado en su dimensión temporal.
  - Isolation Forest analiza TODOS los productos simultáneamente en un
    espacio multidimensional de features. Detecta anomalías por su
    rareza en el espacio de características, no por su desviación temporal.

Principio del algoritmo:
  Construye árboles de decisión aleatorios que particionan el espacio.
  Los puntos anómalos son más fáciles de aislar (necesitan menos particiones)
  porque están en zonas poco densas del espacio de features.
  El score de anomalía = profundidad media de aislamiento (invertida).

Ventaja sobre Z-Score:
  Detecta anomalías MULTIDIMENSIONALES. Un producto puede tener un precio
  normal, pero si combina precio_alto + precio_por_medida_bajo +
  muchos_dias_sin_cambio, IF lo detecta como raro aunque ninguna
  dimensión individual sea extrema.
"""

import pandas as pd
import logging
import joblib
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
PARTITIONED_DIR = Path("data/processed")
ZSCORE_PATH = Path("data/anomalias/zscore_resultados.parquet")
OUTPUT_PATH = Path("data/anomalias/if_resultados.parquet")
MODEL_PATH = Path("models/isolation_forest.pkl")

# Contamination: fracción esperada de anomalías en el dataset.
# Usamos 0.005 (0.5%) para alinearnos con la tasa observada en Z-Score.
# Esto hace la comparativa más justa: ambos métodos operan con la
# misma "sensibilidad esperada".
CONTAMINATION = 0.005
N_ESTIMATORS = 200  # más árboles = más estable, pero más lento
RANDOM_STATE = 42


# ── Features para Isolation Forest ───────────────────────────────────────────
"""
Selección de features justificada:

precio_actual         → valor absoluto del precio
precio_por_medida     → precio normalizado por unidad (detecta shrinkflation)
variacion_pct         → cambio porcentual respecto al día anterior
dias_sin_cambio       → estabilidad temporal del producto
ratio_vs_media_subcat → cuánto se desvía del precio medio de su subcategoría

El ratio_vs_media_subcat es la feature más potente para IF:
captura si un producto es caro/barato RELATIVO a sus competidores
en la misma categoría, algo que el Z-Score no considera.
"""
FEATURES = [
    "precio_actual",
    "precio_por_medida",
    "variacion_pct",
    "dias_sin_cambio",
    "ratio_vs_media_subcat",
]


# ── Carga y preparación de features ──────────────────────────────────────────
def preparar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye el feature space para Isolation Forest.
    Calcula variacion_pct y dias_sin_cambio a partir de los datos crudos
    del parquet particionado (estas columnas no existen en el dataset).
    """
    # Ordenar para calcular variaciones temporales por producto
    df = df.sort_values(["referencia", "fecha"]).reset_index(drop=True)

    # ── variacion_pct: cambio porcentual del precio respecto al día anterior ──
    df["precio_anterior_calc"] = df.groupby("referencia")["precio_actual"].shift(1)
    df["variacion_pct"] = (
        (df["precio_actual"] - df["precio_anterior_calc"]) / df["precio_anterior_calc"]
    ).round(6)
    df.drop(columns=["precio_anterior_calc"], inplace=True)

    # ── dias_sin_cambio: días consecutivos con el mismo precio ────────────────
    # Marcamos cuando el precio cambia y contamos días desde el último cambio
    df["precio_cambio"] = (
        df.groupby("referencia")["precio_actual"].shift(1) != df["precio_actual"]
    )
    df["grupo_cambio"] = df.groupby("referencia")["precio_cambio"].cumsum()
    df["dias_sin_cambio"] = df.groupby(["referencia", "grupo_cambio"]).cumcount()
    df.drop(columns=["precio_cambio", "grupo_cambio"], inplace=True)

    # Feature derivada: ratio precio vs media de subcategoría en ese día
    # Captura si el producto es outlier DENTRO de su categoría
    media_subcat = df.groupby(["subcategoria", "fecha"], observed=True)[
        "precio_actual"
    ].transform("mean")
    df["ratio_vs_media_subcat"] = (df["precio_actual"] / media_subcat).round(4)

    # Imputar NaN en variacion_pct y dias_sin_cambio
    # (primeras fechas del histórico no tienen precio previo)
    df["variacion_pct"] = df["variacion_pct"].fillna(0.0)
    df["dias_sin_cambio"] = df["dias_sin_cambio"].fillna(df["dias_sin_cambio"].median())

    return df


def cargar_datos() -> pd.DataFrame:
    cols = [
        "referencia",
        "fecha",
        "titulo",
        "categoria",
        "subcategoria",
        "marca_propia",
        "precio_actual",
        "precio_por_medida",
    ]
    df = pd.read_parquet(PARTITIONED_DIR, columns=cols)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = preparar_features(df)

    log.info(f"Datos listos: {len(df):,} filas | features: {FEATURES}")
    return df


# ── Entrenamiento ─────────────────────────────────────────────────────────────
def entrenar_if(df: pd.DataFrame):
    """
    Isolation Forest se entrena sobre TODO el histórico.
    No hay train/test split aquí porque es aprendizaje no supervisado:
    no tenemos etiquetas de verdad de lo que es anomalía.
    El modelo aprende la distribución normal del espacio de features
    y puntúa cada punto según su rareza.
    """
    X = df[FEATURES].values

    # Escalar — IF es relativamente robusto al escalado, pero StandardScaler
    # mejora la interpretabilidad del score y evita que precio_actual
    # (rango 0-50€) domine sobre variacion_pct (rango -1 a 1)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    log.info(
        f"Entrenando Isolation Forest (n_estimators={N_ESTIMATORS}, "
        f"contamination={CONTAMINATION})..."
    )

    modelo = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1,  # usa todos los núcleos disponibles
    )
    modelo.fit(X_scaled)

    # Guardar modelo y scaler para reutilización (producción + memoria)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": modelo, "scaler": scaler, "features": FEATURES}, MODEL_PATH)
    log.info(f"Modelo guardado en {MODEL_PATH}")

    return modelo, scaler, X_scaled


# ── Predicción y scores ───────────────────────────────────────────────────────
def predecir(df: pd.DataFrame, modelo, scaler, X_scaled) -> pd.DataFrame:
    """
    decision_function devuelve el score de anomalía:
      valores negativos  → más anómalo
      valores positivos  → más normal
    Lo invertimos y normalizamos a [0,1] para que sea comparable
    con el error de reconstrucción del Autoencoder.
    """
    raw_scores = modelo.decision_function(X_scaled)

    # Normalización min-max → score_if en [0,1] donde 1 = más anómalo
    score_norm = (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min())
    score_if = 1 - score_norm  # invertir: queremos 1 = anómalo

    # predict() devuelve -1 (anomalía) o 1 (normal)
    predicciones = modelo.predict(X_scaled)

    df["score_if"] = score_if.round(4)
    df["anomalia_if"] = predicciones == -1

    return df


# ── Resumen ───────────────────────────────────────────────────────────────────
def resumir(df: pd.DataFrame) -> None:
    anomalias = df[df["anomalia_if"]]
    total = len(df)

    log.info("─" * 60)
    log.info(f"RESUMEN ISOLATION FOREST (contamination={CONTAMINATION})")
    log.info(f"  Observaciones evaluadas : {total:,}")
    log.info(f"  Anomalías detectadas    : {len(anomalias):,}")
    log.info(f"  Tasa de anomalía        : {len(anomalias) / total * 100:.2f}%")
    log.info(f"  Productos afectados     : {anomalias['referencia'].nunique():,}")
    log.info("")
    log.info("  Top 5 categorías con más anomalías:")
    top_cat = anomalias.groupby("categoria").size().sort_values(ascending=False).head(5)
    for cat, n in top_cat.items():
        log.info(f"    {cat:<35} {n:>5} anomalías")
    log.info("")
    log.info("  Distribución por marca:")
    for marca, n in anomalias["marca_propia"].value_counts().items():
        log.info(f"    {marca:<20} {n:>5}")

    # ── Solapamiento con Z-Score ──────────────────────────────────────────
    # Esta es la métrica más importante para la comparativa de la memoria:
    # ¿detectan los mismos casos o casos distintos?
    if ZSCORE_PATH.exists():
        zs = pd.read_parquet(
            ZSCORE_PATH, columns=["referencia", "fecha", "anomalia_zscore"]
        )
        zs = zs[zs["anomalia_zscore"]]
        zs["key"] = zs["referencia"].astype(str) + "_" + zs["fecha"].astype(str)

        if_anom = df[df["anomalia_if"]].copy()
        if_anom["key"] = (
            if_anom["referencia"].astype(str) + "_" + if_anom["fecha"].astype(str)
        )

        solapamiento = if_anom["key"].isin(zs["key"]).sum()
        solo_if = len(if_anom) - solapamiento
        solo_zs = len(zs) - solapamiento

        log.info("")
        log.info("  Comparativa con Z-Score:")
        log.info(f"    Detectados por ambos  : {solapamiento:,}")
        log.info(f"    Solo por IF           : {solo_if:,}")
        log.info(f"    Solo por Z-Score      : {solo_zs:,}")
        log.info(
            f"    Jaccard similarity    : "
            f"{solapamiento / (len(if_anom) + len(zs) - solapamiento):.3f}"
        )

    log.info("─" * 60)


# ── Guardar resultados ────────────────────────────────────────────────────────
def guardar(df: pd.DataFrame) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cols_salida = [
        "referencia",
        "titulo",
        "fecha",
        "categoria",
        "subcategoria",
        "marca_propia",
        "precio_actual",
        "precio_por_medida",
        "variacion_pct",
        "dias_sin_cambio",
        "ratio_vs_media_subcat",
        "score_if",
        "anomalia_if",
    ]
    df[cols_salida].to_parquet(OUTPUT_PATH, index=False)
    log.info(f"Resultados guardados en {OUTPUT_PATH}")


# ── Entrypoint ────────────────────────────────────────────────────────────────
def ejecutar():
    df = cargar_datos()
    modelo, scaler, X_scaled = entrenar_if(df)
    df = predecir(df, modelo, scaler, X_scaled)
    resumir(df)
    guardar(df)
    return df


if __name__ == "__main__":
    df_resultado = ejecutar()
