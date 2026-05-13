"""
detector_catalogo.py

Detecta productos nuevos y descatalogados comparando snapshots diarios.

Lógica:
  - Producto NUEVO       : referencia cuya primera aparición es POSTERIOR
                            al periodo de quemado (burn-in) de 15 días.
                            Los primeros 15 días se usan para establecer
                            el catálogo base y evitar falsos positivos por
                            cobertura incompleta del scraper.
  - Producto DESCATALOGADO: referencia ausente de los últimos 15 días
                            (ventana de confirmación)

Por qué ventana de 15 días y no comparación día a día:
  El scraper puede fallar un día concreto por caídas de red, mantenimiento
  de Mercadona, o errores puntuales. Con comparación día a día, una
  ausencia de un día se interpretaría como descatalogación — un falso positivo.
  La ventana de 15 días garantiza que solo marcamos como descatalogado
  un producto que lleva un mes completo sin aparecer.

Output:
  data/catalogo/nuevos.parquet         → productos nuevos detectados
  data/catalogo/descatalogados.parquet → productos descatalogados confirmados
  data/catalogo/evolucion_catalogo.parquet → serie temporal del tamaño del catálogo
"""

import pandas as pd
import logging
from pathlib import Path
from elasticsearch.helpers import bulk
from es_utils import get_es_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

PARTITIONED_DIR = Path("data/processed")
OUTPUT_DIR = Path("data/catalogo")
ES_INDEX = "mercadona-catalogo"
VENTANA_CONFIRMACION = 15  # días de ausencia para confirmar descatalogación


# ── Carga ─────────────────────────────────────────────────────────────────────
def cargar_presencias() -> pd.DataFrame:
    """
    Carga referencia + fecha + metadatos de todo el histórico.
    Una fila = un producto en un día = una "presencia".
    """
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
    df["fecha"] = pd.to_datetime(df["fecha"].astype(str))
    df = df.sort_values(["fecha", "referencia"]).reset_index(drop=True)

    log.info(
        f"Presencias cargadas: {len(df):,} | "
        f"Fechas: {df['fecha'].nunique()} | "
        f"Referencias únicas: {df['referencia'].nunique():,}"
    )
    return df


# ── Evolución del catálogo ────────────────────────────────────────────────────
def calcular_evolucion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Serie temporal del tamaño del catálogo por día.
    Útil para detectar días con caída masiva del scraper.
    """
    evolucion = (
        df.groupby("fecha")["referencia"]
        .nunique()
        .reset_index()
        .rename(columns={"referencia": "n_productos"})
    )

    evolucion["variacion_dia"] = evolucion["n_productos"].diff()
    evolucion["variacion_pct"] = (evolucion["n_productos"].pct_change() * 100).round(2)

    log.info(
        f"Tamaño medio del catálogo: {evolucion['n_productos'].mean():.0f} productos/día"
    )
    log.info(
        f"Máximo: {evolucion['n_productos'].max()} | "
        f"Mínimo: {evolucion['n_productos'].min()}"
    )

    return evolucion


# ── Detección de productos nuevos ─────────────────────────────────────────────
def detectar_nuevos(df: pd.DataFrame, evolucion: pd.DataFrame) -> pd.DataFrame:
    """
    Un producto es NUEVO si su primera aparición es posterior al periodo
    de estabilización (burn-in) del catálogo base.

    Por qué periodo de quemado:
      El scraper no captura todos los productos el primer día. Por errores
      de red, paginación incompleta o categorías no cubiertas, algunos
      productos existentes pueden tardar varios días en aparecer por
      primera vez. Sin burn-in, esos productos se marcarían como "nuevos"
      erróneamente (falsos positivos).

      Se usa la estabilización de la variación diaria para detectar
      cuándo el catálogo base ha sido completamente capturado, añadiendo
      un margen de seguridad para el 'long tail' de productos.

    Enriquecemos con el precio de entrada y la categoría para
    analizar a qué precio posiciona Mercadona los productos nuevos.
    """
    primera_fecha_global = df["fecha"].min()

    # Buscamos cuándo el crecimiento diario cae por debajo del 1%
    primer_mes = evolucion.head(30)
    dias_estables = primer_mes[primer_mes['variacion_pct'].abs() < 1.0]

    if not dias_estables.empty:
        primer_dia_estable = dias_estables['fecha'].min()
        corte_burnin = primer_dia_estable + pd.Timedelta(days=5)
        dias_burnin = (corte_burnin - primera_fecha_global).days
    else:
        corte_burnin = primera_fecha_global + pd.Timedelta(days=VENTANA_CONFIRMACION)
        dias_burnin = VENTANA_CONFIRMACION

    log.info(
        f"Periodo de quemado: {primera_fecha_global.date()} → "
        f"{corte_burnin.date()} ({dias_burnin} días)"
    )

    # Primera aparición de cada referencia
    primera_aparicion = (
        df.groupby("referencia")
        .agg(
            primera_fecha=("fecha", "min"),
            titulo=("titulo", "first"),
            categoria=("categoria", "first"),
            subcategoria=("subcategoria", "first"),
            marca_propia=("marca_propia", "first"),
            precio_entrada=("precio_actual", "first"),
            precio_medida_entrada=("precio_por_medida", "first"),
        )
        .reset_index()
    )

    # Nuevo = primera aparición DESPUÉS del periodo de quemado
    nuevos = primera_aparicion[
        primera_aparicion["primera_fecha"] > corte_burnin
    ].copy()

    nuevos["dias_desde_inicio"] = (
        nuevos["primera_fecha"] - primera_fecha_global
    ).dt.days

    nuevos = nuevos.sort_values("primera_fecha")

    # Productos descartados por burn-in (para logging)
    descartados_burnin = len(primera_aparicion[
        (primera_aparicion["primera_fecha"] > primera_fecha_global)
        & (primera_aparicion["primera_fecha"] <= corte_burnin)
    ])

    log.info(f"Productos nuevos detectados: {len(nuevos):,}")
    log.info(f"  Descartados por burn-in    : {descartados_burnin}")
    log.info(
        f"  Primer mes post burn-in    : "
        f"{(nuevos['dias_desde_inicio'] <= dias_burnin + 30).sum()}"
    )
    log.info(
        f"  Resto del período          : "
        f"{(nuevos['dias_desde_inicio'] > dias_burnin + 30).sum()}"
    )

    return nuevos


# ── Detección de descatalogados ───────────────────────────────────────────────
def detectar_descatalogados(df: pd.DataFrame) -> pd.DataFrame:
    """
    Un producto está DESCATALOGADO si su última aparición fue hace
    más de VENTANA_CONFIRMACION días respecto a la fecha más reciente.

    La ventana evita falsos positivos por días de scraper fallido.
    """
    fecha_actual = df["fecha"].max()
    corte = fecha_actual - pd.Timedelta(days=VENTANA_CONFIRMACION)

    ultima_aparicion = (
        df.groupby("referencia")
        .agg(
            ultima_fecha=("fecha", "max"),
            titulo=("titulo", "last"),
            categoria=("categoria", "last"),
            subcategoria=("subcategoria", "last"),
            marca_propia=("marca_propia", "last"),
            precio_salida=("precio_actual", "last"),
            n_dias_activo=("fecha", "nunique"),
        )
        .reset_index()
    )

    descatalogados = ultima_aparicion[ultima_aparicion["ultima_fecha"] < corte].copy()

    descatalogados["dias_desde_ultima"] = (
        fecha_actual - descatalogados["ultima_fecha"]
    ).dt.days

    descatalogados = descatalogados.sort_values("ultima_fecha", ascending=False)

    log.info(f"Productos descatalogados confirmados: {len(descatalogados):,}")
    log.info(
        f"  Desaparecidos hace 30-60 días  : "
        f"{((descatalogados['dias_desde_ultima'] >= 30) & (descatalogados['dias_desde_ultima'] < 60)).sum()}"
    )
    log.info(
        f"  Desaparecidos hace >60 días    : "
        f"{(descatalogados['dias_desde_ultima'] >= 60).sum()}"
    )

    return descatalogados


# ── Análisis de estacionalidad ────────────────────────────────────────────────
def analizar_estacionalidad(nuevos: pd.DataFrame) -> None:
    """
    ¿Cuándo añade Mercadona más productos nuevos?
    Agrupa por mes y categoría para detectar patrones estacionales.
    """
    nuevos["mes"] = nuevos["primera_fecha"].dt.to_period("M").astype(str)

    log.info("Productos nuevos por mes:")
    por_mes = nuevos.groupby("mes").size()
    for mes, n in por_mes.items():
        log.info(f"  {mes}: {n:>4} productos nuevos")

    log.info("\nTop 5 categorías con más productos nuevos:")
    top_cat = nuevos["categoria"].value_counts().head(5)
    for cat, n in top_cat.items():
        log.info(f"  {cat:<35} {n:>4}")

    log.info("\nNuevos de marca propia vs comercial:")
    for marca, n in nuevos["marca_propia"].value_counts().head(5).items():
        log.info(f"  {marca:<20} {n:>4}")


# ── Indexar en Elasticsearch ──────────────────────────────────────────────────
def indexar_en_es(nuevos: pd.DataFrame, descatalogados: pd.DataFrame) -> None:
    """
    Indexa los eventos de catálogo en ES para visualizarlos en Kibana.
    Usa un índice separado 'mercadona-catalogo' con campo tipo 'evento'.
    """
    try:
        es = get_es_client()
    except Exception as e:
        log.warning(f"Elasticsearch no disponible — omitiendo indexación: {e}")
        return

    mapping = {
        "mappings": {
            "properties": {
                "fecha": {"type": "date"},
                "tipo_evento": {"type": "keyword"},  # 'nuevo' | 'descatalogado'
                "referencia": {"type": "long"},
                "titulo": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
                "categoria": {"type": "keyword"},
                "subcategoria": {"type": "keyword"},
                "marca_propia": {"type": "keyword"},
                "precio": {"type": "float"},
            }
        }
    }

    if es.indices.exists(index=ES_INDEX):
        es.indices.delete(index=ES_INDEX)
        log.info(f"Índice '{ES_INDEX}' borrado (recreación limpia)")

    es.indices.create(index=ES_INDEX, body=mapping)
    log.info(f"Índice '{ES_INDEX}' creado con mapping explícito")

    def generar_docs():
        # Productos nuevos
        for _, row in nuevos.iterrows():
            yield {
                "_index": ES_INDEX,
                "_id": f"nuevo_{row['referencia']}",
                "_source": {
                    "fecha": row["primera_fecha"].isoformat(),
                    "tipo_evento": "nuevo",
                    "referencia": int(row["referencia"]),
                    "titulo": row["titulo"],
                    "categoria": row["categoria"],
                    "subcategoria": row["subcategoria"],
                    "marca_propia": row["marca_propia"],
                    "precio": float(row["precio_entrada"]),
                },
            }
        # Productos descatalogados
        for _, row in descatalogados.iterrows():
            yield {
                "_index": ES_INDEX,
                "_id": f"desc_{row['referencia']}",
                "_source": {
                    "fecha": row["ultima_fecha"].isoformat(),
                    "tipo_evento": "descatalogado",
                    "referencia": int(row["referencia"]),
                    "titulo": row["titulo"],
                    "categoria": row["categoria"],
                    "subcategoria": row["subcategoria"],
                    "marca_propia": row["marca_propia"],
                    "precio": float(row["precio_salida"]),
                },
            }

    exitos, errores = bulk(es, generar_docs(), raise_on_error=False)
    log.info(f"ES: {exitos} eventos indexados | {len(errores)} errores")


# ── Guardar ───────────────────────────────────────────────────────────────────
def guardar(evolucion, nuevos, descatalogados):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    evolucion.to_parquet(OUTPUT_DIR / "evolucion_catalogo.parquet", index=False)
    nuevos.to_parquet(OUTPUT_DIR / "nuevos.parquet", index=False)
    descatalogados.to_parquet(OUTPUT_DIR / "descatalogados.parquet", index=False)
    log.info(f"Resultados guardados en {OUTPUT_DIR}")


# ── Entrypoint ────────────────────────────────────────────────────────────────
def ejecutar():
    df = cargar_presencias()
    evolucion = calcular_evolucion(df)
    nuevos = detectar_nuevos(df, evolucion)
    descatalogados = detectar_descatalogados(df)
    analizar_estacionalidad(nuevos)
    guardar(evolucion, nuevos, descatalogados)
    indexar_en_es(nuevos, descatalogados)
    return evolucion, nuevos, descatalogados


if __name__ == "__main__":
    evolucion, nuevos, descatalogados = ejecutar()
