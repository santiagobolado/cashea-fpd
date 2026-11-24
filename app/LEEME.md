# Interfaz Streamlit (Persona B)

Solo habla con la API por HTTP (`requests`). Nunca carga el modelo.

## Archivos
```
app/app.py                 pantallas: Nueva solicitud, Lote, Panel de riesgo
app/cliente.py             cliente HTTP + errores en lenguaje llano
app/mock.py                MODO_MOCK: respuestas falsas con el formato del contrato
app/lote.py                lectura y validación del CSV (sin Streamlit)
app/ejemplos_respaldo.json ejemplo provisorio hasta que llegue datos/ejemplos.json
app/requirements.txt
```

## Correr
```bash
python3.13 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r app/requirements.txt

# Sin API (datos falsos):
MODO_MOCK=1 streamlit run app/app.py                      # Windows PowerShell: $env:MODO_MOCK="1"; streamlit run app/app.py

# Con la API real:
API_URL=http://127.0.0.1:8000 streamlit run app/app.py    # o la URL de Render
```
El interruptor "Modo demo" de la barra lateral solo aparece si se arranca con MODO_MOCK=1 (desarrollo); en la versión publicada no se muestra, para no mezclar datos inventados con los reales.

## Qué espera de los demás
- `datos/ejemplos.json` (Persona C): lista (o `{"ejemplos": [...]}`) de solicitudes con los campos del contrato; opcional `"nombre"` para el botón.
- `datos/sensibilidad_validacion.csv` (Persona C, lo sirve la API en `GET /sensibilidad`): columnas
  `umbral, pct_rechazo, pct_fpd_evitado, tasa_fpd_aprobados, precision, recall, tp, fp, fn, tn`.
  El slider se mueve sobre los umbrales que tenga la tabla.
