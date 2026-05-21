# src/etl/ingest.py
"""
Script maestro de ingesta / indexación para Elasticsearch.
Ejecuta de forma secuencial todos los sub-scripts de indexación de MercaIntelligence:
1. Histórico de precios
2. Enriquecimiento con anomalías (Z-Score, Isolation Forest, Autoencoder)
3. Equivalencias NLP
4. Histórico del IPC de cestas predefinidas (requiere que la API esté corriendo)
"""

import sys
from pathlib import Path
import logging
import time

# Importar funciones de los sub-scripts
from es_utils import get_es_client
import indexar_historico_es
import indexar_anomalias_es
import indexar_equivalencias_es
import indexar_ipc_es

# Configurar logging descriptivo y estético
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("ingesta_maestra")

# Silenciar logs HTTP ruidosos del cliente de Elasticsearch
logging.getLogger("elastic_transport").setLevel(logging.WARNING)

# Asegurar que el path de ejecución incluya src/etl
curr_dir = Path(__file__).parent.resolve()
if str(curr_dir) not in sys.path:
    sys.path.insert(0, str(curr_dir))


def main():
    log.info("🚀 INICIANDO PIPELINE MAESTRO DE INGESTIÓN EN ELASTICSEARCH")
    log.info("=" * 65)

    # 0. Verificar conexión con Elasticsearch
    try:
        get_es_client()
        log.info("✅ Conexión establecida correctamente con Elasticsearch.")
    except Exception as e:
        log.critical(
            "❌ No se puede conectar a Elasticsearch. Asegúrate de que el contenedor Docker "
            f"está corriendo y es accesible. Error: {e}"
        )
        sys.exit(1)

    start_time = time.time()

    # 1. Indexar Histórico de Precios
    log.info("\n➡️ [1/4] Paso 1: Indexando catálogo histórico de precios...")
    try:
        indexar_historico_es.indexar()
        log.info("✅ Paso 1 completado.")
    except Exception as e:
        log.error(f"❌ Error en Paso 1 (Histórico): {e}")

    # 2. Indexar Scores de Anomalías
    log.info("\n➡️ [2/4] Paso 2: Enriqueciendo catálogo con scores de anomalías...")
    try:
        indexar_anomalias_es.ejecutar()
        log.info("✅ Paso 2 completado.")
    except Exception as e:
        log.error(f"❌ Error en Paso 2 (Anomalías): {e}")

    # 3. Indexar Equivalencias NLP (Marca propia <-> comercial)
    log.info("\n➡️ [3/4] Paso 3: Indexando equivalencias NLP...")
    try:
        indexar_equivalencias_es.ejecutar()
        log.info("✅ Paso 3 completado.")
    except Exception as e:
        log.error(f"❌ Error en Paso 3 (Equivalencias): {e}")

    # 4. Indexar IPC por cesta predefinida
    log.info("\n➡️ [4/4] Paso 4: Indexando series de IPC para cestas predefinidas...")
    log.info(
        "ℹ️ Nota: Este paso requiere que la API de Flask esté corriendo en http://localhost:5000"
    )
    try:
        indexar_ipc_es.ejecutar()
        log.info("✅ Paso 4 completado.")
    except Exception as e:
        log.error(
            "❌ Error en Paso 4 (IPC). Verifica si la API de Flask está corriendo. "
            f"Error: {e}"
        )

    end_time = time.time()
    elapsed = end_time - start_time

    log.info("=" * 65)
    log.info(f"🎉 PIPELINE MAESTRO COMPLETADO en {elapsed:.2f} segundos.")
    log.info("=" * 65)


if __name__ == "__main__":
    main()
