"""
Lectura y validación del CSV del "Lote" (sin Streamlit, para poder probarlo solo).
Devuelve las solicitudes en el formato del contrato de la API.
"""
from __future__ import annotations

import io

import pandas as pd

from cliente import ErrorDeUsuario

CAMPOS = ["solicitud_id", "fecha_origen", "gmv", "anticipo", "producto", "score",
          "tipo_orden", "ordenes_previas", "comercio_id", "vertical"]
OBLIGATORIAS = [c for c in CAMPOS if c != "score"]   # score puede venir vacío
MAX_FILAS_LOTE = 5000        # tope para que la demo no se cuelgue; cambiar si hace falta


def _entero(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def _filas(mascara: pd.Series) -> str:
    n = [str(i + 1) for i in mascara[mascara].index[:10]]
    extra = "…" if mascara.sum() > 10 else ""
    return "fila(s) " + ", ".join(n) + extra + " (contando desde 1, sin el encabezado)"


def _leer_csv(archivo) -> pd.DataFrame:
    """Lee el CSV aunque venga de Excel: con o sin BOM (UTF-8) o en Windows-1252, con coma o punto y coma."""
    crudo = archivo.getvalue() if hasattr(archivo, "getvalue") else archivo.read()
    for codificacion in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = crudo.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.StringIO(texto), sep=None, engine="python", dtype=str)


def preparar_lote(archivo) -> tuple[pd.DataFrame, list[dict]]:
    try:
        df = _leer_csv(archivo)
    except Exception:
        raise ErrorDeUsuario("No pude leer el archivo. Tiene que ser un CSV con una fila por solicitud y encabezados.") from None
    df.columns = [str(c).strip() for c in df.columns]
    if df.empty:
        raise ErrorDeUsuario("El archivo no tiene filas.")
    if len(df) > MAX_FILAS_LOTE:
        raise ErrorDeUsuario(f"El archivo tiene {_entero(len(df))} filas y el máximo para esta demo es {_entero(MAX_FILAS_LOTE)}.")
    faltan = [c for c in OBLIGATORIAS if c not in df.columns]
    if faltan:
        raise ErrorDeUsuario("Al archivo le faltan estas columnas: " + ", ".join(faltan) +
                             ". Las columnas esperadas son: " + ", ".join(CAMPOS) + " (score puede ir vacío).")

    for c in df.columns:
        df[c] = df[c].str.strip()
    vacias = df[OBLIGATORIAS].isna() | (df[OBLIGATORIAS] == "")
    if vacias.any().any():
        col = vacias.any()[vacias.any()].index[0]
        raise ErrorDeUsuario(f"Hay celdas vacías en la columna «{col}»: {_filas(vacias[col])}.")

    fecha = pd.to_datetime(df["fecha_origen"], format="%Y-%m-%d", errors="coerce")
    if fecha.isna().any():
        raise ErrorDeUsuario(f"Fecha inválida en {_filas(fecha.isna())}. El formato tiene que ser AAAA-MM-DD.")
    out = pd.DataFrame({"solicitud_id": df["solicitud_id"], "fecha_origen": fecha.dt.strftime("%Y-%m-%d")})
    for c in ("gmv", "anticipo"):
        x = pd.to_numeric(df[c], errors="coerce")
        if x.isna().any():
            raise ErrorDeUsuario(f"La columna «{c}» tiene valores que no son números en {_filas(x.isna())}. "
                                 "Usá punto como separador decimal (85.5).")
        out[c] = x.astype(float)
    op = pd.to_numeric(df["ordenes_previas"], errors="coerce")
    if op.isna().any() or (op % 1 != 0).any():
        raise ErrorDeUsuario(f"«ordenes_previas» tiene que ser un número entero. Revisá {_filas(op.isna() | (op % 1 != 0))}.")
    out["ordenes_previas"] = op.astype(int)
    for c in ("producto", "tipo_orden", "comercio_id", "vertical"):
        out[c] = df[c]
    if "score" in df.columns:
        sc = pd.to_numeric(df["score"], errors="coerce")
        malos = sc.isna() & df["score"].notna() & (df["score"] != "")
        if malos.any():
            raise ErrorDeUsuario(f"«score» tiene valores que no son números en {_filas(malos)}. Dejalo vacío si no hay score.")
        out["score"] = sc
    else:
        out["score"] = float("nan")

    payload = out[CAMPOS].astype(object).where(out[CAMPOS].notna(), None).to_dict(orient="records")
    return out, payload
