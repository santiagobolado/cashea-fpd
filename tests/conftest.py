import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent


class ModeloFalso:
    """Reemplaza al modelo real en los tests: prob = gmv / 1000."""
    version = "test"

    def predecir_lote(self, solicitudes):
        return [min(0.99, s["gmv"] / 1000) for s in solicitudes]


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    # Política y logs en una carpeta temporal para no tocar los reales
    shutil.copy(RAIZ / "config" / "politica.yaml", tmp_path / "politica.yaml")
    (tmp_path / "sens.csv").write_text("umbral,pct_rechazo\n0.155,0.08\n")
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))

    import api.main as main
    from src import modelo, registro

    monkeypatch.setattr(main, "RUTA_POLITICA", tmp_path / "politica.yaml")
    monkeypatch.setattr(main, "RUTA_SENSIBILIDAD", tmp_path / "sens.csv")
    monkeypatch.setattr(registro, "DIR_LOGS", tmp_path / "logs")
    monkeypatch.setattr(modelo, "cargar_modelo", lambda: ModeloFalso())

    with TestClient(main.app, raise_server_exceptions=False) as c:
        c.tmp = tmp_path
        yield c


@pytest.fixture
def solicitud():
    return {
        "solicitud_id": "S-1",
        "fecha_origen": "2025-03-10",
        "gmv": 50.0,
        "anticipo": 20.0,
        "producto": "SPLIT_3",
        "score": 120,
        "tipo_orden": "First order",
        "ordenes_previas": 0,
        "comercio_id": "C-10",
        "vertical": "Supermercados",
    }
