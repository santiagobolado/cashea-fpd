"""
Capa de MODELO: carga el .joblib una sola vez y predice la probabilidad de FPD.
No sabe nada de FastAPI ni de la política de negocio.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from src.features import ErrorDeDatos, construir_variables

RAIZ = Path(__file__).resolve().parent.parent
RUTA_MODELO = RAIZ / "modelo" / "modelo_fpd_cashea.joblib"
RUTA_METADATA = RAIZ / "modelo" / "modelo_fpd_cashea_metadata.json"


class ModeloFPD:
    def __init__(self, ruta: Path = RUTA_MODELO, ruta_metadata: Path = RUTA_METADATA):
        if not Path(ruta).exists():
            raise FileNotFoundError(f"No existe el modelo en {ruta}")
        obj = joblib.load(ruta)

        # El .joblib puede ser el pipeline solo o un dict con el pipeline + artefactos.
        if isinstance(obj, dict):
            self.artefactos = obj
            self.pipeline = next(
                (v for v in obj.values() if hasattr(v, "predict_proba")), None
            )
        else:
            self.artefactos = {}
            self.pipeline = obj
        if self.pipeline is None:
            raise ValueError("El .joblib no contiene un objeto con predict_proba")

        self.columnas = list(getattr(self.pipeline, "feature_names_in_", []))
        self.version = self._leer_version(ruta_metadata)

    def _leer_version(self, ruta_metadata: Path) -> str:
        meta = self.artefactos.get("metadata", {})
        if not meta and Path(ruta_metadata).exists():
            meta = json.loads(Path(ruta_metadata).read_text(encoding="utf-8"))
        if isinstance(meta, dict) and meta:
            nombre = meta.get("modelo", "gb")
            fecha = meta.get("fecha_entrenamiento", "")
            return f"{nombre} {fecha}".strip()
        return "gb-entregable3"

    def _preparar(self, solicitudes: list[dict]) -> pd.DataFrame:
        X = construir_variables(solicitudes, self.artefactos)  # todo el lote de una vez
        if self.columnas:
            faltan = [c for c in self.columnas if c not in X.columns]
            if faltan:
                raise ErrorDeDatos(f"Faltan variables para el modelo: {faltan}")
            X = X[self.columnas]  # mismo orden que en el entrenamiento
        return X

    def predecir_lote(self, solicitudes: list[dict]) -> list[float]:
        X = self._preparar(solicitudes)
        return [float(p) for p in self.pipeline.predict_proba(X)[:, 1]]

    def predecir(self, solicitud: dict) -> float:
        return self.predecir_lote([solicitud])[0]


@lru_cache(maxsize=1)
def cargar_modelo() -> ModeloFPD:
    """Carga única (se llama al arrancar la API)."""
    return ModeloFPD()
