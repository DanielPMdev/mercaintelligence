"""
indexar_equivalencias_es.py
Indexa las equivalencias NLP en un índice separado de Elasticsearch.
Solo indexa top-1 por producto (rank == 1).
Idempotente: borra y recrea el índice en cada ejecución.
"""

import pandas as pd
import logging
from pathlib import Path
from elasticsearch.helpers import bulk
from es_utils import get_es_client, to_native

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

ES_INDEX_EQUIV = "mercadona-equivalencias"
EQUIV_PATH = Path("data/nlp/equivalencias.parquet")

MAPPING = {
    "mappings": {
        "properties": {
            "ref_mp":                   {"type": "long"},
            "titulo_mp":                {"type": "text", "fields": {"raw": {"type": "keyword"}}},
            "marca_mp":                 {"type": "keyword"},
            "precio_mp":                {"type": "float"},
            "precio_medida_mp":         {"type": "float"},
            "unidad_medida_mp":         {"type": "keyword"},
            "ref_com":                  {"type": "long"},
            "titulo_com":               {"type": "text", "fields": {"raw": {"type": "keyword"}}},
            "precio_com":               {"type": "float"},
            "precio_medida_com":        {"type": "float"},
            "unidad_medida_com":        {"type": "keyword"},
            "subcategoria":             {"type": "keyword"},
            "similitud":                {"type": "float"},
            "rank":                     {"type": "integer"},
            "misma_unidad":             {"type": "boolean"},
            "diferencia_precio":        {"type": "float"},
            "diferencia_precio_pct":    {"type": "float"},
            "diferencia_por_medida":    {"type": "float"},
            "diferencia_por_medida_pct":{"type": "float"},
        }
    }
}


# ── ID determinístico ─────────────────────────────────────────────────────────
def generar_equiv_id(ref_mp, ref_com) -> str:
    """ID determinístico {ref_mp}_{ref_com} — evita duplicados al re-ejecutar."""
    return f"{int(ref_mp)}_{int(ref_com)}"


# ── Generador de documentos ───────────────────────────────────────────────────
def generar_docs(df: pd.DataFrame):
    for _, row in df.iterrows():
        doc = row.dropna().to_dict()
        doc = {k: to_native(v) for k, v in doc.items()}
        doc_id = generar_equiv_id(doc["ref_mp"], doc["ref_com"])

        yield {
            "_index": ES_INDEX_EQUIV,
            "_id": doc_id,
            "_source": doc,
        }


# ── Verificación ──────────────────────────────────────────────────────────────
def verificar(es):
    es.indices.refresh(index=ES_INDEX_EQUIV)
    total = es.count(index=ES_INDEX_EQUIV)["count"]
    log.info(f"Verificación: {total:,} equivalencias en '{ES_INDEX_EQUIV}'")


# ── Entrypoint ────────────────────────────────────────────────────────────────
def ejecutar():
    es = get_es_client()

    # Borrar y recrear — dataset estático regenerable
    if es.indices.exists(index=ES_INDEX_EQUIV):
        es.indices.delete(index=ES_INDEX_EQUIV)
        log.info(f"Índice '{ES_INDEX_EQUIV}' borrado (recreación limpia)")

    es.indices.create(index=ES_INDEX_EQUIV, body=MAPPING)
    log.info(f"Índice '{ES_INDEX_EQUIV}' creado con mapping explícito")

    # Cargar y filtrar
    df = pd.read_parquet(EQUIV_PATH)
    df = df[df["rank"] == 1].copy()
    log.info(f"Indexando {len(df):,} equivalencias (top-1 por producto)...")

    exitos, errores = bulk(
        es, generar_docs(df), chunk_size=500, raise_on_error=False
    )
    log.info(f"✅ {exitos:,} equivalencias indexadas | {len(errores)} errores")
    if errores:
        log.warning(f"Primeros errores: {errores[:3]}")

    verificar(es)


if __name__ == "__main__":
    ejecutar()
