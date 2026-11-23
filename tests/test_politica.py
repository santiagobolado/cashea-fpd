import pytest

from src.politica import ErrorDePolitica, actualizar_umbral, clasificar

POL = {"version": 1, "umbral": 0.155, "corte_medio": 0.10,
       "acciones": {"bajo": "aprobar", "medio": "ajustar_condiciones", "alto": "revision"}}


@pytest.mark.parametrize("prob,banda,accion", [
    (0.05, "bajo", "aprobar"),
    (0.10, "medio", "ajustar_condiciones"),   # el corte entra en la banda de arriba
    (0.155, "alto", "revision"),
    (0.60, "alto", "revision"),
])
def test_clasificar(prob, banda, accion):
    assert clasificar(prob, POL) == (banda, accion)


def test_subir_umbral_aprueba_mas():
    # Una prob de 0,18 está en revisión con 0,155 y deja de estarlo con 0,25 (ej. Black Friday)
    assert clasificar(0.18, POL)[0] == "alto"
    assert clasificar(0.18, actualizar_umbral(POL, 0.25))[0] == "medio"


def test_umbral_invalido():
    with pytest.raises(ErrorDePolitica):
        actualizar_umbral(POL, 0.05)  # por debajo del corte medio


def test_version_sube():
    assert actualizar_umbral(POL, 0.2)["version"] == 2
