"""
xgboost_prediccion.py

Predicción del precio exacto (€) a 7 días vista mediante XGBoost Regressor.

Complementa al LSTM clasificador del Sprint 3:
  - LSTM  → predice SI habrá cambio de precio (clasificación binaria)
  - XGBoost → predice CUÁNTO costará el producto (regresión sobre precio)

Por qué XGBoost para regresión de precios:
  1. Robusto a outliers — los precios de Mercadona tienen colas largas
     (productos de 0.30€ y de 150€ en el mismo dataset). Los árboles
     de decisión son insensibles a la escala absoluta.
  2. Maneja bien features heterogéneas — mezcla de features continuas
     (precio_actual, precio_por_medida) y discretas (categoria, marca).
  3. No requiere stationariedad — a diferencia de ARIMA/Prophet, no
     asume que la serie es estacionaria. Útil con precios que tienen
     escalones (subidas puntuales sin reversión).
  4. Interpretable — feature importance explica qué variables impulsan
     la predicción, lo que es valioso para la memoria.

Features:
  Temporales  : precio de los últimos 7/14/30 días, media, std, tendencia
  Calendario  : día de la semana, mes (estacionalidad)
  Del producto: precio_por_medida, categoria (encoded), marca_propia
  Contexto    : días_desde_último_cambio, n_cambios_históricos
  LSTM        : probabilidad de cambio predicha por el LSTM clasificador

Target:
  precio_actual en t+7 (precio dentro de 7 días)
"""

import pandas as pd
import numpy as np
import logging
import joblib
import matplotlib.pyplot as plt
from pathlib import Path
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")
log = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
PARTITIONED_DIR = Path("data/processed")
MODEL_PATH = Path("models/xgboost_precio.pkl")
RESULTS_PATH = Path("data/predicciones/xgboost/predicciones.parquet")
IMG_DIR = Path("docs/img/xgboost")

HORIZONTE = 7  # días a predecir
LAGS = [1, 3, 7, 14, 30]  # días de historia como features
MIN_DIAS = 45  # mínimo de días para incluir un producto
TEST_SIZE = 0.2  # proporción temporal del test set

IMG_DIR.mkdir(parents=True, exist_ok=True)


# ── Carga ─────────────────────────────────────────────────────────────────────
def cargar_datos() -> pd.DataFrame:
    cols = [
        "referencia",
        "fecha",
        "precio_actual",
        "precio_por_medida",
        "categoria",
        "subcategoria",
        "marca_propia",
        "es_marca_propia",
        "titulo",
    ]

    df = pd.read_parquet(PARTITIONED_DIR, columns=cols)
    df["fecha"] = pd.to_datetime(df["fecha"].astype(str))

    lstm_path = Path("data/predicciones/lstm/lstm_resultados.parquet")
    if lstm_path.exists():
        df_lstm = pd.read_parquet(lstm_path, columns=["referencia", "fecha", "prob_cambio_lstm"])
        df_lstm["fecha"] = pd.to_datetime(df_lstm["fecha"].astype(str))
        df = df.merge(df_lstm, on=["referencia", "fecha"], how="left")
        df["prob_cambio_lstm"] = df["prob_cambio_lstm"].fillna(0.0)
    else:
        df["prob_cambio_lstm"] = 0.0

    df = df.sort_values(["referencia", "fecha"]).reset_index(drop=True)

    log.info(f"Datos: {len(df):,} filas | {df['referencia'].nunique():,} productos")
    return df


# ── Feature Engineering ───────────────────────────────────────────────────────
def construir_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye features para XGBoost a partir de las series temporales.

    Lags (precio hace N días):
      Son las features más importantes — el precio de ayer es el mejor
      predictor del precio de mañana en series estables.

    Rolling statistics:
      Media y std en ventanas de 7 y 14 días — capturan nivel y volatilidad
      reciente sin depender de un único día (robusto a outliers).

    Tendencia (slope):
      Diferencia entre precio actual y hace 14 días — captura si el precio
      está subiendo, bajando o estable en el período reciente.

    Features del producto:
      categoria y marca_propia codificadas — XGBoost puede aprender que
      ciertos tipos de producto tienen mayor volatilidad de precio.
    """
    log.info("Construyendo features...")

    # Encoders para variables categóricas
    le_cat = LabelEncoder()
    le_marca = LabelEncoder()
    df["categoria_enc"] = le_cat.fit_transform(df["categoria"].astype(str))
    df["marca_enc"] = le_marca.fit_transform(df["marca_propia"].astype(str))

    # Guardar encoders para inferencia
    joblib.dump(
        {"categoria": le_cat, "marca": le_marca}, Path("models/xgboost_encoders.pkl")
    )

    resultado = []

    for ref, grupo in df.groupby("referencia"):
        grupo = grupo.sort_values("fecha").reset_index(drop=True)

        if len(grupo) < MIN_DIAS + HORIZONTE:
            continue

        precios = grupo["precio_actual"].values

        for i in range(max(LAGS) + HORIZONTE, len(grupo)):
            fila = grupo.iloc[i]

            # Lags de precio
            features = {
                "ref": ref,
                "fecha": fila["fecha"],
                "precio_actual": precios[i],
                "target": precios[i],  # precio en t (predecimos t+HORIZONTE)
            }

            # El target es el precio HORIZONTE días hacia adelante
            if i + HORIZONTE < len(grupo):
                features["target"] = grupo.iloc[i + HORIZONTE]["precio_actual"]
            else:
                continue  # no hay target futuro disponible

            # Lags
            for lag in LAGS:
                features[f"precio_lag_{lag}"] = precios[i - lag]

            # Rolling stats (ventana 7 días)
            ventana_7 = precios[i - 7 : i]
            ventana_14 = precios[i - 14 : i]

            features["media_7d"] = ventana_7.mean()
            features["std_7d"] = ventana_7.std()
            features["media_14d"] = ventana_14.mean()
            features["std_14d"] = ventana_14.std()
            features["min_14d"] = ventana_14.min()
            features["max_14d"] = ventana_14.max()

            # Tendencia: slope de los últimos 14 días
            features["tendencia_14d"] = precios[i] - precios[i - 14]

            # Días desde último cambio de precio
            cambios = np.where(np.diff(precios[:i]) != 0)[0]
            features["dias_desde_cambio"] = (
                (i - cambios[-1] - 1) if len(cambios) > 0 else i
            )
            features["n_cambios_total"] = len(cambios)

            # Features del producto
            features["precio_por_medida"] = fila["precio_por_medida"] if pd.notna(fila["precio_por_medida"]) else 0
            features["categoria_enc"] = fila["categoria_enc"]
            features["marca_enc"] = fila["marca_enc"]
            features["es_marca_propia"] = int(fila["es_marca_propia"])
            features["prob_cambio_lstm"] = fila["prob_cambio_lstm"]

            # Features de calendario (estacionalidad)
            fecha_fila = pd.Timestamp(fila["fecha"])
            features["dia_semana"] = fecha_fila.dayofweek   # 0=lunes … 6=domingo
            features["mes"] = fecha_fila.month              # 1-12

            resultado.append(features)

    df_features = pd.DataFrame(resultado)
    df_features = df_features.fillna(0)

    log.info(
        f"Features construidas: {len(df_features):,} muestras | "
        f"{df_features.shape[1]} columnas"
    )
    return df_features


# ── Train / Test split temporal ───────────────────────────────────────────────
def split_temporal(df: pd.DataFrame) -> tuple:
    """
    Split temporal estricto — no aleatorio.
    El 80% de las fechas más antiguas para train,
    el 20% más recientes para test.
    """
    fechas = df["fecha"].sort_values().unique()
    corte_idx = int(len(fechas) * (1 - TEST_SIZE))
    fecha_corte = fechas[corte_idx]

    train = df[df["fecha"] < fecha_corte].copy()
    test = df[df["fecha"] >= fecha_corte].copy()

    log.info(f"Train: {len(train):,} muestras hasta {fecha_corte.date()}")
    log.info(f"Test : {len(test):,}  muestras desde {fecha_corte.date()}")

    return train, test, fecha_corte


# ── Entrenamiento ─────────────────────────────────────────────────────────────
FEATURE_COLS = [
    "precio_lag_1",
    "precio_lag_3",
    "precio_lag_7",
    "precio_lag_14",
    "precio_lag_30",
    "media_7d",
    "std_7d",
    "media_14d",
    "std_14d",
    "min_14d",
    "max_14d",
    "tendencia_14d",
    "dias_desde_cambio",
    "n_cambios_total",
    "precio_por_medida",
    "categoria_enc",
    "marca_enc",
    "es_marca_propia",
    "prob_cambio_lstm",
    "dia_semana",
    "mes",
]

N_WALK_FORWARD_FOLDS = 3  # número de folds para walk-forward validation


def entrenar(train: pd.DataFrame) -> XGBRegressor:
    modelo = XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_alpha=0.1,  # L1 regularización
        reg_lambda=1.0,  # L2 regularización
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=20,
        eval_metric="mae",
    )

    # Validación cruzada temporal para early stopping
    fechas_train = train["fecha"].sort_values().unique()
    corte_val = int(len(fechas_train) * 0.85)
    fecha_val = fechas_train[corte_val]

    mask_val = train["fecha"] >= fecha_val
    X_val = train[mask_val][FEATURE_COLS].values
    y_val = train[mask_val]["target"].values
    X_tr = train[~mask_val][FEATURE_COLS].values
    y_tr = train[~mask_val]["target"].values

    log.info(
        f"Entrenando XGBoost "
        f"(n_estimators={modelo.n_estimators}, "
        f"early_stopping={modelo.early_stopping_rounds})..."
    )

    modelo.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=50)

    log.info(f"Best iteration: {modelo.best_iteration}")
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, MODEL_PATH)
    log.info(f"Modelo guardado: {MODEL_PATH}")

    return modelo


# ── Evaluación ────────────────────────────────────────────────────────────────
def _calcular_metricas(y_test: np.ndarray, y_pred: np.ndarray) -> dict:
    """Calcula MAE, RMSE, R² y MAPE para un par real/predicho."""
    mae = mean_absolute_error(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred) ** 0.5
    r2 = r2_score(y_test, y_pred)
    mask_nz = y_test != 0
    mape = (
        np.mean(np.abs((y_test[mask_nz] - y_pred[mask_nz]) / y_test[mask_nz])) * 100
        if mask_nz.any()
        else 0.0
    )
    return {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "R²": round(r2, 4),
        "MAPE": round(mape, 2),
    }


def _log_metricas(titulo: str, metricas: dict) -> None:
    """Imprime un bloque de métricas con formato consistente."""
    log.info("─" * 55)
    log.info(titulo)
    log.info(f"  MAE  (€)     : {metricas['MAE']:.4f}  ← error medio absoluto")
    log.info(f"  RMSE (€)     : {metricas['RMSE']:.4f} ← penaliza errores grandes")
    log.info(f"  R²           : {metricas['R²']:.4f}  ← varianza explicada (1=perfecto)")
    log.info(f"  MAPE (%)     : {metricas['MAPE']:.2f}% ← error porcentual medio")
    log.info("─" * 55)


def evaluar(modelo: XGBRegressor, test: pd.DataFrame) -> dict:
    X_test = test[FEATURE_COLS].values
    y_test = test["target"].values
    precio_actual = test["precio_actual"].values

    y_pred = modelo.predict(X_test)

    # ── 1. Métricas globales XGBoost ──────────────────────────────────────────
    metricas = _calcular_metricas(y_test, y_pred)
    _log_metricas("EVALUACIÓN XGBOOST — conjunto test (split temporal)", metricas)

    # ── 2. Baseline naive: pred = precio_actual (persistencia) ────────────────
    #   Si el modelo no supera al baseline, no está aportando valor real.
    #   El precio retail es muy estable (~95% días sin cambio), por lo que
    #   la persistencia es un competidor muy fuerte.
    y_naive = precio_actual  # "el precio de mañana = el de hoy"
    metricas_naive = _calcular_metricas(y_test, y_naive)
    _log_metricas("BASELINE NAIVE (persistencia: pred = precio_actual)", metricas_naive)

    mejora_mae = ((metricas_naive["MAE"] - metricas["MAE"]) / metricas_naive["MAE"] * 100
                  if metricas_naive["MAE"] > 0 else 0.0)
    log.info(f"  → XGBoost mejora MAE en {mejora_mae:.1f}% vs baseline naive")

    # ── 3. Evaluación condicional: solo muestras con cambio real de precio ────
    #   Cuando target == precio_actual, cualquier modelo trivial acierta.
    #   La verdadera prueba es predecir bien cuando SÍ hay cambio.
    mask_cambio = y_test != precio_actual
    n_cambio = mask_cambio.sum()
    n_total = len(y_test)
    log.info("─" * 55)
    log.info(
        f"Muestras con cambio real de precio: {n_cambio:,} / {n_total:,} "
        f"({n_cambio / n_total * 100:.1f}%)"
    )
    if n_cambio > 0:
        metricas_cambio = _calcular_metricas(y_test[mask_cambio], y_pred[mask_cambio])
        _log_metricas(
            "EVALUACIÓN XGBOOST — solo muestras con cambio de precio",
            metricas_cambio,
        )
        metricas_naive_cambio = _calcular_metricas(
            y_test[mask_cambio], y_naive[mask_cambio]
        )
        _log_metricas(
            "BASELINE NAIVE — solo muestras con cambio de precio",
            metricas_naive_cambio,
        )
        mejora_cambio = (
            (metricas_naive_cambio["MAE"] - metricas_cambio["MAE"])
            / metricas_naive_cambio["MAE"]
            * 100
            if metricas_naive_cambio["MAE"] > 0
            else 0.0
        )
        log.info(
            f"  → XGBoost mejora MAE en {mejora_cambio:.1f}% vs naive "
            f"(solo cambios)"
        )
    else:
        log.info("  Sin cambios de precio en test — evaluación condicional omitida")

    return metricas, y_pred


# ── SHAP Feature Importance ───────────────────────────────────────────────────
def plot_feature_importance(modelo: XGBRegressor, test: pd.DataFrame) -> None:
    """
    SHAP (SHapley Additive exPlanations) ofrece importancias más fiables
    que la feature_importances_ nativa de XGBoost, ya que:
      - No tiene bias hacia variables de alta cardinalidad.
      - Descompone la contribución de cada feature por muestra individual.
      - Es aditivo: las contribuciones suman la predicción final.

    Para mantener el tiempo de cómputo razonable, calculamos SHAP sobre
    un subconjunto aleatorio de 5000 muestras del test set.
    """
    try:
        import shap
    except ImportError:
        log.warning("SHAP no instalado — usando feature_importances_ estándar")
        _plot_feature_importance_fallback(modelo)
        return

    log.info("Calculando SHAP values (puede tardar unos segundos)...")

    # Subconjunto para velocidad
    n_sample = min(5000, len(test))
    X_sample = test[FEATURE_COLS].sample(n=n_sample, random_state=42)

    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer(X_sample)

    # ── Plot 1: importancia global (bar) ──────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 8))
    shap.plots.bar(shap_values, max_display=15, show=False)
    plt.title("XGBoost — SHAP Feature Importance (top 15)")
    plt.tight_layout()
    plt.savefig(IMG_DIR / "shap_importance.png", dpi=150, bbox_inches="tight")
    plt.show()
    log.info(f"SHAP importance guardada: {IMG_DIR}/shap_importance.png")

    # ── Plot 2: beeswarm (impacto por valor de feature) ───────────────────────
    fig, ax = plt.subplots(figsize=(10, 8))
    shap.plots.beeswarm(shap_values, max_display=15, show=False)
    plt.title("XGBoost — SHAP Beeswarm (impacto por valor de feature)")
    plt.tight_layout()
    plt.savefig(IMG_DIR / "shap_beeswarm.png", dpi=150, bbox_inches="tight")
    plt.show()
    log.info(f"SHAP beeswarm guardada: {IMG_DIR}/shap_beeswarm.png")


def _plot_feature_importance_fallback(modelo: XGBRegressor) -> None:
    """Fallback si SHAP no está instalado: usa feature_importances_ nativa."""
    importance = (
        pd.Series(modelo.feature_importances_, index=FEATURE_COLS)
        .sort_values(ascending=True)
        .tail(15)
    )

    fig, ax = plt.subplots(figsize=(10, 8))
    importance.plot(kind="barh", ax=ax, color="steelblue", alpha=0.8)
    ax.axvline(0, color="black", linewidth=0.5)
    ax.set_title("XGBoost — Feature Importance (top 15)")
    ax.set_xlabel("Importance score")
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(IMG_DIR / "feature_importance.png", dpi=150, bbox_inches="tight")
    plt.show()
    log.info(f"Feature importance guardada: {IMG_DIR}/feature_importance.png")


# ── Plot predicción vs real ───────────────────────────────────────────────────
def plot_prediccion_vs_real(test: pd.DataFrame, y_pred: np.ndarray) -> None:
    """
    Scatter plot de predicción vs valor real.
    Una línea diagonal perfecta = predicción perfecta.
    La dispersión alrededor de la diagonal = error del modelo.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    y_test = test["target"].values

    # Scatter predicción vs real
    axes[0].scatter(y_test, y_pred, alpha=0.1, s=5, color="steelblue")
    lim = max(y_test.max(), y_pred.max())
    axes[0].plot([0, lim], [0, lim], "r--", linewidth=1.5, label="Predicción perfecta")
    axes[0].set_xlabel("Precio real (€)")
    axes[0].set_ylabel("Precio predicho (€)")
    axes[0].set_title("XGBoost: Predicción vs Real")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Distribución del error
    errores = y_pred - y_test
    axes[1].hist(errores, bins=100, alpha=0.7, color="steelblue", edgecolor="white")
    axes[1].axvline(0, color="red", linestyle="--", linewidth=1.5)
    axes[1].axvline(
        errores.mean(),
        color="orange",
        linestyle="--",
        linewidth=1.5,
        label=f"Media: {errores.mean():.4f}€",
    )
    axes[1].set_xlabel("Error (predicho - real) en €")
    axes[1].set_ylabel("Frecuencia")
    axes[1].set_title("Distribución del error de predicción")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.suptitle(f"XGBoost Regressor — Horizonte {HORIZONTE} días", fontsize=13)
    plt.tight_layout()
    plt.savefig(IMG_DIR / "prediccion_vs_real.png", dpi=150, bbox_inches="tight")
    plt.show()


# ── Guardar predicciones ──────────────────────────────────────────────────────
def guardar_predicciones(test: pd.DataFrame, y_pred: np.ndarray) -> None:
    df_pred = test[["ref", "fecha", "precio_actual", "target"]].copy()
    df_pred["precio_predicho_xgb"] = y_pred.round(4)
    df_pred["error_abs"] = (y_pred - test["target"].values).round(4)
    df_pred["error_pct"] = (df_pred["error_abs"] / df_pred["target"] * 100).round(2)
    df_pred = df_pred.rename(columns={"ref": "referencia"})

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_pred.to_parquet(RESULTS_PATH, index=False)
    log.info(f"Predicciones guardadas: {RESULTS_PATH}")


# ── Walk-forward validation ───────────────────────────────────────────────────
def walk_forward_validation(df_features: pd.DataFrame, n_folds: int = N_WALK_FORWARD_FOLDS) -> None:
    """
    Walk-forward validation: simula cómo funcionaría el modelo en producción.

    En vez de un único split train/test, dividimos la línea temporal en
    N folds expansivos:
      Fold 1: train=[0..T1]    test=[T1..T2]
      Fold 2: train=[0..T2]    test=[T2..T3]
      Fold 3: train=[0..T3]    test=[T3..T4]

    El train siempre crece (acumulativo), simulando que cada semana
    reentrenamos con todos los datos disponibles hasta ese momento.
    Esto da una estimación más robusta del error real del modelo.
    """
    log.info("═" * 55)
    log.info(f"WALK-FORWARD VALIDATION ({n_folds} folds)")
    log.info("═" * 55)

    fechas = np.sort(df_features["fecha"].unique())
    n_fechas = len(fechas)

    # Reservamos el primer 50% como train mínimo; el otro 50% se divide en folds
    inicio_test = int(n_fechas * 0.5)
    fechas_test = fechas[inicio_test:]
    fold_size = len(fechas_test) // n_folds

    if fold_size < 7:
        log.warning("  Insuficientes fechas para walk-forward — omitido")
        return

    resultados = []

    for fold in range(n_folds):
        fold_start = fold * fold_size
        fold_end = (fold + 1) * fold_size if fold < n_folds - 1 else len(fechas_test)

        fecha_test_inicio = fechas_test[fold_start]
        fecha_test_fin = fechas_test[fold_end - 1]

        train = df_features[df_features["fecha"] < fecha_test_inicio].copy()
        test = df_features[
            (df_features["fecha"] >= fecha_test_inicio)
            & (df_features["fecha"] <= fecha_test_fin)
        ].copy()

        if len(train) < 100 or len(test) < 10:
            continue

        # Train con early stopping interno
        fechas_train = train["fecha"].sort_values().unique()
        corte_val = int(len(fechas_train) * 0.85)
        fecha_val = fechas_train[corte_val]

        mask_val = train["fecha"] >= fecha_val
        X_val = train[mask_val][FEATURE_COLS].values
        y_val = train[mask_val]["target"].values
        X_tr = train[~mask_val][FEATURE_COLS].values
        y_tr = train[~mask_val]["target"].values

        modelo_fold = XGBRegressor(
            n_estimators=500, learning_rate=0.05, max_depth=6,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
            reg_alpha=0.1, reg_lambda=1.0, random_state=42, n_jobs=-1,
            early_stopping_rounds=20, eval_metric="mae",
        )
        modelo_fold.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=0)

        y_pred = modelo_fold.predict(test[FEATURE_COLS].values)
        y_test = test["target"].values
        metricas_fold = _calcular_metricas(y_test, y_pred)

        log.info(
            f"  Fold {fold + 1}: train={len(train):,} | test={len(test):,} | "
            f"MAE={metricas_fold['MAE']:.4f} | RMSE={metricas_fold['RMSE']:.4f} | "
            f"R²={metricas_fold['R²']:.4f} | MAPE={metricas_fold['MAPE']:.2f}%"
        )
        resultados.append(metricas_fold)

    if resultados:
        mae_medio = np.mean([r["MAE"] for r in resultados])
        rmse_medio = np.mean([r["RMSE"] for r in resultados])
        r2_medio = np.mean([r["R²"] for r in resultados])
        mape_medio = np.mean([r["MAPE"] for r in resultados])
        log.info("─" * 55)
        log.info(
            f"  MEDIA walk-forward: MAE={mae_medio:.4f} | RMSE={rmse_medio:.4f} | "
            f"R²={r2_medio:.4f} | MAPE={mape_medio:.2f}%"
        )
        log.info("═" * 55)


# ── Entrypoint ────────────────────────────────────────────────────────────────
def ejecutar():
    df = cargar_datos()
    df_features = construir_features(df)
    train, test, fecha_corte = split_temporal(df_features)

    modelo = entrenar(train)
    metricas, y_pred = evaluar(modelo, test)

    plot_feature_importance(modelo, test)
    plot_prediccion_vs_real(test, y_pred)
    guardar_predicciones(test, y_pred)

    # Walk-forward validation: estimación más robusta del rendimiento
    walk_forward_validation(df_features)

    return modelo, metricas


if __name__ == "__main__":
    modelo, metricas = ejecutar()
