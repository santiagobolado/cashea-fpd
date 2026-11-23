"""
Registros en CSV: predicciones (base del monitoreo) y cambios de política (auditoría).
"""
from __future__ import annotations

import csv
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_LOGS = Path(os.getenv("LOGS_DIR", RAIZ / "logs"))
_lock = threading.Lock()

COLS_PRED = ["timestamp", "solicitud_id", "entrada_json", "prob_fpd", "banda",
             "accion", "umbral", "version_modelo", "version_politica"]
COLS_CAMBIOS = ["timestamp", "usuario", "motivo", "umbral_anterior", "umbral_nuevo",
                "version_politica_nueva"]


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _agregar(nombre: str, columnas: list[str], filas: list[dict]) -> None:
    DIR_LOGS.mkdir(parents=True, exist_ok=True)
    ruta = DIR_LOGS / nombre
    with _lock:
        nuevo = not ruta.exists()
        with open(ruta, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=columnas)
            if nuevo:
                w.writeheader()
            w.writerows(filas)


def registrar_predicciones(entradas: list[dict], resultados: list[dict]) -> None:
    ts = _ahora()
    filas = [
        {
            "timestamp": ts,
            "solicitud_id": r["solicitud_id"],
            "entrada_json": json.dumps(e, default=str, ensure_ascii=False),
            "prob_fpd": r["prob_fpd"],
            "banda": r["banda"],
            "accion": r["accion"],
            "umbral": r["umbral"],
            "version_modelo": r["version_modelo"],
            "version_politica": r["version_politica"],
        }
        for e, r in zip(entradas, resultados)
    ]
    _agregar("predicciones.csv", COLS_PRED, filas)


def registrar_cambio_politica(usuario: str, motivo: str, anterior: float,
                              nuevo: float, version_nueva: int) -> None:
    _agregar("cambios_politica.csv", COLS_CAMBIOS, [{
        "timestamp": _ahora(), "usuario": usuario, "motivo": motivo,
        "umbral_anterior": anterior, "umbral_nuevo": nuevo,
        "version_politica_nueva": version_nueva,
    }])
