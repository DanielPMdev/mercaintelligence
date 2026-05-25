# Pendientes (TODO)

## 1. Desarrollo y Nuevas Funcionalidades

### 1.1 Mantenimiento y Limpieza
- [x] Eliminar o refactorizar archivos boilerplate del frontend no utilizados:
  - [x] `src/views/AboutView.vue` — Reemplazado por página "Acerca del Proyecto"
  - [x] `src/components/HelloWorld.vue`
  - [x] `src/components/TheWelcome.vue`
  - [x] `src/components/WelcomeItem.vue`
  - [x] `src/components/icons/` (Contenido de la carpeta)
  - [x] `src/assets/logo.svg`
  - [x] `src/assets/base.css`
  - [x] `src/stores/counter.js`

### 1.2 Pulido y Branding (Frontend)
- [x] Reemplazar Favicon por defecto por el logo de MercaIntelligence.
- [x] Configurar `manifest.json` y metadatos de Web App (PWA básica).
- [x] Implementar página 404 personalizada en el router.
- [x] Añadir etiquetas Meta SEO (Open Graph) en `index.html`.
- [x] Actualizar metadatos en `package.json` (nombre y versión).
- [x] Personalizar el `README.md` de la carpeta frontend.

## 2. Infraestructura y Despliegue
- [x] Volver a dockerizar la aplicación con los nuevos modelos ya creados.
- [ ] Despliegue del contenedor Docker en un entorno de producción (ej. VPS como DigitalOcean, AWS, etc.).

## 3. Documentación y Entrega (TFE)
- [x] Crear el README.md del proyecto con explicación de cada parte, cómo ejecutarlo y cualquier información relevante.
- [x] Crear la memoria para el TFE.
- [ ] Crear la presentacion para la defensa del TFE.
- [ ] Crear el video-demo del proyecto para YouTube.

## 4. Mejoras a Futuro (MLOps y Robustez de Modelos)
- [ ] **Ciclo de Reentrenamiento Automatizado (Pipeline CI/CD):** Programar un flujo (ej. en GitHub Actions) para reentrenar periódicamente el regresor XGBoost con los datos frescos del scraper diario.
- [ ] **Monitoreo y Detección de Data Drift:** Implementar pruebas estadísticas (ej. Kolmogorov-Smirnov) sobre variables de precio clave para alertar cuando la distribución de datos actuales difiera de la de entrenamiento (desviación de datos).
- [ ] **Optimización del Regresor (Transformación Logarítmica):** Aplicar la transformación $\log(y + 1)$ sobre los precios y el target en XGBoost para mitigar el sesgo y mejorar predicciones en artículos de gama alta.
- [ ] **Estrategia Cold Start para Nuevos Productos:** Establecer un fallback en la API que devuelva el precio actual (baseline naive) para productos con menos de 45 días de historial, evitando estimaciones erráticas.
- [ ] **Filtro Semántico Híbrido (NLP):** Restringir el emparejamiento semántico a productos de la misma subcategoría y unidad de medida antes de calcular similitudes de coseno para erradicar falsos equivalentes funcionales.
- [ ] **Integración de Explicabilidad SHAP en Frontend:** Exponer mediante endpoints contribuciones de variables de importancia local (SHAP) para mostrar al usuario de manera interactiva en Vue 3 qué factores explican la variación de precio esperada.