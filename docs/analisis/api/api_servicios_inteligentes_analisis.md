# Análisis de los Servicios de API de MercaIntelligence

> Documento de análisis integrado del módulo `src/api/app.py`.
> Recoge el proceso iterativo de diseño, integración algorítmica y validación del sistema
> de endpoints expuestos para la interfaz de usuario, conectando los modelos analíticos con casos de uso reales.

---

## 1. Arquitectura de Servicios

El sistema expone una arquitectura orientada a microservicios monolíticos mediante Flask, que sirve de capa de abstracción entre los datos/modelos subyacentes y el consumidor final.

```mermaid
flowchart LR
    A[Cliente] --> B[API Flask]
    B --> C[/api/ipc/]
    B --> D[/api/ipc/prediccion]
    B --> E[/api/recomendaciones]
    B --> F[/api/cestas]
    B --> G[/api/anomalias/hoy]

    C --> H[Cálculo Gasto y Pesos]
    D --> I[LSTM Clasificador]
    D --> J[Tendencias Históricas]
    E --> K[NLP Embeddings]
    G --> L[Isolation Forest / Autoencoder]
```

### Decisiones de diseño clave

| Decisión | Justificación |
|----------|---------------|
| **Carga de datos en memoria (In-Memory)** | Permite tiempos de respuesta de milisegundos. Con ~4,300 productos, Pandas consume pocos recursos, evitando la necesidad de un motor de BBDD en tiempo real (Redis/PostgreSQL). |
| **Pesos automáticos por cantidad** | Los usuarios no conocen el peso porcentual de la leche en su cesta estadística. Se les pide la frecuencia de compra ("cantidad_mensual") y la API infiere el peso económico. |
| **Retrocompatibilidad de endpoints** | El endpoint soporta referencias simples, lista de productos con cantidad, o identificadores de perfiles predefinidos para facilitar la integración. |
| **Integración híbrida LSTM + Heurística** | El LSTM solo predice probabilidad de cambio, pero el usuario necesita un precio en euros. Se diseñó un proxy multiplicando la probabilidad por la mediana histórica de cambios de ese producto. |
| **Lógica bidireccional NLP** | No solo sugiere productos de marca propia si compras marca comercial; si ya compras marca propia, confirma cuánto dinero estás ahorrando respecto a la opción premium. |

---

## 2. Modelos de Inteligencia Integrados

La API va más allá del clásico CRUD, embebiendo la salida de los algoritmos de Machine Learning desarrollados en otras fases del proyecto.

### 2.1 IPC Personalizado (Estadística Ponderada)

El IPC oficial es una cesta genérica y fija. La API calcula un IPC personalizable basado en la cesta real del usuario.

| Métrica | Cálculo Interno |
|---------|-----------------|
| **Gasto Producto** | `precio_base_i × cantidad_mensual_i` |
| **Gasto Total** | `Σ gasto_i` |
| **Peso Relativo** | `gasto_i / gasto_total` |
| **Índice Producto** | `(precio_actual_i / precio_base_i) × 100` |
| **IPC Ponderado** | `Σ (peso_i × índice_i)` |

> [!TIP]
> Esta fórmula garantiza que si un producto sube mucho de precio pero se compra poco (ej: especias), apenas afecte al IPC final, simulando exactamente el impacto en el bolsillo del consumidor.

### 2.2 Predicción de Coste Futuro (LSTM + Tendencia)

Transforma una salida probabilística binaria en una estimación financiera continua.

| Componente | Origen | Función |
|---------|--------|---------|
| **Probabilidad de cambio (`prob_cambio_lstm`)** | Red Neuronal LSTM (Secuencias de precios) | 0.0 a 1.0. Probabilidad de que el precio mute a corto plazo. |
| **Tendencia histórica (`mediana_cambio`)** | Histórico Pandas (Análisis de ventanas temporales) | Magnitud direccional (ej. -5%). Si cambia, ¿cuánto suele cambiar y hacia dónde? |

**Fórmula**: `precio_predicho = precio_actual × (1 + prob_cambio_lstm × mediana_cambio_historico%)`

> [!IMPORTANT]
> Se utiliza la **mediana** de los cambios históricos (no la media) para proteger la predicción de caídas extremas provocadas por ofertas puntuales de hipermercado.

### 2.3 Motor de Recomendaciones Bidireccional

Utiliza las equivalencias calculadas por `paraphrase-multilingual-MiniLM-L12-v2`. Se filtra por similitud `>0.80` y `misma_unidad_medida = True` para garantizar viabilidad económica.

---

## 3. Proceso de Refinamiento del IPC Personalizado

El diseño de la API sufrió varias iteraciones arquitectónicas enfocadas en mejorar la usabilidad final (UX).

### Iteración 1: Media aritmética simple

```python
ipc = sum(indice_producto) / len(productos)
```

**Problema:** Una subida del 50% en un paquete de pipas de 0.50€ alteraba drásticamente el IPC de la cesta, equiparándose a una subida en la carne fresca (que cuesta 10x más y duele más al bolsillo).

### Iteración 2: Pesos estadísticos manuales

El usuario enviaba el peso porcentual de cada producto.

**Problema:** Alta fricción. Nadie sabe calcular qué porcentaje exacto de su presupuesto alimentario supone el arroz redondo.

### Iteración 3: Pesos implícitos (Versión final)

El usuario solo provee `referencia` y `cantidad_mensual`. La API cruza la cantidad con el `precio_base` del catálogo, estima el presupuesto total y deduce matemáticamente el peso de cada item.

---

## 4. Validación de Perfiles de Cesta

Se validó el sistema con cuatro arquetipos predefinidos, utilizando precios reales a fecha de mayo de 2026 respecto a noviembre de 2025.

| Perfil | N° Productos | Gasto Mensual Estimado | IPC Actual |
|--------|:----------:|:--------------------:|:----------:|
| **Cesta Estudiante** | 13 | ~30 € | 97.67 (-2.3%) |
| **Cesta Vegana** | 11 | ~33 € | 98.34 (-1.7%) |
| **Cesta Deportista** | 12 | ~55 € | 98.54 (-1.5%) |
| **Cesta Familiar** | 18 | ~64 € | 98.40 (-1.6%) |

> Todos los perfiles muestran deflación (-1.5% a -2.3%) desde noviembre de 2025, evidenciando una ligera corrección a la baja en precios de alimentación en los datos extraídos.

---

## 5. Limitaciones Conocidas

1. **Predicción Lineal Heurística:** Asumir que la dirección futura del precio será idéntica a su mediana histórica es una simplificación matemática. Funciona para productos estables pero puede fallar ante shocks de oferta inéditos.
2. **Dependencia Temporal del Backend:** El cálculo exige que todos los productos de la cesta existan en todas las fechas históricas comparadas; de lo contrario, se purgan fechas completas con `dropna()`, reduciendo la resolución de la gráfica del IPC final.
3. **Frecuencia de Compra Asumida Constante:** El cálculo proyecta el gasto mensual multiplicando por `cantidad_mensual` de manera estática, sin modelar variaciones estacionales de consumo (ej. comprar más helados en verano).

---

## 6. Conclusión

La API de MercaIntelligence unifica con éxito el análisis descriptivo (IPC ponderado), el análisis predictivo (LSTM) y el prescriptivo (Motor NLP de recomendación). 

Se ha priorizado un diseño empático con el usuario, donde la complejidad matemática se procesa en el backend (derivación de pesos, transformación de umbrales en euros, cruce bidireccional), dejando interfaces limpias (`POST /api/ipc/prediccion`) que exponen valor de negocio directo: ahorro cuantificable y alertas tempranas de inflación.
