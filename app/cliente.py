"""
Cliente HTTP de la API de riesgo FPD (persona A).
La interfaz SOLO habla con la API por acá: nunca carga el modelo.
Convierte los errores de la API en mensajes que se puedan mostrar a una persona.
"""
from __future__ import annotations

import requests

# (segundos para conectar, segundos para leer). En el plan gratis de Render el servicio
# "duerme" y la primera llamada puede tardar casi un minuto en despertarlo.
TIMEOUT = (10, 60)


class ErrorAPI(Exception):
    """Error pensado para mostrarse en pantalla (sin traceback)."""

    def __init__(self, mensaje: str, detalle: str | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalle = detalle


class ErrorDeUsuario(ErrorAPI):
    """Problema con lo que cargó la persona (formulario, CSV, etc.), no con la API."""


ETIQUETAS = {
    "solicitud_id": "ID de solicitud",
    "fecha_origen": "Fecha de la compra",
    "gmv": "Monto de la compra",
    "anticipo": "Anticipo",
    "producto": "Plan de cuotas",
    "score": "Score",
    "tipo_orden": "Tipo de orden",
    "ordenes_previas": "Órdenes previas",
    "comercio_id": "Comercio",
    "vertical": "Rubro",
    "umbral": "Umbral",
    "usuario": "Usuario",
    "motivo": "Motivo",
}

_TRADUCCIONES = [
    ("Field required", "es obligatorio"),
    ("Input should be greater than or equal to", "tiene que ser mayor o igual a"),
    ("Input should be greater than", "tiene que ser mayor que"),
    ("Input should be less than or equal to", "tiene que ser menor o igual a"),
    ("Input should be less than", "tiene que ser menor que"),
    ("Input should be a valid number", "tiene que ser un número"),
    ("Input should be a valid integer", "tiene que ser un número entero"),
    ("Input should be a valid date", "tiene que ser una fecha válida (AAAA-MM-DD)"),
    ("Input should be a valid string", "tiene que ser texto"),
    ("String should match pattern", "no tiene el formato esperado (por ejemplo SPLIT_3)"),
    ("String should have at least", "no puede estar vacío"),
    ("Extra inputs are not permitted", "no es un campo reconocido por la API"),
    ("List should have at least", "tiene que tener al menos un elemento"),
    ("List should have at most", "tiene demasiados elementos"),
]


def _traducir(msg: str) -> str:
    m = (msg or "").strip()
    if m.startswith("Value error, "):  # mensajes que ya escribió la API en castellano
        return m[len("Value error, "):]
    for en, es in _TRADUCCIONES:
        if m.startswith(en):
            if en in ("String should match pattern", "String should have at least"):
                return es                     # el resto del texto es técnico (regex, longitud)
            return es + m[len(en):]
    return m


def _nombre_campo(campo: str) -> str:
    """'solicitudes.3.gmv' -> 'Solicitud n.º 4 del archivo · Monto de la compra'."""
    partes = [p for p in (campo or "").split(".") if p]
    prefijo = ""
    if len(partes) >= 2 and partes[0] == "solicitudes" and partes[1].isdigit():
        prefijo = f"Solicitud n.º {int(partes[1]) + 1} del archivo"
        partes = partes[2:]
    elif partes and partes[0] == "solicitudes":
        partes = partes[1:]
    nombre = ETIQUETAS.get(partes[-1], partes[-1]) if partes else ""
    return " · ".join(x for x in (prefijo, nombre) if x)


def mensaje_422(cuerpo) -> str:
    """Arma el texto para un 422 de la API ({'error':..., 'detalles': [...] o '...'})."""
    if not isinstance(cuerpo, dict):
        return "La API rechazó los datos enviados."
    det = cuerpo.get("detalles")
    if isinstance(det, list) and det:
        lineas = []
        for d in det[:8]:
            nombre = _nombre_campo(d.get("campo", ""))
            problema = _traducir(d.get("problema", ""))
            lineas.append(f"- **{nombre}:** {problema}" if nombre else f"- {problema[:1].upper()}{problema[1:]}")
        if len(det) > 8:
            lineas.append(f"- … y {len(det) - 8} problemas más.")
        return "Hay datos que la API no puede aceptar:\n\n" + "\n".join(lineas)
    titulo = cuerpo.get("error") or "La API rechazó los datos enviados"
    if isinstance(det, str) and det:
        return f"{titulo}: {det}"
    return titulo


class ClienteAPI:
    def __init__(self, url_base: str):
        self.url_base = url_base.rstrip("/")

    # ------------------------------------------------------------------ interno
    def _llamar(self, metodo: str, ruta: str, **kw):
        url = self.url_base + ruta
        try:
            r = requests.request(metodo, url, timeout=TIMEOUT, **kw)
        except requests.exceptions.Timeout as e:
            raise ErrorAPI(
                "La API tardó demasiado en responder. Si está en el plan gratis de Render, "
                "puede estar despertándose: probá de nuevo en un minuto.",
                f"{metodo} {url}: {type(e).__name__}",
            ) from None
        except requests.exceptions.ConnectionError as e:
            raise ErrorAPI(
                f"No se pudo conectar con la API ({self.url_base}). "
                "Revisá que esté encendida y que la variable API_URL sea correcta.",
                f"{metodo} {url}: {type(e).__name__}",
            ) from None
        except requests.exceptions.RequestException as e:
            raise ErrorAPI("Falló la comunicación con la API.", f"{metodo} {url}: {type(e).__name__}") from None

        detalle = f"{metodo} {url} → HTTP {r.status_code}\n{r.text[:500]}"
        try:
            cuerpo = r.json()
        except ValueError:
            cuerpo = None

        if r.status_code == 200:
            if cuerpo is None:
                raise ErrorAPI("La API respondió algo que no se puede leer.", detalle)
            return cuerpo
        if r.status_code == 422:
            raise ErrorAPI(mensaje_422(cuerpo), detalle)
        if r.status_code == 503:
            motivo = cuerpo.get("detail") if isinstance(cuerpo, dict) else None
            raise ErrorAPI(f"El servicio todavía no puede responder: {motivo or 'no disponible'}", detalle)
        if r.status_code >= 500:
            raise ErrorAPI("La API tuvo un error interno. Avisale a la persona A y probá de nuevo en un rato.", detalle)
        raise ErrorAPI(f"La API respondió algo inesperado (código {r.status_code}).", detalle)

    # ------------------------------------------------------------------ contrato
    def health(self) -> dict:
        return self._llamar("GET", "/health")

    def predecir(self, solicitud: dict) -> dict:
        return self._llamar("POST", "/predecir", json=solicitud)

    def predecir_lote(self, solicitudes: list[dict]) -> list[dict]:
        # OJO: la API recibe {"solicitudes": [...]}, no una lista pelada.
        return self._llamar("POST", "/predecir_lote", json={"solicitudes": solicitudes})

    def politica(self) -> dict:
        return self._llamar("GET", "/politica")

    def cambiar_politica(self, umbral: float, usuario: str, motivo: str) -> dict:
        return self._llamar("PUT", "/politica", json={"umbral": umbral, "usuario": usuario, "motivo": motivo})

    def sensibilidad(self) -> list[dict]:
        return self._llamar("GET", "/sensibilidad")
