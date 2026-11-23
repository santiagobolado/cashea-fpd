# Predicción de First Payment Default (FPD) — Cashea

Proyecto final de Ciencia de Datos Aplicada (ITBA).
Servicio que estima la probabilidad de que un cliente caiga en FPD (más de 3 días de atraso
en la primera cuota) al momento de aprobar una compra en cuotas.

> **El modelo estima el riesgo; el negocio decide cuánto riesgo asumir.**

```
Solicitud de compra -> preparación automática de variables -> modelo FPD -> probabilidad
                    -> umbral configurable por negocio -> aprobar / ajustar condiciones / revisión
```

## Estructura y responsables

| Carpeta | Contenido | Responsable |
|---|---|---|
| `src/`, `api/`, `config/`, `modelo/` | Modelo, política de decisión y API (FastAPI) | Persona A |
| `app/` | Interfaz (Streamlit) que consume la API | Persona B |
| `notebooks/`, `datos/`, `docs/` | Análisis (sensibilidad, bandas, matriz de confusión), documentación y presentación | Persona C |

## Correr la API en local

```bash
python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
uvicorn api.main:app --reload      # http://127.0.0.1:8000/docs
```

Detalle de endpoints, contrato y errores: [`api/LEEME.md`](api/LEEME.md).
