# Pendientes (TODO)

- [ ] **Imágenes**: Crear carpeta `docs/img/` y subcarpeta `docs/img/lstm/` para organizar las gráficas y diagramas generados por el modelo.
- [ ] **Añadir Imagenes Autoencoder**: Crear subcarpeta `docs/img/autoencoder/` y añadir las gráficas generadas por el modelo autoencoder, realizar cambios en el notebook para guardar las imagenes en la carpeta local.
- [ ] **Modelos**: Descargar desde Colab/Drive y añadir a la carpeta local `models/`:
    - `lstm_clasificador.keras`
    - `lstm_scaler.pkl`
- [ ] **Datos**: Crear subcarpeta `data/predicciones/lstm/` para organizar el archivo `lstm_resultados.parquet`.
    - [ ] Actualizar `RESULTS_PATH` en `lstm_clasificador_colab.ipynb` para apuntar a la nueva ruta.

---

### Nota sobre la estructura de datos (Decisión de Diseño)
Se ha decidido separar los resultados del LSTM de la carpeta `anomalias/` por motivos semánticos:
- **`data/anomalias/`**: Reservada para modelos no supervisados que detectan eventos atípicos (Z-Score, Isolation Forest, Autoencoder).
- **`data/predicciones/`**: Nueva categoría para modelos supervisados como el LSTM que realizan una clasificación predictiva sobre el futuro de los precios.
