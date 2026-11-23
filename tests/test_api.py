import csv


def test_health(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200 and r.json()["modelo_cargado"] is True


def test_predecir_ok_y_registra(cliente, solicitud):
    r = cliente.post("/predecir", json=solicitud)
    assert r.status_code == 200
    body = r.json()
    assert body["prob_fpd"] == 0.05 and body["banda"] == "bajo" and body["accion"] == "aprobar"
    filas = list(csv.DictReader(open(cliente.tmp / "logs" / "predicciones.csv")))
    assert len(filas) == 1 and filas[0]["solicitud_id"] == "S-1"


def test_predecir_lote(cliente, solicitud):
    otra = {**solicitud, "solicitud_id": "S-2", "gmv": 300}
    r = cliente.post("/predecir_lote", json={"solicitudes": [solicitud, otra]})
    assert r.status_code == 200
    assert [x["banda"] for x in r.json()] == ["bajo", "alto"]


def test_monto_negativo_da_422(cliente, solicitud):
    r = cliente.post("/predecir", json={**solicitud, "gmv": -5})
    assert r.status_code == 422
    assert r.json()["detalles"][0]["campo"] == "gmv"


def test_campo_desconocido_da_422(cliente, solicitud):
    r = cliente.post("/predecir", json={**solicitud, "gmvv": 5})
    assert r.status_code == 422


def test_anticipo_mayor_que_monto(cliente, solicitud):
    assert cliente.post("/predecir", json={**solicitud, "anticipo": 80}).status_code == 422


def test_producto_mal_formado(cliente, solicitud):
    assert cliente.post("/predecir", json={**solicitud, "producto": "3 cuotas"}).status_code == 422


def test_score_vacio_es_valido(cliente, solicitud):
    assert cliente.post("/predecir", json={**solicitud, "score": None}).status_code == 200


def test_cambiar_politica_y_auditar(cliente, solicitud):
    r = cliente.put("/politica", json={"umbral": 0.25, "usuario": "riesgo", "motivo": "Black Friday: priorizar volumen"})
    assert r.status_code == 200 and r.json()["version"] == 2
    assert cliente.get("/politica").json()["umbral"] == 0.25
    cambios = list(csv.DictReader(open(cliente.tmp / "logs" / "cambios_politica.csv")))
    assert cambios[0]["umbral_anterior"] == "0.155" and cambios[0]["usuario"] == "riesgo"
    # La predicción usa la política nueva
    assert cliente.post("/predecir", json=solicitud).json()["version_politica"] == 2


def test_politica_invalida_da_422(cliente):
    r = cliente.put("/politica", json={"umbral": 0.05, "usuario": "x", "motivo": "prueba de error"})
    assert r.status_code == 422


def test_sensibilidad(cliente):
    assert cliente.get("/sensibilidad").json()[0]["umbral"] == 0.155


def test_error_interno_da_500(cliente, solicitud, monkeypatch):
    def explota(_):
        raise RuntimeError("boom")
    monkeypatch.setattr(cliente.app.state.modelo, "predecir_lote", explota)
    r = cliente.post("/predecir", json=solicitud)
    assert r.status_code == 500 and "boom" not in r.text  # no filtra detalles internos
