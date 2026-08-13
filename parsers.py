"""
Lectura flexible de archivos reales (exportaciones SAP u otro origen) hacia el
esquema exacto que espera app.py.

Si el archivo subido ya viene con las columnas exactas (fecha_documento, monto,
moneda, glosa, centro_costo, referencia, cuenta_contable / cuenta_contable,
saldo_f01_esperado — como los datos ficticios), no se toca nada: pasa intacto.
Solo entra en juego cuando el archivo trae nombres de columna distintos
(exportacion SAP real: "Cuenta de mayor", "Importe en moneda local", etc.),
encoding distinto a UTF-8, o filas de metadata antes del encabezado real.

No inventa ni completa datos: si una columna requerida no se puede mapear,
simplemente no aparece en el resultado — la validacion existente en app.py
(`validar_columnas`) es la que avisa que falta, tal como avisaria con
cualquier otro archivo incompleto.
"""
import io

import numpy as np
import pandas as pd

COLUMNAS_MOVIMIENTOS = [
    "fecha_documento", "monto", "moneda", "glosa",
    "centro_costo", "referencia", "cuenta_contable",
]
COLUMNAS_SALDOS_F01 = ["cuenta_contable", "saldo_f01_esperado"]

# Palabras que delatan la fila de encabezado real en un export SAP con
# metadata (nombre de empresa, RUT, periodo) antes de la tabla de datos.
_PALABRAS_HEADER = ("cuenta", "fecha", "monto", "importe", "debe", "haber", "saldo")

_ENCODINGS = ("utf-8", "latin-1", "cp1252")


def _limpiar_numero_sap(val):
    """Convierte numeros con formato SAP/es-CL (punto miles, coma decimal:
    '6.793.771,71') a float. Si ya es numerico, lo deja igual."""
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float, np.integer, np.floating)):
        return float(val)
    texto = str(val).strip().replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return np.nan


def _detectar_fila_header(lineas_o_filas, separador=None):
    """Busca, entre las primeras filas, la que parece el encabezado real de
    una tabla (varias columnas no vacias, alguna con palabra clave de
    columna esperada). Devuelve el indice, o 0 si no encuentra ninguna
    (asume que no hay metadata y la fila 0 ya es el encabezado)."""
    for i, fila in enumerate(lineas_o_filas[:15]):
        if separador is not None:
            celdas = [c.strip().lower() for c in fila.split(separador)]
        else:
            celdas = [str(v).strip().lower() for v in fila if pd.notna(v)]
        celdas_con_texto = [c for c in celdas if c]
        if len(celdas_con_texto) >= 3 and any(
            any(p in c for p in _PALABRAS_HEADER) for c in celdas_con_texto
        ):
            return i
    return 0


def _leer_csv_flexible(contenido: bytes) -> pd.DataFrame:
    """Lee un CSV probando encoding y separador, saltando metadata si hace
    falta. Los datos ficticios del proyecto (coma, sin metadata) se leen
    igual que siempre: la deteccion encuentra el encabezado en la fila 0."""
    ultimo_error = None
    for encoding in _ENCODINGS:
        try:
            texto = contenido.decode(encoding)
        except UnicodeDecodeError as exc:
            ultimo_error = exc
            continue

        primera_linea = next((l for l in texto.split("\n") if l.strip()), "")
        separador = ";" if primera_linea.count(";") > primera_linea.count(",") else ","

        lineas = texto.split("\n")
        fila_header = _detectar_fila_header(lineas, separador=separador)

        return pd.read_csv(io.StringIO(texto), sep=separador, skiprows=fila_header)

    raise ValueError(
        f"No se pudo leer el CSV con ninguno de los encodings probados "
        f"({', '.join(_ENCODINGS)}): {ultimo_error}"
    )


def _leer_xlsx_flexible(archivo) -> pd.DataFrame:
    """Lee un XLSX saltando metadata (nombre de sociedad, cuenta, ledger)
    si la hoja trae esas filas antes del encabezado real, como en las
    exportaciones FBL3N de SAP."""
    xl = pd.ExcelFile(archivo)
    hoja = "Data" if "Data" in xl.sheet_names else xl.sheet_names[0]

    filas_muestra = pd.read_excel(archivo, sheet_name=hoja, header=None, nrows=15)
    fila_header = _detectar_fila_header(
        [filas_muestra.iloc[i].tolist() for i in range(len(filas_muestra))]
    )

    return pd.read_excel(archivo, sheet_name=hoja, skiprows=fila_header)


def leer_archivo_flexible(archivo) -> pd.DataFrame:
    """Punto de entrada: recibe el UploadedFile de Streamlit (o cualquier
    objeto con .name y .getvalue()) y devuelve el DataFrame crudo, listo
    para normalizar_movimientos() o normalizar_saldos_f01()."""
    nombre = archivo.name.lower()
    contenido = archivo.getvalue()
    if nombre.endswith(".csv"):
        return _leer_csv_flexible(contenido)
    return _leer_xlsx_flexible(io.BytesIO(contenido))


def _aplicar_mapa(df: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    """Renombra columnas segun el mapa {nombre_estandar: [sinonimos]},
    por coincidencia exacta primero y luego por prefijo. Cada columna
    origen se usa a lo sumo una vez; cada columna destino tambien."""
    cambios = {}
    usados = set()
    for col_actual in df.columns:
        actual_lower = str(col_actual).strip().lower()
        for destino, sinonimos in mapa.items():
            if destino in usados:
                continue
            if actual_lower in sinonimos or any(actual_lower.startswith(s) for s in sinonimos):
                cambios[col_actual] = destino
                usados.add(destino)
                break
    return df.rename(columns=cambios)


def normalizar_movimientos(df: pd.DataFrame) -> pd.DataFrame:
    """Mapea un export de movimientos (SAP u otro) al esquema exacto que
    usa app.py. Si el archivo ya trae las columnas requeridas (datos
    ficticios, u otro sistema ya compatible), lo devuelve intacto."""
    if all(c in df.columns for c in COLUMNAS_MOVIMIENTOS):
        return df

    mapa = {
        "fecha_documento": ["fecha de documento", "fecha_documento", "fecha contabiliz"],
        "monto": ["importe en moneda local", "importe", "monto"],
        "moneda": ["moneda local", "moneda del documento", "moneda"],
        "glosa": ["texto cab.documento", "texto", "glosa"],
        "centro_costo": ["centro de coste", "centro de beneficio", "centro_costo"],
        "referencia": ["n° documento", "n documento", "referencia"],
        "cuenta_contable": ["cuenta", "cuenta_contable"],
    }
    df = _aplicar_mapa(df, mapa)

    if "monto" in df.columns:
        df["monto"] = df["monto"].apply(_limpiar_numero_sap)
    if "cuenta_contable" in df.columns:
        df["cuenta_contable"] = pd.to_numeric(df["cuenta_contable"], errors="coerce")

    # Algunos exports SAP traen la columna "Referencia" vacia y el
    # identificador real del documento en "N° documento" -- ese simbolo
    # de grado a veces llega corrupto por el encoding del archivo original,
    # asi que no matchea el mapa de arriba. Si referencia quedo vacia del
    # todo, se usa esa columna como respaldo (afecta la deteccion de
    # duplicidades, que agrupa por referencia+monto+cuenta).
    if "referencia" in df.columns and df["referencia"].isna().all():
        candidata = next(
            (
                c for c in df.columns
                if c != "referencia"
                and str(c).strip().lower().startswith("n")
                and "documento" in str(c).strip().lower()
            ),
            None,
        )
        if candidata is not None:
            df["referencia"] = df[candidata]

    return df


def normalizar_saldos_f01(df: pd.DataFrame) -> pd.DataFrame:
    """Mapea un balance F.01 (SAP: Cuenta de mayor / Saldo Debe / Saldo
    Haber) al esquema {cuenta_contable, saldo_f01_esperado} que usa
    app.py. El saldo esperado se calcula como Saldo Debe - Saldo Haber
    (convencion: positivo = neto deudor), igual que 'monto' en
    movimientos para una cuenta deudora. Si el archivo ya trae
    saldo_f01_esperado directamente, lo deja igual."""
    if {"cuenta_contable", "saldo_f01_esperado"}.issubset(df.columns):
        return df

    df = _aplicar_mapa(df, {"cuenta_contable": ["cuenta de mayor", "cuenta", "cuenta_contable"]})

    col_debe = next(
        (c for c in df.columns if str(c).strip().lower().startswith("saldo debe")), None
    )
    col_haber = next(
        (c for c in df.columns if str(c).strip().lower().startswith("saldo haber")), None
    )
    if col_debe is not None and col_haber is not None:
        debe = df[col_debe].apply(_limpiar_numero_sap)
        haber = df[col_haber].apply(_limpiar_numero_sap)
        df["saldo_f01_esperado"] = debe - haber

    if "cuenta_contable" in df.columns:
        df["cuenta_contable"] = pd.to_numeric(df["cuenta_contable"], errors="coerce")

    return df
