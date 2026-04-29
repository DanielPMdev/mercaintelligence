# src/etl/es_utils.py

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import logging

log = logging.getLogger(__name__)

ES_INDEX = "mercadona-precios"

# ── Cliente ────────────────────────────────────────────────────────────────
def get_es_client():
    return Elasticsearch("http://localhost:9200")


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

        # Convertir numpy types
        doc = {k: (v.item() if hasattr(v, "item") else v) for k, v in doc.items()}

        # Fechas → ISO
        for campo in ["fecha", "timestamp"]:
            if campo in doc and hasattr(doc[campo], "isoformat"):
                doc[campo] = doc[campo].isoformat()

        # ⚠️ ID determinístico → evita duplicados
        doc_id = f"{doc.get('referencia')}_{doc.get('fecha')[:10]}"

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