# Fecha Hoy --> 27/04/2026

## Ejecución script consolidar_historico.py

PS E:\Estudios\CE_IAyBD\TFE\mercaintelligence> & "C:/Users/Daniel PC/AppData/Local/Programs/Python/Python313/python.exe" e:/Estudios/CE_IAyBD/TFE/mercaintelligence/src/etl/consolidar_historico.py
2026-04-27 11:59:10,320 — Encontrados 152 CSVs en data\raw
2026-04-27 11:59:12,351 — Procesados 20/152 ficheros...
2026-04-27 11:59:14,493 — Procesados 40/152 ficheros...
2026-04-27 11:59:16,408 — Procesados 60/152 ficheros...
2026-04-27 11:59:18,298 — Procesados 80/152 ficheros...
2026-04-27 11:59:20,116 — Procesados 100/152 ficheros...
2026-04-27 11:59:22,017 — Procesados 120/152 ficheros...
2026-04-27 11:59:23,905 — Procesados 140/152 ficheros...
2026-04-27 11:59:29,114 — ✅ Parquet maestro guardado en data\processed\maestro.parquet
2026-04-27 11:59:29,114 — Filas totales : 659,997
2026-04-27 11:59:29,124 — Productos únicos: 5,009
2026-04-27 11:59:29,127 — Rango fechas: 2025-11-03 → 2026-04-26
2026-04-27 11:59:29,127 — Columnas: ['url', 'referencia', 'categoria', 'subcategoria', 'titulo', 'formato', 'precio_por_medida', 'unidad_medida', 'precio_anterior', 'precio_actual', 'unidad_precio', 'divisa', 'imagen_principal', 'imagenes_secundarias', 'timestamp', 'fecha', 'es_marca_propia', 'marca_propia', 'tiene_precio_anterior']

---

## Ejecución script verificacion_parquet.ipynb

El shape del parquet es (659997, 19)

url object
referencia int64
categoria object
subcategoria object
titulo object
formato object
precio_por_medida float64
unidad_medida object
precio_anterior float64
precio_actual float64
unidad_precio object
divisa object
imagen_principal object
imagenes_secundarias object
timestamp datetime64[ns]
fecha datetime64[ns]
es_marca_propia bool
marca_propia object
tiene_precio_anterior bool
dtype: object

La cantidad de archivos es 152

La cantidad de columnas con nulos es:
url 0
referencia 0
categoria 0
subcategoria 0
titulo 0
formato 0
precio_por_medida 0
unidad_medida 0
precio_anterior 629264
precio_actual 0
unidad_precio 0
divisa 0
imagen_principal 0
imagenes_secundarias 0
timestamp 0
fecha 0
es_marca_propia 0
marca_propia 0
tiene_precio_anterior 0
dtype: int64

marca_propia
hacendado 272525
comercial 228118
deliplus 106125
bosque verde 46497
compy 6732
Name: count, dtype: int64

La cantidad de duplicados es 0

---

## Analisis de los resultados

### 🔍 Análisis del Parquet maestro

Lo que tienen tus datos es muy bueno. Vamos columna a columna con lo que importa:

- **Volumen y cobertura — sin problemas:**
  659.997 filas, 152 snapshots (4 más de los previstos, el scraper ha seguido corriendo), rango 3 noviembre 2025 → 26 abril 2026. Son casi 6 meses de datos. Eso es un dataset serio y justificable en la memoria.

- **Tipos — correctos:**
  `precio_actual`, `precio_anterior` y `precio_por_medida` son `float64`. `timestamp` y `fecha` son `datetime64`. `referencia` es `int64`. No hay nada que corregir aquí.

- **Duplicados — cero:**
  El `drop_duplicates` funcionó perfectamente. No hay ningún día duplicado por producto.

- **Nulos — esperados y valiosos:**
  Es `precio_anterior` con 629.264 nulos — y esto es exactamente lo esperado y valioso. Significa que el 95,3% de las filas no tienen precio anterior, lo que implica que ese día ese producto no había cambiado de precio. Solo cuando hay cambio aparece `precio_anterior`. Esto te lo confirma también `tiene_precio_anterior` con los mismos valores. Ese 4,7% de filas con precio anterior son tus eventos de cambio de precio, que son exactamente los datos que alimentan el módulo de anomalías y el LSTM.

- **Distribución Marca Propia vs Comercial — muy interesante:**
  Las marcas propias de Mercadona dominan el catálogo de forma masiva (65,4% del total) frente a las marcas comerciales (34,6% con 228.118 filas). El desglose de marcas propias es:
  - **Hacendado**: 272.525 filas (41,3%)
  - **Deliplus**: 106.125 filas (16,1%)
  - **Bosque Verde**: 46.497 filas (7,0%)
  - **Compy**: 6.732 filas (1,0%)
    Esto significa que Mercadona prioriza fuertemente sus propias marcas en el surtido, mucho más de lo que se esperaría de un supermercado tradicional. Esto es un hallazgo propio y muy relevante que debes mencionar en la introducción de la memoria.

- **Columnas que puedes descartar para ML:**
  `url`, `imagen_principal`, `imagenes_secundarias` y `divisa` no aportan nada a los modelos. Las excluyes al cargar features. `divisa` es constante (todo euros). Esto también va en la memoria como "selección de variables relevantes".

---

# Fecha Hoy --> 28/04/2026-29/04/2026

## ingesta_incremental.py + watchdog

C:\actions-runner\...\samples\ ← carpeta vigilada por watchdog
↓ detecta CSV nuevo
mercaintelligence/src/etl/ingesta_incremental.py
↓ limpia + features
mercaintelligence/data/processed/maestro.parquet (append)
↓ indexa
Elasticsearch

### Resultado

MAÑANA RELLENAR

## indexar_historico_es.py

## Cambio a Parquet Particionado

### Resultado

PS E:\Estudios\CE_IAyBD\TFE\mercaintelligence> & "C:/Users/Daniel PC/AppData/Local/Programs/Python/Python313/python.exe" e:/Estudios/CE_IAyBD/TFE/mercaintelligence/src/etl/indexar_historico_es.py
2026-04-28 19:04:54,902 — HEAD http://localhost:9200/mercadona-precios [status:404 duration:2.052s]
2026-04-28 19:04:55,839 — PUT http://localhost:9200/mercadona-precios [status:200 duration:0.936s]
2026-04-28 19:04:55,839 — Índice 'mercadona-precios' creado con mapping explícito
2026-04-28 19:04:56,410 — Indexando 668,625 documentos...
2026-04-28 19:04:58,158 — PUT http://localhost:9200/\_bulk [status:200 duration:0.386s]
2026-04-28 19:04:58,552 — PUT http://localhost:9200/\_bulk [status:200 duration:0.097s]
2026-04-28 19:04:58,879 — PUT http://localhost:9200/\_bulk [status:200 duration:0.081s]
2026-04-28 19:04:59,061 — PUT http://localhost:9200/\_bulk [status:200 duration:0.068s]
...
2026-04-28 19:08:52,918 — ✅ 668,625 documentos indexados, 0 errores

### 🚀 Optimización del Almacenamiento: Migración a Parquet Particionado

A medida que el volumen de datos históricos crecía, se detectó un problema de escalabilidad crítico en el pipeline de ingesta. El diseño original consistía en un único fichero monolítico (`maestro.parquet`), lo que provocaba un **cuello de botella de I/O y memoria**:

- **El problema de O(N):** Cada día, al procesar un nuevo CSV de ~5,000 filas, el sistema se veía obligado a cargar todo el histórico (+660,000 filas) en memoria RAM, concatenar los datos nuevos y reescribir el fichero completo. A medida que los datos crecieran a millones de filas, este proceso se volvería inmanejable e ineficiente.

> Un matiz para la memoria: el coste no es estrictamente O(1) sino O(k) donde k es el tamaño de una partición (~4.300 filas). Lo que sí es O(1) respecto al histórico total, que es lo que importa.

#### Solución Implementada: Diseño Batch Incremental

Para solucionar esto, se refactorizó la arquitectura hacia un modelo **append-only particionado**, un patrón estándar en _Data Engineering_ y Data Lakes:

1. **Parquet particionado por fecha (`data/processed/fecha=YYYY-MM-DD/`)**:
   En lugar de un único archivo, los datos se guardan en carpetas independientes para cada día de extracción. Esto permite que la ingesta diaria sea de **escritura ultra-rápida (O(1))** y totalmente idempotente (procesar el mismo día solo sobrescribe esa carpeta específica).
2. **Tabla de estado (`data/state/ultimo_precio.parquet`)**:
   La necesidad de calcular métricas históricas (ej. _días sin cambio_, _variación porcentual_) exigía leer el histórico. Para evitarlo, se extrajo el estado a una tabla auxiliar. Esta tabla compacta guarda únicamente la última fila conocida de cada producto, permitiendo calcular el _feature engineering_ incremental en memoria en fracciones de segundo.
3. **Lectura con empuje de predicados (Predicate Pushdown)**:
   Herramientas como `pandas` o consultas de _Elasticsearch_ ahora pueden leer todo el directorio `data/processed`. Al filtrar por una fecha concreta, el motor solo lee la carpeta necesaria, reduciendo drásticamente la latencia y la lectura en disco.

#### Resumen de Cambios en el Código:

- **`ingesta_incremental.py`**: Refactorizado para usar escrituras particionadas (`partition_cols=["fecha"]`) y actualizar la tabla de estado tras procesar las _features_.
- **`indexar_historico_es.py` y Notebooks**: Actualizados para leer transparentemente desde el directorio particionado sin notar el cambio de estructura interna.
- **Separación de responsabilidades**: Creación del directorio `data/state/` para separar el estado transaccional de los datos inmutables de `data/processed/`.


