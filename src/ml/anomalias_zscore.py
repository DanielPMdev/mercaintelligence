"""
anomalias_zscore.py

Detección de anomalías de precio mediante Z-Score rolling.
Actúa como BASELINE estadístico — punto de referencia para comparar
con Isolation Forest y Autoencoder.

Lógica:
  Para cada producto (referencia), se calcula la media y desviación típica
  de su precio en una ventana deslizante de N días anteriores.
  Un precio es anómalo si se aleja más de `umbral` desviaciones típicas
  de esa media local.

  z = (precio_actual - media_ventana) / std_ventana

  |z| > umbral  →  anomalía

Por qué rolling y no global:
  Un precio global de 2.50€ puede ser normal en noviembre y anómalo en abril
  si hubo inflación. La ventana deslizante captura el contexto temporal local,
  lo que lo hace mucho más robusto que el Z-Score estático.
"""

import pandas as pd
import numpy as np
import logging
import matplotlib.pyplot as plt
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
PARTITIONED_DIR = Path("data/processed")
OUTPUT_PATH = Path("data/anomalias/zscore_resultados.parquet")
IMG_DIR = Path("docs/img/zscore")

IMG_DIR.mkdir(parents=True, exist_ok=True)

VENTANA_DIAS = 14  # días de contexto para calcular media/std local
UMBRAL_Z = 2.5  # número de desviaciones típicas para considerar anomalía
# 2.5 es más selectivo que el clásico 2.0:
# reduce falsos positivos en series de precios con poca varianza


# ── Carga de datos ────────────────────────────────────────────────────────────
def cargar_series() -> pd.DataFrame:
    """
    Carga solo las columnas necesarias para el análisis de anomalías.
    El filtrado de columnas en read_parquet evita cargar en RAM campos
    irrelevantes (url, imágenes, etc.) — partition pruning + column pruning.
    """
    cols = [
        "referencia",
        "fecha",
        "precio_actual",
        "categoria",
        "subcategoria",
        "titulo",
        "marca_propia",
        "precio_por_medida",
    ]

    df = pd.read_parquet(PARTITIONED_DIR, columns=cols)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values(["referencia", "fecha"]).reset_index(drop=True)

    log.info(
        f"Datos cargados: {len(df):,} filas | {df['referencia'].nunique():,} productos | "
        f"{df['fecha'].nunique()} fechas"
    )
    return df


# ── Z-Score rolling por producto ──────────────────────────────────────────────
def calcular_zscore_rolling(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica Z-Score rolling a cada producto de forma independiente.

    Pasos por grupo (referencia):
      1. Ordenar por fecha (ya viene ordenado, pero se garantiza)
      2. Calcular media y std en ventana deslizante de VENTANA_DIAS
      3. Calcular z = (precio - media) / std
      4. Marcar como anomalía si |z| > UMBRAL_Z

    min_periods=5: necesita al menos 5 observaciones para calcular
    estadísticos fiables. Los primeros días quedan como NaN → no se
    etiquetan como anomalía (conservador por defecto).
    """
    log.info(
        f"Calculando Z-Score rolling (ventana={VENTANA_DIAS} días, umbral={UMBRAL_Z})..."
    )

    def zscore_grupo(grupo: pd.DataFrame) -> pd.DataFrame:
        precio = grupo["precio_actual"]

        # Media y std de la ventana anterior (closed='left' excluye el día actual
        # para evitar que el propio valor influya en su propio score)
        media_rolling = (
            precio.rolling(
                window=VENTANA_DIAS,
                min_periods=5,
            )
            .mean()
            .shift(1)
        )  # shift(1): la ventana termina en t-1, no en t

        std_rolling = (
            precio.rolling(
                window=VENTANA_DIAS,
                min_periods=5,
            )
            .std()
            .shift(1)
        )

        # Z-Score: cuántas desviaciones típicas se aleja del contexto local
        # Donde std=0 (precio constante mucho tiempo) → z=0, nunca anomalía
        z = (precio - media_rolling) / std_rolling.replace(0, np.nan)

        grupo["zscore"] = z.round(4)
        grupo["media_local"] = media_rolling.round(4)
        grupo["std_local"] = std_rolling.round(4)
        grupo["anomalia_zscore"] = z.abs() > UMBRAL_Z

        return grupo

    # apply por grupo — el más costoso computacionalmente de los 3 métodos
    # pero el más interpretable: puedes explicar cada anomalía con un número
    resultado = df.groupby("referencia", group_keys=False)[df.columns].apply(
        zscore_grupo
    )

    return resultado


# ── Resumen de anomalías detectadas ──────────────────────────────────────────
def resumir_anomalias(df: pd.DataFrame) -> None:
    """Imprime estadísticas clave para la sección de Evaluación de la memoria."""

    anomalias = df[df["anomalia_zscore"]]
    total = df["anomalia_zscore"].notna().sum()  # excluye NaN (primeros días)

    log.info("─" * 60)
    log.info(f"RESUMEN Z-SCORE (ventana={VENTANA_DIAS}d, umbral={UMBRAL_Z}σ)")
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
    log.info("─" * 60)


def generar_visualizaciones(df: pd.DataFrame) -> None:
    """Genera gráficas diagnósticas de los Z-Scores."""
    # 1. Histograma de Z-Scores
    plt.figure(figsize=(10, 5))
    plt.hist(df["zscore"].dropna(), bins=100, color="steelblue", alpha=0.7, edgecolor="white")
    plt.axvline(UMBRAL_Z, color="red", linestyle="--", label=f"Umbral +{UMBRAL_Z}σ")
    plt.axvline(-UMBRAL_Z, color="red", linestyle="--", label=f"Umbral -{UMBRAL_Z}σ")
    plt.title("Distribución de Z-Scores (Desviaciones Típicas)")
    plt.xlabel("Z-Score")
    plt.ylabel("Frecuencia")
    plt.legend()
    plt.grid(True, alpha=0.3)
    caption_dist = "Explicación: Distribución empírica del rolling Z-Score de las variaciones de precios. El umbral establecido en ±2.5 desviaciones típicas (líneas discontinuas rojas) enmarca el comportamiento estadístico habitual; los valores extremos fuera de esta región se clasifican como anomalías Z-Score."
    plt.figtext(0.5, 0.01, caption_dist, wrap=True, horizontalalignment='center', fontsize=9, style='italic', color='#555555')
    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    plt.savefig(IMG_DIR / "zscore_distribucion.png", dpi=150)
    plt.close()
 
    # 2. Ejemplo de serie temporal con anomalía (el producto con mayor desviación)
    top_anom = df.loc[df["zscore"].abs().idxmax()]
    ref_ejemplo = top_anom["referencia"]
    df_ejemplo = df[df["referencia"] == ref_ejemplo].sort_values("fecha")
 
    plt.figure(figsize=(12, 6))
    plt.plot(df_ejemplo["fecha"], df_ejemplo["precio_actual"], marker="o", label="Precio Real")
    anomalias_ej = df_ejemplo[df_ejemplo["anomalia_zscore"]]
    plt.scatter(anomalias_ej["fecha"], anomalias_ej["precio_actual"], color="red", s=100, label="Anomalía Detectada", zorder=5)
     
    plt.title(f"Serie Temporal: {df_ejemplo['titulo'].iloc[0]} (Ref: {ref_ejemplo})")
    plt.xlabel("Fecha")
    plt.ylabel("Precio (€)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    caption_ej = "Explicación: Ejemplo visual del rolling Z-Score sobre una serie temporal real de precios. El gráfico muestra cómo el score dinámico detecta de forma efectiva el cambio repentino en la serie temporal y resalta las anomalías con círculos rojos en los puntos de precio real."
    plt.figtext(0.5, 0.01, caption_ej, wrap=True, horizontalalignment='center', fontsize=9, style='italic', color='#555555')
    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    plt.savefig(IMG_DIR / "zscore_ejemplo_anomalia.png", dpi=150)
    plt.close()
    
    log.info(f"Gráficas guardadas en {IMG_DIR}")


# ── Guardar resultados ────────────────────────────────────────────────────────
def guardar_resultados(df: pd.DataFrame) -> None:
    """
    Guarda SOLO las filas marcadas como anomalía + columnas relevantes.
    El dataset completo con zscore se puede regenerar; lo que importa
    es tener las anomalías detectadas disponibles para:
      - Comparativa con IF y Autoencoder
      - Indexación en Elasticsearch (dashboard de alertas)
    """
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    cols_salida = [
        "referencia",
        "titulo",
        "fecha",
        "categoria",
        "subcategoria",
        "marca_propia",
        "precio_actual",
        "media_local",
        "std_local",
        "zscore",
        "anomalia_zscore",
    ]

    # Guardamos todas las filas evaluadas (no solo anomalías) para poder
    # calcular precision/recall en la comparativa final
    df[cols_salida].to_parquet(OUTPUT_PATH, index=False)
    log.info(f"Resultados guardados en {OUTPUT_PATH}")


# ── Entrypoint ────────────────────────────────────────────────────────────────
def ejecutar():
    df = cargar_series()
    df = calcular_zscore_rolling(df)
    resumir_anomalias(df)
    generar_visualizaciones(df)
    guardar_resultados(df)
    return df  # lo devuelve para usarlo en el notebook de comparativa


if __name__ == "__main__":
    df_resultado = ejecutar()
