"""
Interfaz Streamlit del riesgo FPD (persona B).

Correr:  streamlit run app/app.py
Variables de entorno:
  API_URL    URL base de la API (ej. http://127.0.0.1:8000 o la de Render)
  MODO_MOCK  "1" para usar respuestas falsas sin API (también hay un interruptor en la barra lateral)

Regla: esta app SIEMPRE habla con la API por HTTP. Nunca carga el modelo.
"""
from __future__ import annotations

import html
import json
import os
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from cliente import ClienteAPI, ErrorAPI
from lote import CAMPOS, preparar_lote
from mock import ClienteMock

st.set_page_config(page_title="Riesgo FPD · Cashea", page_icon="💳", layout="wide")

RAIZ = Path(__file__).resolve().parent
RUTA_EJEMPLOS = Path(os.getenv("EJEMPLOS_PATH", RAIZ.parent / "datos" / "ejemplos.json"))  # los pasa la persona C
RUTA_RESPALDO = RAIZ / "ejemplos_respaldo.json"
API_URL_DEFECTO = "http://127.0.0.1:8000"

# Rubros que conoce el modelo (salen de verticales_modelo del .joblib). Cualquier otro la API lo trata como "Otros".
VERTICALES = ["Deporte", "Farmacias", "Herramientas", "Hogar", "Moda", "Otros",
              "Restaurantes", "Salud", "Servicios", "Supermercados", "Tecnología"]

TAMANO_LOTE_API = 1000       # la API acepta hasta 1000 solicitudes por llamada
SUBIDA_CAMPANIA = 0.05       # ejemplo del "modo campaña": cuánto se sube el umbral

ORDEN_BANDAS = ["alto", "medio", "bajo"]
COLORES = {  # (texto/borde, fondo)
    "bajo": ("#1b7a37", "#e6f4ea"),
    "medio": ("#a85f00", "#fff1d6"),
    "alto": ("#b3261e", "#fdecea"),
}
ACCIONES = {"aprobar": "Aprobar", "ajustar_condiciones": "Ajustar condiciones", "revision": "Enviar a revisión"}
FRASES = {
    "bajo": "Riesgo bajo: se puede aprobar la compra tal como está.",
    "medio": "Riesgo medio: conviene ajustar las condiciones (menos cuotas, más anticipo o menor monto).",
    "alto": "Riesgo alto: se recomienda mandar la solicitud a revisión antes de aprobarla.",
}


# ----------------------------------------------------------------------------- formato
def pct(x: float, dec: int = 1) -> str:
    return f"{x * 100:.{dec}f}%".replace(".", ",")


def num(x: float, dec: int | None = None) -> str:
    """Decimales con coma. Sin 'dec': los necesarios (hasta 4) y al menos 3, así 0.155 -> 0,155 y 0.1001 -> 0,1001."""
    if dec is None:
        s = f"{x:.4f}".rstrip("0")
        s += "0" * max(0, 3 - len(s.split(".")[1]))
    else:
        s = f"{x:.{dec}f}"
    return s.replace(".", ",")


def entero(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def mostrar_error(e: ErrorAPI) -> None:
    st.error(e.mensaje)
    if e.detalle:
        with st.expander("Detalle técnico (para pasarle a quien mantiene la API)"):
            st.code(e.detalle)


# ----------------------------------------------------------------------------- cliente
def obtener_cliente():
    if st.session_state.get("modo_mock"):
        if "cliente_mock" not in st.session_state:
            st.session_state["cliente_mock"] = ClienteMock()   # guarda la política falsa entre interacciones
        return st.session_state["cliente_mock"]
    return ClienteAPI(os.getenv("API_URL", API_URL_DEFECTO))


def barra_lateral() -> str:
    st.sidebar.title("Riesgo FPD · Cashea")
    pagina = st.sidebar.radio("Pantalla", ["Nueva solicitud", "Lote", "Panel de riesgo"])
    mock_por_defecto = os.getenv("MODO_MOCK", "").strip().lower() in ("1", "true", "si", "sí", "yes")
    st.sidebar.toggle("Modo demo (respuestas falsas)", value=mock_por_defecto, key="modo_mock",
                      help="Usa respuestas inventadas con el mismo formato de la API. No se conecta a nada.")
    st.sidebar.divider()
    if st.session_state.get("modo_mock"):
        st.sidebar.caption("Modo demo: no se usa la API.")
    else:
        url = os.getenv("API_URL")
        st.sidebar.caption(f"API: {url or API_URL_DEFECTO}")
        if not url:
            st.sidebar.warning("Falta la variable de entorno API_URL; uso la dirección local por defecto.")
        if st.sidebar.button("Probar conexión"):
            try:
                with st.spinner("Consultando la API…"):
                    h = obtener_cliente().health()
                if h.get("modelo_cargado"):
                    st.sidebar.success("La API responde y tiene el modelo cargado.")
                else:
                    st.sidebar.warning(f"La API responde, pero sin modelo: {h.get('error_modelo') or 'motivo desconocido'}")
            except ErrorAPI as e:
                st.sidebar.error(e.mensaje)
    return pagina


def aviso_demo() -> None:
    if st.session_state.get("modo_mock"):
        st.warning("**MODO DEMO:** las respuestas son falsas y sirven solo para probar la interfaz. "
                   "Los números no significan nada.")


# ----------------------------------------------------------------------------- ejemplos
def cargar_ejemplos() -> tuple[list[dict], bool]:
    """Devuelve (ejemplos, son_de_respaldo). Acepta una lista o {"ejemplos": [...]}."""
    for ruta, respaldo in ((RUTA_EJEMPLOS, False), (RUTA_RESPALDO, True)):
        if not ruta.exists():
            continue
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        lista = datos.get("ejemplos", []) if isinstance(datos, dict) else datos
        salida = []
        for i, e in enumerate(lista, 1):
            if not isinstance(e, dict):
                continue
            sol = e.get("solicitud", e)
            nombre = e.get("nombre") or e.get("titulo") or e.get("descripcion") or f"Ejemplo {i}"
            salida.append({"nombre": str(nombre), "solicitud": {c: sol.get(c) for c in CAMPOS}})
        if salida:
            return salida, respaldo
    return [], True


def poner_en_formulario(sol: dict) -> None:
    """Guarda los valores iniciales del formulario y sube la versión para que los widgets se creen de nuevo
    con esos valores (más confiable que escribir directamente en las claves de los widgets)."""
    ss = st.session_state
    try:
        fecha = date.fromisoformat(str(sol.get("fecha_origen")))
    except ValueError:
        fecha = date.today()
    ss["form_datos"] = {
        "solicitud_id": str(sol.get("solicitud_id") or ""),
        "fecha": fecha,
        "gmv": float(sol.get("gmv") or 1.0),
        "anticipo": float(sol.get("anticipo") or 0.0),
        "producto": str(sol.get("producto") or ""),
        "tipo_orden": str(sol.get("tipo_orden") or ""),
        "ordenes_previas": int(sol.get("ordenes_previas") or 0),
        "comercio_id": str(sol.get("comercio_id") or ""),
        "vertical": sol.get("vertical") if sol.get("vertical") in VERTICALES else "Otros",
        "sin_score": sol.get("score") is None,
        "score": float(sol["score"]) if sol.get("score") is not None else 0.0,
    }
    ss["form_ver"] = ss.get("form_ver", 0) + 1
    ss.pop("resultado_individual", None)


# ----------------------------------------------------------------------------- pantalla 1
def tarjeta_resultado(res: dict) -> None:
    banda = res["banda"]
    fg, bg = COLORES.get(banda, ("#444", "#eee"))
    accion = ACCIONES.get(res["accion"], res["accion"])
    st.markdown(
        f"""<div style="background:{bg};border-left:8px solid {fg};padding:16px 20px;border-radius:8px;color:#1f1f1f">
        <div style="font-size:14px;color:{fg};font-weight:600;text-transform:uppercase">Riesgo {html.escape(banda)}</div>
        <div style="font-size:40px;font-weight:700;color:{fg};line-height:1.2">{pct(res['prob_fpd'])}</div>
        <div style="font-size:16px">Acción sugerida: <b>{html.escape(accion)}</b></div></div>""",
        unsafe_allow_html=True,
    )


def pagina_nueva_solicitud(cliente) -> None:
    st.header("Nueva solicitud")
    st.caption("Simula lo que llega del checkout: se cargan los datos crudos de la compra y la API calcula el riesgo.")
    aviso_demo()

    ejemplos, es_respaldo = cargar_ejemplos()
    if "form_datos" not in st.session_state:
        poner_en_formulario(ejemplos[0]["solicitud"] if ejemplos else {})

    if ejemplos:
        st.markdown("**Cargar un ejemplo**")
        cols = st.columns(len(ejemplos[:3]))
        for col, ej in zip(cols, ejemplos[:3]):
            col.button(ej["nombre"], key=f"ej_{ej['nombre']}", width="stretch",
                       on_click=poner_en_formulario, args=(ej["solicitud"],))
        if es_respaldo:
            st.caption("Todavía no está datos/ejemplos.json (lo pasa la persona C): muestro un ejemplo provisorio.")

    d = st.session_state["form_datos"]
    v = st.session_state["form_ver"]

    def k(nombre: str) -> str:
        return f"f_{nombre}_{v}"

    with st.form("form_solicitud"):
        c1, c2, c3 = st.columns(3)
        c1.text_input("ID de solicitud", value=d["solicitud_id"], key=k("solicitud_id"))
        c1.date_input("Fecha de la compra", value=d["fecha"], key=k("fecha"), format="YYYY-MM-DD")
        c1.text_input("Comercio (ID)", value=d["comercio_id"], key=k("comercio_id"))
        c2.number_input("Monto de la compra", min_value=0.0, value=d["gmv"], step=1.0, key=k("gmv"))
        c2.number_input("Anticipo (monto, no porcentaje)", min_value=0.0, value=d["anticipo"], step=1.0, key=k("anticipo"))
        c2.text_input("Plan de cuotas", value=d["producto"], key=k("producto"),
                      help="Formato SPLIT_<cantidad>, por ejemplo SPLIT_3")
        c3.selectbox("Rubro", VERTICALES, index=VERTICALES.index(d["vertical"]), key=k("vertical"))
        c3.text_input("Tipo de orden", value=d["tipo_orden"], key=k("tipo_orden"), help='Por ejemplo "First order"')
        c3.number_input("Órdenes previas del cliente", min_value=0, value=d["ordenes_previas"], step=1, key=k("ordenes_previas"))
        s1, s2 = st.columns([1, 2])
        s1.number_input("Score del cliente (0 a 1000)", value=d["score"], step=1.0, key=k("score"))
        s2.checkbox("El cliente no tiene score", value=d["sin_score"], key=k("sin_score"))
        enviar = st.form_submit_button("Calcular riesgo", type="primary")

    if enviar:
        ss = st.session_state
        solicitud = {
            "solicitud_id": ss[k("solicitud_id")].strip(),
            "fecha_origen": ss[k("fecha")].isoformat(),
            "gmv": float(ss[k("gmv")]),
            "anticipo": float(ss[k("anticipo")]),
            "producto": ss[k("producto")].strip(),
            "score": None if ss[k("sin_score")] else float(ss[k("score")]),
            "tipo_orden": ss[k("tipo_orden")].strip(),
            "ordenes_previas": int(ss[k("ordenes_previas")]),
            "comercio_id": ss[k("comercio_id")].strip(),
            "vertical": ss[k("vertical")],
        }
        try:
            with st.spinner("Consultando la API… (si estaba dormida, puede tardar hasta un minuto)"):
                ss["resultado_individual"] = cliente.predecir(solicitud)
        except ErrorAPI as e:
            ss.pop("resultado_individual", None)
            mostrar_error(e)

    res = st.session_state.get("resultado_individual")
    if res:
        st.divider()
        izq, der = st.columns([1, 2])
        with izq:
            tarjeta_resultado(res)
        with der:
            st.markdown(
                f"Esta compra tiene una probabilidad estimada de **{pct(res['prob_fpd'])}** de caer en mora en la "
                f"primera cuota (más de 3 días de atraso). El umbral de alto riesgo es hoy **{pct(res['umbral'])}**."
            )
            st.markdown(f"**{FRASES.get(res['banda'], '')}**")
            st.caption(f"Modelo: {res['version_modelo']} · Política n.º {res['version_politica']}")
        with st.expander("Ver respuesta completa de la API"):
            st.json(res)


# ----------------------------------------------------------------------------- pantalla 2
def pagina_lote(cliente) -> None:
    st.header("Lote de solicitudes")
    st.caption("Subí un CSV con una solicitud por fila y la API calcula el riesgo de todas.")
    aviso_demo()

    ejemplos, _ = cargar_ejemplos()
    fila = {c: "" for c in CAMPOS}
    if ejemplos:
        fila.update({k: ("" if v is None else v) for k, v in ejemplos[0]["solicitud"].items()})
    plantilla = pd.DataFrame([fila])[CAMPOS].to_csv(index=False).encode("utf-8")
    st.download_button("Descargar plantilla CSV", plantilla, file_name="plantilla_solicitudes.csv", mime="text/csv")

    archivo = st.file_uploader("Archivo CSV", type=["csv"])
    if archivo is not None and st.button("Calcular riesgo del lote", type="primary"):
        try:
            entrada, payload = preparar_lote(archivo)
            resultados: list[dict] = []
            barra = st.progress(0.0, text="Consultando la API…")
            for i in range(0, len(payload), TAMANO_LOTE_API):
                resultados += cliente.predecir_lote(payload[i:i + TAMANO_LOTE_API])
                barra.progress(min(1.0, (i + TAMANO_LOTE_API) / len(payload)), text="Consultando la API…")
            barra.empty()
            if len(resultados) != len(payload):
                raise ErrorAPI("La API devolvió una cantidad de resultados distinta a la enviada. Avisale a la persona A.")
            res = pd.DataFrame(resultados)
            tabla = pd.concat([entrada[["solicitud_id", "gmv", "anticipo", "producto", "vertical"]].reset_index(drop=True),
                               res[["prob_fpd", "banda", "accion"]]], axis=1)
            st.session_state["lote_tabla"] = tabla
        except ErrorAPI as e:
            st.session_state.pop("lote_tabla", None)
            mostrar_error(e)

    tabla = st.session_state.get("lote_tabla")
    if tabla is None:
        return

    st.divider()
    cuenta = tabla["banda"].value_counts().reindex(ORDEN_BANDAS, fill_value=0)
    st.subheader(f"Resultado: {entero(len(tabla))} solicitudes")
    cols = st.columns(3)
    for col, b in zip(cols, ORDEN_BANDAS):
        col.metric(f"Riesgo {b}", entero(cuenta[b]))
        col.caption(f"{pct(cuenta[b] / len(tabla))} del lote")

    dist = pd.DataFrame({"banda": ORDEN_BANDAS, "solicitudes": [int(cuenta[b]) for b in ORDEN_BANDAS]})
    dist["porcentaje"] = dist["solicitudes"] / len(tabla)
    grafico = alt.Chart(dist).mark_bar().encode(
        x=alt.X("banda:N", sort=ORDEN_BANDAS, title="Banda de riesgo", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("solicitudes:Q", title="Solicitudes"),
        color=alt.Color("banda:N", legend=None,
                        scale=alt.Scale(domain=ORDEN_BANDAS, range=[COLORES[b][0] for b in ORDEN_BANDAS])),
        tooltip=["banda", "solicitudes", alt.Tooltip("porcentaje:Q", format=".1%")],
    ).properties(height=260)
    st.altair_chart(grafico, width="stretch")

    def pintar(b):
        fg, bg = COLORES.get(b, ("#444", "#fff"))
        return f"background-color:{bg};color:{fg};font-weight:600"

    mostrar = tabla.copy()
    mostrar["acción"] = mostrar["accion"].map(lambda a: ACCIONES.get(a, a))
    mostrar = mostrar.drop(columns="accion")
    st.dataframe(
        mostrar.style.map(pintar, subset=["banda"]).format({"prob_fpd": lambda x: pct(x), "gmv": "{:,.2f}", "anticipo": "{:,.2f}"}),
        width="stretch", hide_index=True,
    )
    st.download_button("Descargar resultados (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                       file_name="resultados_lote.csv", mime="text/csv")


# ----------------------------------------------------------------------------- pantalla 3
COLUMNAS_SENS = ["umbral", "pct_rechazo", "pct_fpd_evitado", "tasa_fpd_aprobados", "precision", "recall", "tp", "fp", "fn", "tn"]


def obtener_sensibilidad(cliente) -> pd.DataFrame:
    clave = ("mock" if st.session_state.get("modo_mock") else os.getenv("API_URL", API_URL_DEFECTO))
    if st.session_state.get("sens_clave") != clave:
        filas = cliente.sensibilidad()
        df = pd.DataFrame(filas)
        faltan = [c for c in COLUMNAS_SENS if c not in df.columns]
        if df.empty or faltan:
            raise ErrorAPI("La tabla de sensibilidad no tiene el formato esperado"
                           + (f" (faltan columnas: {', '.join(faltan)})." if faltan else " (está vacía)."))
        df = df[COLUMNAS_SENS].astype(float).sort_values("umbral").reset_index(drop=True)
        for c in ("pct_rechazo", "pct_fpd_evitado", "tasa_fpd_aprobados", "precision", "recall"):
            if df[c].max() > 1.0:          # por si la tabla viene en porcentaje (0-100) en lugar de fracción (0-1)
                df[c] = df[c] / 100
        st.session_state["sens_df"], st.session_state["sens_clave"] = df, clave
    return st.session_state["sens_df"]


def _subir_umbral(key: str, umbrales: list[float], objetivo: float) -> None:
    st.session_state[key] = min(umbrales, key=lambda u: abs(u - objetivo))


def pagina_panel(cliente) -> None:
    st.header("Panel de riesgo")
    st.caption("Para el equipo de negocio: el modelo estima el riesgo; el negocio decide cuánto riesgo asumir.")
    aviso_demo()

    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)

    try:
        pol = cliente.politica()
    except ErrorAPI as e:
        mostrar_error(e)
        return

    # --- política vigente
    st.subheader("Política vigente")
    c1, c2, c3 = st.columns(3)
    c1.metric("Umbral de alto riesgo", num(pol["umbral"]))
    c2.metric("Corte de riesgo medio", num(pol["corte_medio"]))
    c3.metric("Versión de la política", pol["version"])
    if pol.get("corte_medio_pendiente"):
        st.info("El corte de riesgo medio es un valor provisorio: todavía lo tiene que calcular el equipo de datos.")
    acciones = pol.get("acciones", {})
    st.dataframe(pd.DataFrame([
        {"Banda": "Alto", "Cuándo": f"probabilidad ≥ {num(pol['umbral'])}", "Acción": ACCIONES.get(acciones.get("alto"), acciones.get("alto"))},
        {"Banda": "Medio", "Cuándo": f"entre {num(pol['corte_medio'])} y {num(pol['umbral'])}", "Acción": ACCIONES.get(acciones.get("medio"), acciones.get("medio"))},
        {"Banda": "Bajo", "Cuándo": f"probabilidad < {num(pol['corte_medio'])}", "Acción": ACCIONES.get(acciones.get("bajo"), acciones.get("bajo"))},
    ]), hide_index=True, width="stretch")
    st.caption("Subir el umbral = aprobar más (se acepta más riesgo). Bajarlo = más conservador.")

    # --- simulador
    st.divider()
    st.subheader("Simulador de umbral")
    try:
        sens = obtener_sensibilidad(cliente)
    except ErrorAPI as e:
        mostrar_error(e)
        return

    umbrales = sens["umbral"].round(6).tolist()
    idx_vig = int((sens["umbral"] - pol["umbral"]).abs().idxmin())
    key = f"slider_umbral_v{pol['version']}"
    if key not in st.session_state:
        st.session_state[key] = umbrales[idx_vig]
    elegido = st.select_slider("Umbral a simular", options=umbrales, key=key, format_func=num)
    if elegido <= pol["corte_medio"]:
        st.warning(f"Con este umbral ({num(elegido)}) no queda banda media: tiene que ser mayor que el corte de riesgo "
                   f"medio ({num(pol['corte_medio'])}). Podés simularlo, pero no se va a poder guardar.")
    if abs(umbrales[idx_vig] - pol["umbral"]) > 1e-9:
        st.caption(f"El umbral vigente ({num(pol['umbral'])}) no está en la tabla de sensibilidad; "
                   f"para comparar uso el punto más cercano ({num(umbrales[idx_vig])}).")

    f = sens.loc[(sens["umbral"] - elegido).abs().idxmin()]
    v = sens.loc[idx_vig]
    cambia = abs(elegido - umbrales[idx_vig]) > 1e-9

    def delta(campo: str):
        return f"{(f[campo] - v[campo]) * 100:+.1f} pp vs vigente".replace(".", ",") if cambia else None

    m1, m2, m3 = st.columns(3)
    m1.metric("% de solicitudes con alto riesgo (rechazo)", pct(f["pct_rechazo"]), delta("pct_rechazo"), delta_color="off")
    m2.metric("% de FPD evitado", pct(f["pct_fpd_evitado"]), delta("pct_fpd_evitado"), delta_color="off")
    m3.metric("Tasa de FPD entre las aprobadas", pct(f["tasa_fpd_aprobados"]), delta("tasa_fpd_aprobados"), delta_color="off")

    st.caption("Indicadores calculados sobre datos de validación (no de producción).")
    st.markdown("**Matriz de confusión** (compras históricas de validación)")
    matriz = pd.DataFrame(
        [[entero(f["tp"]), entero(f["fn"])], [entero(f["fp"]), entero(f["tn"])]],
        index=["Cayó en FPD", "Pagó bien"],
        columns=["Marcadas como alto riesgo", "No marcadas (aprobadas)"],
    )
    st.table(matriz)
    st.caption("Son compras del pasado, no de producción. Cada cambio de umbral reparte las mismas compras de otra forma.")

    # --- modo campaña
    with st.expander("Modo campaña (ejemplo: Black Friday)"):
        st.markdown(
            "En una campaña se **sube** el umbral para aprobar más compras. Es un ejemplo para ver el efecto, "
            "no una recomendación."
        )
        st.warning(
            "En campaña puede cambiar la cartera (más compras nuevas, tickets más altos, otro tipo de clientes) y el "
            "modelo se entrenó con otro período. Subir el umbral deja pasar más compras riesgosas: hay que **vigilar la "
            "calibración** (que la probabilidad estimada siga pareciéndose a la mora real) y volver al umbral anterior "
            "cuando termine la campaña."
        )
        st.button(f"Simular campaña: subir el umbral {num(SUBIDA_CAMPANIA, 2)}", on_click=_subir_umbral,
                  args=(key, umbrales, pol["umbral"] + SUBIDA_CAMPANIA))

    # --- guardar
    st.divider()
    st.subheader("Guardar cambio")
    st.caption("Ojo: en la demo (servidor gratis) el cambio y su registro se pierden si el servicio se reinicia. "
               "Hacelo en vivo y no cuentes con que quede guardado de antes.")
    st.markdown(f"Umbral vigente: **{num(pol['umbral'])}** · Umbral a guardar (el del simulador): **{num(elegido)}**")
    with st.form("form_guardar"):
        usuario = st.text_input("Usuario (quién hace el cambio)")
        motivo = st.text_area("Motivo del cambio (mínimo 5 caracteres)", placeholder="Ej.: Black Friday: priorizar volumen")
        guardar = st.form_submit_button("Guardar cambio", type="primary")
    if guardar:
        if abs(elegido - pol["umbral"]) < 1e-9:
            st.warning("El umbral elegido es igual al vigente: no hay nada que guardar.")
        elif elegido <= pol["corte_medio"]:
            st.error(f"El umbral tiene que ser mayor que el corte de riesgo medio ({num(pol['corte_medio'])}).")
        elif not usuario.strip():
            st.error("Escribí quién hace el cambio.")
        elif len(motivo.strip()) < 5:
            st.error("Contanos el motivo del cambio (al menos 5 caracteres): queda registrado para auditoría.")
        else:
            try:
                with st.spinner("Guardando…"):
                    nueva = cliente.cambiar_politica(float(elegido), usuario.strip(), motivo.strip())
                st.session_state["flash"] = (f"Listo: el umbral pasó de {num(pol['umbral'])} a {num(nueva['umbral'])} "
                                             f"(política n.º {nueva['version']}). Quedó registrado quién, cuándo y por qué (mientras el servidor no se reinicie).")
                st.rerun()
            except ErrorAPI as e:
                mostrar_error(e)


# ----------------------------------------------------------------------------- main
def main() -> None:
    pagina = barra_lateral()
    cliente = obtener_cliente()
    if pagina == "Nueva solicitud":
        pagina_nueva_solicitud(cliente)
    elif pagina == "Lote":
        pagina_lote(cliente)
    else:
        pagina_panel(cliente)


main()
