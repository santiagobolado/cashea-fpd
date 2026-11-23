"""Prueba de humo con el modelo REAL. Se saltea si todavía no está el .joblib
o si falta pegar preparar_solicitud()."""
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "modelo" / "modelo_fpd_cashea.joblib"


@pytest.mark.skipif(not RUTA.exists(), reason="Falta modelo/modelo_fpd_cashea.joblib")
def test_modelo_real_predice():
    from src.modelo import ModeloFPD
    m = ModeloFPD()
    ejemplo = json.loads((RAIZ / "scripts" / "ejemplo_solicitud.json").read_text())
    try:
        p = m.predecir(ejemplo)
    except NotImplementedError:
        pytest.skip("Falta pegar preparar_solicitud() en src/features.py")
    assert 0 <= p <= 1
