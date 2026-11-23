"""
Capa de SERVICIO: expone el modelo y la política por HTTP.
Correr:  uvicorn api.main:app --reload
Docs interactivas: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.schemas import CambioPolitica, Lote, Resultado, Solicitud
from src import modelo as capa_modelo
from src import politica as capa_politica
from src import registro
from src.features import ErrorDeDatos

log = logging.getLogger("api")
RAIZ = Path(__file__).resolve().parent.parent
RUTA_POLITICA = Path(os.getenv("POLITICA_PATH", RAIZ / "config" / "politica.yaml"))
RUTA_SENSIBILIDAD = Path(os.getenv("SENSIBILIDAD_PATH", RAIZ / "datos" / "sensibilidad_validacion.csv"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Se carga UNA vez al arrancar, no en cada request.
    app.state.politica = capa_politica.cargar_politica(RUTA_POLITICA)
    try:
        app.state.modelo = capa_modelo.cargar_modelo()
        app.state.error_modelo = None
    except Exception as e:  # la API arranca igual y /health muestra el problema
        log.exception("No se pudo cargar el modelo")
        app.state.modelo, app.state.error_modelo = None, str(e)
    yield


app = FastAPI(
    title="API de riesgo FPD — Cashea",
    description="El modelo estima la probabilidad de FPD; la política de negocio decide qué hacer.",
    version="1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------- errores
@app.exception_handler(RequestValidationError)
async def error_validacion(request: Request, exc: RequestValidationError):
    detalles = [
        {"campo": ".".join(str(p) for p in e["loc"] if p != "body"), "problema": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"error": "Datos de entrada inválidos", "detalles": detalles})


@app.exception_handler(ErrorDeDatos)
async def error_datos(request: Request, exc: ErrorDeDatos):
    return JSONResponse(status_code=422, content={"error": "El modelo no puede usar estos datos", "detalles": str(exc)})


@app.exception_handler(capa_politica.ErrorDePolitica)
async def error_politica(request: Request, exc: capa_politica.ErrorDePolitica):
    return JSONResponse(status_code=422, content={"error": "Cambio de política inválido", "detalles": str(exc)})


@app.exception_handler(Exception)
async def error_interno(request: Request, exc: Exception):
    log.exception("Error no controlado")
    return JSONResponse(status_code=500, content={"error": "Error interno del servicio. Ver logs del servidor."})


# ---------------------------------------------------------------- helpers
def _modelo(request: Request):
    m = request.app.state.modelo
    if m is None:
        raise HTTPException(503, detail=f"Modelo no disponible: {request.app.state.error_modelo}")
    return m


def _resultados(request: Request, solicitudes: list[Solicitud]) -> list[dict]:
    modelo = _modelo(request)
    politica = request.app.state.politica
    entradas = [s.model_dump(mode="json") for s in solicitudes]
    probs = modelo.predecir_lote(entradas)
    resultados = []
    for s, p in zip(solicitudes, probs):
        banda, accion = capa_politica.clasificar(p, politica)
        resultados.append({
            "solicitud_id": s.solicitud_id,
            "prob_fpd": round(p, 4),
            "banda": banda,
            "accion": accion,
            "umbral": politica["umbral"],
            "version_modelo": modelo.version,
            "version_politica": politica["version"],
        })
    try:
        registro.registrar_predicciones(entradas, resultados)
    except OSError:  # que un problema de disco no tire la predicción
        log.exception("No se pudo registrar la predicción")
    return resultados


# ---------------------------------------------------------------- endpoints
@app.get("/health")
def health(request: Request):
    ok = request.app.state.modelo is not None
    return {
        "estado": "ok" if ok else "sin_modelo",
        "modelo_cargado": ok,
        "error_modelo": request.app.state.error_modelo,
        "version_politica": request.app.state.politica["version"],
    }


@app.post("/predecir", response_model=Resultado)
def predecir(solicitud: Solicitud, request: Request):
    return _resultados(request, [solicitud])[0]


@app.post("/predecir_lote", response_model=list[Resultado])
def predecir_lote(lote: Lote, request: Request):
    return _resultados(request, lote.solicitudes)


@app.get("/politica")
def ver_politica(request: Request):
    return request.app.state.politica


@app.put("/politica")
def cambiar_politica(cambio: CambioPolitica, request: Request):
    actual = request.app.state.politica
    nueva = capa_politica.actualizar_umbral(actual, cambio.umbral)  # valida
    capa_politica.guardar_politica(nueva, RUTA_POLITICA)
    request.app.state.politica = nueva
    registro.registrar_cambio_politica(cambio.usuario, cambio.motivo, actual["umbral"],
                                       nueva["umbral"], nueva["version"])
    return nueva


@app.get("/sensibilidad")
def sensibilidad():
    if not RUTA_SENSIBILIDAD.exists():
        raise HTTPException(503, detail="Tabla de sensibilidad todavía no disponible (la genera el notebook).")
    return pd.read_csv(RUTA_SENSIBILIDAD).to_dict(orient="records")
