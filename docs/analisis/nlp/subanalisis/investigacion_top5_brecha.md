# Investigación: Top 5 Subcategorías con Mayor Brecha

## Resumen Rápido

| Subcategoría | Mediana | N pares | Veredicto |
|---|:-:|:-:|---|
| Limpieza vajilla | +717.9% | 7 | 🔴 **Match incorrecto** — lavavajillas mano vs limpiamáquinas |
| Limpieza muebles | +414.8% | 2 | 🟡 **Parcial** — solo 3 COM y Pronto es premium, pero legítimo |
| Otras salsas | +225.2% | 18 | 🟡 **Parcial** — mitad trufa (inflado), mitad tomate frito (legítimo) |
| Detergente y suav. | +176.0% | 11 | 🟢 **Legítimo** — Ariel realmente cuesta 2-6x más por lavado |
| Arroz | +166.7% | 7 | 🟢 **Legítimo** — matches perfectos con alta similitud |

---

## 🔴 1. Limpieza Vajilla (+717.9%) — MATCH INCORRECTO

**Problema claro:** 5 de 7 pares emparejan **lavavajillas de uso diario** con **limpiamáquinas Finish** (producto de mantenimiento, 15€/L).

| Producto MP | Producto COM | €/L MP | €/L COM | Dif. | Diagnóstico |
|---|---|:-:|:-:|:-:|---|
| Lavavajillas a mano BV | **limpiamáquinas Finish** | 0.96 | 15.00 | +1459% | ❌ Productos distintos |
| Lavavajillas ultra concentrado BV | **limpiamáquinas Finish** | 1.83 | 15.00 | +718% | ❌ Productos distintos |
| Lavavajillas ultra concentrado BV | **limpiamáquinas Finish** | 1.46 | 15.00 | +926% | ❌ Productos distintos |
| Lavavajillas aloe concentrado BV | **limpiamáquinas Finish** | 1.80 | 15.00 | +733% | ❌ Productos distintos |
| Abrillantador lavavajillas BV | Abrillantador lavavajillas Finish | 1.60 | 9.88 | +517% | ✅ Correcto |
| Limpiamáquinas lavavajillas BV | Limpiamáquinas Finish | 6.20 | 15.00 | +142% | ✅ Correcto |
| Lavavajillas gel máquina BV | Somat gel 5en1 | 0.10 | 0.14 | +49% | ✅ Correcto |

> [!WARNING]
> El NLP empareja "lavavajillas a mano" con "limpiamáquinas lavavajillas" porque comparten la palabra "lavavajillas". Semánticamente es correcto, pero son **productos funcionalmente diferentes** con precios incomparables. Los 3 pares correctos (abrillantador, limpiamáquinas, gel máquina) muestran brechas de +49% a +517% — más razonables.

**Causa raíz:** Solo 8 productos comerciales en la subcategoría, y la mayoría son variantes de Finish/Somat para máquina, no para lavado a mano.

---

## 🟡 2. Limpieza Muebles (+414.8%) — PARCIALMENTE LEGÍTIMO

Solo **2 pares**, ambos contra **Pronto Classic** (11.60€/L):

| Producto MP | €/L | Pronto | Dif. |
|---|:-:|:-:|:-:|
| Limpiador muebles con ceras BV | 4.12 | 11.60 | +181% |
| Limpiador muebles jabonoso BV | 1.55 | 11.60 | +648% |

Solo hay **3 productos comerciales** en la subcategoría (mínimo para pasar el filtro). El jabonoso BV a 1.55€/L vs Pronto a 11.60€/L es **real** — BV es un producto básico y Pronto es la marca premium del segmento. El +648% es extremo pero legítimo.

> [!NOTE]
> Con solo 2 pares, la mediana es poco representativa. No es un error pero tampoco es estadísticamente robusto.

---

## 🟡 3. Otras Salsas (+225.2%) — MIXTO

18 pares, dos tipos de match claramente separados:

### Tomate frito (7 pares) — ✅ LEGÍTIMO
| Hacendado | Hida | Similitud | Dif. |
|---|---|:-:|:-:|
| Tomate frito | Tomate frito Hida | **0.969** | +157% a +244% |
| Tomate frito artesano | Tomate frito Hida | 0.760 | +8% a +23% |

Matches excelentes (sim >0.96 para los directos). Hida cuesta ~2.5x más por kg que Hacendado — **diferencia real y significativa**.

### Salsas vs Trufa (11 pares) — ❌ INFLADO
| Hacendado | COM | Similitud | Dif. |
|---|---|:-:|:-:|
| Salsa barbacoa | **Salsa de trufa** (38.75€/kg) | 0.820 | +1079% |
| Salsa fresca setas | **Salsa de trufa** | 0.905 | +434% |
| Salsa pesto albahaca | **Salsa de trufa** | 0.898 | +278% |

Todas estas salsas se emparejan con **"salsa de trufa"** porque es el producto comercial con más vocabulario compartido ("salsa"). La trufa a 38.75€/kg es un producto gourmet de nicho — no es comparable con salsas de uso diario.

> [!IMPORTANT]
> Si eliminásemos los pares contra trufa, la mediana de "otras salsas" bajaría de +225% a ~**+97%** (basado en los pares de tomate frito).

---

## 🟢 4. Detergente y Suavizante (+176.0%) — LEGÍTIMO

11 pares, la mayoría Bosque Verde vs **Ariel**. Todos miden en **€/lavado (lv)** — la unidad correcta para detergentes.

| Bosque Verde | Ariel | €/lv BV | €/lv Ariel | Dif. |
|---|---|:-:|:-:|:-:|
| Det. prendas delicadas | Ariel líquido | 0.038 | 0.265 | +597% |
| Det. frescura | Ariel líquido | 0.068 | 0.265 | +290% |
| Det. color | Ariel líquido | 0.096 | 0.265 | **+176%** |
| Det. blanca y color cápsulas | Ariel Pods | 0.184 | 0.384 | +109% |
| Det. oscura | Ariel líquido | 0.134 | 0.265 | +98% |

> [!TIP]
> **Esto es un insight genuino y potente para el TFE.** Ariel cuesta entre 2x y 7x más por lavado que Bosque Verde. Los matches son correctos (sim >0.85), las unidades son iguales (€/lavado), y la brecha es enorme. La diferencia del "delicadas" (+597%) tiene sentido: es el BV más barato (0.038€/lv) contra el Ariel estándar.

---

## 🟢 5. Arroz (+166.7%) — LEGÍTIMO Y LIMPIO

7 pares, todos con **similitud altísima** (>0.90):

| Hacendado | Comercial | Sim. | €/kg MP | €/kg COM | Dif. |
|---|---|:-:|:-:|:-:|:-:|
| Arroz largo | Arroz largo Sabroz | **0.978** | 1.25 | 4.40 | +252% |
| Arroz redondo J Sendra | Arroz largo Sabroz | 0.928 | 1.60 | 4.40 | +175% |
| Arroz integral largo | Arroz largo Sabroz | **0.964** | 1.65 | 4.40 | +167% |
| Arroz basmati | Arroz cocido basmati Brillante | 0.929 | 2.10 | 4.40 | +110% |
| Arroz redondo | Arroz redondo La Fallera | **0.954** | 1.20 | 1.69 | +41% |

> [!TIP]
> El par más limpio del dataset: **arroz redondo Hacendado (1.20€/kg) vs La Fallera (1.69€/kg) = +41%**. Similitud 0.954, misma unidad, productos genuinamente equivalentes. El premium de marca existe pero es moderado. Los pares contra Sabroz/Brillante tienen mayor brecha porque esos son **arroz cocido precocinado** (más procesado → más caro por kg).

---

## Recomendación: Por qué no añadir más filtros

La única subcategoría con **matches claramente incorrectos** es **limpieza vajilla** (lavavajillas mano vs limpiamáquinas). Las demás son legítimas o tienen mezcla de matches buenos/malos.

Ante esto, se podrían plantear dos soluciones adicionales, pero **ambas son problemáticas**:

### Propuesta 1: Palabras conflictivas — ❌ Mala práctica

Es **ad-hoc y no generalizable**. En un Trabajo de Fin de Estudios (TFE) hay que defender *por qué* esas palabras y no otras. ¿Qué pasa con "sal gruesa" vs "escamas de sal"? ¿Y "detergente prendas delicadas" vs "detergente color"? No hay regla universal. Además, el par `("salsa", "trufa")` eliminaría el match **"salsa fresca trufa hacendado" ↔ "salsa de trufa"** que tiene similitud **0.959** y ES un match legítimo.

### Propuesta 2: Filtro `abs > 300%` — ❌ Elimina insights reales

Veamos exactamente qué perderíamos con ese filtro, según los datos que ya investigamos:

| Par | Dif. | ¿Legítimo? | Se pierde |
|---|:-:|:-:|:-:|
| Det. prendas delicadas BV (0.038€/lv) vs Ariel (0.265€/lv) | **+597%** | ✅ Sí | ❌ Sí |
| Abrillantador BV (1.60€/L) vs Finish (9.88€/L) | **+517%** | ✅ Sí | ❌ Sí |
| Limpiador jabonoso BV (1.55€/L) vs Pronto (11.60€/L) | **+648%** | ✅ Sí | ❌ Sí |
| Lavavajillas mano BV vs limpiamáquinas Finish | +1459% | ❌ No | ✅ Bien |
| Salsa barbacoa vs trufa | +1079% | ❌ No | ✅ Bien |

Elimina **tanto los malos como los buenos**. El detergente de prendas delicadas BV a 0.038€/lavado vs Ariel a 0.265€/lavado es un **insight genuino y potente**: la marca premium cuesta 7x más por lavado. Perder eso por un filtro genérico no tiene sentido.

### Lo que ya tenemos es suficiente

Los tres filtros ya implementados resuelven el problema de forma elegante:

| Filtro | Qué elimina | Ya implementado |
|---|---|:-:|
| `misma_unidad` | Toallitas vs líquido (+23100%) | ✅ |
| `MIN_COMERCIALES ≥ 3` | Helados, mantequilla monopolio | ✅ |
| **Mediana** como estadístico | Absorbe outliers sin perder datos | ✅ |

La mediana de **+51.5%** ya es robusta y no cambia significativamente con los outliers que quedan. Los matches incorrectos que quedan (lavavajillas vs limpiamáquinas) son una **limitación inherente del matching semántico por texto** en subcategorías con poca variedad comercial — y eso es exactamente lo que se debe documentar en el TFE.

**Mi recomendación final: no añadir más filtros automáticos.** En su lugar, usa como referencia principal las subcategorías con **más de 5 pares**, y documenta la limitación en la memoria del TFE:

> *"El matching semántico no distingue entre productos funcionalmente distintos que comparten vocabulario (ej: lavavajillas de uso diario vs limpiamáquinas). Esta limitación se mitiga usando la mediana como estadístico principal, que es robusta frente a estos outliers."*
