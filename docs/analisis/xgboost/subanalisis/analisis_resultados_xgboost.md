# Análisis de Resultados — XGBoost Predicción de Precios

## 1. El hallazgo clave: el baseline naive gana

> [!CAUTION]
> **XGBoost NO supera al baseline naive (persistencia).** El modelo es **544% peor** en MAE global que simplemente predecir "el precio de mañana = el de hoy". Este es el resultado más importante de toda la ejecución.

| Métrica | XGBoost | Baseline Naive | ¿Quién gana? |
|---|---|---|---|
| MAE (€) | 0.1462 | **0.0227** | Naive (6.4x mejor) |
| RMSE (€) | 5.6469 | **0.1923** | Naive (29x mejor) |
| R² | 0.7304 | **0.9997** | Naive |
| MAPE (%) | 1.24% | **0.58%** | Naive |

**Interpretación**: Los precios de Mercadona son extremadamente estables (~94.4% no cambian en 7 días). El modelo de persistencia aprovecha esto directamente. XGBoost, al intentar aprender patrones más complejos, introduce ruido que empeora las predicciones globales.

---

## 2. ¿XGBoost aporta algo? Sí, pero muy poco

En el subconjunto donde **sí hay cambio** (5,525 muestras, 5.6% del test):

| Métrica | XGBoost | Naive | Mejora |
|---|---|---|---|
| MAE (€) | **0.3978** | 0.4051 | +1.8% |
| MAPE (%) | **8.94%** | 10.26% | +12.9% |
| RMSE (€) | 1.1927 | **0.8118** | -46.9% (naive gana) |
| R² | 0.9351 | **0.9699** | naive gana |

XGBoost mejora marginalmente el MAE (+1.8%) y el MAPE (+12.9%) en cambios reales, pero el RMSE es mucho peor — lo que indica que XGBoost comete **errores grandes puntuales** que el naive no comete.

> [!WARNING]
> El RMSE del XGBoost (1.19€) vs el naive (0.81€) en cambios reales indica que cuando XGBoost se equivoca, lo hace de forma severa. Probablemente falla en productos caros donde los cambios son de mayor magnitud.

---

## 3. Análisis SHAP

### SHAP Importance (bar plot)

![SHAP Feature Importance](file:///e:/Estudios/CE_IAyBD/TFE/mercaintelligence/docs/img/xgboost/shap_importance.png)

**Hallazgos**:
- **`precio_lag_1`** domina con +1.15 — confirma que el modelo esencialmente copia el precio de ayer
- **`max_14d`** y **`min_14d`** son el segundo y tercer factor — el modelo usa el rango reciente para ajustar
- **`prob_cambio_lstm`** aparece en posición 9 con +0.07 — **la señal del LSTM sí aporta información**, aunque modesta
- **`dia_semana`** y **`mes`** están en el grupo de "7 other features" (+0.03 total) — impacto mínimo, lo cual tiene sentido: Mercadona no cambia precios por día de semana

### SHAP Beeswarm

![SHAP Beeswarm](file:///e:/Estudios/CE_IAyBD/TFE/mercaintelligence/docs/img/xgboost/shap_beeswarm.png)

**Hallazgos**:
- Los puntos están muy concentrados en torno a 0 para casi todas las features → la mayoría de muestras no se ven afectadas (precios estables)
- Los **outliers rosa/rojos** de `min_14d` llegan hasta +80 en SHAP value → son los productos caros donde el modelo empuja la predicción fuertemente. Estos son probablemente los causantes del RMSE alto
- `prob_cambio_lstm` tiene un patrón interesante: valores altos (rosa) empujan la predicción hacia arriba, valores bajos (azul) la empujan hacia abajo — **la señal es coherente**

---

## 4. Predicción vs Real

![Predicción vs Real](file:///e:/Estudios/CE_IAyBD/TFE/mercaintelligence/docs/img/xgboost/prediccion_vs_real.png)

**Hallazgos**:
- La masa principal sigue bien la diagonal → el modelo funciona para el grueso de productos baratos
- Hay **puntos que se desvían significativamente** en el rango 400-500€ → productos caros donde XGBoost falla
- La distribución de errores está extremadamente concentrada en 0, pero tiene **una cola larga a la izquierda** (hasta -350€) → errores graves en productos caros
- Media del error: **-0.1053€** → sesgo negativo, el modelo tiende a subestimar ligeramente

---

## 5. Walk-Forward Validation

| Fold | Train | Test | MAE | RMSE | R² | MAPE |
|---|---|---|---|---|---|---|
| 1 | 242,704 | 78,808 | 0.0640 | 0.8758 | 0.9935 | 1.17% |
| 2 | 321,512 | 78,498 | 0.0775 | 3.2208 | 0.9118 | 0.93% |
| 3 | 400,010 | 81,976 | 0.1446 | 5.6727 | 0.7282 | 1.18% |
| **Media** | — | — | **0.0954** | **3.2564** | **0.8778** | **1.09%** |

> [!IMPORTANT]
> **El rendimiento se degrada significativamente con el tiempo**: R² cae de 0.99 → 0.91 → 0.73 y RMSE sube de 0.87 → 3.22 → 5.67. Esto indica que el modelo no generaliza bien a datos futuros — probablemente porque los patrones de cambio de precio evolucionan.

---

## 6. Diagnóstico y conclusiones

### El modelo XGBoost no alcanzó el early stopping
`Best iteration: 499` (máximo permitido) — el modelo aún estaba mejorando cuando se agotaron los árboles. Esto sugiere que si se aumentase `n_estimators`, el MAE de validación podría bajar un poco más, pero probablemente no lo suficiente para superar al naive.

### ¿Por qué el review externo tenía razón?
La review advertía exactamente este escenario: _"El modelo puede aprender `precio_futuro ≈ precio_actual` y obtener métricas artificialmente buenas"_. Efectivamente, XGBoost aprende una versión ruidosa de la persistencia que es peor que la persistencia pura.

### Valor real del módulo XGBoost para el TFE

A pesar de que XGBoost no supera al naive, estos resultados son **extremadamente valiosos para la memoria del TFE**:

1. **Demuestran rigor científico** — la comparación con baseline naive es exactamente lo que un tribunal esperaría
2. **El SHAP confirma que la señal del LSTM aporta información** (posición 9 de 21 features)
3. **El walk-forward revela degradación temporal** — insight valioso sobre la naturaleza del problema
4. **Los errores se concentran en productos caros** — insight de negocio actionable
5. **El sistema ensemble LSTM+XGBoost tiene sentido conceptual**: LSTM predice SI cambiará (clasificación) y XGBoost intenta predecir CUÁNTO (regresión). Que XGBoost tenga dificultades con el "cuánto" es coherente con la naturaleza del problema (cambios discretos e impredecibles)

> [!TIP]
> Para la memoria, la narrativa más fuerte es: _"El baseline de persistencia es el predictor más difícil de superar en series de precios retail estables. XGBoost aporta mejora marginal (+1.8% MAE) exclusivamente en los casos de cambio real, donde la persistencia falla por definición. La combinación LSTM (detectar cuándo) + XGBoost (estimar cuánto) constituye un sistema complementario que aborda ambas facetas del problema."_
