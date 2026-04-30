# recalibrar_umbral_ae.py  (ejecutar una vez, luego borrar)
import numpy as np
import joblib
from pathlib import Path
import pandas as pd

OUTPUT_PATH = Path("data/anomalias/ae_resultados.parquet")
UMBRAL_PATH = Path("models/ae_umbral.pkl")

# Cargar los errores MSE ya calculados en la inferencia completa
df = pd.read_parquet(OUTPUT_PATH, columns=["error_mse"])
errores = df["error_mse"].values

# Nuevo umbral: percentil 95 sobre la distribución REAL de inferencia
# (equivale a etiquetar el 5% más anómalo del catálogo completo)
nuevo_umbral = float(np.percentile(errores, 95))

print("Distribución errores inferencia:")
print(f"  Media : {errores.mean():.8f}")
print(f"  Std   : {errores.std():.8f}")
print(f"  P90   : {np.percentile(errores, 90):.8f}")
print(f"  P95   : {nuevo_umbral:.8f}  ← nuevo umbral")
print(f"  P99   : {np.percentile(errores, 99):.8f}")
print(f"  Max   : {errores.max():.8f}")

# Cuántas anomalías quedan con cada percentil
for p in [90, 95, 99]:
    t = np.percentile(errores, p)
    n = (errores > t).sum()
    print(f"  P{p} → {n:,} anomalías ({n / len(errores) * 100:.2f}%)")

# Guardar nuevo umbral
umbral_data = joblib.load(UMBRAL_PATH)
umbral_data["umbral"] = nuevo_umbral
umbral_data["metodo"] = "percentil_95_inferencia"
joblib.dump(umbral_data, UMBRAL_PATH)
print(f"\n✅ Umbral actualizado a {nuevo_umbral:.8f}")
