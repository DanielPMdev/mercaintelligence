# Pendientes (TODO)

## 1. Desarrollo y Nuevas Funcionalidades
- [ ] **Predicción de Precios**: Añadir modelo Prophet o XGBoost para predicción de precios.
- [ ] **Motor de Shrinkflation**: Implementar detección por variación de `precio_por_medida` vs `precio_actual`. Indexar alertas en Elasticsearch y crear endpoint de consulta.
- [ ] **Análisis de Catálogo**: Implementar detector de productos nuevos y descatalaogados mediante comparativa de snapshots diarios (joins) (Por ejemplo, una ventana de tiempo de 30 días). Consulta disponible vía API.
- [ ] **Frontend**: Realizar la interfaz web que consuma los datos de predicción, anomalías, shrinkflation, etc mediante la API.

## 2. Infraestructura y Despliegue
- [ ] Dockerizar la aplicación (crear Dockerfile y docker-compose.yml con la API, Elasticsearch y Kibana).
- [ ] Despliegue del contenedor Docker en un entorno de producción (ej. VPS como DigitalOcean, AWS, etc.).

## 3. Documentación y Entrega (TFE)
- [ ] Crear el README.md del proyecto con explicación de cada parte, cómo ejecutarlo y cualquier información relevante.
- [ ] Crear la memoria para el TFE.
- [ ] Crear el video-demo del proyecto para YouTube.