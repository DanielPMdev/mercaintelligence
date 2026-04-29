# src/etl/indexar_historico_es.py

import pandas as pd
import logging
from es_utils import get_es_client, crear_indice, bulk_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)


PARTITIONED_DIR = "data/processed"


def indexar():
    es = get_es_client()

    crear_indice(es)

    df = pd.read_parquet(PARTITIONED_DIR)
    log.info(f"Indexando histórico: {len(df):,} documentos...")

    bulk_index(es, df)


if __name__ == "__main__":
    indexar()