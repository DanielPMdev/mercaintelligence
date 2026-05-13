"""
detector_shrinkflation.py

Detecta shrinkflation: el fabricante mantiene el precio pero reduce
el gramaje, haciendo que el precio_por_medida suba aunque el precio
absoluto no cambie.

Patrón:
  precio_actual   IGUAL (o sube poco)
  precio_por_medida SUBE significativamente
  → El producto tiene menos cantidad por el mismo dinero

Umbrales:
  - precio_actual  : variación < UMBRAL_PRECIO_PCT (5%) → "precio estable"
  - precio_por_medida: variación > UMBRAL_MEDIDA_PCT (8%) → "medida sube"

Por qué 8% para precio_por_medida y no 5%:
  Mercadona puede redondear el precio_por_medida al céntimo, lo que
  introduce ruido de ±2-3% sin cambio real de gramaje. Con 8% nos
  aseguramos de detectar solo cambios reales de formato.

Limitación documentada:
  Mercadona actualiza precio_por_medida automáticamente al cambiar el
  formato. Esto hace la shrinkflation VISIBLE en nuestros datos, pero
  también significa que Mercadona la detectaría internamente antes de
  publicarla. Los casos encontrados pueden ser genuinos o errores de
  etiquetado del scraper — se documentan como hallazgos a investigar.
"""

import pandas as pd
import logging
from elasticsearch.helpers import bulk
from pathlib import Path
from es_utils import get_es_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

PARTITIONED_DIR = Path("data/processed")
OUTPUT_PATH = Path("data/shrinkflation/alertas.parquet")
ES_INDEX = "mercadona-shrinkflation"

UMBRAL_PRECIO_PCT = 5.0  # % máximo de variación de precio para considerarlo "estable"
UMBRAL_MEDIDA_PCT = 8.0  # % mínimo de subida de precio_por_medida para alertar
VENTANA_DIAS = 15  # días de ventana para calcular el cambio


# ── Carga ─────────────────────────────────────────────────────────────────────
def cargar_series() -> pd.DataFrame:
    cols = [
        "referencia",
        "fecha",
        "titulo",
        "categoria",
        "subcategoria",
        "marca_propia",
        "precio_actual",
        "precio_por_medida",
        "unidad_medida",
        "formato",
    ]

    df = pd.read_parquet(PARTITIONED_DIR, columns=cols)
    df["fecha"] = pd.to_datetime(df["fecha"].astype(str))
    df = df.sort_values(["referencia", "fecha"]).reset_index(drop=True)

    # Solo productos con precio_por_medida válido en ambas fechas
    df = df.dropna(subset=["precio_por_medida", "precio_actual"])
    df = df[df["precio_por_medida"] > 0]

    log.info(
        f"Series cargadas: {len(df):,} filas | "
        f"{df['referencia'].nunique():,} productos con precio/medida"
    )
    return df


# ── Detección de shrinkflation ────────────────────────────────────────────────
def detectar_shrinkflation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada producto calcula la variación de precio_actual y
    precio_por_medida entre ventanas de VENTANA_DIAS días.

    Compara el precio de hace VENTANA_DIAS con el precio actual:
      - Si precio_actual varía poco (< UMBRAL_PRECIO_PCT%)
      - Y precio_por_medida sube significativamente (> UMBRAL_MEDIDA_PCT%)
      → Posible shrinkflation
    """
    log.info(
        f"Detectando shrinkflation "
        f"(ventana={VENTANA_DIAS}d, "
        f"precio<{UMBRAL_PRECIO_PCT}%, medida>{UMBRAL_MEDIDA_PCT}%)..."
    )

    alertas = []

    for ref, grupo in df.groupby("referencia"):
        grupo = grupo.sort_values("fecha").reset_index(drop=True)

        if len(grupo) < VENTANA_DIAS:
            continue

        # Para cada fecha, comparar con el valor de hace VENTANA_DIAS
        for i in range(VENTANA_DIAS, len(grupo)):
            fila_actual = grupo.iloc[i]
            fila_anterior = grupo.iloc[i - VENTANA_DIAS]

            precio_act = fila_actual["precio_actual"]
            precio_prev = fila_anterior["precio_actual"]
            medida_act = fila_actual["precio_por_medida"]
            medida_prev = fila_anterior["precio_por_medida"]

            if precio_prev == 0 or medida_prev == 0:
                continue

            var_precio = (precio_act - precio_prev) / precio_prev * 100
            var_medida = (medida_act - medida_prev) / medida_prev * 100

            # Patrón shrinkflation:
            # precio estable (o baja ligeramente) + precio_por_medida sube
            if abs(var_precio) < UMBRAL_PRECIO_PCT and var_medida > UMBRAL_MEDIDA_PCT:
                alertas.append(
                    {
                        "referencia": int(ref),
                        "titulo": fila_actual["titulo"],
                        "categoria": fila_actual["categoria"],
                        "subcategoria": fila_actual["subcategoria"],
                        "marca_propia": fila_actual["marca_propia"],
                        "fecha_anterior": fila_anterior["fecha"],
                        "fecha_actual": fila_actual["fecha"],
                        "precio_anterior": round(float(precio_prev), 4),
                        "precio_actual": round(float(precio_act), 4),
                        "medida_anterior": round(float(medida_prev), 4),
                        "medida_actual": round(float(medida_act), 4),
                        "unidad_medida": fila_actual["unidad_medida"],
                        "formato_anterior": fila_anterior["formato"],
                        "formato_actual": fila_actual["formato"],
                        "var_precio_pct": round(float(var_precio), 2),
                        "var_medida_pct": round(float(var_medida), 2),
                        # Severidad: cuánto más sube la medida que el precio
                        "severidad": round(float(var_medida - var_precio), 2),
                    }
                )

    resultado = pd.DataFrame(alertas)

    if resultado.empty:
        log.info("No se detectaron casos de shrinkflation con los umbrales actuales")
        return resultado

    # Deduplicar: quedarse con la alerta más severa por producto
    resultado = (
        resultado.sort_values("severidad", ascending=False)
        .drop_duplicates(subset=["referencia"], keep="first")
        .reset_index(drop=True)
    )

    return resultado


# ── Resumen ───────────────────────────────────────────────────────────────────
def resumir(df: pd.DataFrame) -> None:
    if df.empty:
        log.info("Sin alertas de shrinkflation")
        return

    log.info("─" * 60)
    log.info("RESUMEN SHRINKFLATION")
    log.info(f"  Alertas únicas (1 por producto) : {len(df):,}")
    log.info(f"  Variación media precio (%)      : {df['var_precio_pct'].mean():+.2f}%")
    log.info(f"  Variación media medida (%)      : {df['var_medida_pct'].mean():+.2f}%")
    log.info(f"  Severidad media                 : {df['severidad'].mean():.2f}")
    log.info("")

    log.info("  Top 5 categorías afectadas:")
    for cat, n in df["categoria"].value_counts().head(5).items():
        log.info(f"    {cat:<35} {n:>4}")

    log.info("")
    log.info("  Por marca:")
    for marca, n in df["marca_propia"].value_counts().items():
        log.info(f"    {marca:<20} {n:>4}")

    log.info("")
    log.info("  Top 10 casos más severos:")
    cols = [
        "titulo",
        "var_precio_pct",
        "var_medida_pct",
        "severidad",
        "formato_anterior",
        "formato_actual",
    ]
    top10 = df.nlargest(10, "severidad")[cols]
    for _, row in top10.iterrows():
        log.info(
            f"    [{row['severidad']:+.1f}] {row['titulo'][:40]:<40} "
            f"precio:{row['var_precio_pct']:+.1f}% "
            f"medida:{row['var_medida_pct']:+.1f}%"
        )
        if row["formato_anterior"] != row["formato_actual"]:
            log.info(
                f"           Formato: '{row['formato_anterior']}' → "
                f"'{row['formato_actual']}'"
            )
    log.info("─" * 60)


# ── Indexar en ES ─────────────────────────────────────────────────────────────
def indexar_en_es(df: pd.DataFrame) -> None:
    if df.empty:
        return

    try:
        es = get_es_client()
    except Exception as e:
        log.warning(f"Elasticsearch no disponible — omitiendo indexación: {e}")
        return

    mapping = {
        "mappings": {
            "properties": {
                "fecha_actual": {"type": "date"},
                "fecha_anterior": {"type": "date"},
                "referencia": {"type": "long"},
                "titulo": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
                "categoria": {"type": "keyword"},
                "subcategoria": {"type": "keyword"},
                "marca_propia": {"type": "keyword"},
                "var_precio_pct": {"type": "float"},
                "var_medida_pct": {"type": "float"},
                "severidad": {"type": "float"},
            }
        }
    }

    if es.indices.exists(index=ES_INDEX):
        es.indices.delete(index=ES_INDEX)
        log.info(f"Índice '{ES_INDEX}' borrado (recreación limpia)")

    es.indices.create(index=ES_INDEX, body=mapping)
    log.info(f"Índice '{ES_INDEX}' creado con mapping explícito")

    def generar_docs(df):
        for _, row in df.iterrows():
            doc = row.dropna().to_dict()
            doc = {k: (v.item() if hasattr(v, "item") else v) for k, v in doc.items()}
            for campo in ["fecha_actual", "fecha_anterior"]:
                if campo in doc and hasattr(doc[campo], "isoformat"):
                    doc[campo] = doc[campo].isoformat()
            yield {
                "_index": ES_INDEX,
                "_id": f"shrink_{doc['referencia']}",
                "_source": doc,
            }

    exitos, errores = bulk(es, generar_docs(df), raise_on_error=False)
    log.info(f"ES: {exitos} alertas indexadas | {len(errores)} errores")


# ── Guardar ───────────────────────────────────────────────────────────────────
def guardar(df: pd.DataFrame) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)
    log.info(f"Alertas guardadas: {OUTPUT_PATH}")


# ── Entrypoint ────────────────────────────────────────────────────────────────
def ejecutar():
    df = cargar_series()
    alertas = detectar_shrinkflation(df)
    resumir(alertas)
    if not alertas.empty:
        guardar(alertas)
        indexar_en_es(alertas)
    return alertas


if __name__ == "__main__":
    alertas = ejecutar()
