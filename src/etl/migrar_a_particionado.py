"""
migrar_a_particionado.py

Script de migración ONE-SHOT:
Convierte el maestro.parquet monolítico al formato particionado por fecha
y genera la tabla auxiliar ultimo_precio.parquet.

Ejecutar UNA SOLA VEZ tras la actualización del pipeline.
Después, el fichero maestro.parquet puede eliminarse manualmente.
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

MAESTRO_PATH        = Path("data/processed/maestro.parquet")
PARTITIONED_DIR     = Path("data/processed")
ULTIMO_PRECIO_PATH  = Path("data/state/ultimo_precio.parquet")


def migrar():
    if not MAESTRO_PATH.exists():
        log.error(f"No se encontró {MAESTRO_PATH}. Nada que migrar.")
        return

    log.info(f"Leyendo {MAESTRO_PATH}...")
    maestro = pd.read_parquet(MAESTRO_PATH)
    log.info(f"   {len(maestro):,} filas cargadas")

    # ── 1. Escribir particionado por fecha ──────────────────────────────────
    # Convertir a string YYYY-MM-DD para nombres de partición limpios
    maestro["fecha"] = pd.to_datetime(maestro["fecha"]).dt.strftime("%Y-%m-%d")

    log.info("Escribiendo particiones por fecha...")
    maestro.to_parquet(
        PARTITIONED_DIR,
        partition_cols=["fecha"],
        engine="pyarrow",
        index=False,
        compression="snappy"
    )

    n_fechas = maestro["fecha"].nunique()
    log.info(f"   {n_fechas} particiones creadas en {PARTITIONED_DIR}")

    # ── 2. Generar tabla auxiliar ultimo_precio ─────────────────────────────
    log.info("Generando ultimo_precio.parquet...")
    ultimo = (
        maestro[["referencia", "precio_actual", "fecha"]]
        .sort_values("fecha")
        .groupby("referencia")
        .last()
        .reset_index()
        .rename(columns={
            "precio_actual": "precio_previo",
            "fecha": "fecha_previo"
        })
    )

    ultimo.to_parquet(ULTIMO_PRECIO_PATH, index=False)
    log.info(f"   {len(ultimo):,} productos en ultimo_precio.parquet")

    # ── 3. Resumen ──────────────────────────────────────────────────────────
    log.info("")
    log.info("=" * 60)
    log.info("✅ Migración completada")
    log.info(f"   Particiones:     {n_fechas} fechas")
    log.info(f"   Productos:       {len(ultimo):,}")
    log.info(f"   Rango:           {maestro['fecha'].min()} → {maestro['fecha'].max()}")
    log.info("")
    log.info("⚠️  Puedes eliminar maestro.parquet manualmente cuando confirmes")
    log.info(f"    que todo funciona:  del {MAESTRO_PATH}")
    log.info("=" * 60)


if __name__ == "__main__":
    migrar()
