"""
Contrato de entrada/salida de la API (validación con Pydantic).
Los campos de entrada son los mismos que recibe preparar_solicitud() en el notebook.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Solicitud(BaseModel):
    """Solicitud cruda, tal como llegaría del checkout (NO las variables del modelo)."""
    model_config = ConfigDict(extra="forbid")  # un campo mal escrito -> 422

    solicitud_id: str = Field(..., min_length=1, examples=["S-0001"])
    fecha_origen: date = Field(..., examples=["2025-03-10"])
    gmv: float = Field(..., gt=0, description="Monto total de la compra")
    anticipo: float = Field(..., ge=0, description="Monto del anticipo (no porcentaje)")
    producto: str = Field(..., pattern=r"^SPLIT_\d+$", examples=["SPLIT_3"],
                          description="Plan de cuotas: SPLIT_<n>")
    score: Optional[float] = Field(None, description="Score de Cashea; vacío o fuera de 0–1000 = inválido")
    tipo_orden: str = Field(..., examples=["First order"])
    ordenes_previas: int = Field(..., ge=0, description="En producción lo completa el sistema")
    comercio_id: str = Field(..., min_length=1)
    vertical: str = Field(..., min_length=1, examples=["Supermercados"])

    @model_validator(mode="after")
    def anticipo_menor_que_monto(self):
        if self.anticipo >= self.gmv:
            raise ValueError("el anticipo tiene que ser menor que el monto (gmv)")
        return self


class Lote(BaseModel):
    solicitudes: list[Solicitud] = Field(..., min_length=1, max_length=1000)


class Resultado(BaseModel):
    solicitud_id: str
    prob_fpd: float
    banda: Literal["bajo", "medio", "alto"]
    accion: str
    umbral: float
    version_modelo: str
    version_politica: int


class CambioPolitica(BaseModel):
    model_config = ConfigDict(extra="forbid")
    umbral: float = Field(..., gt=0, lt=1)
    usuario: str = Field(..., min_length=1)
    motivo: str = Field(..., min_length=5, description="Por qué se cambia (queda auditado)")
