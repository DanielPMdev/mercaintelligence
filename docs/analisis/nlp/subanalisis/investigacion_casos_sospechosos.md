# Investigación de Casos Sospechosos — NLP Equivalencias

## 🍦 1. Helados (-40%): Explicación

### El Problema

**TODOS** los helados Hacendado (22 productos) se emparejan con un **ÚNICO** producto comercial:

> **helado cucurucho fresa nata** — 3.40€/L

Esto ocurre porque en la subcategoría "helados" **solo hay 1 producto comercial** en el catálogo. El sistema no tiene otra opción.

### Los datos

| Producto Hacendado | €/L MP | €/L COM | Dif. |
|---|:-:|:-:|:-:|
| Helado bombón doble chocolate | 8.55 | 3.40 | **-60%** |
| Helado bombón almendrado | 7.24 | 3.40 | **-53%** |
| Helado bombón negro | 4.44 | 3.40 | -23% |
| Helado cucurucho choco nata | 3.40 | 3.40 | 0% |
| Helado de vainilla | 2.40 | 3.40 | +42% |
| Barra helado 3 sabores | 1.90 | 3.40 | +79% |

> [!IMPORTANT]
> Los helados Hacendado tipo "bombón" son premium (chocolate, almendras) y cuestan más por litro que un cucurucho básico. **No es un error del NLP — el match semántico es correcto** ("helado" ↔ "helado"). El problema es que **no hay suficientes productos comerciales** en esta subcategoría para encontrar equivalentes adecuados.

**Veredicto:** Match técnicamente válido pero **no comparable funcionalmente** por falta de variedad comercial.

---

## 🧹 2. Limpieza Vajilla (+718%): Producto Equivocado

### El Problema

5 de 7 productos Bosque Verde se emparejan con **"limpiamáquinas lavavajillas finish líquido"** (15€/L), que es un **producto de mantenimiento de la máquina**, no un lavavajillas de uso diario.

| Producto MP | Producto COM | €/L MP | €/L COM | Dif. |
|---|---|:-:|:-:|:-:|
| Lavavajillas a mano BV | **limpiamáquinas Finish** | 0.96 | 15.00 | **+1459%** |
| Lavavajillas ultra concentrado BV | **limpiamáquinas Finish** | 1.83 | 15.00 | +718% |
| Lavavajillas en gel BV máquina | Somat gel 5en1 | 0.10 | 0.14 | +49% |

> [!WARNING]
> El NLP acierta semánticamente ("lavavajillas" ↔ "lavavajillas") pero el **limpiamáquinas es un producto totalmente distinto** con un precio/L mucho mayor. Esto es un problema de **poca variedad comercial** en la subcategoría, igual que helados.

**Veredicto:** Match semántico correcto, comparación funcional **incorrecta**.

---

## 🧂 3. Sal Gruesa vs Escamas de Sal (+3900%)

| Producto | €/kg | Tipo |
|---|:-:|---|
| Sal gruesa Hacendado | 0.40 | Commodity básico |
| Escamas de sal marina Polasal | 16.00 | Producto gourmet |

Match semántico (sim=0.75): "sal" ↔ "sal" — técnicamente correcto, pero son **categorías de producto completamente distintas**. Es como comparar agua del grifo con agua mineral premium.

**Veredicto:** Falso equivalente.

---

## 🧈 4. Mantequilla y Margarina (+373%)

**TODOS** los productos se emparejan con **"margarina Flora Proactiv"** (14.18€/kg) — un producto funcional/salud que cuesta 4-5x más que una margarina normal.

| Margarina MP | €/kg | Flora Proactiv | Dif. |
|---|:-:|:-:|:-:|
| Margarina 100% vegetal | 6.40 | 14.18 | +122% |
| Margarina normal | 3.00 | 14.18 | +373% |
| Margarina ligera | 2.90 | 14.18 | +389% |

**Veredicto:** Match semántico correcto, pero Flora Proactiv es un outlier de precio (producto funcional/salud).

---

## 🍕 5. Otras Salsas — Todas contra Trufa

Ya detectado anteriormente: TODAS las salsas Hacendado se emparejan con **"salsa de trufa"** (38.75€/kg). Mismo patrón: un solo producto comercial de lujo.

---

## 🔍 Patrón Común: "Monopolio de Match"

Todos estos casos comparten la misma raíz:

```
Subcategoría con 1-2 productos comerciales
→ Todos los MP se emparejan con ese único COM
→ Si ese COM es premium/diferente, la brecha explota
```

| Subcategoría | N productos COM | COM único | Impacto |
|---|:-:|---|:-:|
| helados | 1 | cucurucho fresa nata | -40% falso |
| otras salsas | 1 | salsa de trufa | +225% inflado |
| mantequilla | 1 | Flora Proactiv | +373% inflado |
| limpieza vajilla | ~2 | limpiamáquinas Finish | +718% inflado |

---

## 📊 Distribución General de Calidad

A continuación se muestra la comparación de la distribución de calidad y las brechas calculadas **antes** y **después** de aplicar los filtros de calidad metodológicos (`misma_unidad` y `MIN_COMERCIALES >= 3`):

| Métrica / Distribución | Antes de Filtros Completos (Fase Exploratoria) | Con Filtros Completos (Fase Final / Dashboard) |
|---|:---:|:---:|
| **Pares comparables (misma unidad)** | 829 | **892** |
| **Cuartil 25%** | +1.5% | **+3.7%** |
| **Cuartil 50% (Mediana)** | +45.6% | **+49.0%** |
| **Cuartil 75%** | +115.2% | **+108.7%** |
| **Pares en rango razonable (-50% a 200%)** | 715 de 829 (86.2%) | **791 de 892 (88.7%)** |
| **Pares con brecha extrema (> 200%)** | 68 (8.2%) | **62 (7.0%)** |
| **Pares con brecha negativa (< -50%)** | 46 (5.5%) | **39 (4.4%)** |

> [!TIP]
> La aplicación de los filtros no solo incrementó el volumen neto de pares de calidad comparables (al refinar el catálogo actual), sino que además **aumentó el porcentaje de pares en el rango razonable de 86.2% a 88.7%** y **redujo la proporción de brechas extremas erróneas (outliers) del 8.2% al 7.0%**. Esto confirma cuantitativamente que la restricción de dominio por variedad comercial purifica el dataset de anomalías.


> [!TIP]
> El **88.7% de los pares** del catálogo final están en un rango razonable (-50% a 200%). Los problemas remanentes se concentran en contadas subcategorías con dinámicas de precios muy asimétricas de fabricante o limitaciones menores del matching por texto.

---

## 🎯 Recomendación: Filtro de Variedad Mínima

El fix más limpio es exigir un **mínimo de productos comerciales** en la subcategoría antes de buscar equivalencias:

```python
# Solo buscar equivalencias si hay >= 3 productos comerciales
if len(idx_com) < 3:
    continue
```

**Justificación para el TFE:**
> "Se excluyen subcategorías con menos de 3 productos comerciales, ya que la falta de variedad impide encontrar equivalentes funcionales adecuados"

### Impacto estimado:
- Elimina los casos de helados, trufa, Flora Proactiv
- Mantiene todas las subcategorías con suficiente competencia
- **No pierde información útil** — esos pares no eran comparables de todas formas
