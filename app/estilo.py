"""
Estilo visual de la interfaz (solo apariencia; no toca la lógica).
Se inyecta con CSS porque en Streamlit Cloud el archivo de tema (.streamlit/config.toml) se busca en la raíz del repo,
y nosotros trabajamos solo dentro de app/.
"""
from __future__ import annotations

import html

import streamlit as st

PRIMARIO = "#4f46e5"        # índigo: acento de botones, selección y slider
PRIMARIO_OSCURO = "#3730a3"
TINTA = "#0f172a"           # texto principal
TINTA_SUAVE = "#64748b"     # texto secundario
BORDE = "#e2e8f0"
FONDO = "#f8fafc"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp, button, input, textarea, select {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
}}
.stApp {{ background: {FONDO}; color: {TINTA}; }}
.block-container {{ max-width: 1180px; padding-top: 2.2rem; padding-bottom: 4rem; }}

/* barra superior de Streamlit: sin el botón Deploy */
[data-testid="stAppDeployButton"], .stDeployButton {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent; }}

/* ---------- encabezado de cada pantalla ---------- */
.enc {{ margin: 0 0 1.4rem 0; }}
.enc .ojo {{ font-size: 12px; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; color: {PRIMARIO}; }}
.enc h1 {{ font-size: 2.1rem; font-weight: 700; margin: .15rem 0 .3rem 0; padding: 0; color: {TINTA}; letter-spacing: -.02em; }}
.enc p {{ color: {TINTA_SUAVE}; font-size: 1rem; margin: 0; max-width: 46rem; }}

/* títulos de sección */
.stApp h2, .stApp h3 {{ color: {TINTA}; font-weight: 650; letter-spacing: -.01em; }}
[data-testid="stHeadingWithActionElements"] h3 {{ font-size: 1.25rem; margin-top: .4rem; }}

/* ---------- barra lateral ---------- */
[data-testid="stSidebar"] {{ background: #ffffff; border-right: 1px solid {BORDE}; }}
[data-testid="stSidebar"] .marca {{ display: flex; align-items: center; gap: .6rem; margin: .4rem 0 1.4rem 0; }}
[data-testid="stSidebar"] .marca .logo {{ width: 38px; height: 38px; border-radius: 10px; display: grid; place-items: center;
    background: linear-gradient(135deg, {PRIMARIO}, #7c3aed); color: #fff; font-weight: 700; font-size: 18px; }}
[data-testid="stSidebar"] .marca .t1 {{ font-weight: 700; font-size: 1rem; line-height: 1.1; color: {TINTA}; }}
[data-testid="stSidebar"] .marca .t2 {{ font-size: .78rem; color: {TINTA_SUAVE}; }}

/* el selector de pantalla como menú de "pastillas" */
[data-testid="stSidebar"] [role="radiogroup"] {{ gap: .25rem; }}
[data-testid="stSidebar"] [role="radiogroup"] label {{
    padding: .55rem .8rem; border-radius: 10px; width: 100%; cursor: pointer; transition: background .15s;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background: #eef2ff; }}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background: #eef2ff; }}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{ color: {PRIMARIO_OSCURO}; font-weight: 600; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {{ display: none; }}  /* oculta el circulito */

/* ---------- tarjetas de métricas ---------- */
[data-testid="stMetric"] {{
    background: #fff; border: 1px solid {BORDE}; border-radius: 14px; padding: 1rem 1.2rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
}}
[data-testid="stMetricLabel"] p {{ color: {TINTA_SUAVE}; font-size: .85rem; font-weight: 500; white-space: normal; overflow: visible; text-overflow: clip; }}
[data-testid="stMetricLabel"] {{ overflow: visible; }}
[data-testid="stMetricValue"] {{ font-weight: 700; letter-spacing: -.02em; color: {TINTA}; }}

/* ---------- formularios, tablas, avisos ---------- */
[data-testid="stForm"] {{
    background: #fff; border: 1px solid {BORDE}; border-radius: 16px; padding: 1.4rem 1.4rem 1rem 1.4rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, .05);
}}
[data-testid="stTable"] table, [data-testid="stDataFrame"] {{ border-radius: 12px; }}
[data-testid="stDataFrame"] {{ border: 1px solid {BORDE}; overflow: hidden; }}
[data-testid="stAlert"] {{ border-radius: 12px; }}
[data-testid="stExpander"] {{ background: #fff; border: 1px solid {BORDE}; border-radius: 12px; margin-top: 1rem; }}
[data-testid="stFileUploaderDropzone"] {{ background: #fff; border: 1.5px dashed #c7d2fe; border-radius: 14px; }}
hr {{ border-color: {BORDE}; margin: 2rem 0; }}
[data-testid="stCaptionContainer"] {{ color: {TINTA_SUAVE}; }}

/* ---------- botones ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {{
    border-radius: 10px; font-weight: 600; padding: .55rem 1.1rem; border: 1px solid {BORDE}; background: #fff; color: {TINTA};
    transition: all .15s;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color: {PRIMARIO}; color: {PRIMARIO}; }}
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"],
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {{
    background: linear-gradient(135deg, {PRIMARIO}, {PRIMARIO_OSCURO}); color: #fff; border: none;
    box-shadow: 0 2px 6px rgba(79, 70, 229, .3);
}}
button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover {{
    color: #fff; filter: brightness(1.08);
}}

/* ---------- controles con color de acento ---------- */
[data-baseweb="slider"] div[role="slider"] {{ background: {PRIMARIO} !important; box-shadow: 0 0 0 4px rgba(79,70,229,.18); }}
[data-baseweb="slider"] > div > div > div:first-child {{ background: linear-gradient(90deg, {PRIMARIO}, #818cf8) !important; }}
[data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"] {{ background: {PRIMARIO} !important; border-color: {PRIMARIO} !important; }}
[data-baseweb="checkbox"] input:checked + div {{ background: {PRIMARIO} !important; }}

/* ---------- tarjeta de resultado ---------- */
.res {{ border-radius: 18px; padding: 1.3rem 1.5rem; background: #fff; border: 1px solid {BORDE};
        box-shadow: 0 4px 14px rgba(15, 23, 42, .06); }}
.res .pastilla {{ display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
        padding: .25rem .7rem; border-radius: 999px; }}
.res .prob {{ font-size: 3.2rem; font-weight: 700; line-height: 1.1; letter-spacing: -.03em; margin: .5rem 0 .1rem 0; }}
.res .cap {{ color: {TINTA_SUAVE}; font-size: .85rem; }}
.res .accion {{ margin-top: .9rem; padding-top: .8rem; border-top: 1px solid {BORDE}; font-size: .95rem; color: {TINTA}; }}
.res .barra {{ position: relative; height: 8px; border-radius: 999px; background: #e2e8f0; margin-top: 1rem; }}
.res .barra > span {{ position: absolute; left: 0; top: 0; bottom: 0; border-radius: 999px; }}
.res .barra > i {{ position: absolute; top: -4px; bottom: -4px; width: 2px; background: {TINTA}; }}
.res .leyenda {{ display: flex; justify-content: space-between; font-size: .75rem; color: {TINTA_SUAVE}; margin-top: .35rem; }}

/* ---------- pantallas angostas (celular) ---------- */
@media (max-width: 640px) {{
    .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
    .enc h1 {{ font-size: 1.6rem; }}
    .res .prob {{ font-size: 2.6rem; }}
}}
</style>
"""


def aplicar() -> None:
    """Llamar una sola vez, al principio de la app."""
    try:   # color principal de Streamlit (interruptor, selección, etc.); si esta versión no lo permite, se ignora
        for clave, valor in (("theme.primaryColor", PRIMARIO), ("theme.base", "light")):
            st._config.set_option(clave, valor)
    except Exception:
        pass
    st.markdown(CSS, unsafe_allow_html=True)


def encabezado(ojo: str, titulo: str, subtitulo: str) -> None:
    st.markdown(
        f'<div class="enc"><div class="ojo">{html.escape(ojo)}</div><h1>{html.escape(titulo)}</h1>'
        f"<p>{html.escape(subtitulo)}</p></div>",
        unsafe_allow_html=True,
    )


def marca_lateral() -> None:
    st.sidebar.markdown(
        '<div class="marca"><div class="logo">C</div><div><div class="t1">Cashea</div>'
        '<div class="t2">Riesgo de primer pago (FPD)</div></div></div>',
        unsafe_allow_html=True,
    )
