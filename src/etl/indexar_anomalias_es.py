"""
indexar_anomalias_es.py

Indexa los scores de anomalía de los 3 métodos en Elasticsearch.
Enriquece los documentos existentes (referencia + fecha) con los scores,
sin duplicar datos — usa update con doc_as_upsert.

Ejecutar una vez tras completar el Sprint 2.
En producción, se puede integrar al final de cada pipeline de anomalías.
"""

import pandas as pd
import logging
from pathlib import Path
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from es_utils import get_es_client, ES_INDEX, to_native, generar_doc_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

ZSCORE_PATH = Path("data/anomalias/zscore_resultados.parquet")
IF_PATH = Path("data/anomalias/if_resultados.parquet")
AE_PATH = Path("data/anomalias/ae_resultados.parquet")


# ── Generador de updates ───────────────────────────────────────────────────────
def generar_updates(df: pd.DataFrame, campos: list[str]):
    """
    Genera operaciones _update para enriquecer documentos existentes.
    El _id determinístico {referencia}_{fecha} coincide con el usado
    en indexar_historico_es.py → actualiza el documento correcto.
    update con doc_as_upsert=True: si el doc no existe lo crea,
    si existe solo añade/sobreescribe los campos indicados.
    """
    for _, row in df.iterrows():
        fecha_str = pd.to_datetime(row["fecha"]).strftime("%Y-%m-%d")
        doc_id = generar_doc_id(row["referencia"], fecha_str)

        # Solo los campos de anomalía — no reescribimos precio ni categoría
        doc_fields = {}
        for campo in campos:
            val = row.get(campo)
            if pd.notna(val):
                doc_fields[campo] = (
                    bool(val) if isinstance(val, (bool,)) else to_native(val)
                )

        yield {
            "_op_type": "update",
            "_index": ES_INDEX,
            "_id": doc_id,
            "doc": doc_fields,
            "doc_as_upsert": True,
        }


# ── Indexar cada método ────────────────────────────────────────────────────────
def indexar_metodo(es: Elasticsearch, path: Path, campos: list[str], nombre: str):
    if not path.exists():
        log.warning(f"No encontrado: {path} — omitiendo {nombre}")
        return

    df = pd.read_parquet(path, columns=["referencia", "fecha"] + campos)
    df["fecha"] = pd.to_datetime(df["fecha"])

    log.info(f"Indexando {nombre}: {len(df):,} documentos | campos: {campos}")

    from tqdm import tqdm
    exitos, errores = bulk(
        es,
        tqdm(generar_updates(df, campos), total=len(df), desc=f"Subiendo {nombre}"),
        chunk_size=5000,
        raise_on_error=False,
        request_timeout=60,
    )

    log.info(f"  ✅ {exitos:,} actualizados | {len(errores)} errores")
    if errores:
        log.warning(f"  Primeros errores: {errores[:3]}")


# ── Verificación post-indexación ──────────────────────────────────────────────
def verificar(es: Elasticsearch):
    """
    Comprueba que los campos de anomalía están disponibles en ES.
    Útil para confirmar antes de construir los dashboards.
    """
    es.indices.refresh(index=ES_INDEX)

    # Contar documentos con cada campo de anomalía
    campos_check = ["anomalia_zscore", "anomalia_if", "anomalia_ae"]
    log.info("─" * 55)
    log.info("VERIFICACIÓN EN ELASTICSEARCH")

    for campo in campos_check:
        resp = es.count(index=ES_INDEX, body={"query": {"exists": {"field": campo}}})
        total = resp["count"]

        # Cuántos son True
        resp_true = es.count(index=ES_INDEX, body={"query": {"term": {campo: True}}})
        n_true = resp_true["count"]

        log.info(
            f"  {campo:<22} → {total:>8,} docs con campo | {n_true:>6,} anomalías (True)"
        )

    log.info("─" * 55)


# ── Entrypoint ────────────────────────────────────────────────────────────────
def ejecutar():
    es = get_es_client()
    log.info(f"Conectado a Elasticsearch — índice: {ES_INDEX}")

    # Z-Score: score + flag + métricas estadísticas (útiles para el dashboard)
    indexar_metodo(
        es,
        ZSCORE_PATH,
        campos=["zscore", "anomalia_zscore", "media_local", "std_local"],
        nombre="Z-Score",
    )

    # Isolation Forest: score + flag
    indexar_metodo(
        es, IF_PATH, campos=["score_if", "anomalia_if"], nombre="Isolation Forest"
    )

    # Autoencoder: score + flag + error MSE (para histograma en Kibana)
    indexar_metodo(
        es,
        AE_PATH,
        campos=["score_ae", "error_mse", "anomalia_ae"],
        nombre="Autoencoder LSTM",
    )

    verificar(es)


if __name__ == "__main__":
    ejecutar()
