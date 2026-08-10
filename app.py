"""
Tablero de Analisis Inteligente de Cuentas (piloto).

Carga un archivo de movimientos contables, detecta anomalias con reglas fijas
(no IA), muestra un semaforo por cuenta y permite exportar el resultado a Excel.

Reglas del piloto:
- No se inventan ni suponen datos: todo comentario sale de lo que hay en el archivo.
- Si faltan datos clave en una fila, se avisa y esa fila se excluye del analisis.
"""
import io
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

CARPETA_DATOS = Path(__file__).parent / "datos"
COLUMNAS_REQUERIDAS = [
    "fecha_documento", "monto", "moneda", "glosa",
    "centro_costo", "referencia", "cuenta_contable",
]
DIAS_ANTIGUEDAD = 90

# primer digito de la cuenta -> naturaleza esperada
NATURALEZA_POR_PREFIJO = {
    "1": "deudora", "5": "deudora",
    "2": "acreedora", "3": "acreedora", "4": "acreedora",
}

st.set_page_config(page_title="Analisis Inteligente de Cuentas", layout="wide")


# ---------- Carga y validacion ----------

def cargar_archivo(archivo):
    if archivo is None:
        return None
    nombre = archivo.name.lower()
    if nombre.endswith(".csv"):
        return pd.read_csv(archivo)
    return pd.read_excel(archivo)


def validar_columnas(df):
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    return faltantes


def separar_filas_incompletas(df):
    claves = ["monto", "fecha_documento", "cuenta_contable"]
    incompletas_mask = df[claves].isna().any(axis=1)
    return df[~incompletas_mask].copy(), df[incompletas_mask].copy()


# ---------- Deteccion de anomalias ----------

def detectar_duplicidades(df):
    grupo = df.groupby(["referencia", "monto", "cuenta_contable"])["referencia"].transform("count")
    return grupo > 1


def naturaleza_esperada(cuenta_contable):
    prefijo = str(cuenta_contable)[0]
    return NATURALEZA_POR_PREFIJO.get(prefijo, "desconocida")


UMBRAL_DUPLICADOS_AMARILLO = 0.02
UMBRAL_DUPLICADOS_ROJO = 0.03
UMBRAL_ANTIGUEDAD = 0.20
UMBRAL_CUADRATURA_MODERADO = 500
UMBRAL_CUADRATURA_GRAVE = 50_000


def construir_resumen(df, saldos_f01):
    df = df.copy()
    # errors="coerce": si llega una fecha invalida hasta aca (no deberia, el
    # flujo normal ya la filtro antes), no revienta la app, queda como NaT.
    df["fecha_documento"] = pd.to_datetime(df["fecha_documento"], errors="coerce")
    df["es_duplicado"] = detectar_duplicidades(df)
    df["dias_antiguedad"] = (pd.Timestamp(date.today()) - df["fecha_documento"]).dt.days
    df["es_antigua"] = df["dias_antiguedad"] > DIAS_ANTIGUEDAD

    filas_resumen = []
    for cuenta, grupo in df.groupby("cuenta_contable"):
        naturaleza = naturaleza_esperada(cuenta)
        saldo_neto = grupo["monto"].sum()

        saldo_contrario = False
        if naturaleza == "deudora":
            saldo_contrario = saldo_neto < 0
        elif naturaleza == "acreedora":
            saldo_contrario = saldo_neto > 0

        n_filas = len(grupo)
        n_duplicados = int(grupo["es_duplicado"].sum())
        n_antiguas = int(grupo["es_antigua"].sum())
        tasa_duplicados = n_duplicados / n_filas
        tasa_antiguas = n_antiguas / n_filas

        diferencia_cuadratura = None
        if saldos_f01 is not None:
            fila_f01 = saldos_f01[saldos_f01["cuenta_contable"] == cuenta]
            if not fila_f01.empty:
                esperado = fila_f01["saldo_f01_esperado"].iloc[0]
                diferencia_cuadratura = round(saldo_neto - esperado, 2)

        # El comentario solo reporta lo que cruza el mismo umbral que define el
        # semaforo: unos pocos duplicados o partidas antiguas sueltas son ruido
        # normal, no una observacion real. Cada linea nombra el umbral exacto
        # que se cruzo, para que el comentario sea auditable, no una caja negra.
        comentarios = []
        if tasa_duplicados > UMBRAL_DUPLICADOS_AMARILLO:
            comentarios.append(
                f"{n_duplicados} filas duplicadas (mismo documento, monto y cuenta) — "
                f"tasa {tasa_duplicados:.1%} > umbral {UMBRAL_DUPLICADOS_AMARILLO:.0%}."
            )
        if saldo_contrario:
            comentarios.append(
                f"Saldo contrario a su naturaleza ({naturaleza}): saldo neto {saldo_neto:,.0f}."
            )
        if tasa_antiguas > UMBRAL_ANTIGUEDAD:
            comentarios.append(
                f"{n_antiguas} partidas con antiguedad mayor a {DIAS_ANTIGUEDAD} dias — "
                f"tasa {tasa_antiguas:.1%} > umbral {UMBRAL_ANTIGUEDAD:.0%}."
            )
        if diferencia_cuadratura is not None and abs(diferencia_cuadratura) > UMBRAL_CUADRATURA_MODERADO:
            comentarios.append(
                f"Diferencia de {diferencia_cuadratura:,.0f} vs saldo esperado (F.01) — "
                f"umbral {UMBRAL_CUADRATURA_MODERADO:,.0f}."
            )
        if not comentarios:
            comentarios.append("Sin observaciones.")

        # Semaforo (umbrales sobre tasa, no conteo absoluto, para no castigar
        # por igual a cuentas con mucho o poco volumen de movimientos)
        descuadre_grave = diferencia_cuadratura is not None and abs(diferencia_cuadratura) > UMBRAL_CUADRATURA_GRAVE
        descuadre_moderado = diferencia_cuadratura is not None and abs(diferencia_cuadratura) > UMBRAL_CUADRATURA_MODERADO
        if saldo_contrario or descuadre_grave:
            semaforo = "Negro"
        elif descuadre_moderado or tasa_duplicados > UMBRAL_DUPLICADOS_ROJO:
            semaforo = "Rojo"
        elif tasa_antiguas > UMBRAL_ANTIGUEDAD or tasa_duplicados > UMBRAL_DUPLICADOS_AMARILLO:
            semaforo = "Amarillo"
        else:
            semaforo = "Verde"

        filas_resumen.append({
            "cuenta_contable": cuenta,
            "naturaleza_esperada": naturaleza,
            "saldo_neto": round(saldo_neto, 2),
            "duplicidades": n_duplicados,
            "saldo_contrario": saldo_contrario,
            "partidas_antiguas": n_antiguas,
            "diferencia_cuadratura": diferencia_cuadratura,
            "semaforo": semaforo,
            "comentario": " ".join(comentarios),
        })

    resumen = pd.DataFrame(filas_resumen).sort_values(
        by="semaforo", key=lambda s: s.map({"Negro": 0, "Rojo": 1, "Amarillo": 2, "Verde": 3})
    )
    return df, resumen


COLOR_SEMAFORO = {"Verde": "#d4edda", "Amarillo": "#fff3cd", "Rojo": "#f8d7da", "Negro": "#343a40"}


def pintar_semaforo(val):
    color = COLOR_SEMAFORO.get(val, "")
    texto = "white" if val == "Negro" else "black"
    return f"background-color: {color}; color: {texto}"


def exportar_excel(resumen, detalle, incompletas):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        resumen.to_excel(writer, sheet_name="Resumen", index=False)
        detalle.to_excel(writer, sheet_name="Detalle", index=False)
        if not incompletas.empty:
            incompletas.to_excel(writer, sheet_name="Datos_faltantes", index=False)
    buffer.seek(0)
    return buffer


# ---------- UI ----------

def render_tablero():
    with st.sidebar:
        st.header("Datos de entrada")
        usar_demo = st.checkbox("Usar datos ficticios de ejemplo", value=True)
        archivo_movs = st.file_uploader("Movimientos (Excel o CSV)", type=["xlsx", "csv"])
        archivo_f01 = st.file_uploader("Saldos F.01 esperados (opcional, CSV)", type=["csv"])

    if usar_demo and archivo_movs is None:
        ruta_demo = CARPETA_DATOS / "movimientos.xlsx"
        if not ruta_demo.exists():
            st.error(
                "No encontre datos de ejemplo. Corre primero `python generar_datos.py` "
                "en esta carpeta."
            )
            st.stop()
        df_original = pd.read_excel(ruta_demo)
        saldos_f01 = pd.read_csv(CARPETA_DATOS / "saldos_f01.csv")
    elif archivo_movs is not None:
        df_original = cargar_archivo(archivo_movs)
        saldos_f01 = cargar_archivo(archivo_f01) if archivo_f01 is not None else None
        if saldos_f01 is None:
            st.info(
                "No subiste saldos F.01: la validacion de diferencias de cuadratura "
                "quedara deshabilitada para este archivo."
            )
    else:
        st.info("Sube un archivo o activa los datos de ejemplo para comenzar.")
        st.stop()

    faltantes_cols = validar_columnas(df_original)
    if faltantes_cols:
        st.error(f"Al archivo le faltan columnas obligatorias: {faltantes_cols}. No se puede continuar.")
        st.stop()

    # Una fecha mal escrita (no vacia, pero invalida) se trata igual que un
    # dato faltante: se marca como dudosa, no se deja reventar el analisis.
    fechas_antes = df_original["fecha_documento"].isna().sum()
    df_original["fecha_documento"] = pd.to_datetime(df_original["fecha_documento"], errors="coerce")
    n_fechas_invalidas = int(df_original["fecha_documento"].isna().sum() - fechas_antes)

    df_validas, df_incompletas = separar_filas_incompletas(df_original)

    if not df_incompletas.empty:
        st.warning(
            f"{len(df_incompletas)} filas tienen datos faltantes o dudosos en columnas clave "
            f"(monto, fecha_documento o cuenta_contable) y se excluyeron del analisis. "
            + (f"De esas, {n_fechas_invalidas} tenian una fecha invalida (no vacia, mal escrita). "
               if n_fechas_invalidas else "")
            + "Quedan disponibles en la pestana 'Datos_faltantes' del Excel exportado."
        )

    detalle, resumen = construir_resumen(df_validas, saldos_f01)

    # --- Resumen ejecutivo ---
    st.subheader("Resumen ejecutivo")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Cuentas evaluadas", len(resumen))
    c2.metric("Cuentas Rojo/Negro", int(resumen["semaforo"].isin(["Rojo", "Negro"]).sum()))
    c3.metric("Duplicidades totales", int(resumen["duplicidades"].sum()))
    c4.metric("Partidas antiguas", int(resumen["partidas_antiguas"].sum()))
    c5.metric("Filas con datos faltantes", len(df_incompletas))

    # --- Tabla resumen por cuenta ---
    st.subheader("Semaforo por cuenta")
    st.dataframe(
        resumen.style.map(pintar_semaforo, subset=["semaforo"]),
        use_container_width=True,
        hide_index=True,
    )

    # --- Detalle de filas flagged ---
    with st.expander("Ver detalle de filas con anomalias (duplicadas o antiguas)"):
        detalle_anomalo = detalle[detalle["es_duplicado"] | detalle["es_antigua"]]
        st.dataframe(detalle_anomalo, use_container_width=True, hide_index=True)

    # --- Export ---
    st.subheader("Exportar")
    excel_bytes = exportar_excel(resumen, detalle, df_incompletas)
    st.download_button(
        "Descargar Excel con resultados",
        data=excel_bytes,
        file_name="analisis_cuentas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def render_acerca():
    ruta_prd = Path(__file__).parent / "prd-v2.md"
    if not ruta_prd.exists():
        st.warning("No se encontro prd-v2.md en el proyecto.")
        return
    st.markdown(ruta_prd.read_text(encoding="utf-8"))


st.title("Analisis Inteligente de Cuentas — Piloto")
st.caption(
    "Detecta duplicidades, saldos contrarios, partidas antiguas y diferencias de "
    "cuadratura. Los comentarios se generan con reglas fijas (sin IA): no se inventa nada."
)

tab_tablero, tab_acerca = st.tabs(["Tablero", "Acerca de / Gobernanza"])

with tab_tablero:
    render_tablero()

with tab_acerca:
    render_acerca()
