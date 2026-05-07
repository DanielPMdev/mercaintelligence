"""
app.py — API Flask del IPC personalizado MercaIntelligence

Endpoints:
  GET  /api/categorias          → lista de categorías disponibles
  GET  /api/productos           → productos filtrados por categoría/marca
  GET  /api/cestas              → perfiles de cesta predefinidos
  POST /api/ipc                 → calcula IPC de una cesta personalizada
  POST /api/ipc/prediccion      → predicción de coste futuro (LSTM + tendencia)
  POST /api/recomendaciones     → alternativas más baratas (NLP embeddings)
  GET  /api/equivalencias       → equivalencias NLP marca propia ↔ comercial
  GET  /api/anomalias/hoy       → productos anómalos en la última fecha
  GET  /health                  → healthcheck

El IPC personalizado funciona así:
  1. El usuario selecciona productos y su cantidad mensual de compra
  2. El sistema calcula pesos automáticamente:
       gasto_i = precio_base_i × cantidad_mensual_i
       peso_i  = gasto_i / gasto_total
  3. Para cada producto: índice_t = precio_t / precio_base × 100
  4. IPC(t) = Σ [ peso_i × índice_i(t) ]  ← ponderado por consumo real

La fecha base es la primera fecha disponible en el dataset (2025-11-03).
Un IPC de 105 significa que la cesta es un 5% más cara que en noviembre 2025.

También se pueden usar perfiles predefinidos (familiar, estudiante, vegano,
deportista) que cargan cestas con productos y cantidades típicas.
"""

import pandas as pd
import numpy as np
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
LSTM_PRED_PATH = Path("data/predicciones/lstm/lstm_resultados.parquet")
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

# Predicciones LSTM (probabilidad de cambio de precio)
df_lstm = pd.DataFrame()
if LSTM_PRED_PATH.exists():
    df_lstm = pd.read_parquet(LSTM_PRED_PATH)
    df_lstm["fecha"] = pd.to_datetime(df_lstm["fecha"])
    log.info(f"Predicciones LSTM cargadas: {len(df_lstm):,} filas")

# Tendencia histórica de precios por producto — precalculada al arrancar.
# Para cada producto calculamos la dirección y magnitud media de sus cambios
# reales de precio. Esto se combina con la prob_cambio del LSTM para
# estimar el precio futuro: precio_futuro = precio_actual × (1 + prob × tendencia).
df_tendencias = pd.DataFrame()
if not df_historico.empty:
    _cambios = df_historico.sort_values(["referencia", "fecha"]).copy()
    _cambios["cambio_pct"] = (
        _cambios.groupby("referencia")["precio_actual"].pct_change() * 100
    )
    # Solo filas con cambio real (> 0.001% para evitar ruido de flotantes)
    _cambios = _cambios[_cambios["cambio_pct"].abs() > 0.001]
    df_tendencias = (
        _cambios.groupby("referencia")["cambio_pct"]
        .agg(["mean", "median", "count"])
        .rename(columns={"mean": "media_cambio", "median": "mediana_cambio", "count": "n_cambios"})
    )
    log.info(
        f"Tendencias calculadas: {len(df_tendencias):,} productos con al menos 1 cambio"
    )

log.info(
    f"Datos cargados: {len(df_historico):,} filas | "
    f"{len(df_catalogo):,} productos actuales | "
    f"rango {FECHA_BASE.date()} → {FECHA_ACTUAL.date()}"
)


# ── Cestas predefinidas ──────────────────────────────────────────────────────
CESTAS_PREDEFINIDAS = {
    "dani": {
        "nombre": "Cesta Dani",
        "descripcion": (
            "Compra habitual de Daniel basada en tickets reales de abril 2026. "
            "Incluye proteínas frescas, lácteos, verduras, snacks y limpieza."
        ),
        "productos": [
            # ── LÁCTEOS ──────────────────────────────────────────────
            {
                "referencia": 10380,
                "cantidad_mensual": 8,
            },  # Leche entera Hacendado 1L (0.96€)
            {
                "referencia": 20029,
                "cantidad_mensual": 4,
            },  # Kéfir natural sabor suave (1.10€)
            {
                "referencia": 51218,
                "cantidad_mensual": 4,
            },  # Burrata fresca Hacendado (2.20€)
            {
                "referencia": 51110,
                "cantidad_mensual": 2,
            },  # Queso rallado mozzarella pizza (1.60€)
            # ── CARNE Y EMBUTIDO ─────────────────────────────────────
            {
                "referencia": 2714,
                "cantidad_mensual": 4,
            },  # Filetes lomo de cerdo (3.37€)
            {
                "referencia": 5710,
                "cantidad_mensual": 4,
            },  # Pechuga 92% pavo Hacendado lonchas (2.85€)
            {
                "referencia": 2872,
                "cantidad_mensual": 2,
            },  # Burger de vacuno y cerdo (4.20€)
            {
                "referencia": 35884,
                "cantidad_mensual": 2,
            },  # Hamburguesa de lomo de vacuno (4.00€)
            {"referencia": 2685, "cantidad_mensual": 2},  # Secreto de cerdo (3.04€)
            {
                "referencia": 59071,
                "cantidad_mensual": 2,
            },  # Taquitos de jamón Incarlopsa (2.65€)
            {
                "referencia": 21628,
                "cantidad_mensual": 4,
            },  # Bacón ahumado La Selva lonchas (2.30€) ← NEW
            # ── PESCADO Y MARISCO ────────────────────────────────────
            {
                "referencia": 87342,
                "cantidad_mensual": 4,
            },  # Filetes de trucha Arco iris (3.50€)
            {
                "referencia": 80405,
                "cantidad_mensual": 4,
            },  # Boquerones en vinagre Hacendado (1.65€)
            {
                "referencia": 24230,
                "cantidad_mensual": 1,
            },  # Gamba pelada cruda grande Hacendado (6.35€)
            {
                "referencia": 18002,
                "cantidad_mensual": 2,
            },  # Atún claro en aceite de oliva Hacendado pk6 (4.90€)
            # ── HUEVOS ───────────────────────────────────────────────
            {"referencia": 31504, "cantidad_mensual": 2},  # Huevos grandes L (3.20€)
            # ── VERDURAS Y FRESCOS ───────────────────────────────────
            {"referencia": 69089, "cantidad_mensual": 2},  # Cebollas (2.40€)
            {"referencia": 69297, "cantidad_mensual": 1},  # Ajos morados (1.85€)
            {
                "referencia": 3313,
                "cantidad_mensual": 1,
            },  # Uva blanca sin semillas (3.30€)
            {"referencia": 3824, "cantidad_mensual": 4},  # Banana (0.28€/ud)
            {
                "referencia": 3852,
                "cantidad_mensual": 2,
            },  # Guacamole Hacendado 95% aguacate (1.80€)
            {
                "referencia": 3858,
                "cantidad_mensual": 2,
            },  # Aguacates bandeja (3.87€) ← NEW
            {
                "referencia": 26029,
                "cantidad_mensual": 2,
            },  # Garbanzo cocido Hacendado (0.85€)
            {
                "referencia": 16616,
                "cantidad_mensual": 2,
            },  # Champiñón laminado Hacendado (1.80€)
            {
                "referencia": 35221,
                "cantidad_mensual": 2,
            },  # Pimiento rojo y verde ultracongelado (1.20€)
            {"referencia": 69669, "cantidad_mensual": 2},  # Zanahorias (0.80€) ← NEW
            {"referencia": 69714, "cantidad_mensual": 2},  # Ensalada California (2.60€)
            # ── PASTA, ARROZ Y CONSERVAS ─────────────────────────────
            {
                "referencia": 5044,
                "cantidad_mensual": 4,
            },  # Arroz redondo Hacendado (1.20€)
            {
                "referencia": 6175,
                "cantidad_mensual": 2,
            },  # Pasta fresca gnocchi Hacendado (1.00€) ← NEW
            # ── CONGELADOS Y PRECOCINADOS ────────────────────────────
            {
                "referencia": 63645,
                "cantidad_mensual": 2,
            },  # Pizza pollo y bacón Hacendado (2.90€)
            # ── PAN Y PANADERÍA ──────────────────────────────────────
            {
                "referencia": 52602,
                "cantidad_mensual": 2,
            },  # Pan de burger Brioche Hacendado (1.10€)
            {
                "referencia": 80859,
                "cantidad_mensual": 2,
            },  # Tortillas de trigo Hacendado (1.15€)
            {
                "referencia": 80942,
                "cantidad_mensual": 1,
            },  # Tortillas de trigo integrales Hacendado (1.55€)
            # ── ESPECIAS Y CONDIMENTOS ───────────────────────────────
            {"referencia": 34125, "cantidad_mensual": 1},  # Curry Hacendado (1.10€)
            {
                "referencia": 34183,
                "cantidad_mensual": 1,
            },  # Pimentón picante Hacendado (1.35€)
            {
                "referencia": 47994,
                "cantidad_mensual": 1,
            },  # Hoja de laurel Hacendado (0.85€)
            # ── SNACKS Y APERITIVOS ──────────────────────────────────
            {"referencia": 33640, "cantidad_mensual": 2},  # Nachos Hacendado (0.90€)
            {
                "referencia": 5398,
                "cantidad_mensual": 2,
            },  # Patatas fritas 0% sal añadida Hacendado (1.50€)
            {
                "referencia": 80858,
                "cantidad_mensual": 2,
            },  # Hummus garbanzos clásico Hacendado (1.05€)
            {
                "referencia": 34188,
                "cantidad_mensual": 1,
            },  # Pipas de calabaza natural Hacendado (1.70€)
            {
                "referencia": 23575,
                "cantidad_mensual": 1,
            },  # Almendra natural Hacendado sin piel (2.90€)
            {
                "referencia": 9357,
                "cantidad_mensual": 2,
            },  # Muesli Crunchy Hacendado frutos secos (2.10€)
            # ── DESAYUNO ─────────────────────────────────────────────
            {
                "referencia": 11187,
                "cantidad_mensual": 1,
            },  # Cereales solubles con achicoria Hacendado (2.15€)
            # ── BEBIDAS ──────────────────────────────────────────────
            {
                "referencia": 28270,
                "cantidad_mensual": 6,
            },  # Agua mineral Cortes 1.5L (0.27€)
            # ── LIMPIEZA ─────────────────────────────────────────────
            {
                "referencia": 35998,
                "cantidad_mensual": 2,
            },  # Lavavajillas Ultra concentrado Bosque Verde (1.90€)
            {
                "referencia": 49619,
                "cantidad_mensual": 2,
            },  # Papel hogar Compacto Absorbente Bosque Verde (2.30€)
            # ── HIGIENE / VARIOS ─────────────────────────────────────
            {
                "referencia": 60555,
                "cantidad_mensual": 1,
            },  # Gel de baño vainilla y miel Deliplus (1.60€) ← NEW
            {
                "referencia": 35734,
                "cantidad_mensual": 1,
            },  # Tiras adhesivas protectoras espuma Deliplus (1.30€) ← NEW
            {
                "referencia": 13780,
                "cantidad_mensual": 1,
            },  # Ambientador varitas Fruta Tropical Bosque Verde (2.10€)
        ],
    },
    "familiar": {
        "nombre": "Cesta familiar",
        "descripcion": (
            "Compra mensual realista para una familia de 3-4 personas, "
            "incluyendo carne, pescado, huevos, desayuno, y limpieza."
        ),
        "productos": [
            {"referencia": 10380, "cantidad_mensual": 12},  # leche entera Hacendado 1L
            {"referencia": 22313, "cantidad_mensual": 16},  # yogur natural
            {"referencia": 13810, "cantidad_mensual": 6},  # pan de molde
            {"referencia": 15768, "cantidad_mensual": 4},  # huevos gallinas camperas
            {"referencia": 2787, "cantidad_mensual": 8},  # filetes pechuga de pollo
            {"referencia": 2867, "cantidad_mensual": 4},  # carne picada cerdo
            {"referencia": 24324, "cantidad_mensual": 4},  # merluza congelada
            {"referencia": 5044, "cantidad_mensual": 4},  # arroz redondo
            {"referencia": 5063, "cantidad_mensual": 3},  # arroz largo
            {"referencia": 17108, "cantidad_mensual": 6},  # tomate frito
            {"referencia": 18002, "cantidad_mensual": 6},  # atún claro
            {"referencia": 26101, "cantidad_mensual": 3},  # lentejas
            {"referencia": 26110, "cantidad_mensual": 3},  # garbanzos
            {"referencia": 14102, "cantidad_mensual": 2},  # galletas maría
            {"referencia": 11172, "cantidad_mensual": 1},  # café molido
            {"referencia": 4706, "cantidad_mensual": 2},  # aceite oliva virgen extra
            {"referencia": 11664, "cantidad_mensual": 2},  # detergente
            {"referencia": 12912, "cantidad_mensual": 4},  # papel higiénico
        ],
    },
    "estudiante": {
        "nombre": "Cesta estudiante",
        "descripcion": (
            "Compra económica y práctica para una persona, "
            "pensada para comidas rápidas, carne, huevos y limpieza."
        ),
        "productos": [
            {"referencia": 10382, "cantidad_mensual": 8},  # leche semidesnatada
            {"referencia": 13810, "cantidad_mensual": 4},  # pan de molde
            {"referencia": 15768, "cantidad_mensual": 2},  # huevos
            {"referencia": 2787, "cantidad_mensual": 4},  # filetes pechuga de pollo
            {"referencia": 12083, "cantidad_mensual": 3},  # pizza carnivora
            {"referencia": 5044, "cantidad_mensual": 3},  # arroz
            {"referencia": 17108, "cantidad_mensual": 4},  # tomate frito
            {"referencia": 18002, "cantidad_mensual": 4},  # atún claro
            {"referencia": 21581, "cantidad_mensual": 2},  # queso rallado
            {"referencia": 26101, "cantidad_mensual": 2},  # lentejas
            {"referencia": 14102, "cantidad_mensual": 1},  # galletas maría
            {"referencia": 11172, "cantidad_mensual": 1},  # café molido
            {"referencia": 12912, "cantidad_mensual": 2},  # papel higiénico
        ],
    },
    "vegano": {
        "nombre": "Cesta vegana",
        "descripcion": (
            "Compra 100% vegetal con buena variedad nutricional: "
            "legumbres, bebidas vegetales, cereales y proteína vegetal."
        ),
        "productos": [
            {"referencia": 14707, "cantidad_mensual": 10},  # bebida de soja
            {"referencia": 51097, "cantidad_mensual": 6},  # tofu firme
            {"referencia": 5044, "cantidad_mensual": 3},  # arroz redondo
            {"referencia": 5063, "cantidad_mensual": 2},  # arroz largo
            {"referencia": 26101, "cantidad_mensual": 4},  # lentejas
            {"referencia": 26110, "cantidad_mensual": 4},  # garbanzos
            {"referencia": 86368, "cantidad_mensual": 3},  # avena
            {"referencia": 17108, "cantidad_mensual": 4},  # tomate frito
            {"referencia": 4706, "cantidad_mensual": 1},  # aceite oliva virgen extra
            {"referencia": 15068, "cantidad_mensual": 1},  # mermelada
            {"referencia": 12912, "cantidad_mensual": 2},  # papel higiénico
        ],
    },
    "deportista": {
        "nombre": "Cesta deportista",
        "descripcion": (
            "Compra alta en proteínas (huevos, pollo, atún) y carbohidratos "
            "complejos para entrenamientos frecuentes."
        ),
        "productos": [
            {"referencia": 10382, "cantidad_mensual": 12},  # leche semidesnatada
            {"referencia": 22313, "cantidad_mensual": 16},  # yogur natural
            {"referencia": 15768, "cantidad_mensual": 6},  # huevos (muchos)
            {"referencia": 2787, "cantidad_mensual": 12},  # pechuga pollo (mucha)
            {"referencia": 18002, "cantidad_mensual": 8},  # atún claro
            {"referencia": 24324, "cantidad_mensual": 4},  # merluza
            {"referencia": 86368, "cantidad_mensual": 4},  # avena
            {"referencia": 5063, "cantidad_mensual": 4},  # arroz largo
            {"referencia": 5044, "cantidad_mensual": 2},  # arroz redondo
            {"referencia": 26101, "cantidad_mensual": 2},  # lentejas
            {"referencia": 26110, "cantidad_mensual": 2},  # garbanzos
            {"referencia": 13810, "cantidad_mensual": 3},  # pan de molde
        ],
    },
    "pareja": {
        "nombre": "Cesta pareja",
        "descripcion": (
            "Compra equilibrada para dos personas con desayuno, "
            "comidas caseras (carne, huevos) y cenas rápidas."
        ),
        "productos": [
            {"referencia": 10380, "cantidad_mensual": 8},  # leche entera
            {"referencia": 22313, "cantidad_mensual": 10},  # yogur natural
            {"referencia": 15768, "cantidad_mensual": 3},  # huevos
            {"referencia": 2787, "cantidad_mensual": 6},  # pechuga pollo
            {"referencia": 2867, "cantidad_mensual": 3},  # carne picada
            {"referencia": 13810, "cantidad_mensual": 4},  # pan de molde
            {"referencia": 5044, "cantidad_mensual": 3},  # arroz
            {"referencia": 17108, "cantidad_mensual": 4},  # tomate frito
            {"referencia": 18002, "cantidad_mensual": 4},  # atún claro
            {"referencia": 4706, "cantidad_mensual": 1},  # aceite oliva
            {"referencia": 26101, "cantidad_mensual": 2},  # lentejas
            {"referencia": 12912, "cantidad_mensual": 3},  # papel higiénico
            {"referencia": 11664, "cantidad_mensual": 1},  # detergente
        ],
    },
}


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


def titulo_producto(ref: int) -> str:
    """Devuelve el título de un producto por su referencia."""
    match = df_catalogo[df_catalogo["referencia"] == ref]
    return match["titulo"].iloc[0] if not match.empty else str(ref)


def calcular_ipc_cesta(productos: list[dict]) -> dict:
    """
    Calcula el IPC ponderado de una cesta de productos.

    Cada elemento de `productos` es un dict con:
      - referencia       : int
      - cantidad_mensual : int (default 1)

    Metodología:
      1. Fecha base: primera fecha del dataset (2025-11-03)
      2. Para cada producto: índice_t = precio_t / precio_base × 100
      3. Pesos automáticos basados en gasto estimado:
           gasto_i = precio_base_i × cantidad_mensual_i
           peso_i  = gasto_i / gasto_total
      4. IPC(t) = Σ [ peso_i × índice_i(t) ]
      5. Solo se incluyen fechas donde todos los productos tienen precio

    Retorna dict con:
      fechas             : lista de fechas ISO
      ipc_cesta          : índice ponderado por fecha
      gasto_total_estimado: gasto mensual estimado de la cesta
      por_producto       : desglose individual (índice, peso, gasto, cantidad)
    """
    series = {}
    gastos = {}
    info = {}

    for prod in productos:
        ref = prod["referencia"]
        cantidad = prod.get("cantidad_mensual", 1)

        if ref not in REFS_VALIDAS:
            continue
        s = serie_precio(ref)
        if s.empty:
            continue
        precio_base = s.iloc[0]["precio_actual"]
        if precio_base == 0:
            continue

        gasto = precio_base * cantidad
        series[ref] = (s["precio_actual"] / precio_base * 100).rename(ref)
        gastos[ref] = gasto
        info[ref] = {
            "cantidad_mensual": cantidad,
            "precio_base": round(precio_base, 2),
            "gasto_estimado": round(gasto, 2),
        }

    if not series:
        return {"error": "Ningún producto válido en la cesta"}

    # ── Normalizar pesos: peso_i = gasto_i / gasto_total ──
    gasto_total = sum(gastos.values())
    for ref in gastos:
        info[ref]["peso"] = round(gastos[ref] / gasto_total, 4)

    df_ipc = pd.DataFrame(series).dropna()  # solo fechas con todos los productos

    # IPC ponderado — cada producto contribuye según su peso real
    ipc_ponderado = sum(df_ipc[ref] * info[ref]["peso"] for ref in series)

    resultado = {
        "fecha_base": FECHA_BASE.date().isoformat(),
        "fecha_actual": FECHA_ACTUAL.date().isoformat(),
        "n_productos": len(series),
        "gasto_total_estimado": round(gasto_total, 2),
        "fechas": [f.date().isoformat() for f in df_ipc.index],
        "ipc_cesta": ipc_ponderado.round(2).tolist(),
        "por_producto": {
            str(ref): {
                "titulo": titulo_producto(ref),
                "indices": df_ipc[ref].round(2).tolist(),
                **info[ref],
            }
            for ref in series
        },
    }
    return resultado


def calcular_prediccion_cesta(productos: list[dict], horizonte_dias: int = 30) -> dict:
    """
    Predice el coste futuro de una cesta combinando dos señales:

    1. prob_cambio_lstm: probabilidad de que el precio cambie (LSTM clasificador)
    2. tendencia histórica: dirección y magnitud media de cambios reales

    Fórmula por producto:
      precio_predicho = precio_actual × (1 + prob_cambio × mediana_cambio / 100)

    Justificación:
      - Si prob_cambio ≈ 0 → el precio no se mueve → predicción ≈ actual
      - Si prob_cambio ≈ 1 y mediana_cambio = -5% → baja un 5%
      - La mediana se usa porque es robusta a outliers (cambios extremos
        como ofertas flash de -40% distorsionan la media)

    Retorna dict con coste actual, predicho, variación y desglose.
    """
    if df_lstm.empty:
        return {"error": "Predicciones LSTM no disponibles"}

    desglose = []
    coste_actual = 0.0
    coste_predicho = 0.0
    productos_sin_prediccion = []

    # Última prob_cambio disponible por producto
    lstm_ultima = (
        df_lstm.sort_values("fecha")
        .groupby("referencia")
        .last()
        .reset_index()[["referencia", "prob_cambio_lstm", "fecha"]]
    )

    for prod in productos:
        ref = prod["referencia"]
        cantidad = prod.get("cantidad_mensual", 1)

        if ref not in REFS_VALIDAS:
            continue

        # Precio actual
        match = df_catalogo[df_catalogo["referencia"] == ref]
        if match.empty:
            continue
        precio_actual = match["precio_actual"].iloc[0]

        # Probabilidad de cambio (LSTM)
        lstm_row = lstm_ultima[lstm_ultima["referencia"] == ref]
        prob_cambio = float(lstm_row["prob_cambio_lstm"].iloc[0]) if not lstm_row.empty else 0.0

        # Tendencia histórica (mediana de cambios pasados)
        if ref in df_tendencias.index:
            tendencia = df_tendencias.loc[ref]
            mediana_cambio = tendencia["mediana_cambio"]
            n_cambios = int(tendencia["n_cambios"])
        else:
            # Sin historial de cambios → producto estable
            mediana_cambio = 0.0
            n_cambios = 0

        # Predicción: precio × (1 + prob × mediana / 100)
        # Escalar por horizonte relativo a 30 días (periodo de referencia del LSTM)
        factor = prob_cambio * (mediana_cambio / 100) * (horizonte_dias / 30)
        precio_predicho_unit = precio_actual * (1 + factor)

        gasto_actual = precio_actual * cantidad
        gasto_predicho = precio_predicho_unit * cantidad
        coste_actual += gasto_actual
        coste_predicho += gasto_predicho

        info_prod = {
            "referencia": ref,
            "titulo": titulo_producto(ref),
            "cantidad_mensual": cantidad,
            "precio_actual": round(precio_actual, 2),
            "precio_predicho": round(precio_predicho_unit, 2),
            "prob_cambio_lstm": round(prob_cambio, 4),
            "mediana_cambio_historico": round(mediana_cambio, 2),
            "n_cambios_historicos": n_cambios,
            "gasto_actual": round(gasto_actual, 2),
            "gasto_predicho": round(gasto_predicho, 2),
        }

        if lstm_row.empty:
            productos_sin_prediccion.append(ref)
            info_prod["nota"] = "Sin datos LSTM — se asume precio estable"

        desglose.append(info_prod)

    if not desglose:
        return {"error": "Ningún producto válido en la cesta"}

    variacion = ((coste_predicho - coste_actual) / coste_actual * 100) if coste_actual > 0 else 0.0

    return {
        "horizonte_dias": horizonte_dias,
        "coste_actual": round(coste_actual, 2),
        "coste_predicho": round(coste_predicho, 2),
        "variacion_esperada": f"{variacion:+.2f}%",
        "variacion_pct": round(variacion, 2),
        "n_productos": len(desglose),
        "productos_sin_lstm": productos_sin_prediccion,
        "metodologia": (
            "Combinación de probabilidad de cambio (LSTM clasificador) "
            "con tendencia histórica de precios (mediana de cambios reales). "
            "precio_pred = precio_actual × (1 + prob_cambio × mediana_cambio%)"
        ),
        "desglose": desglose,
    }


def buscar_alternativas_cesta(productos: list[dict]) -> dict:
    """
    Para cada producto de la cesta, busca alternativas más baratas
    usando las equivalencias NLP (marca propia ↔ comercial).

    Lógica bidireccional:
      - Si el usuario compra marca COMERCIAL → sugerir equivalente MP más barato
      - Si el usuario compra marca PROPIA → informar cuánto pagaría de más
        comprando el equivalente comercial (confirmación de ahorro)

    Solo devuelve alternativas con similitud ≥ 0.80 y misma unidad de medida.
    """
    if df_equiv.empty:
        return {"error": "Equivalencias NLP no disponibles"}

    top1 = df_equiv[df_equiv["rank"] == 1].copy()
    recomendaciones = []
    ahorro_total = 0.0

    for prod in productos:
        ref = prod["referencia"]
        cantidad = prod.get("cantidad_mensual", 1)

        # Buscar como marca propia (ref es MP → el equivalente es COM)
        match_mp = top1[top1["ref_mp"] == ref]
        # Buscar como marca comercial (ref es COM → el equivalente es MP)
        match_com = top1[top1["ref_com"] == ref]

        if not match_mp.empty:
            row = match_mp.iloc[0]
            # El usuario compra MP — ¿la alternativa COM es más cara o más barata?
            precio_usuario = row["precio_mp"]
            precio_alt = row["precio_com"]
            titulo_usuario = row["titulo_mp"]
            titulo_alt = row["titulo_com"]
            tipo_usuario = "marca_propia"
            tipo_alt = "comercial"
            ref_alt = int(row["ref_com"])
            similitud = row["similitud"]
            misma_unidad = row["misma_unidad"]
            dif_por_medida_pct = row.get("diferencia_por_medida_pct", None)
        elif not match_com.empty:
            row = match_com.iloc[0]
            # El usuario compra COM — ¿existe un MP más barato?
            precio_usuario = row["precio_com"]
            precio_alt = row["precio_mp"]
            titulo_usuario = row["titulo_com"]
            titulo_alt = row["titulo_mp"]
            tipo_usuario = "comercial"
            tipo_alt = "marca_propia"
            ref_alt = int(row["ref_mp"])
            similitud = row["similitud"]
            misma_unidad = row["misma_unidad"]
            # Invertir el signo: dif_por_medida_pct en equivalencias es COM-MP
            raw_dif = row.get("diferencia_por_medida_pct", None)
            dif_por_medida_pct = -raw_dif if pd.notna(raw_dif) else None
        else:
            # No hay equivalencia NLP para este producto
            continue

        ahorro_unitario = precio_usuario - precio_alt
        ahorro_mensual = ahorro_unitario * cantidad
        ahorro_pct = (ahorro_unitario / precio_usuario * 100) if precio_usuario > 0 else 0

        # Solo recomendar si la alternativa es realmente más barata
        es_mas_barata = ahorro_unitario > 0
        if es_mas_barata:
            ahorro_total += ahorro_mensual

        recomendaciones.append({
            "referencia_actual": int(ref),
            "titulo_actual": str(titulo_usuario),
            "tipo_actual": str(tipo_usuario),
            "precio_actual": float(round(precio_usuario, 2)),
            "referencia_alternativa": int(ref_alt),
            "titulo_alternativa": str(titulo_alt),
            "tipo_alternativa": str(tipo_alt),
            "precio_alternativa": float(round(precio_alt, 2)),
            "similitud_nlp": float(round(similitud, 4)),
            "misma_unidad_medida": bool(misma_unidad),
            "diferencia_por_medida_pct": float(round(dif_por_medida_pct, 2)) if pd.notna(dif_por_medida_pct) else None,
            "cantidad_mensual": int(cantidad),
            "ahorro_unitario": float(round(ahorro_unitario, 2)),
            "ahorro_mensual": float(round(ahorro_mensual, 2)),
            "ahorro_pct": float(round(ahorro_pct, 1)),
            "es_mas_barata": bool(es_mas_barata),
        })

    # Ordenar: primero las que ahorran más
    recomendaciones.sort(key=lambda x: x["ahorro_mensual"], reverse=True)

    n_con_ahorro = sum(1 for r in recomendaciones if r["es_mas_barata"])
    n_sin_equiv = len(productos) - len(recomendaciones)

    return {
        "n_productos_cesta": int(len(productos)),
        "n_con_alternativa": int(len(recomendaciones)),
        "n_con_ahorro": int(n_con_ahorro),
        "n_sin_equivalencia": int(n_sin_equiv),
        "ahorro_total_mensual": float(round(ahorro_total, 2)),
        "recomendaciones": recomendaciones,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "productos": len(df_catalogo),
            "fecha_actual": FECHA_ACTUAL.date().isoformat(),
            "fecha_base": FECHA_BASE.date().isoformat(),
            "perfiles_disponibles": list(CESTAS_PREDEFINIDAS.keys()),
            "predicciones_lstm": not df_lstm.empty,
            "equivalencias_nlp": not df_equiv.empty,
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


@app.route("/api/cestas")
def cestas():
    """
    Lista los perfiles de cesta predefinidos.

    Respuesta:
      {
        "perfiles": {
          "familiar": {
            "nombre": "Cesta familiar",
            "descripcion": "...",
            "n_productos": 12,
            "productos": [{"referencia": 10380, "titulo": "...", ...}, ...]
          },
          ...
        }
      }
    """
    perfiles = {}
    for clave, perfil in CESTAS_PREDEFINIDAS.items():
        perfiles[clave] = {
            "nombre": perfil["nombre"],
            "descripcion": perfil["descripcion"],
            "n_productos": len(perfil["productos"]),
            "productos": [
                {
                    "referencia": p["referencia"],
                    "titulo": titulo_producto(p["referencia"]),
                    "cantidad_mensual": p["cantidad_mensual"],
                }
                for p in perfil["productos"]
            ],
        }
    return jsonify({"perfiles": perfiles})


@app.route("/api/ipc", methods=["POST"])
def ipc():
    """
    Calcula el IPC ponderado de una cesta personalizada.

    Acepta tres formatos de entrada:

    1. Productos con cantidades (RECOMENDADO):
      {
        "productos": [
          {"referencia": 10380, "cantidad_mensual": 8},
          {"referencia": 5044,  "cantidad_mensual": 3}
        ],
        "nombre_cesta": "Mi cesta"
      }

    2. Perfil predefinido:
      {"perfil": "familiar"}

    3. Solo referencias (retrocompatible — pesos iguales):
      {"referencias": [10380, 5044, 17108]}

    Los pesos se calculan automáticamente:
      gasto_i = precio_base_i × cantidad_mensual_i
      peso_i  = gasto_i / gasto_total

    Respuesta:
      {
        "nombre_cesta": "...",
        "fecha_base": "2025-11-03",
        "ipc_actual": 108.3,
        "variacion_total": "+8.3%",
        "gasto_total_estimado": 42.50,
        "fechas": [...],
        "ipc_cesta": [100, 101.2, ...],
        "por_producto": {
          "10380": {
            "titulo": "leche entera hacendado",
            "indices": [...],
            "cantidad_mensual": 8,
            "precio_base": 0.96,
            "gasto_estimado": 7.68,
            "peso": 0.1807
          }
        }
      }
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "Body JSON requerido"}), 400

    # ── Formato 1: perfil predefinido ──
    if "perfil" in body:
        perfil = body["perfil"]
        if perfil not in CESTAS_PREDEFINIDAS:
            return jsonify(
                {
                    "error": f"Perfil '{perfil}' no encontrado",
                    "perfiles_disponibles": list(CESTAS_PREDEFINIDAS.keys()),
                }
            ), 404
        productos = CESTAS_PREDEFINIDAS[perfil]["productos"]
        nombre = body.get("nombre_cesta", CESTAS_PREDEFINIDAS[perfil]["nombre"])

    # ── Formato 2: productos con cantidades (recomendado) ──
    elif "productos" in body:
        productos = [
            {
                "referencia": int(p["referencia"]),
                "cantidad_mensual": int(p.get("cantidad_mensual", 1)),
            }
            for p in body["productos"]
        ]
        nombre = body.get("nombre_cesta", "Cesta personalizada")

    # ── Formato 3: retrocompatible — solo referencias (pesos iguales) ──
    elif "referencias" in body:
        productos = [
            {"referencia": int(r), "cantidad_mensual": 1} for r in body["referencias"]
        ]
        nombre = body.get("nombre_cesta", "Cesta personalizada")

    else:
        return jsonify(
            {
                "error": "Se requiere 'productos', 'referencias' o 'perfil'",
                "ejemplo_productos": [
                    {"referencia": 10380, "cantidad_mensual": 8},
                    {"referencia": 5044, "cantidad_mensual": 3},
                ],
                "perfiles_disponibles": list(CESTAS_PREDEFINIDAS.keys()),
            }
        ), 400

    if not productos:
        return jsonify({"error": "Lista de productos vacía"}), 400

    resultado = calcular_ipc_cesta(productos)
    if "error" in resultado:
        return jsonify(resultado), 404

    # Enriquecer con variación total y IPC actual
    ipc_actual = resultado["ipc_cesta"][-1] if resultado["ipc_cesta"] else 100.0
    resultado["nombre_cesta"] = nombre
    resultado["ipc_actual"] = round(ipc_actual, 2)
    resultado["variacion_total"] = f"{ipc_actual - 100:+.1f}%"

    return jsonify(resultado)


def _parsear_productos_body(body: dict) -> tuple[list[dict], str] | tuple[None, dict]:
    """
    Extrae lista de productos + nombre de cesta desde el body JSON.
    Soporta los 3 formatos: perfil, productos con cantidades, referencias.
    Retorna (productos, nombre) o (None, error_dict).
    """
    if "perfil" in body:
        perfil = body["perfil"]
        if perfil not in CESTAS_PREDEFINIDAS:
            return None, {
                "error": f"Perfil '{perfil}' no encontrado",
                "perfiles_disponibles": list(CESTAS_PREDEFINIDAS.keys()),
            }
        return CESTAS_PREDEFINIDAS[perfil]["productos"], body.get(
            "nombre_cesta", CESTAS_PREDEFINIDAS[perfil]["nombre"]
        )
    elif "productos" in body:
        return [
            {
                "referencia": int(p["referencia"]),
                "cantidad_mensual": int(p.get("cantidad_mensual", 1)),
            }
            for p in body["productos"]
        ], body.get("nombre_cesta", "Cesta personalizada")
    elif "referencias" in body:
        return [
            {"referencia": int(r), "cantidad_mensual": 1} for r in body["referencias"]
        ], body.get("nombre_cesta", "Cesta personalizada")
    else:
        return None, {
            "error": "Se requiere 'productos', 'referencias' o 'perfil'",
            "ejemplo_productos": [
                {"referencia": 10380, "cantidad_mensual": 8},
                {"referencia": 5044, "cantidad_mensual": 3},
            ],
            "perfiles_disponibles": list(CESTAS_PREDEFINIDAS.keys()),
        }


@app.route("/api/ipc/prediccion", methods=["POST"])
def ipc_prediccion():
    """
    Predice el coste futuro de una cesta.

    Combina dos señales por producto:
      - prob_cambio_lstm : probabilidad de cambio de precio (LSTM clasificador)
      - mediana_cambio   : tendencia histórica (mediana de cambios reales)

    Fórmula:
      precio_predicho = precio_actual × (1 + prob_cambio × mediana_cambio%)

    Acepta los mismos 3 formatos que /api/ipc:
      {"productos": [...]}, {"perfil": "familiar"}, {"referencias": [...]}

    Query params:
      horizonte : días a futuro (default 30, max 90)

    Respuesta:
      {
        "nombre_cesta": "...",
        "horizonte_dias": 30,
        "coste_actual": 125.40,
        "coste_predicho": 123.80,
        "variacion_esperada": "-1.28%",
        "desglose": [{...}, ...]
      }
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "Body JSON requerido"}), 400

    productos, nombre = _parsear_productos_body(body)
    if productos is None:
        return jsonify(nombre), 400  # nombre contiene el error_dict

    if not productos:
        return jsonify({"error": "Lista de productos vacía"}), 400

    horizonte = min(int(request.args.get("horizonte", 30)), 90)

    resultado = calcular_prediccion_cesta(productos, horizonte_dias=horizonte)
    if "error" in resultado:
        return jsonify(resultado), 503

    resultado["nombre_cesta"] = nombre
    return jsonify(resultado)


@app.route("/api/recomendaciones", methods=["POST"])
def recomendaciones():
    """
    Recomienda alternativas más baratas para los productos de una cesta.

    Para cada producto busca su equivalente NLP (marca propia ↔ comercial)
    y calcula el ahorro potencial si se sustituye.

    Lógica bidireccional:
      - Compras marca comercial → te sugiere Hacendado/Bosque Verde más barato
      - Compras marca propia → te confirma cuánto ahorras vs la comercial

    Acepta los mismos 3 formatos que /api/ipc.

    Respuesta:
      {
        "nombre_cesta": "...",
        "ahorro_total_mensual": 12.35,
        "n_con_ahorro": 5,
        "recomendaciones": [
          {
            "titulo_actual": "cacao soluble instantáneo nesquik",
            "titulo_alternativa": "cacao soluble hacendado",
            "ahorro_unitario": 11.25,
            "ahorro_mensual": 11.25,
            "similitud_nlp": 0.9232,
            ...
          }
        ]
      }
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "Body JSON requerido"}), 400

    productos, nombre = _parsear_productos_body(body)
    if productos is None:
        return jsonify(nombre), 400

    if not productos:
        return jsonify({"error": "Lista de productos vacía"}), 400

    resultado = buscar_alternativas_cesta(productos)
    if "error" in resultado:
        return jsonify(resultado), 503

    resultado["nombre_cesta"] = nombre
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
