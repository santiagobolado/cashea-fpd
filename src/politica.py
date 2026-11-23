"""
Capa de POLÍTICA DE NEGOCIO: probabilidad -> banda -> acción.
No sabe nada de ML. "El modelo estima riesgo; el negocio decide cuánto riesgo asumir."
"""
from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
RUTA_POLITICA = RAIZ / "config" / "politica.yaml"


class ErrorDePolitica(ValueError):
    """Cambio de política inválido (ej. umbral por debajo del corte medio)."""


def cargar_politica(ruta: Path = RUTA_POLITICA) -> dict:
    with open(ruta, encoding="utf-8") as f:
        politica = yaml.safe_load(f)
    validar_politica(politica)
    return politica


def validar_politica(politica: dict) -> None:
    umbral, corte = politica["umbral"], politica["corte_medio"]
    if not (0 < corte < umbral < 1):
        raise ErrorDePolitica(
            f"Se necesita 0 < corte_medio ({corte}) < umbral ({umbral}) < 1"
        )


def clasificar(prob: float, politica: dict) -> tuple[str, str]:
    """Devuelve (banda, accion)."""
    if prob >= politica["umbral"]:
        banda = "alto"
    elif prob >= politica["corte_medio"]:
        banda = "medio"
    else:
        banda = "bajo"
    return banda, politica["acciones"][banda]


def actualizar_umbral(politica: dict, nuevo_umbral: float) -> dict:
    """Devuelve una política NUEVA con el umbral cambiado y la versión +1 (no guarda)."""
    nueva = {**politica, "umbral": float(nuevo_umbral), "version": politica["version"] + 1}
    validar_politica(nueva)
    return nueva


def guardar_politica(politica: dict, ruta: Path = RUTA_POLITICA) -> None:
    with open(ruta, "w", encoding="utf-8") as f:
        yaml.safe_dump(politica, f, allow_unicode=True, sort_keys=False)
