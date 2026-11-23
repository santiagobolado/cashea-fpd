"""
MODO_MOCK: reemplaza a la API con respuestas FALSAS que tienen exactamente el mismo formato
del contrato. Sirve para desarrollar la interfaz sin depender de la API. Los números NO
significan nada: no se usan para tomar ninguna decisión.
"""
from __future__ import annotations

import random
import re

import numpy as np

from cliente import ErrorAPI, mensaje_422

VERSION_MODELO_MOCK = "MOCK (datos falsos)"


def _sensibilidad_falsa() -> list[dict]:
    """Tabla con las mismas columnas que datos/sensibilidad_validacion.csv, sobre una población inventada."""
    rng = np.random.default_rng(42)
    n = 10_000
    y = rng.random(n) < 0.08                       # ~8% de positivos, como el problema real
    p = np.where(y, rng.beta(3, 12, n), rng.beta(1.5, 14, n))
    filas = []
    for u in np.round(np.arange(0.05, 0.4001, 0.005), 3):
        alto = p >= u
        tp = int((alto & y).sum()); fp = int((alto & ~y).sum())
        fn = int((~alto & y).sum()); tn = int((~alto & ~y).sum())
        filas.append({
            "umbral": float(u),
            "pct_rechazo": (tp + fp) / n,
            "pct_fpd_evitado": tp / (tp + fn),
            "tasa_fpd_aprobados": fn / (fn + tn),
            "precision": tp / (tp + fp) if (tp + fp) else 0.0,
            "recall": tp / (tp + fn),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        })
    return filas


class ClienteMock:
    def __init__(self):
        self._politica = {
            "version": 1, "umbral": 0.155, "corte_medio": 0.1001,
            "acciones": {"bajo": "aprobar", "medio": "ajustar_condiciones", "alto": "revision"},
        }
        self._sens = _sensibilidad_falsa()

    # ---- helpers
    def _problemas(self, s: dict) -> list[dict]:
        det = []
        if not isinstance(s.get("gmv"), (int, float)) or s["gmv"] <= 0:
            det.append({"campo": "gmv", "problema": "Input should be greater than 0"})
        if not re.fullmatch(r"SPLIT_\d+", str(s.get("producto", ""))):
            det.append({"campo": "producto", "problema": "String should match pattern '^SPLIT_\\d+$'"})
        if isinstance(s.get("gmv"), (int, float)) and isinstance(s.get("anticipo"), (int, float)) \
                and s["gmv"] > 0 and s["anticipo"] >= s["gmv"]:
            det.append({"campo": "", "problema": "Value error, el anticipo tiene que ser menor que el monto (gmv)"})
        return det

    def _una(self, s: dict) -> dict:
        det = self._problemas(s)
        if det:
            raise ErrorAPI(mensaje_422({"error": "Datos de entrada inválidos", "detalles": det}))
        rng = random.Random(str(s.get("solicitud_id")))
        prob = rng.betavariate(1.3, 9)
        if s["anticipo"] / s["gmv"] < 0.2:
            prob += 0.10
        if s.get("score") is None:
            prob += 0.08
        prob = round(min(prob, 0.95), 4)
        pol = self._politica
        banda = "alto" if prob >= pol["umbral"] else "medio" if prob >= pol["corte_medio"] else "bajo"
        return {"solicitud_id": s["solicitud_id"], "prob_fpd": prob, "banda": banda,
                "accion": pol["acciones"][banda], "umbral": pol["umbral"],
                "version_modelo": VERSION_MODELO_MOCK, "version_politica": pol["version"]}

    # ---- contrato
    def health(self) -> dict:
        return {"estado": "ok", "modelo_cargado": True, "error_modelo": None,
                "version_politica": self._politica["version"]}

    def predecir(self, solicitud: dict) -> dict:
        return self._una(solicitud)

    def predecir_lote(self, solicitudes: list[dict]) -> list[dict]:
        det = []
        for i, s in enumerate(solicitudes):   # como la API real: informa los problemas de todas las filas
            for d in self._problemas(s):
                det.append({"campo": ".".join(x for x in ("solicitudes", str(i), d["campo"]) if x), "problema": d["problema"]})
        if det:
            raise ErrorAPI(mensaje_422({"error": "Datos de entrada inválidos", "detalles": det}))
        return [self._una(s) for s in solicitudes]

    def politica(self) -> dict:
        return dict(self._politica)

    def cambiar_politica(self, umbral: float, usuario: str, motivo: str) -> dict:
        corte = self._politica["corte_medio"]
        if not (0 < corte < umbral < 1):
            raise ErrorAPI(mensaje_422({
                "error": "Cambio de política inválido",
                "detalles": f"Se necesita 0 < corte_medio ({corte}) < umbral ({umbral}) < 1"}))
        self._politica = {**self._politica, "umbral": float(umbral), "version": self._politica["version"] + 1}
        return dict(self._politica)

    def sensibilidad(self) -> list[dict]:
        return list(self._sens)
