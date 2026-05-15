# MercaIntelligence — Frontend Dashboard

Dashboard analítico desarrollado con **Vue 3 + Vite** para visualizar los datos recopilados por el pipeline de MercaIntelligence.

## Stack Tecnológico

- **Framework**: Vue 3 (Composition API)
- **Build tool**: Vite
- **Routing**: Vue Router
- **State**: Pinia
- **Charts**: Chart.js · ECharts · vue-echarts
- **HTTP**: Axios
- **Estilo**: Vanilla CSS (dark mode, design tokens)

## Vistas disponibles

| Ruta | Descripción |
|------|-------------|
| `/` | Dashboard principal con KPIs y resumen |
| `/ipc` | IPC personalizado de Mercadona |
| `/anomalias` | Detección de anomalías de precios (XGBoost) |
| `/marcas` | Equivalencias NLP entre marcas |
| `/catalogo` | Catálogo completo (~4.300 productos) |
| `/shrinkflation` | Detección de reduflación |
| `/about` | Información sobre el proyecto y el autor |

## Cómo ejecutar

```bash
# Instalar dependencias
pnpm install

# Servidor de desarrollo (requiere backend en :5000)
pnpm dev

# Build de producción
pnpm build
```

> El frontend requiere que el backend FastAPI (`src/api/app.py`) esté corriendo en `http://localhost:5000`.

## Autor

**Daniel Porras Morales** — [danielpm.is-a.dev](https://danielpm.is-a.dev) | [GitHub](https://github.com/DanielPMdev)
