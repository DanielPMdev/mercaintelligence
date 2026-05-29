"""
ingesta_incremental.py

Modos de uso:
    - CSV puntual: python ingesta_incremental.py --csv <ruta_al_csv> <ruta_al_csv2>
    - Carpeta local una sola vez: python ingesta_incremental.py --input-dir <ruta_carpeta>
    - Vigilancia local: python ingesta_incremental.py --watch --watch-dir <ruta_carpeta>

La vigilancia solo funciona sobre una carpeta local del runner o de la máquina
que ejecuta el proceso. En GitHub Actions suele ser mejor procesar el CSV recién
generado con --csv o la carpeta del checkout con --input-dir.
"""

import argparse
import os
import logging
import shutil
import time
from pathlib import Path

import pandas as pd
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from es_utils import get_es_client, bulk_index

# ── Configuración ────────────────────────────────────────────────────────────
CARPETA_WATCH_POR_DEFECTO = Path(
    os.getenv("INGESTA_WATCH_DIR", Path.cwd())
)
PARTITIONED_DIR = Path("data/processed")  # directorio particionado por fecha
ULTIMO_PRECIO_PATH = Path("data/state/ultimo_precio.parquet")
ES_INDEX = "mercadona-precios"
MARCAS_PROPIAS = ["hacendado", "bosque verde", "deliplus", "compy"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

# ── Cliente Elasticsearch (levantado con Docker) ──────────────────────────────
def crear_cliente_elasticsearch():
    """Devuelve un cliente ES disponible o None si la indexacion esta desactivada."""
    if os.getenv("INGESTA_SKIP_ES", "").lower() in {"1", "true", "yes"}:
        log.info("   Elasticsearch desactivado por INGESTA_SKIP_ES")
        return None

    try:
        return get_es_client()
    except Exception as e:
        log.warning(f"   Elasticsearch no disponible - se omitira indexacion: {e}")
        return None


es = crear_cliente_elasticsearch()


# ── Limpieza (misma lógica que consolidar_historico.py) ──────────────────────
def limpiar(df: pd.DataFrame, ruta_csv: str) -> pd.DataFrame:
    """Limpieza y normalización de tipos."""

    # 1. Fecha desde el nombre del fichero (más fiable que el timestamp interno)
    #    El fichero se llama YYYY-MM-DD_Mercadona_*.csv
    #    La columna 'fecha' ya viene del nombre al cargar (ver más abajo)
    #    Convertir timestamp a datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["fecha"] = pd.to_datetime(Path(ruta_csv).name[:10])

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
    patron = "|".join(MARCAS_PROPIAS)
    df["es_marca_propia"] = df["titulo"].str.contains(patron, case=False, na=False)

    # Columna adicional: qué marca propia es (útil para el módulo NLP y clustering)
    def detectar_marca(titulo: str) -> str:
        t = titulo.lower()
        for marca in MARCAS_PROPIAS:
            if marca in t:
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


# ── Tabla auxiliar: último precio por producto ──────────────────────────────
def obtener_ultimo_precio() -> pd.DataFrame:
    """Lee la tabla auxiliar con el último precio conocido por producto."""
    if not ULTIMO_PRECIO_PATH.exists():
        return pd.DataFrame(columns=["referencia", "precio_previo", "fecha_previo"])
    return pd.read_parquet(ULTIMO_PRECIO_PATH)


def actualizar_ultimo_precio(nuevo: pd.DataFrame):
    """
    Actualiza la tabla auxiliar con el último precio/fecha de cada producto.
    Solo mantiene una fila por referencia (la más reciente).
    """
    ultimo_actual = obtener_ultimo_precio()

    nuevo_ultimo = nuevo[["referencia", "precio_actual", "fecha"]].rename(
        columns={"precio_actual": "precio_previo", "fecha": "fecha_previo"}
    )

    combinado = pd.concat([ultimo_actual, nuevo_ultimo], ignore_index=True)
    combinado["fecha_previo"] = pd.to_datetime(combinado["fecha_previo"])
    combinado = (
        combinado.sort_values("fecha_previo").groupby("referencia").last().reset_index()
    )

    ULTIMO_PRECIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_parquet(ULTIMO_PRECIO_PATH, index=False)
    log.info(f"   ultimo_precio.parquet actualizado → {len(combinado):,} productos")


# ── Feature engineering incremental ──────────────────────────────────────────
def calcular_features(nuevo: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula features que requieren contexto histórico:
    variacion_pct y dias_sin_cambio.
    Lee desde la tabla auxiliar ultimo_precio.parquet (O(1), no todo el histórico).
    """
    assert pd.api.types.is_datetime64_any_dtype(nuevo["fecha"]), (
        "fecha debe ser datetime antes de calcular_features"
    )

    ultimo = obtener_ultimo_precio()

    if ultimo.empty:
        nuevo["variacion_pct"] = None
        nuevo["dias_sin_cambio"] = None
        return nuevo

    nuevo = nuevo.merge(ultimo, on="referencia", how="left")

    # Aseguramos que fecha_previo sea datetime por si viene como string desde el parquet
    nuevo["fecha_previo"] = pd.to_datetime(nuevo["fecha_previo"])

    nuevo["variacion_pct"] = (
        (nuevo["precio_actual"] - nuevo["precio_previo"]) / nuevo["precio_previo"] * 100
    ).round(4)

    nuevo["dias_sin_cambio"] = (nuevo["fecha"] - nuevo["fecha_previo"]).dt.days

    nuevo = nuevo.drop(columns=["precio_previo", "fecha_previo"])
    return nuevo


# ── Escritura particionada por fecha ──────────────────────────────────────────
def actualizar_parquet(nuevo: pd.DataFrame):
    """
    Guarda los datos en parquet particionado por fecha.
    NO reescribe histórico, solo añade/sobreescribe la partición del día.
    Idempotente: si se reprocesa un CSV del mismo día, sobreescribe esa partición.
    """
    if nuevo.empty:
        log.warning("DataFrame vacío — no se guarda nada")
        return

    PARTITIONED_DIR.mkdir(parents=True, exist_ok=True)

    # Convertir a string YYYY-MM-DD para nombres de partición limpios
    # Usamos assign para no mutar in-place y afectar pasos posteriores del pipeline
    df_save = nuevo.assign(fecha=pd.to_datetime(nuevo["fecha"]).dt.strftime("%Y-%m-%d"))

    df_save.to_parquet(
        PARTITIONED_DIR,
        partition_cols=["fecha"],
        engine="pyarrow",
        index=False,
        compression="snappy",
    )

    log.info(f"   Datos guardados en partición → {PARTITIONED_DIR}")


# ── Indexar en Elasticsearch ──────────────────────────────────────────────────
def indexar_en_elasticsearch(df: pd.DataFrame):
    if es is None:
        log.warning("   Elasticsearch no configurado - omitiendo indexacion")
        return

    try:
        if not es.ping():
            log.warning("   Elasticsearch no disponible - omitiendo indexacion")
            return
    except Exception as e:
        log.warning(f"   Error al comprobar Elasticsearch - omitiendo indexacion: {e}")
        return

    bulk_index(es, df)


def procesar_directorio(ruta_directorio: str):
    """Procesa todos los CSV de una carpeta local una sola vez."""
    directorio = Path(ruta_directorio)

    if not directorio.exists():
        log.error(f"   La carpeta no existe: {directorio}")
        return

    csvs = sorted(directorio.glob("*.csv"))
    if not csvs:
        log.warning(f"   No se encontraron CSV en {directorio}")
        return

    log.info(f"📂 Procesando {len(csvs):,} CSV desde: {directorio}")
    for ruta_csv in csvs:
        procesar_csv(str(ruta_csv))


def esperar_fichero_estable(ruta: Path, reintentos: int = 10, pausa: float = 1.0):
    """Espera a que el fichero termine de escribirse comprobando que su tamaño se estabiliza."""
    tamaño_anterior = -1
    for _ in range(reintentos):
        if not ruta.exists():
            time.sleep(pausa)
            continue

        tamaño_actual = ruta.stat().st_size
        if tamaño_actual == tamaño_anterior:
            return

        tamaño_anterior = tamaño_actual
        time.sleep(pausa)

    log.warning(f"   El fichero tardó en estabilizarse: {ruta}")


# ── Pipeline principal ────────────────────────────────────────────────────────
def procesar_csv(ruta_csv: str):
    ruta = Path(ruta_csv)
    log.info(f"📥 Procesando: {ruta.name}")

    # Guardar copia en raw
    destino_raw = Path("data/raw") / ruta.name
    try:
        destino_raw.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ruta, destino_raw)
        log.info(f"   Copia guardada en: {destino_raw}")
    except Exception as e:
        log.warning(f"   Error al copiar en raw: {e}")

    try:
        df = pd.read_csv(ruta)
    except Exception as e:
        log.error(f"   Error al leer CSV: {e}")
        return

    df = limpiar(df, str(ruta))
    df = calcular_features(df)
    actualizar_parquet(df)
    actualizar_ultimo_precio(df)
    indexar_en_elasticsearch(df)

    log.info(f"✅ {ruta.name} procesado — {len(df):,} productos ingresados")


# ── Watchdog handler ──────────────────────────────────────────────────────────
class NuevoCSVHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".csv"):
            # Espera a que termine la escritura antes de leer el CSV.
            esperar_fichero_estable(Path(event.src_path))
            procesar_csv(event.src_path)


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv", nargs="+", help="Procesar uno o varios CSV (modo desarrollo)"
    )
    parser.add_argument(
        "--input-dir",
        help="Procesar una carpeta local con CSV una sola vez y salir",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Vigilar una carpeta local del runner o de la máquina",
    )
    parser.add_argument(
        "--watch-dir",
        default=None,
        help="Carpeta local a vigilar cuando se use --watch",
    )
    args = parser.parse_args()

    if args.csv:
        # Modo desarrollo / CI: procesar manualmente uno o varios CSV
        for archivo in args.csv:
            procesar_csv(archivo)

    elif args.input_dir:
        # Modo batch para GitHub Actions: procesar el contenido del checkout o de una carpeta local.
        procesar_directorio(args.input_dir)

    elif args.watch:
        # Modo producción: vigilar una carpeta local persistente.
        carpeta_vigilada = Path(args.watch_dir or CARPETA_WATCH_POR_DEFECTO).resolve()

        if not carpeta_vigilada.exists():
            log.error(f"   La carpeta a vigilar no existe: {carpeta_vigilada}")
            raise SystemExit(1)

        log.info(f"👁️  Vigilando: {carpeta_vigilada}")
        log.info("   Ctrl+C para detener")
        handler = NuevoCSVHandler()
        observer = Observer()
        observer.schedule(handler, str(carpeta_vigilada), recursive=False)
        observer.start()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    else:
        parser.print_help()
