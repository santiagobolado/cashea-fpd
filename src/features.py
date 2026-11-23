"""
Preparación de variables: solicitud cruda -> filas con las columnas que espera el pipeline.

preparar_solicitud() está copiada TAL CUAL del notebook del Entregable 3
(no cambiar la lógica: el modelo se entrenó con estas transformaciones).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class ErrorDeDatos(ValueError):
    """Dato válido en formato pero que el modelo no puede usar.
    La API lo devuelve como 422 con este mensaje."""


# Constante del notebook usada para dia_semana.
# Mismo orden que dayofweek (0 = lunes); etiquetas verificadas contra el encoder del pipeline.
DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]


# ---------------------------------------------------------------------------
# Copiada del notebook (Entregable 3, sección 14)
# ---------------------------------------------------------------------------
def preparar_solicitud(sol, art):
    # Convierte los datos crudos de una solicitud en las variables que espera el pipeline.
    d = pd.DataFrame(sol).copy()
    d["fecha_origen"] = pd.to_datetime(d["fecha_origen"])
    invalido = d["score"].isna() | (d["score"] < 0) | (d["score"] > 1000)
    d["score_invalido"] = invalido.astype(int)
    d["score"] = d["score"].where(~invalido)
    d["score_bajo"] = (d["score"] <= 19).astype(int)
    d["log_gmv"] = np.log1p(d["gmv"])
    d["ratio_anticipo"] = d["anticipo"] / d["gmv"]
    d["n_cuotas"] = d["producto"].str.replace("SPLIT_", "").astype(int)
    d["primera_orden"] = (d["tipo_orden"] == "First order").astype(int)
    d["log_frec_comercio"] = np.log1p(d["comercio_id"].map(art["frecuencia_comercio"]).fillna(0))
    d["vertical"] = d["vertical"].where(d["vertical"].isin(art["verticales_modelo"]), "Otros")
    d["dia_semana"] = d["fecha_origen"].dt.dayofweek.map(dict(enumerate(DIAS)))
    dia = d["fecha_origen"].dt.day
    d["cerca_de_cobro"] = (dia.between(13, 15) | (dia >= 28)).astype(int)
    d["comercio_id"] = d["comercio_id"].astype(str)
    return d[art["metadata"]["variables_entrada"]]


def construir_variables(solicitudes: list[dict], artefactos: dict) -> pd.DataFrame:
    """Adaptador entre la API y preparar_solicitud(): recibe una lista de solicitudes
    (dicts validados por la API) y devuelve un DataFrame con una fila por solicitud."""
    if DIAS is None:
        raise NotImplementedError("Falta copiar la constante DIAS del notebook en src/features.py")
    df = pd.DataFrame(solicitudes)
    # score puede venir vacío (None): forzar numérico para que None -> NaN
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    try:
        return preparar_solicitud(df, artefactos)
    except KeyError as e:
        raise ErrorDeDatos(f"Falta un dato que necesita el modelo: {e}") from e
