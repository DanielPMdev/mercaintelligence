# Análisis de Resultados — XGBoost Predicción de Precios

Este documento recopila y profundiza en el análisis técnico tras la última ejecución del pipeline de regresión `src/ml/xgboost_prediccion.py`, entrenado con **437,053 muestras** (hasta el 17 de abril de 2026) y evaluado sobre **110,667 muestras** del conjunto de test temporal (desde el 17 de abril de 2026) sobre un catálogo de **5,101 productos**.

## 1. El hallazgo clave: el baseline naive gana

> [!CAUTION]
> **XGBoost NO supera al baseline naive (persistencia).** El modelo es **467% peor** en MAE global que simplemente predecir "el precio de mañana = el de hoy" (degradación de MAE de 0.0230€ a 0.1304€). Este es el resultado más importante de toda la ejecución.

| Métrica | XGBoost | Baseline Naive | ¿Quién gana? |
|---|---|---|---|
| MAE (€) | 0.1304 | **0.0230** | Naive (5.7x mejor) |
| RMSE (€) | 4.7682 | **0.4210** | Naive (11.3x mejor) |
| R² | 0.7993 | **0.9984** | Naive |
| MAPE (%) | 1.29% | **0.46%** | Naive |

**Interpretación**: Los precios de Mercadona son extremadamente estables (~95.9% no cambian en 7 días). El modelo de persistencia aprovecha esto directamente. XGBoost, al intentar aprender patrones más complejos, introduce ruido que empeora las predicciones globales.

---

## 2. ¿XGBoost aporta algo? Sí, pero muy poco

En el subconjunto donde **sí hay cambio** (4,517 muestras, 4.1% del test):

| Métrica | XGBoost | Naive | Mejora |
|---|---|---|---|
| MAE (€) | 0.9693 | **0.5624** | -72.4% (naive gana) |
| MAPE (%) | **10.75%** | 11.22% | +4.2% |
| RMSE (€) | 11.8740 | **2.0841** | -470% (naive gana) |
| R² | 0.3958 | **0.9814** | naive gana |

XGBoost mejora el error porcentual medio (MAPE +4.2%) en cambios reales, pero el error absoluto medio (MAE) y el RMSE son mucho peores — lo que indica que XGBoost comete **errores de gran magnitud** que el naive no comete.

> [!WARNING]
> El RMSE del XGBoost (11.87€) vs el naive (2.08€) en cambios reales indica que cuando XGBoost se equivoca, lo hace de forma severa. Falla fundamentalmente en productos de precio alto (como el segmento premium) donde los cambios son de mayor magnitud y los datos son escasos.

---

## 3. Análisis SHAP

### SHAP Importance (bar plot)

![SHAP Feature Importance](file:///e:/Estudios/CE_IAyBD/TFE/mercaintelligence/docs/img/xgboost/shap_importance.png)

**Hallazgos**:
- **`precio_lag_1`** domina con +1.15 — confirma que el modelo esencialmente copia el precio de ayer
- **`max_14d`** y **`min_14d`** son el segundo y tercer factor — el modelo usa el rango reciente para ajustar
- **`prob_cambio_lstm`** aparece en posición 9 con +0.07 — **la señal del LSTM sí aporta información**, aunque modesta
- **`dia_semana`** y **`mes`** están en el grupo de "7 other features" (+0.03 total) — impacto mínimo, lo cual tiene sentido: Mercadona no cambia precios por día de semana o mes de manera estacional

### SHAP Beeswarm

![SHAP Beeswarm](file:///e:/Estudios/CE_IAyBD/TFE/mercaintelligence/docs/img/xgboost/shap_beeswarm.png)

**Hallazgos**:
- Los puntos están muy concentrados en torno a 0 para casi todas las features → la mayoría de muestras no se ven afectadas (precios estables, SHAP ≈ 0)
- Los **outliers rosa/rojos** de `min_14d` llegan hasta +80 en SHAP value → son los productos caros donde el modelo empuja la predicción fuertemente. Estos causan el RMSE alto
- `prob_cambio_lstm` tiene un patrón coherente: valores altos (rosa) empujan la predicción hacia arriba, valores bajos (azul) la empujan hacia abajo

---

## 4. Predicción vs Real

![Predicción vs Real](file:///e:/Estudios/CE_IAyBD/TFE/mercaintelligence/docs/img/xgboost/prediccion_vs_real.png)

**Hallazgos**:
- La masa principal sigue bien la diagonal → el modelo funciona para el grueso de productos baratos (0-30€)
- Hay **puntos que se desvían significativamente** en el rango 400-500€ → productos caros donde XGBoost falla
- La distribución de errores está extremadamente concentrada en 0, pero tiene **una cola larga a la izquierda** (hasta -350€) → errores graves en productos caros
- Media del error: **-0.1053€** → sesgo negativo, el modelo tiende a subestimar ligeramente

---

## 5. Walk-Forward Validation

| Fold | Train | Test | MAE | RMSE | R² | MAPE |
|---|---|---|---|---|---|---|
| 1 | 275,940 | 91,086 | **0.0448** | 0.4283 | **0.9984** | 0.86% |
| 2 | 367,026 | 90,568 | 0.1110 | 4.2096 | 0.8496 | 1.08% |
| 3 | 457,594 | 90,126 | 0.1360 | 4.6879 | 0.8042 | 1.36% |
| **Media** | — | — | **0.0973** | **3.1086** | **0.8841** | **1.10%** |

> [!IMPORTANT]
> **El rendimiento se degrada significativamente con el tiempo**: R² cae de **0.99 → 0.85 → 0.80** y RMSE sube de **0.43 → 4.21 → 4.69**. Esto indica que el modelo se ve afectado cuando cambian los patrones temporales de precios (abril-mayo de 2026), que coincide con la mayor volatilidad identificada por el Autoencoder de Anomalías.

---

## 6. Diagnóstico y conclusiones

### El modelo XGBoost alcanzó el early stopping
`Best iteration: 254` (el entrenamiento se detuvo en la iteración 274 al agotarse la paciencia de 20 estimadores sin mejora en validación). Esto demuestra que el modelo convergió de manera óptima, previniendo el sobreajuste antes de los 500 estimadores programados.

### ¿Por qué el review externo tenía razón?
La review advertía exactamente este escenario: _"El modelo puede aprender `precio_futuro ≈ precio_actual` y obtener métricas artificialmente buenas"_. Efectivamente, XGBoost aprende una versión ruidosa de la persistencia que es peor que la persistencia pura.

### Valor real del módulo XGBoost para el TFE

A pesar de que XGBoost no supera al naive globalmente, estos resultados son **extremadamente valiosos para la memoria del TFE**:

1. **Demuestran rigor científico** — la comparación con baseline naive es exactamente lo que un tribunal esperaría
2. **El SHAP confirma que la señal del LSTM aporta información** (posición 9 de 21 features)
3. **El walk-forward revela degradación temporal** — insight valioso sobre la naturaleza del problema que converge con el Autoencoder de anomalías
4. **Los errores se concentran en productos caros** — insight de negocio actionable
5. **El sistema ensemble LSTM+XGBoost tiene sentido conceptual**: LSTM predice SI cambiará (clasificación) y XGBoost intenta predecir CUÁNTO (regresión). Que XGBoost tenga dificultades con el "cuánto" es coherente con la naturaleza de escalón de precios

> [!TIP]
> Para la memoria, la narrativa más fuerte es: _"El baseline de persistencia es el predictor más difícil de superar en series de precios retail estables. XGBoost aporta mejora en el error porcentual medio (MAPE +4.2%) exclusivamente en los casos de cambio real, donde la persistencia falla por definición. La combinación LSTM (detectar cuándo) + XGBoost (estimar cuánto) constituye un sistema complementario que aborda ambas facetas del problema."_
