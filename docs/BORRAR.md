Te paso también el notebook, ya que entreno en Google Colab, luego me descargo los modelos y la inferencia en local



Aqui tienes el resultado de la ejecución:



PS E:\Estudios\CE_IAyBD\TFE\mercaintelligence> & "C:/Users/Daniel PC/AppData/Local/Programs/Python/Python313/python.exe" e:/Estudios/CE_IAyBD/TFE/mercaintelligence/src/etl/recalibrar_umbral_ae.py

Distribución errores inferencia:

  Media : 0.00553778

  Std   : 0.02500659

  P90   : 0.00000023

  P95   : 0.03627351  ← nuevo umbral

  P99   : 0.14324459

  Max   : 0.20561838

  P90 → 59,864 anomalías (9.99%)

  P95 → 29,958 anomalías (5.00%)

  P99 → 5,989 anomalías (1.00%) 

✅ Umbral actualizado a 0.03627351

PS E:\Estudios\CE_IAyBD\TFE\mercaintelligence>