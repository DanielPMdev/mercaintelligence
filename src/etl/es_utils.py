# src/etl/es_utils.py

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import logging
import os

log = logging.getLogger(__name__)

ES_INDEX = "mercadona-precios"


# ── Helpers ────────────────────────────────────────────────────────────────
def to_native(val):
    """Convierte tipos numpy/pandas a tipos nativos de Python para serialización."""
    if hasattr(val, "item"):
        return val.item()
    return val


def generar_doc_id(referencia, fecha_str: str) -> str:
    """ID determinístico {referencia}_{fecha} para evitar duplicados en ES."""
    return f"{int(referencia)}_{fecha_str[:10]}"


# ── Cliente ────────────────────────────────────────────────────────────────
def get_es_client():
    host = os.getenv("ES_HOST", "http://localhost:9200")
    es = Elasticsearch(host)
    if not es.ping():
        raise ConnectionError(f"Elasticsearch no disponible en {host}")
    return es


# ── Mapping ────────────────────────────────────────────────────────────────
MAPPING = {
    "mappings": {
        "properties": {
            "fecha":              {"type": "date"},
            "timestamp":          {"type": "date"},
            "referencia":         {"type": "long"},
            "categoria":          {"type": "keyword"},
            "subcategoria":       {"type": "keyword"},
            "titulo":             {"type": "text", "fields": {"raw": {"type": "keyword"}}},
            "marca_propia":       {"type": "keyword"},
            "es_marca_propia":    {"type": "boolean"},
            "precio_actual":      {"type": "float"},
            "precio_anterior":    {"type": "float"},
            "precio_por_medida":  {"type": "float"},
            "unidad_medida":      {"type": "keyword"},
            "variacion_pct":      {"type": "float"},
            "dias_sin_cambio":    {"type": "integer"},
            "tiene_precio_anterior": {"type": "boolean"},
        }
    }
}


# ── Crear índice ───────────────────────────────────────────────────────────
def crear_indice(es):
    if es.indices.exists(index=ES_INDEX):
        log.info(f"Índice '{ES_INDEX}' ya existe — omitiendo creación")
        return

    es.indices.create(index=ES_INDEX, body=MAPPING)
    log.info(f"Índice '{ES_INDEX}' creado con mapping explícito")


# ── Generador de documentos (con _id determinístico) ────────────────────────
def generar_docs(df):
    for _, row in df.iterrows():
        doc = row.dropna().to_dict()

        # Convertir numpy types a nativos de Python
        doc = {k: to_native(v) for k, v in doc.items()}

        # Fechas → ISO
        for campo in ["fecha", "timestamp"]:
            if campo in doc and hasattr(doc[campo], "isoformat"):
                doc[campo] = doc[campo].isoformat()

        # ⚠️ ID determinístico → evita duplicados
        doc_id = generar_doc_id(doc.get("referencia"), doc.get("fecha"))

        yield {
            "_index": ES_INDEX,
            "_id": doc_id,
            "op_type": "index",
            "_source": doc
        }


# ── Bulk index ─────────────────────────────────────────────────────────────
def bulk_index(es, df, chunk_size=500):
    if df.empty:
        log.warning("DataFrame vacío — no se indexa nada")
        return

    exitos, errores = bulk(
        es,
        generar_docs(df),
        chunk_size=chunk_size,
        raise_on_error=False
    )

    log.info(f"Elasticsearch → {exitos:,} docs indexados, {len(errores)} errores")