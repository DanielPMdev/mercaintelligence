# Evaluación del Segundo Análisis Externo — Verificado con Datos

## Veredicto General

El análisis **tiene razón en el diagnóstico** (hay outliers que distorsionan) pero **se equivoca parcialmente en las causas y soluciones**.

---

## Datos Reales del Dataset

Antes de evaluar punto por punto, estos son los datos que lo verifican:

| Métrica | Valor |
|---------|-------|
| Total pares rank=1 | 882 |
| Pares con **misma unidad** | 829 (94.0%) |
| Pares con **distinta unidad** | 53 (6.0%) |
| Dif. media (todos) | +173.5% |
| Dif. media (solo misma unidad) | **+80.3%** |
| Dif. **mediana** (solo misma unidad) | **+45.6%** |
| Outliers >500% | 26 pares |

---

## Punto por Punto

### ✅ CORRECTO: "Hay ruido en los datos, +7976% no es realista"

**Tiene toda la razón.** El caso concreto de "limpieza muebles y multiusos":

| Producto MP | Producto COM | €/medida MP | €/medida COM | Unidad MP | Unidad COM | Diferencia |
|-------------|-------------|:-----------:|:------------:|:---------:|:----------:|:----------:|
| limpiador muebles con ceras bosque verde | limpiador muebles classic pronto | 4.12 | 11.60 | **L** | **L** | +181% |
| limpiador muebles jabonoso bosque verde | limpiador muebles classic pronto | 1.55 | 11.60 | **L** | **L** | +648% |
| **toallitas limpiadoras bosque verde** | limpiador muebles classic pronto | **0.05** | **11.60** | **ud** | **L** | **+23100%** |

El +7976% de media viene de promediar un +23100% (toallitas a 0.05€/ud vs líquido a 11.60€/L). Es literalmente comparar una toallita con un litro de líquido.

> [!IMPORTANT]
> El caso de "otras salsas" es aún más revelador: **TODAS las salsas hacendado se comparan con "salsa de trufa"** a 38.75€/kg — un producto de lujo que infla todas las brechas de esa subcategoría. Este es un problema del matching (hay pocas salsas comerciales en la subcategoría), no de las unidades.

---

### ✅ CORRECTO: "Filtrar por misma unidad_medida"

**Dato clave:** Solo 53 de 882 pares (6%) tienen unidades distintas, pero esos 53 pares son los que generan casi todos los outliers extremos.

Combinaciones problemáticas reales encontradas:

| Unidad MP | Unidad COM | N pares | Dif. media |
|:---------:|:----------:|:-------:|:----------:|
| L | kg | 13 | +762% |
| 100 g | kg | 6 | +1017% |
| ud | L | 1 | +23100% |
| lv (lavado) | ud | 1 | +1035% |

> [!TIP]
> Filtrar por `unidad_medida_mp == unidad_medida_com` es **la corrección más impactante y simple**. Reduce la media de +173.5% a +80.3%.

---

### ⚠️ PARCIALMENTE CORRECTO: "Filtrar pm_mp < 0.1"

Los datos muestran 100 pares con `pm_mp < 0.5`, pero la mayoría son **cápsulas de café** con unidades correctas (ud vs ud) y diferencias razonables (+14% a +30%). Los denominadores pequeños NO son un problema generalizado en tu dataset — el problema real es la unidad incompatible, no el valor bajo.

**Veredicto:** Solo sería necesario si quedan outliers DESPUÉS del filtro de unidad. No como filtro primario.

---

### ❌ INCORRECTO: "Limitar outliers abs > 500%"

Después de filtrar por misma unidad, los outliers >500% que quedan son:
- Limpiador jabonoso (1.55€/L) vs Pronto (11.60€/L) → **+648%** — legítimo, Pronto realmente cuesta 7x más por litro
- Acondicionador Deliplus (0.16€/100ml) vs Elvive (1.36€/100ml) → **+750%** — legítimo, cosmética premium
- Salsas vs trufa → problema de matching, no de outlier

**Un filtro ciego de >500% eliminaría insights legítimos.** Lo correcto es:
1. Filtrar por misma unidad (elimina los absurdos)
2. Investigar los restantes >500% caso por caso
3. Usar la **mediana** en vez de la media como métrica principal (resiste outliers sin perder datos)

---

### ✅ CORRECTO: "La diferencia real es +20-60%"

**Parcialmente confirmado.** Con filtro de misma unidad:
- Media: **+80.3%**
- **Mediana: +45.6%**

La mediana (+45.6%) cae exactamente en el rango que el análisis predecía (+20-60%). La media sigue alta por los pares legítimos de cosmética/limpieza con grandes primas de marca.

---

### ✅ CORRECTO: "Evaluación manual te sube nota"

Esto es genuinamente buen consejo para un TFE. Un `equiv.sample(50)` clasificado a mano da una métrica de precision@1 publicable.

---

## Resumen de Cambios a Implementar

| Cambio | Prioridad | Impacto |
|--------|:---------:|:-------:|
| Filtrar `unidad_medida_mp == unidad_medida_com` | 🔴 Alta | Elimina 53 pares absurdos, baja media de +173% a +80% |
| Usar **mediana** como métrica principal en resumen | 🔴 Alta | +45.6% es más robusto y defensible que +80.3% |
| Reportar media **y** mediana | 🟡 Media | Transparencia estadística |
| Evaluación manual de 50 pares | 🟡 Media | Precision@1 para el TFE |
| ~~Filtro pm_mp < 0.1~~ | ~~Baja~~ | Innecesario tras filtro de unidad |
| ~~Filtro abs > 500~~  | ~~No~~ | Eliminaría insights legítimos |
