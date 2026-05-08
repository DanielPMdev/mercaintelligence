"""
indexar_ipc_es.py
Llama a la API Flask para calcular el IPC de cada perfil predefinido
e indexa los resultados en Elasticsearch para visualizarlos en Kibana.

Idempotente: borra y recrea el índice en cada ejecución.
Requiere que la API esté corriendo: python src/api/app.py
"""

import requests
import logging
from elasticsearch.helpers import bulk
from es_utils import get_es_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

API_URL = "http://localhost:5000"
ES_INDEX_IPC = "mercadona-ipc"

PERFILES = ["dani", "familiar", "estudiante", "vegano", "deportista", "pareja"]

MAPPING = {
    "mappings": {
        "properties": {
            "fecha":          {"type": "date"},
            "perfil":         {"type": "keyword"},
            "nombre_cesta":   {"type": "keyword"},
            "ipc":            {"type": "float"},
            "variacion_pct":  {"type": "float"},
            "gasto_estimado": {"type": "float"},
        }
    }
}


# ── Llamada a la API ──────────────────────────────────────────────────────────
def obtener_ipc_perfil(perfil: str) -> dict:
    """Llama al endpoint /api/ipc y devuelve el JSON con la serie temporal."""
    resp = requests.post(f"{API_URL}/api/ipc", json={"perfil": perfil})
    resp.raise_for_status()
    return resp.json()


# ── Generador de documentos ───────────────────────────────────────────────────
def generar_docs(perfil: str, data: dict):
    """
    Genera un documento por fecha con el IPC de ese perfil.
    _id determinístico {perfil}_{fecha} — evita duplicados al re-ejecutar.
    """
    fechas = data["fechas"]
    ipc_vals = data["ipc_cesta"]
    nombre = data["nombre_cesta"]
    gasto = data.get("gasto_total_estimado", 0)

    for fecha, ipc in zip(fechas, ipc_vals):
        variacion = round(ipc - 100, 2)
        yield {
            "_index": ES_INDEX_IPC,
            "_id": f"{perfil}_{fecha}",
            "_source": {
                "fecha": fecha,
                "perfil": perfil,
                "nombre_cesta": nombre,
                "ipc": round(ipc, 4),
                "variacion_pct": variacion,
                "gasto_estimado": gasto,
            },
        }


# ── Verificación ──────────────────────────────────────────────────────────────
def verificar(es):
    es.indices.refresh(index=ES_INDEX_IPC)
    total = es.count(index=ES_INDEX_IPC)["count"]
    log.info(f"Verificación: {total:,} documentos en '{ES_INDEX_IPC}'")


# ── Entrypoint ────────────────────────────────────────────────────────────────
def ejecutar():
    es = get_es_client()

    # Borrar y recrear — datos regenerables desde la API
    if es.indices.exists(index=ES_INDEX_IPC):
        es.indices.delete(index=ES_INDEX_IPC)
        log.info(f"Índice '{ES_INDEX_IPC}' borrado (recreación limpia)")

    es.indices.create(index=ES_INDEX_IPC, body=MAPPING)
    log.info(f"Índice '{ES_INDEX_IPC}' creado con mapping explícito")

    total_ok = 0
    for perfil in PERFILES:
        log.info(f"Calculando IPC para perfil: {perfil}...")
        try:
            data = obtener_ipc_perfil(perfil)
            docs = list(generar_docs(perfil, data))
            ok, errores = bulk(es, docs, raise_on_error=False)
            total_ok += ok
            ipc_actual = data["ipc_cesta"][-1] if data["ipc_cesta"] else 100
            log.info(f"  ✅ {perfil}: {ok} fechas indexadas | IPC actual: {ipc_actual:.2f}")
            if errores:
                log.warning(f"  Primeros errores: {errores[:3]}")
        except Exception as e:
            log.error(f"  ❌ Error en perfil {perfil}: {e}")

    log.info(f"Total indexado: {total_ok:,} documentos en '{ES_INDEX_IPC}'")
    verificar(es)


if __name__ == "__main__":
    ejecutar()
