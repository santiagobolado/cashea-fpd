# API de riesgo FPD (Persona A)

## Estructura
```
src/features.py   solicitud cruda -> variables (ÚNICO punto a adaptar: pegar preparar_solicitud)
src/modelo.py     carga el .joblib una vez y predice (sin FastAPI)
src/politica.py   probabilidad -> banda -> acción (sin ML)
src/registro.py   logs/predicciones.csv y logs/cambios_politica.csv
api/schemas.py    contrato de entrada/salida (Pydantic)
api/main.py       endpoints y manejo de errores
config/politica.yaml  umbral y cortes (los cambia negocio vía PUT /politica)
```

## Correr en local
```bash
python3.13 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q                        # tests
uvicorn api.main:app --reload    # API en http://127.0.0.1:8000  (docs: /docs)
```

## Probar
```bash
curl -X POST http://127.0.0.1:8000/predecir -H "content-type: application/json" -d @scripts/ejemplo_solicitud.json
curl -X PUT  http://127.0.0.1:8000/politica -H "content-type: application/json" \
     -d '{"umbral":0.25,"usuario":"riesgo","motivo":"Black Friday: priorizar volumen"}'
```

## Errores
| Código | Cuándo |
|---|---|
| 422 | Datos inválidos (monto <= 0, anticipo fuera de 0–1, campo desconocido) o umbral < corte_medio |
| 503 | Modelo no cargado o tabla de sensibilidad todavía no generada |
| 500 | Error interno (mensaje genérico; el detalle queda en los logs del servidor) |

## Limitación conocida
En Render (plan gratis) el disco se borra al reiniciar: los CSV de logs y los cambios de política
se pierden. Alcanza para la demo; en producción irían a una base de datos.
