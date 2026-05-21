# Análisis del Pipeline de Segmentación con K-Means

> Documento de análisis integrado del módulo `notebooks/clustering_kmeans.ipynb`.
> Recoge el proceso iterativo de diseño, feature engineering, validación y refinamiento del modelo de clustering
> para descubrir perfiles de negocio reales en el catálogo de productos de Mercadona.

---

## 1. Arquitectura del Pipeline de Clustering

El sistema sigue una arquitectura de pipeline secuencial centrada en el *feature engineering* a partir de series temporales de precios:

```mermaid
flowchart LR
    A[Carga de histórico] --> B[Feature Engineering]
    B --> C[Limpieza y Transformación]
    C --> D[Escalado Standard]
    D --> E[K-Means Clustering]
    E --> F[Proyección PCA]
    E --> G[Guardado Resultados]
```

### Decisiones de diseño clave

| Decisión | Justificación |
|----------|---------------|
| **Estadísticos en lugar de serie temporal plana** | Evita la "maldición de la dimensionalidad". Usar 154 columnas de días para K-Means generaría ruido. En su lugar se usan estadísticos descriptivos (`n_cambios`, `precio_std`, etc.) que resumen el comportamiento. |
| **Eliminación del percentil 99 (Outliers)** | El K-Means es extremadamente sensible a distancias euclidianas. Antes de filtrar, el algoritmo agrupaba 1 solo producto de lujo en un cluster y los 5,041 restantes en otro, inutilizando la segmentación. |
| **Transformación logarítmica (`np.log1p`)** | Las variables financieras (`precio_medio`, `rango_precio`, `variacion_media`) presentan fuerte asimetría positiva. El logaritmo normaliza la distribución, facilitando el trabajo del escalador y del algoritmo. |
| **Forzar K=5 sobre K=2 (Silhouette Máximo)** | Matemáticamente, Silhouette sugería K=2 para separar lo normal de los extremos. A nivel de negocio, forzar K=5 obligó al algoritmo a descubrir perfiles de comportamiento reales y útiles. |

---

## 2. Resultados de Segmentación

### 2.1 Métricas globales del modelo

| Métrica | Valor |
|---------|:-----:|
| Productos totales analizados | 5,049 |
| Outliers extremos eliminados | 52 |
| Número de dimensiones (Features) | 7 |
| Número de clusters (K) | 5 |
| Silhouette Score (K=5) | 0.441 |
| Varianza explicada (PCA 2D) | **76.0%** |

> [!TIP]
> Una varianza explicada del **76.0%** en solo dos componentes principales (PC1 y PC2) es un resultado excepcionalmente bueno, garantizando que nuestra proyección visual representa fielmente las distancias reales de los grupos en el espacio multidimensional.

---

## 3. Proceso de Refinamiento del Modelo

El modelo de clustering pasó por iteraciones críticas para resolver un colapso matemático inicial donde la distancia de los productos extremos dominaba todo el espacio.

### Iteración 1: Entrenamiento crudo inicial

```
Cluster 0: 5041 productos
Cluster 1: 1 producto
```

**Problema detectado:** El algoritmo detectó correctamente un *outlier* extremo (un producto con un precio absurdamente alto), pero fracasó en segmentar el catálogo. El Silhouette Score era casi perfecto (0.987) pero a nivel de negocio era inútil.

### Iteración 2: Eliminación de outliers (`q99`)

Se eliminó el percentil 99 superior de la variable `precio_medio` (los 52 productos más caros). 

**Mejora:** El modelo comenzó a dividir el bloque grande en subgrupos, pero las variables muy asimétricas seguían dominando.

### Iteración 3: Transformación Logarítmica (`np.log1p`)

Se aplicó logaritmo a las variables asimétricas: `precio_medio`, `precio_std`, `rango_precio` y `variacion_media`.

**Mejora:** La distribución de las features se normalizó, permitiendo que variables como `prop_estable` (proporción de días sin cambios) y `n_cambios` empezaran a tener peso real en la decisión del modelo sin ser aplastadas por la magnitud de los precios absolutos.

### Iteración 4: Selección manual del hiperparámetro K (Versión Final)

```
Cluster 0: 1,467 productos
Cluster 1: 120 productos
Cluster 2: 2,942 productos
Cluster 3: 30 productos
Cluster 4: 490 productos
```

En clustering, el mejor K matemático no siempre es el mejor K de negocio. Forzamos **K=5**, sacrificando un poco de Silhouette Score matemático para obtener perfiles funcionales que el departamento de *pricing* pueda utilizar.

---

## 4. Perfiles de Negocio Descubiertos

La segmentación final arroja cinco arquetipos claros y accionables:

### 🍅 Cluster 3: "Frescos de Alta Volatilidad" (30 productos)
- **Perfil**: Cambian de precio **89 veces** de media en el histórico. Estabilidad del 41.8%. 
- **Marca**: 0% Marca propia (todo es genérico de mercado).
- **Categorías top**: Fruta y verdura, marisco y pescado.
- **Insights**: Detecta a la perfección los productos de lonja y productos frescos cuyo precio fluctúa casi a diario por la dinámica mayorista.

### 🧼 Cluster 2: "Básicos Estables de Marca Blanca" (2,942 productos)
- **Perfil**: Precios muy bajos y estabilidad monolítica (99.8% del tiempo sin cambios).
- **Marca**: Altísima dominancia de marca propia (77.4%).
- **Categorías top**: Cuidado facial y corporal, limpieza y hogar, charcutería y quesos.
- **Insights**: El gran bloque de *commodities*. Artículos esenciales donde el supermercado clava el precio como estrategia de anclaje mental para el consumidor.

### 🧴 Cluster 1: "Marcas Nacionales en Promoción" (120 productos)
- **Perfil**: Precio medio-alto, desviación estándar alta. 
- **Marca**: Mayoría de marcas comerciales (solo 10.8% marca propia).
- **Categorías top**: Cuidado facial y corporal, bodega.
- **Insights**: Son productos premium que sufren campañas agresivas de marketing, generando grandes escalones (rebajas y subidas) que el algoritmo detecta a través del `rango_precio`.

### 🛒 Cluster 4: "Dinámicos de Variabilidad Moderada" (490 productos)
- **Perfil**: Unas ~4.9 variaciones de precio en el histórico. Estabilidad del 96.2%.
- **Marca**: Mixto (26.7% marca propia).
- **Insights**: Productos que sufren ajustes por inflación, temporada o costes logísticos, pero sin la histeria de los productos frescos del Cluster 3.

### 📦 Cluster 0: "Estables de Precio Medio" (1,467 productos)
- **Perfil**: Muy estables (99.8%), similares al Cluster 2, pero con un precio base muy superior.
- **Marca**: Más presencia del fabricante nacional (58.6% marca propia).

---

## 5. Visualizaciones y Diagnóstico

El análisis visual de los clusters generados es una de las partes más críticas para validar y comprender la robustez del modelo. Se han generado tres gráficas principales:

### Gráfica del Codo y Silhouette (`codo_silhouette.png`)
* **El método del codo (Inercia):** Muestra una caída fuerte desde K=2 hasta K=4, y a partir de K=5 la curva de inercia empieza a suavizarse (desciende muy lentamente). Esto confirma empíricamente que **K=5** es donde se sitúa el "codo" real de la distribución, justificando la decisión de no forzar un modelo más fragmentado.
* **Silhouette Score:** El score es matemáticamente más alto en K=2 (0.77), lo cual es habitual en distribuciones con asimetría (el modelo parte el dataset en "lo masivo" vs "los extremos"). Sin embargo, el valor se estabiliza alrededor de `0.44` para K=5 a K=8. Esta estabilización nos indica que **nos encontramos dentro de un rango de segmentación válido**, pero al forzar K=5 obtenemos muchísimo más valor interpretativo y de negocio sin colapsar la calidad matemática.

### Proyección PCA 2D (`pca_clusters.png`)
* **Varianza retenida:** El Componente Principal 1 (PC1) captura un impresionante 48.1% de la varianza, y el PC2 un 27.9%. En total, **el 76.0% de la información multidimensional está representada en esta figura 2D**, lo cual garantiza que las posiciones relativas que observamos son fiables y no meros artefactos visuales de la reducción de dimensionalidad.
* **Distribución espacial:**
  * **Foco central (Cian/Azul):** A la izquierda vemos una inmensa nube compacta formada por los clusters masivos (2 y 0). Esto refleja su extremada estabilidad de precio (variabilidad casi nula).
  * **Los outliers de volatilidad (Verde):** Arriba a la derecha, muy alejado del resto, se distingue el Cluster 3 (Frescos de Alta Volatilidad). El PCA lo separa drásticamente del bloque central debido a la extrema cantidad de cambios de precio diarios.
  * **Las nubes de transición:** Los Clusters 4 y 1 actúan como puentes o extensiones de transición. El polo de variabilidad moderada y el de artículos con alto rango de precio y ofertas puntuales se separan de manera clara y coherente en las dimensiones reducidas.

### Silhouette Plot (`silhouette_plot.png`)
* **Bloques mayoritarios (Clusters 2 y 0):** Presentan siluetas gruesas donde gran parte de la distribución cruza o supera holgadamente la media roja (`0.44`), rozando en muchos casos valores de `0.6`. Esto indica que los productos estables están excelentemente anclados a sus respectivos centroides; hay muy poca duda sobre su pertenencia.
* **El extremo volátil (Cluster 3):** Aunque es una franja extremadamente delgada (por su reducido volumen de 30 productos), se alarga sorprendentemente hacia la derecha, superando también la media. Esto corrobora que, pese a su escasez, su comportamiento es tan anómalo y único que el modelo tiene total confianza en aislarlos como un grupo independiente.
* **El puente (Cluster 4):** Se observa una pequeña "cola" de puntuaciones negativas hacia la izquierda del 0. Esto es completamente normal y sintomático del clustering en escenarios reales: los productos de "variabilidad moderada" tienen puntos fronterizos que ocasionalmente se solapan geométricamente con los artículos más estables o con los más volátiles, creando una transición fluida (un continuo) en lugar de una frontera rígida.

---

## 6. Limitaciones Conocidas

1. **Sesgo por geometría esférica:** K-Means asume distancias euclidianas (clusters esféricos). Esto puede forzar divisiones artificiales en distribuciones alargadas, aunque PCA demuestra una separación bastante limpia en este caso.
2. **Dependencia de la Ventana Temporal:** Las variables de volatilidad (`n_cambios`) dependen directamente de la ventana de 154 días analizada. En periodos macroeconómicos muy estables, los perfiles de los clusters 4 y 1 podrían fusionarse.

---

## 7. Conclusión

El pipeline de clustering de MercaIntelligence cumple con éxito el paso del **Análisis Descriptivo al Descubrimiento de Conocimiento**.

Se ha pasado de "saber los precios" a "entender el comportamiento de los precios". Identificar de forma totalmente automatizada qué artículos forman la cesta ancla (estables), cuáles se usan como ganchos promocionales (volátiles de marca nacional) y cuáles dictan el mercado diario (frescos), dota a la herramienta de una capacidad de inteligencia competitiva de primer nivel.
