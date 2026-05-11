"""
consolidar_historico.py
Ejecutar UNA SOLA VEZ para construir el parquet maestro inicial.
A partir de aquí, usar ingesta_incremental.py para cada CSV nuevo.
"""

import pandas as pd
import glob
import logging
from pathlib import Path

# Opt-in to pandas future behavior to silence downcasting warnings in ffill/bfill
pd.set_option("future.no_silent_downcasting", True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

RAW_DIR = Path("data/raw")
PARQUET_PATH = Path("data/processed/maestro.parquet")


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Limpieza y normalización de tipos."""

    # 1. Fecha desde el nombre del fichero (más fiable que el timestamp interno)
    #    El fichero se llama YYYY-MM-DD_Mercadona_*.csv
    #    La columna 'fecha' ya viene del nombre al cargar (ver más abajo)
    #    Convertir timestamp a datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # 2. Tipos numéricos — eliminar símbolo € si viene como string
    for col in ["precio_actual", "precio_anterior", "precio_por_medida"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("€", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 3. Normalizar texto — categoría y subcategoría en minúsculas sin espacios extra
    for col in ["categoria", "subcategoria", "titulo"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()

    # 4. Detectar marca blanca (todas las marcas propias de Mercadona)
    MARCAS_PROPIAS = ["hacendado", "bosque verde", "deliplus", "compy"]

    patron = "|".join(MARCAS_PROPIAS)
    df["es_marca_propia"] = df["titulo"].str.contains(patron, case=False, na=False)

    # Columna adicional: qué marca propia es (útil para el módulo NLP y clustering)
    def detectar_marca(titulo: str) -> str:
        titulo = titulo.lower()
        for marca in MARCAS_PROPIAS:
            if marca in titulo:
                return marca
        return "comercial"

    df["marca_propia"] = df["titulo"].apply(detectar_marca)

    # 5. Variación de precio (calculada dentro del mismo CSV — útil como feature base)
    df["tiene_precio_anterior"] = df["precio_anterior"].notna() & (
        df["precio_anterior"] > 0
    )

    # 6. Eliminar duplicados exactos por si el scraper corrió dos veces el mismo día
    df = df.drop_duplicates(subset=["referencia", "fecha"])

    # 7. Eliminar filas sin referencia o sin precio
    df = df.dropna(subset=["referencia", "precio_actual"])

    return df


def extraer_fecha_del_nombre(nombre_fichero: str) -> str:
    """Extrae la fecha del nombre del CSV: YYYY-MM-DD_Mercadona_*.csv"""
    return Path(nombre_fichero).name[:10]  # los primeros 10 caracteres


def cargar_csv(ruta: str) -> pd.DataFrame:
    """Carga un CSV individual y añade la columna fecha."""
    try:
        df = pd.read_csv(ruta)
        df["fecha"] = extraer_fecha_del_nombre(ruta)
        df["fecha"] = pd.to_datetime(df["fecha"])
        return df
    except Exception as e:
        log.warning(f"Error al leer {ruta}: {e}")
        return pd.DataFrame()


def consolidar():
    csvs = sorted(glob.glob(str(RAW_DIR / "*.csv")))
    log.info(f"Encontrados {len(csvs)} CSVs en {RAW_DIR}")

    if not csvs:
        log.error("No se encontraron CSVs. Revisa la ruta data/raw/")
        return

    fragmentos = []
    for i, ruta in enumerate(csvs):
        df = cargar_csv(ruta)
        if not df.empty:
            df = limpiar(df)
            fragmentos.append(df)
            if (i + 1) % 20 == 0:
                log.info(f"  Procesados {i + 1}/{len(csvs)} ficheros...")

    maestro = pd.concat(fragmentos, ignore_index=True)
    maestro = maestro.sort_values(["referencia", "fecha"]).reset_index(drop=True)

    # Imputar unidad de medida para rellenar los nulos de las primeras extracciones
    maestro["unidad_medida"] = maestro.groupby("referencia")["unidad_medida"].transform(
        lambda x: x.ffill().bfill()
    )

    # Para los pocos que queden sin unidad (productos que nunca tuvieron unidad_medida),
    # inferimos basándonos en el formato o asignamos 'ud' por defecto.
    nulos = maestro["unidad_medida"].isna()
    if nulos.any():
        formato = maestro.loc[nulos, "formato"].astype(str).str.lower()
        maestro.loc[
            nulos & formato.str.contains(r"\b(?:ml|l)\b", regex=True), "unidad_medida"
        ] = "100 ml"
        maestro.loc[
            nulos & formato.str.contains(r"\b(?:g|kg)\b", regex=True), "unidad_medida"
        ] = "kg"
        maestro.loc[maestro["unidad_medida"].isna(), "unidad_medida"] = "ud"

    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    maestro.to_parquet(PARQUET_PATH, index=False)

    log.info(f"✅ Parquet maestro guardado en {PARQUET_PATH}")
    log.info(f"   Filas totales : {len(maestro):,}")
    log.info(f"   Productos únicos: {maestro['referencia'].nunique():,}")
    log.info(
        f"   Rango fechas: {maestro['fecha'].min().date()} → {maestro['fecha'].max().date()}"
    )
    log.info(f"   Columnas: {list(maestro.columns)}")


if __name__ == "__main__":
    consolidar()
