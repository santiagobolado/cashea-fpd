"""
PASO 1 — Inspeccionar el modelo guardado.

Correr esto en el MISMO Colab donde está el notebook del Entregable 3
(después de ejecutar las celdas que definen preparar_solicitud), o pegarlo en una celda.
Copiá TODA la salida y pasásela a Claude / al grupo.
"""
import inspect
import json
import sys

import joblib
import numpy
import pandas
import sklearn

RUTA = "modelo/modelo_fpd_cashea.joblib"

print("=" * 60)
print("1) VERSIONES (para fijar requirements.txt)")
print("python", sys.version.split()[0])
print("scikit-learn", sklearn.__version__)
print("numpy", numpy.__version__)
print("pandas", pandas.__version__)
print("joblib", joblib.__version__)

print("=" * 60)
print("2) QUÉ HAY ADENTRO DEL .joblib")
obj = joblib.load(RUTA)
print("tipo:", type(obj))
if isinstance(obj, dict):
    for k, v in obj.items():
        resumen = ""
        if isinstance(v, dict):
            muestra = list(v.items())[:3]
            resumen = f"dict con {len(v)} claves, ej: {muestra}"
        elif isinstance(v, (list, tuple, set)):
            resumen = f"{type(v).__name__} de {len(v)}, ej: {list(v)[:5]}"
        elif isinstance(v, (int, float, str, bool)):
            resumen = repr(v)
        else:
            resumen = type(v).__name__
        print(f"  - {k}: {resumen}")

    # Buscar el pipeline
    pipe = next((v for v in obj.values() if hasattr(v, "predict_proba")), None)
else:
    pipe = obj if hasattr(obj, "predict_proba") else None

print("=" * 60)
print("3) COLUMNAS QUE ESPERA EL PIPELINE")
if pipe is not None:
    print("pasos:", [n for n, _ in getattr(pipe, "steps", [])])
    print("feature_names_in_:", list(getattr(pipe, "feature_names_in_", [])))
else:
    print("No encontré un objeto con predict_proba")

print("=" * 60)
print("4) preparar_solicitud (definida en el notebook)")
try:
    print("firma:", inspect.signature(preparar_solicitud))  # noqa: F821
    print(inspect.getsource(preparar_solicitud))  # noqa: F821
except NameError:
    print("preparar_solicitud no está definida: ejecutá antes la celda del notebook que la crea.")

print("=" * 60)
print("5) metadata.json")
try:
    with open("modelo/modelo_fpd_cashea_metadata.json") as f:
        print(json.dumps(json.load(f), indent=2, ensure_ascii=False)[:3000])
except FileNotFoundError:
    print("No encontré modelo/modelo_fpd_cashea_metadata.json")
