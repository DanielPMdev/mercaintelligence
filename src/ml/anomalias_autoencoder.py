"""
anomalias_autoencoder.py

Detección de anomalías mediante Autoencoder LSTM.

Diferencia fundamental respecto a Z-Score e IF:
  - Z-Score: estadístico, univariante, por producto.
  - IF: ML clásico, multivariante, espacio de features estático.
  - Autoencoder: Deep Learning, aprende la ESTRUCTURA TEMPORAL normal
    de las series de precio y detecta anomalías por error de reconstrucción.

Principio:
  El Autoencoder se entrena SOLO con secuencias de días sin cambio de precio
  (comportamiento normal). Aprende a comprimir y reconstruir esas secuencias.
  Cuando se le da una secuencia con un cambio anómalo, no sabe reconstruirla
  bien → el error de reconstrucción (MSE) es alto → anomalía.

Ventaja diferencial:
  Detecta anomalías temporales SUTILES: un producto cuyo precio es normal
  en valor absoluto pero que rompe un patrón de estabilidad prolongada.
  Ni Z-Score ni IF capturan esto con la misma sensibilidad.

Arquitectura:
  Encoder: LSTM(64) → LSTM(32)   [compresión]
  Decoder: RepeatVector → LSTM(32) → LSTM(64) → Dense(n_features)
  Entrenado con MSE sobre secuencias normales (precio sin cambio).
"""

import zipfile
import numpy as np
import pandas as pd
import logging
import joblib
import matplotlib.pyplot as plt
from pathlib import Path

from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, LSTM, Dense, RepeatVector, TimeDistributed

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
PARTITIONED_DIR = Path("data/processed")
ZSCORE_PATH = Path("data/anomalias/zscore_resultados.parquet")
IF_PATH = Path("data/anomalias/if_resultados.parquet")
OUTPUT_PATH = Path("data/anomalias/ae_resultados.parquet")
MODEL_PATH = Path("models/autoencoder_lstm.keras")
UMBRAL_PATH = Path("models/ae_umbral.pkl")
IMG_DIR = Path("docs/img/autoencoder")

IMG_DIR.mkdir(parents=True, exist_ok=True)

VENTANA = 14  # días de secuencia temporal (igual que Z-Score para comparabilidad)
N_FEATURES = 3  # precio_actual_norm, variacion_pct, dias_sin_cambio_norm
MIN_DIAS = 20  # productos con menos días se excluyen del entrenamiento
EPOCHS = 30
BATCH_SIZE = 64
VALIDATION_SPLIT = 0.1
PERCENTIL_UMBRAL_INFERENCIA = (
    99  # Umbral = P99 del error de reconstrucción en TODA la inferencia
)


# ── Preparación de datos ──────────────────────────────────────────────────────
def cargar_y_preparar() -> pd.DataFrame:
    cols = [
        "referencia",
        "fecha",
        "precio_actual",
        "precio_por_medida",
        "categoria",
        "subcategoria",
        "titulo",
        "marca_propia",
    ]

    df = pd.read_parquet(PARTITIONED_DIR, columns=cols)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values(["referencia", "fecha"]).reset_index(drop=True)

    # Calcular features temporales (igual que IF para consistencia)
    df["precio_anterior"] = df.groupby("referencia")["precio_actual"].shift(1)
    df["variacion_pct"] = (
        ((df["precio_actual"] - df["precio_anterior"]) / df["precio_anterior"])
        .fillna(0.0)
        .round(6)
    )

    df["precio_cambio"] = (
        df.groupby("referencia")["precio_actual"].shift(1) != df["precio_actual"]
    )
    df["grupo_cambio"] = df.groupby("referencia")["precio_cambio"].cumsum()
    df["dias_sin_cambio"] = df.groupby(["referencia", "grupo_cambio"]).cumcount()
    df = df.drop(columns=["precio_anterior", "precio_cambio", "grupo_cambio"])

    log.info(
        f"Datos cargados: {len(df):,} filas | {df['referencia'].nunique():,} productos"
    )
    return df


def normalizar_por_producto(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalización min-max POR PRODUCTO para que el autoencoder aprenda
    patrones de forma, no de escala absoluta.
    Un pan de 1€ y un jamón de 50€ deben tener la misma escala interna.
    """
    for col in ["precio_actual", "dias_sin_cambio"]:
        min_val = df.groupby("referencia")[col].transform("min")
        max_val = df.groupby("referencia")[col].transform("max")
        rango = (max_val - min_val).replace(0, 1)  # evitar división por cero
        df[f"{col}_norm"] = ((df[col] - min_val) / rango).round(6)

    return df


def construir_secuencias(df: pd.DataFrame, solo_normales: bool = False):
    """
    Convierte series temporales por producto en ventanas deslizantes.

    Parámetro solo_normales:
      True  → solo secuencias sin cambio de precio (para entrenamiento)
      False → todas las secuencias (para inferencia/detección)

    Retorna:
      X       : array (n_secuencias, VENTANA, N_FEATURES)
      meta    : lista de (referencia, fecha_fin) para reconstruir qué producto/día
    """
    features = ["precio_actual_norm", "variacion_pct", "dias_sin_cambio_norm"]
    X, meta = [], []

    productos = df.groupby("referencia")

    for ref, grupo in productos:
        grupo = grupo.sort_values("fecha").reset_index(drop=True)

        # Filtrar productos con suficientes días
        if len(grupo) < MIN_DIAS:
            continue

        vals = grupo[features].values

        for i in range(VENTANA, len(grupo)):
            secuencia = vals[i - VENTANA : i]

            if solo_normales:
                # Solo incluir secuencias donde NINGÚN día tuvo cambio de precio
                # (variacion_pct == 0 para toda la ventana)
                if np.any(secuencia[:, 1] != 0):
                    continue

            X.append(secuencia)
            meta.append((ref, grupo["fecha"].iloc[i]))

    return np.array(X, dtype=np.float32), meta


# ── Arquitectura del Autoencoder LSTM ────────────────────────────────────────
def construir_modelo(ventana: int, n_features: int):
    """
    Autoencoder LSTM para series temporales.

    Encoder:
      LSTM(64, return_sequences=True) → captura dependencias locales
      LSTM(32, return_sequences=False) → representación comprimida (bottleneck)

    Bottleneck → RepeatVector(ventana):
      Expande el vector comprimido para que el decoder pueda reconstruir
      la secuencia completa. Este es el cuello de botella que fuerza
      al modelo a aprender representaciones compactas de lo "normal".

    Decoder:
      LSTM(32, return_sequences=True) → reconstruye secuencia comprimida
      LSTM(64, return_sequences=True) → expande a resolución original
      TimeDistributed(Dense(n_features)) → reconstruye cada paso temporal
    """

    inputs = Input(shape=(ventana, n_features), name="input_secuencia")

    # Encoder
    x = LSTM(64, return_sequences=True, name="encoder_lstm1")(inputs)
    x = LSTM(32, return_sequences=False, name="encoder_lstm2")(x)

    # Bottleneck → expansión para decoder
    x = RepeatVector(ventana, name="bottleneck")(x)

    # Decoder
    x = LSTM(32, return_sequences=True, name="decoder_lstm1")(x)
    x = LSTM(64, return_sequences=True, name="decoder_lstm2")(x)
    outputs = TimeDistributed(Dense(n_features), name="output")(x)

    modelo = Model(inputs, outputs, name="autoencoder_lstm")
    modelo.compile(optimizer="adam", loss="mse")
    return modelo


# ── Entrenamiento ─────────────────────────────────────────────────────────────
def entrenar(X_train: np.ndarray) -> tuple:
    """
    El autoencoder se entrena con X_train como entrada Y como salida.
    Objetivo: reconstruir la secuencia de entrada lo más fielmente posible.
    La pérdida es MSE entre secuencia original y reconstruida.
    """
    log.info(f"Secuencias de entrenamiento (normales): {len(X_train):,}")
    log.info(
        f"Shape: {X_train.shape}  →  (n_secuencias, {VENTANA} días, {N_FEATURES} features)"
    )

    modelo = construir_modelo(VENTANA, N_FEATURES)
    modelo.summary(print_fn=log.info)

    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

    callbacks = [
        EarlyStopping(
            monitor="val_loss",
            patience=5,  # para si no mejora en 5 épocas consecutivas
            restore_best_weights=True,
            verbose=1,
        ),
        ModelCheckpoint(MODEL_PATH, save_best_only=True, verbose=0),
    ]

    history = modelo.fit(
        X_train,
        X_train,  # entrada = salida (autoencoder)
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_split=VALIDATION_SPLIT,
        callbacks=callbacks,
        verbose=1,
    )

    log.info(f"Modelo guardado en {MODEL_PATH}")
    return modelo, history


def guardar_graficas_entrenamiento(history, X_train, modelo):
    """Genera y guarda las gráficas de entrenamiento y distribución de error."""
    # 1. Curvas de pérdida
    plt.figure(figsize=(10, 5))
    plt.plot(history.history["loss"], label="Train Loss")
    plt.plot(history.history["val_loss"], label="Val Loss")
    plt.title("Curvas de entrenamiento - Autoencoder LSTM")
    plt.xlabel("Época")
    plt.ylabel("MSE")
    plt.legend()
    plt.grid(True, alpha=0.3)
    caption_loss = "Explicación: El gráfico de curvas de entrenamiento muestra la pérdida (MSE) en el conjunto de entrenamiento (azul) y de validación (naranja) a lo largo de las épocas. Una convergencia suave sin divergencia indica un aprendizaje estable y la ausencia de sobreajuste (overfitting)."
    plt.figtext(
        0.5,
        0.01,
        caption_loss,
        wrap=True,
        horizontalalignment="center",
        fontsize=9,
        style="italic",
        color="#555555",
    )
    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    plt.savefig(IMG_DIR / "ae_training_curves_local.png", dpi=150)
    plt.close()

    # 2. Distribución del error
    X_pred_train = modelo.predict(X_train, verbose=0)
    errores_train = np.mean(np.square(X_train - X_pred_train), axis=(1, 2))

    plt.figure(figsize=(10, 5))
    plt.hist(errores_train, bins=100, alpha=0.7, color="steelblue")
    plt.title("Distribución del error de reconstrucción (Train)")
    plt.xlabel("MSE")
    plt.ylabel("Frecuencia")
    plt.grid(True, alpha=0.3)
    caption_err = "Explicación: Distribución del error de reconstrucción (MSE) para los datos de entrenamiento. La gran mayoría de los productos normales muestran un error bajo y concentrado a la izquierda. La cola derecha representa reconstrucciones imprecisas, que sirven de base para estimar el umbral de anomalías."
    plt.figtext(
        0.5,
        0.01,
        caption_err,
        wrap=True,
        horizontalalignment="center",
        fontsize=9,
        style="italic",
        color="#555555",
    )
    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    plt.savefig(IMG_DIR / "ae_error_distribution_local.png", dpi=150)
    plt.close()
    log.info(f"Gráficas de entrenamiento guardadas en {IMG_DIR}")


# ── Detección en todo el histórico ───────────────────────────────────────────
def detectar_anomalias(df: pd.DataFrame, modelo: Model, umbral: float) -> pd.DataFrame:
    """
    Aplica el modelo sobre TODAS las secuencias (normales y anómalas).
    Calcula el error de reconstrucción y lo compara con el umbral.
    """
    log.info("Construyendo secuencias para inferencia (todas)...")
    X_all, meta = construir_secuencias(df, solo_normales=False)
    log.info(f"Secuencias totales para inferencia: {len(X_all):,}")

    X_pred = modelo.predict(X_all, batch_size=256, verbose=1)
    errores = np.mean(np.square(X_all - X_pred), axis=(1, 2))

    if umbral is None:
        umbral = float(np.percentile(errores, PERCENTIL_UMBRAL_INFERENCIA))
        umbral_data = {
            "umbral": umbral,
            "metodo": f"percentil_{PERCENTIL_UMBRAL_INFERENCIA}_inferencia",
        }
        joblib.dump(umbral_data, UMBRAL_PATH)
        log.info(
            f"Umbral (P{PERCENTIL_UMBRAL_INFERENCIA}) calculado y guardado en {UMBRAL_PATH}"
        )

    # Normalizar error a [0,1] para comparabilidad con score_if
    rango_err = errores.max() - errores.min()
    if rango_err > 0:
        score_ae = (errores - errores.min()) / rango_err
    else:
        score_ae = np.zeros_like(errores)

    log.info("Distribución error inferencia:")
    log.info(f"  Media: {errores.mean():.10f} | Std: {errores.std():.10f}")
    log.info(f"  Min: {errores.min():.10f} | Max: {errores.max():.10f}")
    log.info(f"  Umbral aplicado: {umbral:.10f}")

    resultados = pd.DataFrame(meta, columns=["referencia", "fecha"])
    resultados["score_ae"] = score_ae.round(4)
    resultados["error_mse"] = errores.round(10)
    resultados["anomalia_ae"] = errores > umbral

    n_anom = resultados["anomalia_ae"].sum()
    log.info(
        f"  Anomalías detectadas: {n_anom:,} / {len(resultados):,} ({n_anom / len(resultados) * 100:.2f}%)"
    )

    return resultados


# ── Merge con datos originales ────────────────────────────────────────────────
def enriquecer_resultados(df: pd.DataFrame, resultados: pd.DataFrame) -> pd.DataFrame:
    """Une los scores con los metadatos del producto."""
    meta_cols = [
        "referencia",
        "fecha",
        "titulo",
        "categoria",
        "subcategoria",
        "marca_propia",
        "precio_actual",
    ]

    df_meta = df[meta_cols].copy()
    df_meta["fecha"] = pd.to_datetime(df_meta["fecha"].astype(str))
    resultados["fecha"] = pd.to_datetime(resultados["fecha"])

    return resultados.merge(df_meta, on=["referencia", "fecha"], how="left")


# ── Resumen con comparativa de los 3 métodos ─────────────────────────────────
def resumir(df_resultado: pd.DataFrame) -> None:
    anomalias = df_resultado[df_resultado["anomalia_ae"]]
    total = len(df_resultado)

    log.info("─" * 60)
    log.info(f"RESUMEN AUTOENCODER LSTM (ventana={VENTANA}d)")
    log.info(f"  Secuencias evaluadas    : {total:,}")
    log.info(f"  Anomalías detectadas    : {len(anomalias):,}")
    log.info(f"  Tasa de anomalía        : {len(anomalias) / total * 100:.2f}%")
    log.info(f"  Productos afectados     : {anomalias['referencia'].nunique():,}")
    log.info("")
    log.info("  Top 5 categorías:")
    top = anomalias.groupby("categoria").size().sort_values(ascending=False).head(5)
    for cat, n in top.items():
        log.info(f"    {cat:<35} {n:>5}")
    log.info("")
    log.info("  Por marca:")
    for marca, n in anomalias["marca_propia"].value_counts().items():
        log.info(f"    {marca:<20} {n:>5}")

    # Comparativa con Z-Score e IF
    def cargar_keys(path, col):
        d = pd.read_parquet(path, columns=["referencia", "fecha", col])
        d = d[d[col]]
        return set(d["referencia"].astype(str) + "_" + d["fecha"].astype(str))

    ae_keys = set(
        anomalias["referencia"].astype(str) + "_" + anomalias["fecha"].astype(str)
    )

    if ZSCORE_PATH.exists():
        zs_keys = cargar_keys(ZSCORE_PATH, "anomalia_zscore")
        solap_zs = len(ae_keys & zs_keys)
        jaccard_zs = solap_zs / len(ae_keys | zs_keys) if ae_keys | zs_keys else 0
        log.info(
            f"\n  Solapamiento AE vs Z-Score : {solap_zs} casos | Jaccard={jaccard_zs:.3f}"
        )

    if IF_PATH.exists():
        if_keys = cargar_keys(IF_PATH, "anomalia_if")
        solap_if = len(ae_keys & if_keys)
        jaccard_if = solap_if / len(ae_keys | if_keys) if ae_keys | if_keys else 0
        log.info(
            f"  Solapamiento AE vs IF      : {solap_if} casos | Jaccard={jaccard_if:.3f}"
        )

    log.info("─" * 60)


# ── Guardar resultados ────────────────────────────────────────────────────────
def guardar(df: pd.DataFrame) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)
    log.info(f"Resultados guardados en {OUTPUT_PATH}")


# ── Cargar modelo pre-entrenado ───────────────────────────────────────────────
def _es_keras_valido(ruta: Path) -> bool:
    """
    Comprueba que el fichero .keras es un ZIP real y no un puntero LFS.
    Un puntero LFS es un fichero de texto de ~130 bytes que no puede
    abrirse como ZIP. Intentar cargarlo con load_model() lanza un ValueError
    que corrompe el estado interno de TensorFlow, causando un segfault en
    los módulos que se importen a continuación (ej. sentence-transformers).
    """
    try:
        with zipfile.ZipFile(ruta, "r") as _:
            return True
    except (zipfile.BadZipFile, OSError):
        return False


def cargar_modelo_pretrained() -> tuple:
    """
    Carga un modelo ya entrenado (ej. desde Google Colab) y su umbral.
    Devuelve (modelo, umbral) o (None, None) si no existen o el fichero
    no es un .keras válido (ej. puntero LFS sin Git LFS instalado).

    Compatible con ambos formatos de umbral:
      - dict con {umbral, mean, std, n_sigmas} (nuevo formato)
      - float simple (formato legacy)
    """
    from tensorflow.keras.models import load_model  # import diferido: solo si se usa

    if MODEL_PATH.exists() and UMBRAL_PATH.exists():
        if not _es_keras_valido(MODEL_PATH):
            log.warning(
                f"   {MODEL_PATH} existe pero no es un ZIP .keras válido "
                "(¿puntero LFS sin descargar?). Se re-entrenará el modelo."
            )
            return None, None

        log.info(f"Modelo pre-entrenado encontrado: {MODEL_PATH}")
        modelo = load_model(MODEL_PATH)
        umbral_data = joblib.load(UMBRAL_PATH)

        # Compatibilidad con formato antiguo (float) y nuevo (dict)
        if isinstance(umbral_data, dict):
            umbral = umbral_data["umbral"]
            metodo = umbral_data.get(
                "metodo", f"mean+{umbral_data.get('n_sigmas', '?')}σ"
            )
            log.info(f"Umbral cargado ({metodo}): {umbral:.10f}")
            if "mean" in umbral_data and "std" in umbral_data:
                log.info(
                    f"  Media: {umbral_data['mean']:.10f} | Std: {umbral_data['std']:.10f}"
                )
        else:
            umbral = float(umbral_data)
            log.info(f"Umbral cargado (legacy): {umbral:.10f}")

        return modelo, umbral
    return None, None


# ── Entrypoint ────────────────────────────────────────────────────────────────
def ejecutar():
    df = cargar_y_preparar()
    df = normalizar_por_producto(df)

    # Intentar cargar modelo pre-entrenado (ej. entrenado en Google Colab)
    modelo, umbral = cargar_modelo_pretrained()

    if modelo is not None:
        log.info("Usando modelo pre-entrenado → solo inferencia (sin GPU)")
    else:
        log.info("No se encontró modelo pre-entrenado → entrenamiento completo")
        log.info("Construyendo secuencias normales para entrenamiento...")
        X_train, _ = construir_secuencias(df, solo_normales=True)
        modelo, history = entrenar(X_train)
        guardar_graficas_entrenamiento(history, X_train, modelo)
        umbral = None  # Se calculará dinámicamente durante la inferencia

    resultados = detectar_anomalias(df, modelo, umbral)
    resultados = enriquecer_resultados(df, resultados)

    resumir(resultados)
    guardar(resultados)
    return resultados


if __name__ == "__main__":
    df_resultado = ejecutar()
