mercaintelligence/
├── data/
│ ├── raw/ ← CSVs originales (clonados del repo)
│ ├── processed/ ← datos transformados (parquet particionado)
│ │ ├── fecha=2025-11-03/
│ │ ├── fecha=2025-11-08/
│ │ └── ... (hasta 154 particiones)
│ └── state/ ← estado incremental (tablas auxiliares)
│ └── ultimo_precio.parquet
│
├── notebooks/ ← Jupyter para ML/DL
│
├── src/
│ ├── etl/ ← pipeline de ingestión
│ ├── ml/ ← modelos
│ └── api/ ← API Flask
│
├── models/ ← modelos entrenados (.h5, .pkl)
│
└── dashboards/ ← exportaciones de Kibana
