# Análisis del Pipeline ETL e Ingesta de Datos

> Documento de análisis integrado de los módulos ETL de MercaIntelligence (`src/etl/*`).
> Recoge la arquitectura de extracción, transformación, optimización de almacenamiento y carga a Elasticsearch, destacando la transición de un modelo monolítico a un sistema incremental en tiempo real.

---

## 1. Arquitectura del Pipeline ETL

El sistema ha evolucionado de un procesamiento batch monolítico a una arquitectura orientada a eventos (*event-driven*) con particionado eficiente:

```mermaid
flowchart TD
    A[Scraper / CSV Nuevo] -->|Watchdog| B(ingesta_incremental.py)
    B --> C{Fase 1: Limpieza}
    C --> D{Fase 2: Feature Engineering}
    D <-->|Lectura/Escritura O(1)| E[(data/state/ultimo_precio.parquet)]
    D --> F{Fase 3: Almacenamiento}
    F -->|Append-only| G[(data/processed/fecha=YYYY-MM-DD/)]
    D --> H{Fase 4: Indexación}
    H -->|Bulk Index| I[(Elasticsearch: mercadona-precios)]
```

### Decisiones de diseño clave

| Decisión | Justificación |
|----------|---------------|
| **Parquet Particionado por Fecha** | Resuelve el cuello de botella O(N) al concatenar históricos. Permite escritura O(1) y lectura optimizada (*predicate pushdown*). |
| **Tabla de Estado (`ultimo_precio.parquet`)** | Separa el estado transaccional (último precio conocido) de los datos inmutables. Permite calcular métricas temporales (`variacion_pct`, `dias_sin_cambio`) sin cargar todo el histórico. |
| **ID Determinístico en Elasticsearch** | El formato `{referencia}_{fecha}` garantiza la idempotencia de la ingesta. Reprocesar el mismo día actualiza el documento en vez de duplicarlo. |
| **Watchdog Event-Driven** | Permite el paso a producción reaccionando instantáneamente a nuevos archivos del scraper sin necesidad de programar crons rígidos. |
| **Drop de variables estéticas** | Columnas como `url`, `imagen_principal`, o `divisa` se descartan para los modelos ML al no aportar valor analítico. |

---

## 2. Resultados del Procesamiento Histórico

El consolidado histórico abarca casi 6 meses de datos, demostrando la madurez y robustez del dataset extraído.

### 2.1 Métricas de Volumen y Cobertura

| Métrica | Valor |
|---------|:-----:|
| **Filas totales procesadas** | 659,997 |
| **Ficheros CSV consolidados** | 152 |
| **Rango temporal** | 2025-11-03 → 2026-04-26 |
| **Productos únicos** | 5,009 |
| **Documentos indexados en ES** | 668,625 |

### 2.2 Dinámica de Precios y Dominio de Marca

> [!TIP]
> Solo el **4.7%** del histórico presenta variaciones de precio (detectado por `precio_anterior`). El 95.3% restante son confirmaciones de precio mantenido. Este 4.7% de eventos de cambio es el combustible clave para los módulos de Anomalías y pronóstico LSTM.

| Distribución del Catálogo | % del Total | Volumen (filas) |
|---------------------------|:-----------:|:---------------:|
| **Marcas Propias (Total)** | **65.4%** | 431,879 |
| - Hacendado | 41.3% | 272,525 |
| - Deliplus | 16.1% | 106,125 |
| - Bosque Verde | 7.0% | 46,497 |
| - Compy | 1.0% | 6,732 |
| **Marcas Comerciales** | **34.6%** | 228,118 |

> [!IMPORTANT]
> El abrumador dominio de la marca propia (65.4%) sobre la marca de fabricante (34.6%) evidencia la estrategia de surtido de Mercadona. Este hallazgo es fundamental para justificar los esfuerzos en el análisis NLP de equivalencias semánticas.

---

## 3. Optimización del Almacenamiento: De Monolito a Particionado

A medida que el dataset superó el medio millón de registros, el script original `consolidar_historico.py` evidenció problemas de escalabilidad.

### El Problema de Escalabilidad (O(N))
El diseño inicial (`maestro.parquet`) requería cargar los +660,000 registros en RAM cada día, añadir las ~5,000 filas nuevas, y reescribir el fichero monolítico completo.

### La Solución Implementada (`migrar_a_particionado.py`)
Se migró la arquitectura hacia un modelo estándar de Data Lake:
1. **Append-only Particionado (`data/processed/fecha=...`)**: La ingesta diaria ahora es una escritura ultrarrápida.
2. **Idempotencia a nivel de día**: Procesar múltiples veces el mismo CSV solo sobrescribe la partición de esa fecha.
3. **Eficiencia en Lectura**: Consultas para días específicos reducen drásticamente la latencia y la lectura en disco gracias al *predicate pushdown* de los motores analíticos (ej. PyArrow/Pandas).

---

## 4. Ingeniería de Características y Limpieza

Durante la ingesta, se aplican transformaciones en vuelo que enriquecen los datos limpios de la capa raw a la capa procesada:

### Limpieza de Tipos
- Eliminación de símbolos de divisa (`€`) y normalización de separadores decimales.
- Casteo robusto de `float64` (`precio_actual`, `precio_anterior`) y `int64` (`referencia`).

### Feature Engineering
| Feature Creada | Método de Obtención | Utilidad |
|----------------|---------------------|----------|
| `marca_propia` | Detección mediante Regex de las marcas insignia. | Clasificación de surtido. |
| `tiene_precio_anterior` | Booleano basado en la existencia de un precio anterior válido. | Filtro rápido de eventos de fluctuación. |
| `variacion_pct` | Incremento porcentual usando `precio_previo` de la tabla de estado. | Detección de anomalías. |
| `dias_sin_cambio` | Diferencia en días desde la última fecha modificada en `ultimo_precio`. | Feature para LSTM y elasticidad. |
| `unidad_medida` | Imputación mediante `ffill()` / `bfill()` e inferencia por formato (`ml`, `g`). | Comparativa justa de NLP. |

---

## 5. Módulo de Indexación (Elasticsearch)

El pipeline integra directamente con Elasticsearch para servir a los dashboards de Kibana, manejado por `es_utils.py` y alimentado desde la capa particionada o incremental.

### 5.1 Indexación Base (Datos Raw y Limpios)
- **Mapping Estricto:** Previene la explosión de campos. Los tipos clave (`keyword` para agregaciones, `text` para búsquedas en `titulo`) están blindados.
- **Eficiencia Bulk:** Uso de la API `helpers.bulk` para cargas masivas con chunks de 500 documentos, permitiendo la indexación de +660k registros en escasos segundos sin fallos.
- **Safe Types:** Función `to_native()` para convertir explícitamente tipos de `numpy` a tipos nativos de Python, evitando errores de serialización JSON.

### 5.2 Procesos Post-Indexación (ML y Analítica Avanzada)

Una vez los datos base están indexados y los modelos de Machine Learning o de Analítica han generado sus inferencias, se ejecutan scripts especializados que actúan sobre Elasticsearch para integrar estos resultados y hacerlos consumibles directamente desde los dashboards de Kibana:

1. **Detección de Anomalías (`indexar_anomalias_es.py`)**: 
   - Utiliza la API de Update de Elasticsearch para **enriquecer** los documentos existentes en el índice principal (`mercadona-precios`) sin sobrescribirlos.
   - Inyecta de forma eficiente métricas y booleanos calculados: `zscore`, `anomalia_zscore`, `media_local`, `std_local`, `score_if`, `anomalia_if`, `score_ae`, `error_mse` y `anomalia_ae`.
   - *Rendimiento:* Es capaz de actualizar y enriquecer más de 668,000 documentos asíncronamente (ej. etiquetando 3,293 anomalías Z-Score y 3,343 por Isolation Forest).
   - 🔗 *Más detalles metodológicos en: [Análisis de Anomalías](../anomalias/anomalias_analisis.md)*

2. **Índice de Precios al Consumidor (`indexar_ipc_es.py`)**:
   - Consolida y almacena las proyecciones y variaciones del IPC calculadas a partir del histórico de la cesta de la compra. Indexa en una estructura optimizada para el análisis macroeconómico de la inflación.

3. **Equivalencias de Mercado (`indexar_equivalencias_es.py`)**:
   - Tras la ejecución de `src/ml/nlp_embeddings.py` que calcula las similitudes vectoriales, este script lee los artefactos resultantes (`data/nlp/embeddings.parquet` y `data/nlp/equivalencias.parquet`).
   - Indexa los resultados del matching semántico bidireccional dentro del catálogo de Mercadona, estableciendo la relación directa entre sus **marcas propias** (Hacendado, Deliplus, etc.) y las **marcas comerciales** equivalentes en un índice dedicado (`equivalencias-nlp`).
   - Mapea un ID determinístico por pareja de productos, posibilitando la comparativa directa de precios e inflación entre la marca blanca y la marca de fabricante en los dashboards de Kibana.
   - 🔗 *Más detalles metodológicos en: [Análisis NLP Equivalencias](../nlp/nlp_equivalencias_analisis.md)*

---

## 6. Limitaciones Conocidas y Áreas de Mejora

1. **Gestión de eventos Watchdog:** El uso de `time.sleep(2)` en `NuevoCSVHandler` para esperar que el archivo CSV se escriba por completo es funcional pero propenso a fallos en discos lentos. Se recomendaría validar el cierre del archivo o usar archivos en tránsito (`.tmp`).
2. **Inferencia de unidades heredadas:** El proceso de `bfill/ffill` para `unidad_medida` es efectivo, pero en casos muy antiguos donde nunca se capturó la unidad, la inferencia por regex del campo `formato` es el último recurso (asignando "ud" por defecto si falla).
3. **Manejo de borrados físicos:** Si un producto es descatalogado por Mercadona, no genera un evento de eliminación explícito, simplemente deja de aparecer en los CSVs diarios. El estado en `ultimo_precio.parquet` permanecería congelado para siempre.

---

## 7. Conclusión

El pipeline ETL ha evolucionado de un script local de consolidación a una **arquitectura de datos resiliente, orientada a eventos y preparada para Big Data**. 

La separación estratégica entre almacenamiento de **histórico inmutable** (Particionado por Fecha) y **estado en tiempo real** (Último Precio) ha eliminado los cuellos de botella de memoria, permitiendo un procesamiento O(1) de nuevas ingestas. La integración fluida con Elasticsearch habilita directamente la fase analítica y de Machine Learning sobre un dataset limpio, tipado y validado.
