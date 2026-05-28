# Pendientes (TODO)

## 1. Infraestructura y Despliegue
- [] Volver a dockerizar la aplicación con los nuevos modelos ya creados.
- [ ] Despliegue del contenedor Docker en un entorno de producción (ej. VPS como DigitalOcean, AWS, etc.).

## 3. Documentación y Entrega (TFE)  
- [ ] Crear el video-demo del proyecto para YouTube.

## 4. Mejoras a Futuro (MLOps y Robustez de Modelos)
- [ ] **Ciclo de Reentrenamiento Automatizado (Pipeline CI/CD):** Programar un flujo (ej. en GitHub Actions) para reentrenar periódicamente el regresor XGBoost con los datos frescos del scraper diario.
- [ ] **Monitoreo y Detección de Data Drift:** Implementar pruebas estadísticas (ej. Kolmogorov-Smirnov) sobre variables de precio clave para alertar cuando la distribución de datos actuales difiera de la de entrenamiento (desviación de datos).
- [ ] **Optimización del Regresor (Transformación Logarítmica):** Aplicar la transformación $\log(y + 1)$ sobre los precios y el target en XGBoost para mitigar el sesgo y mejorar predicciones en artículos de gama alta.
- [ ] **Estrategia Cold Start para Nuevos Productos:** Establecer un fallback en la API que devuelva el precio actual (baseline naive) para productos con menos de 45 días de historial, evitando estimaciones erráticas.
- [ ] **Filtro Semántico Híbrido (NLP):** Restringir el emparejamiento semántico a productos de la misma subcategoría y unidad de medida antes de calcular similitudes de coseno para erradicar falsos equivalentes funcionales.
- [ ] **Integración de Explicabilidad SHAP en Frontend:** Exponer mediante endpoints contribuciones de variables de importancia local (SHAP) para mostrar al usuario de manera interactiva en Vue 3 qué factores explican la variación de precio esperada.