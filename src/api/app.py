"""
app.py — API Flask del IPC personalizado MercaIntelligence

Endpoints:
  GET  /api/categorias          → lista de categorías disponibles
  GET  /api/productos           → productos filtrados por categoría/marca
  POST /api/ipc                 → calcula IPC de una cesta personalizada
  GET  /api/equivalencias       → equivalencias NLP marca propia ↔ comercial
  GET  /api/anomalias/hoy       → productos anómalos en la última fecha
  GET  /health                  → healthcheck

El IPC personalizado funciona así:
  1. El usuario selecciona una cesta de productos (referencias)
  2. Para cada producto, recuperamos su precio en cada fecha histórica
  3. Calculamos el índice: precio_fecha_t / precio_fecha_base × 100
  4. Agregamos por cesta con pesos iguales (o por gasto relativo)

La fecha base es la primera fecha disponible en el dataset (2025-11-03).
Un IPC de 105 significa que la cesta es un 5% más cara que en noviembre 2025.
"""

import pandas as pd
import logging
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # permite peticiones desde el frontend de Kibana o cualquier origen

# ── Rutas de datos ────────────────────────────────────────────────────────────
PARTITIONED_DIR = Path("data/processed")
EQUIV_PATH = Path("data/nlp/equivalencias.parquet")
ANOMALIAS_ZS = Path("data/anomalias/zscore_resultados.parquet")
ANOMALIAS_IF = Path("data/anomalias/if_resultados.parquet")
ANOMALIAS_AE = Path("data/anomalias/ae_resultados.parquet")


# ── Carga de datos en memoria al arrancar ────────────────────────────────────
# Se cargan una vez al inicio — no en cada petición.
# Para un proyecto académico con ~4K productos esto es suficiente.
# En producción real usaríamos caché con TTL o Redis.

log.info("Cargando datos en memoria...")

COLS_CATALOGO = [
    "referencia",
    "fecha",
    "titulo",
    "categoria",
    "subcategoria",
    "marca_propia",
    "es_marca_propia",
    "precio_actual",
    "precio_por_medida",
    "unidad_medida",
]

df_historico = pd.read_parquet(PARTITIONED_DIR, columns=COLS_CATALOGO)
df_historico["fecha"] = pd.to_datetime(df_historico["fecha"].astype(str))
df_historico = df_historico.sort_values(["referencia", "fecha"])

FECHA_BASE = df_historico["fecha"].min()
FECHA_ACTUAL = df_historico["fecha"].max()
REFS_VALIDAS = set(df_historico["referencia"].unique())

# Catálogo actual (última fecha) — para búsquedas de productos
df_catalogo = df_historico[df_historico["fecha"] == FECHA_ACTUAL].copy()

# Equivalencias NLP
df_equiv = pd.read_parquet(EQUIV_PATH) if EQUIV_PATH.exists() else pd.DataFrame()

log.info(
    f"Datos cargados: {len(df_historico):,} filas | "
    f"{len(df_catalogo):,} productos actuales | "
    f"rango {FECHA_BASE.date()} → {FECHA_ACTUAL.date()}"
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def serie_precio(referencia: int) -> pd.DataFrame:
    """Devuelve la serie temporal de precios de un producto."""
    return (
        df_historico[df_historico["referencia"] == referencia][
            ["fecha", "precio_actual"]
        ]
        .set_index("fecha")
        .sort_index()
    )


def calcular_ipc_cesta(referencias: list[int]) -> dict:
    """
    Calcula el IPC de una cesta de productos.

    Metodología:
      - Fecha base: primera fecha del dataset (2025-11-03)
      - Para cada producto: índice_t = precio_t / precio_base × 100
      - IPC cesta en t: media aritmética de los índices individuales
        (pesos iguales — simplificación académica justificada)
      - Solo se incluyen fechas donde todos los productos tienen precio

    Retorna dict con:
      fechas     : lista de fechas ISO
      ipc_cesta  : índice agregado por fecha
      por_producto: índice individual de cada producto
    """
    series = {}
    for ref in referencias:
        if ref not in REFS_VALIDAS:
            continue
        s = serie_precio(ref)
        if s.empty:
            continue
        precio_base = s.iloc[0]["precio_actual"]
        if precio_base == 0:
            continue
        series[ref] = (s["precio_actual"] / precio_base * 100).rename(ref)

    if not series:
        return {"error": "Ningún producto válido en la cesta"}

    df_ipc = pd.DataFrame(series).dropna()  # solo fechas con todos los productos

    resultado = {
        "fecha_base": FECHA_BASE.date().isoformat(),
        "fecha_actual": FECHA_ACTUAL.date().isoformat(),
        "n_productos": len(series),
        "fechas": [f.date().isoformat() for f in df_ipc.index],
        "ipc_cesta": df_ipc.mean(axis=1).round(2).tolist(),
        "por_producto": {
            str(ref): {
                "titulo": df_catalogo[df_catalogo["referencia"] == ref]["titulo"].iloc[
                    0
                ]
                if ref in df_catalogo["referencia"].values
                else str(ref),
                "indices": df_ipc[ref].round(2).tolist(),
            }
            for ref in series
        },
    }
    return resultado


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "productos": len(df_catalogo),
            "fecha_actual": FECHA_ACTUAL.date().isoformat(),
            "fecha_base": FECHA_BASE.date().isoformat(),
        }
    )


@app.route("/api/categorias")
def categorias():
    """Lista de categorías y subcategorías disponibles."""
    cats = (
        df_catalogo.groupby("categoria")["subcategoria"]
        .unique()
        .apply(sorted)
        .apply(list)
        .to_dict()
    )
    return jsonify({"categorias": cats})


@app.route("/api/productos")
def productos():
    """
    Búsqueda de productos con filtros opcionales.
    Query params:
      categoria   : filtrar por categoría
      subcategoria: filtrar por subcategoría
      marca       : 'propia' | 'comercial' | 'hacendado' | ...
      q           : búsqueda por texto en título
      limit       : máximo de resultados (default 50)
    """
    df = df_catalogo.copy()

    if cat := request.args.get("categoria"):
        df = df[df["categoria"] == cat.lower()]

    if subcat := request.args.get("subcategoria"):
        df = df[df["subcategoria"] == subcat.lower()]

    if marca := request.args.get("marca"):
        if marca == "propia":
            df = df[df["es_marca_propia"]]
        elif marca == "comercial":
            df = df[~df["es_marca_propia"]]
        else:
            df = df[df["marca_propia"] == marca.lower()]

    if q := request.args.get("q"):
        df = df[df["titulo"].str.contains(q.lower(), na=False)]

    limit = int(request.args.get("limit", 50))
    df = df.head(limit)

    return jsonify(
        {
            "total": len(df),
            "productos": df[
                [
                    "referencia",
                    "titulo",
                    "categoria",
                    "subcategoria",
                    "marca_propia",
                    "precio_actual",
                    "precio_por_medida",
                    "unidad_medida",
                ]
            ].to_dict(orient="records"),
        }
    )


@app.route("/api/ipc", methods=["POST"])
def ipc():
    """
    Calcula el IPC de una cesta personalizada.

    Body JSON:
      {
        "referencias": [1393, 1564, 2120],   // referencias de productos
        "nombre_cesta": "Mi cesta de la compra"
      }

    Respuesta:
      {
        "nombre_cesta": "...",
        "fecha_base": "2025-11-03",
        "ipc_actual": 108.3,      // IPC en la última fecha
        "variacion_total": "+8.3%",
        "fechas": [...],
        "ipc_cesta": [100, 101.2, ...],
        "por_producto": {...}
      }
    """
    body = request.get_json()
    if not body or "referencias" not in body:
        return jsonify({"error": "Se requiere 'referencias' en el body"}), 400

    referencias = [int(r) for r in body["referencias"]]
    if not referencias:
        return jsonify({"error": "Lista de referencias vacía"}), 400

    resultado = calcular_ipc_cesta(referencias)
    if "error" in resultado:
        return jsonify(resultado), 404

    # Enriquecer con variación total y IPC actual
    ipc_actual = resultado["ipc_cesta"][-1] if resultado["ipc_cesta"] else 100.0
    resultado["nombre_cesta"] = body.get("nombre_cesta", "Cesta personalizada")
    resultado["ipc_actual"] = round(ipc_actual, 2)
    resultado["variacion_total"] = f"{ipc_actual - 100:+.1f}%"

    return jsonify(resultado)


@app.route("/api/equivalencias")
def equivalencias():
    """
    Equivalencias NLP entre marca propia y comercial.
    Query params:
      subcategoria : filtrar por subcategoría
      marca        : filtrar por marca propia (hacendado, deliplus, etc.)
      min_similitud: umbral mínimo de similitud (default 0.80)
      limit        : máximo de resultados (default 50)
    """
    if df_equiv.empty:
        return jsonify({"error": "Equivalencias no disponibles"}), 503

    df = df_equiv[df_equiv["rank"] == 1].copy()

    if subcat := request.args.get("subcategoria"):
        df = df[df["subcategoria"] == subcat.lower()]

    if marca := request.args.get("marca"):
        df = df[df["marca_mp"] == marca.lower()]

    min_sim = float(request.args.get("min_similitud", 0.80))
    df = df[df["similitud"] >= min_sim]

    limit = int(request.args.get("limit", 50))
    df = df.sort_values("similitud", ascending=False).head(limit)

    cols = [
        "titulo_mp",
        "marca_mp",
        "precio_mp",
        "titulo_com",
        "precio_com",
        "subcategoria",
        "similitud",
        "diferencia_precio_pct",
        "diferencia_por_medida_pct",
        "misma_unidad",
    ]
    cols_disponibles = [c for c in cols if c in df.columns]

    return jsonify(
        {
            "total": len(df),
            "equivalencias": df[cols_disponibles].to_dict(orient="records"),
        }
    )


@app.route("/api/anomalias/hoy")
def anomalias_hoy():
    """
    Productos anómalos en la última fecha disponible.
    Combina los tres métodos — un producto puede aparecer en varios.
    Query params:
      metodo: 'zscore' | 'if' | 'ae' | 'todos' (default: 'todos')
    """
    metodo = request.args.get("metodo", "todos")
    resultados = {}

    def cargar_anomalias(path: Path, col_flag: str, cols_extra: list):
        if not path.exists():
            return []
        df = pd.read_parquet(path)
        df["fecha"] = pd.to_datetime(df["fecha"])
        ultima = df["fecha"].max()
        df = df[(df["fecha"] == ultima) & df[col_flag]]
        base_cols = [
            "referencia",
            "titulo",
            "categoria",
            "subcategoria",
            "marca_propia",
            "precio_actual",
        ]
        cols_disponibles = [c for c in base_cols + cols_extra if c in df.columns]
        return df[cols_disponibles].to_dict(orient="records")

    if metodo in ("zscore", "todos"):
        resultados["zscore"] = cargar_anomalias(
            ANOMALIAS_ZS, "anomalia_zscore", ["zscore", "media_local"]
        )

    if metodo in ("if", "todos"):
        resultados["isolation_forest"] = cargar_anomalias(
            ANOMALIAS_IF, "anomalia_if", ["score_if"]
        )

    if metodo in ("ae", "todos"):
        resultados["autoencoder"] = cargar_anomalias(
            ANOMALIAS_AE, "anomalia_ae", ["score_ae", "error_mse"]
        )

    # Resumen de conteos
    resumen = {k: len(v) for k, v in resultados.items()}

    return jsonify(
        {
            "fecha": FECHA_ACTUAL.date().isoformat(),
            "resumen": resumen,
            "anomalias": resultados,
        }
    )


# ── Arranque ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("Arrancando MercaIntelligence API...")
    log.info(f"  Fecha base   : {FECHA_BASE.date()}")
    log.info(f"  Fecha actual : {FECHA_ACTUAL.date()}")
    log.info(f"  Productos    : {len(df_catalogo):,}")
    app.run(debug=True, host="0.0.0.0", port=5000)
