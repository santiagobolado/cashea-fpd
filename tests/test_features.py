"""preparar_solicitud con artefactos de mentira (no necesita el .joblib)."""
import numpy as np
import pytest

from src import features

ART = {
    "frecuencia_comercio": {"C-1": 99},
    "verticales_modelo": ["Supermercados", "Moda"],
    "metadata": {"variables_entrada": [
        "log_gmv", "ratio_anticipo", "score", "n_cuotas", "ordenes_previas",
        "log_frec_comercio", "primera_orden", "score_invalido", "score_bajo",
        "cerca_de_cobro", "vertical", "dia_semana", "comercio_id"]},
}
BASE = {"solicitud_id": "S", "fecha_origen": "2025-03-14", "gmv": 100.0, "anticipo": 40.0,
        "producto": "SPLIT_3", "score": 10, "tipo_orden": "First order",
        "ordenes_previas": 0, "comercio_id": "C-1", "vertical": "Joyería"}


@pytest.fixture(autouse=True)
def dias(monkeypatch):
    monkeypatch.setattr(features, "DIAS", ["L", "M", "X", "J", "V", "S", "D"])


def test_transformaciones():
    X = features.construir_variables([BASE], ART)
    f = X.iloc[0]
    assert list(X.columns) == ART["metadata"]["variables_entrada"]
    assert f.ratio_anticipo == 0.4 and f.n_cuotas == 3 and f.primera_orden == 1
    assert f.score_bajo == 1 and f.score_invalido == 0
    assert f.vertical == "Otros"            # vertical fuera del modelo -> Otros
    assert f.dia_semana == "V"              # 14/03/2025 fue viernes
    assert f.cerca_de_cobro == 1            # día 14
    assert np.isclose(f.log_frec_comercio, np.log1p(99))


def test_score_vacio_e_invalido():
    X = features.construir_variables([{**BASE, "score": None}, {**BASE, "score": 5000}], ART)
    assert X.score_invalido.tolist() == [1, 1] and X.score.isna().all()


def test_lote_varias_filas():
    assert len(features.construir_variables([BASE, {**BASE, "comercio_id": "nuevo"}], ART)) == 2


def test_sin_dias_avisa(monkeypatch):
    monkeypatch.setattr(features, "DIAS", None)
    with pytest.raises(NotImplementedError):
        features.construir_variables([BASE], ART)
