"""
Tablero de Analisis Inteligente de Cuentas (piloto).

Carga un archivo de movimientos contables, detecta anomalias con reglas fijas
(no IA), muestra un semaforo por cuenta y permite exportar el resultado a Excel.

Reglas del piloto:
- No se inventan ni suponen datos: todo comentario sale de lo que hay en el archivo.
- Si faltan datos clave en una fila, se avisa y esa fila se excluye del analisis.
"""
import io
import sys
import traceback
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from error_handler import registrar_error

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


# ---------- Acceso ----------

def verificar_acceso():
    """Clave interina (mitigacion #3 del debrief): si no hay clave configurada
    en st.secrets (ej. desarrollo local), no bloquea. En Streamlit Cloud, se
    configura APP_PASSWORD en Settings > Secrets para restringir el acceso."""
    try:
        clave_configurada = st.secrets["APP_PASSWORD"]
    except Exception:
        clave_configurada = None

    if not clave_configurada:
        return True
    if st.session_state.get("acceso_autorizado"):
        return True

    st.title("Analisis Inteligente de Cuentas")
    st.write("Acceso restringido — uso exclusivo de analistas contables autorizados.")
    clave = st.text_input("Clave de acceso", type="password")
    if clave:
        if clave == clave_configurada:
            st.session_state["acceso_autorizado"] = True
            st.rerun()
        else:
            st.error("Clave incorrecta.")
    return False


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
# Con menos filas que esto, un porcentaje (ej. "40% duplicado") es ruido
# estadistico, no una senal real -- se avisa aparte, no se omite.
UMBRAL_MUESTRA_CHICA = 10


def construir_resumen(df, saldos_f01, naturaleza_overrides=None):
    """naturaleza_overrides: dict opcional {cuenta_contable: {"naturaleza": str,
    "confirmada": bool}}. Si una cuenta no viene en el dict (o no se pasa nada),
    se usa el supuesto por prefijo (naturaleza_esperada) y queda marcada como
    no confirmada -- asi el analista sabe cuando "saldo_contrario" se apoya en
    un supuesto y cuando en un dato verificado del plan de cuentas real."""
    naturaleza_overrides = naturaleza_overrides or {}
    df = df.copy()
    # errors="coerce": si llega una fecha invalida hasta aca (no deberia, el
    # flujo normal ya la filtro antes), no revienta la app, queda como NaT.
    df["fecha_documento"] = pd.to_datetime(df["fecha_documento"], errors="coerce")
    df["es_duplicado"] = detectar_duplicidades(df)
    df["dias_antiguedad"] = (pd.Timestamp(date.today()) - df["fecha_documento"]).dt.days
    df["es_antigua"] = df["dias_antiguedad"] > DIAS_ANTIGUEDAD

    filas_resumen = []
    for cuenta, grupo in df.groupby("cuenta_contable"):
        override = naturaleza_overrides.get(cuenta)
        if override and override.get("naturaleza") in ("deudora", "acreedora"):
            naturaleza = override["naturaleza"]
            naturaleza_confirmada = bool(override.get("confirmada"))
        else:
            naturaleza = naturaleza_esperada(cuenta)
            naturaleza_confirmada = False
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
            if not naturaleza_confirmada:
                comentarios.append(
                    "Naturaleza asumida por el prefijo de cuenta (no confirmada): "
                    "verificar el plan de cuentas real antes de tomar esto como definitivo."
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
            "naturaleza_confirmada": naturaleza_confirmada,
            "saldo_neto": round(saldo_neto, 2),
            "duplicidades": n_duplicados,
            "saldo_contrario": saldo_contrario,
            "partidas_antiguas": n_antiguas,
            "diferencia_cuadratura": diferencia_cuadratura,
            "semaforo": semaforo,
            "comentario": " ".join(comentarios),
            "n_filas": n_filas,
            "tasa_duplicados": round(tasa_duplicados, 4),
            "tasa_antiguas": round(tasa_antiguas, 4),
        })

    resumen = pd.DataFrame(filas_resumen)

    # Aviso de confiabilidad: el semaforo no debe verse igual de "seguro" en
    # una cuenta con pocos movimientos (% poco confiable) o con un patron muy
    # fuera de lo comun frente al resto del archivo -- se marca aparte, sin
    # tocar el color del semaforo (que sigue siendo 100% por umbral fijo).
    resumen["muestra_chica"] = resumen["n_filas"] < UMBRAL_MUESTRA_CHICA
    resumen["atipico_vs_otras_cuentas"] = False
    if len(resumen) >= 4:
        for col in ["tasa_duplicados", "tasa_antiguas"]:
            q1, q3 = resumen[col].quantile([0.25, 0.75])
            iqr = q3 - q1
            if iqr > 0:
                resumen["atipico_vs_otras_cuentas"] |= resumen[col] > (q3 + 1.5 * iqr)

    def _aviso(row):
        notas = []
        if row["muestra_chica"]:
            notas.append(
                f"Muestra chica (n={row['n_filas']}): los porcentajes pueden no ser "
                "confiables, revisar igual aunque no cruce ningun umbral."
            )
        if row["atipico_vs_otras_cuentas"]:
            notas.append(
                "Patron fuera de lo comun frente a las demas cuentas de este archivo: "
                "revisar con cuidado extra."
            )
        return " ".join(notas)

    resumen["aviso_confiabilidad"] = resumen.apply(_aviso, axis=1)
    resumen["comentario"] = resumen["comentario"] + resumen["aviso_confiabilidad"].apply(
        lambda t: f" ⚠ {t}" if t else ""
    )

    resumen = resumen.sort_values(
        by="semaforo", key=lambda s: s.map({"Negro": 0, "Rojo": 1, "Amarillo": 2, "Verde": 3})
    )
    return df, resumen


COLOR_SEMAFORO = {"Verde": "#d4edda", "Amarillo": "#fff3cd", "Rojo": "#f8d7da", "Negro": "#343a40"}

# Columnas que se muestran en pantalla (las de detalle estadistico -- n_filas,
# tasas, flags crudos -- quedan solo en el Excel exportado para no saturar la
# vista rapida; el comentario ya narra lo relevante de esas columnas).
COLUMNAS_RESUMEN_UI = [
    "cuenta_contable", "naturaleza_esperada", "naturaleza_confirmada", "saldo_neto",
    "duplicidades", "saldo_contrario", "partidas_antiguas", "diferencia_cuadratura",
    "semaforo", "comentario",
]


def pintar_semaforo(val):
    color = COLOR_SEMAFORO.get(val, "")
    texto = "white" if val == "Negro" else "black"
    return f"background-color: {color}; color: {texto}"


def identificar_compensaciones(detalle):
    """Empareja, dentro de cada cuenta, partidas del mismo monto absoluto pero
    signo contrario (ej. +150.000 y -150.000) — se anulan entre si y no aportan
    a un analisis 'limpio'. No se borran: quedan marcadas y trazables, cada par
    con el mismo numero de 'par_compensacion' para poder auditarlas."""
    df = detalle.copy()
    df["compensada"] = False
    df["par_compensacion"] = pd.NA

    par_id = 0
    for _, grupo in df.groupby("cuenta_contable"):
        for _, sub in grupo.groupby(grupo["monto"].abs()):
            positivos = sub[sub["monto"] > 0].index.tolist()
            negativos = sub[sub["monto"] < 0].index.tolist()
            n_pares = min(len(positivos), len(negativos))
            for i in range(n_pares):
                par_id += 1
                df.loc[positivos[i], ["compensada", "par_compensacion"]] = [True, par_id]
                df.loc[negativos[i], ["compensada", "par_compensacion"]] = [True, par_id]
    return df


COLUMNAS_EXPORT_AMIGABLES = [
    "fecha_documento", "cuenta_contable", "referencia", "glosa", "centro_costo",
    "moneda", "monto", "antiguedad_dias", "monto_duplicado",
]


def formatear_para_export(df, incluir_par_compensacion=False):
    """Renombra a nombres claros para el analista y traduce el flag de
    duplicado a Si/No en vez de True/False."""
    out = df.rename(columns={
        "dias_antiguedad": "antiguedad_dias",
        "es_duplicado": "monto_duplicado",
    }).copy()
    out["monto_duplicado"] = out["monto_duplicado"].map({True: "Si", False: "No"})
    columnas = [c for c in COLUMNAS_EXPORT_AMIGABLES if c in out.columns]
    if incluir_par_compensacion and "par_compensacion" in out.columns:
        columnas = columnas + ["par_compensacion"]
    return out[columnas]


def exportar_excel(resumen, detalle, incompletas):
    detalle_marcado = identificar_compensaciones(detalle)
    detalle_limpio = detalle_marcado[~detalle_marcado["compensada"]]
    partidas_compensadas = detalle_marcado[detalle_marcado["compensada"]]

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        resumen.to_excel(writer, sheet_name="Resumen", index=False)
        formatear_para_export(detalle_limpio).to_excel(writer, sheet_name="Detalle_Limpio", index=False)
        detalle.to_excel(writer, sheet_name="Detalle_Completo", index=False)
        if not partidas_compensadas.empty:
            formatear_para_export(partidas_compensadas, incluir_par_compensacion=True).to_excel(
                writer, sheet_name="Partidas_Compensadas", index=False
            )
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
        st.warning(
            "⚠️ Estas subiendo un archivo propio. Si contiene datos reales de la empresa: "
            "confirma primero que Seguridad TI y Legal ya aprobaron procesar estos datos en "
            "Streamlit Cloud (servidor externo) — ver plan de accion en el PRD, pestana "
            "'Acerca de / Gobernanza'. Mientras no este esa aprobacion, usa solo datos ficticios."
        )
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

    cuentas_unicas = sorted(df_validas["cuenta_contable"].dropna().unique(), key=str)
    tabla_naturaleza_base = pd.DataFrame({
        "cuenta_contable": cuentas_unicas,
        "naturaleza": [naturaleza_esperada(c) for c in cuentas_unicas],
        "confirmada": False,
    })
    with st.expander(
        "Naturaleza deudora/acreedora por cuenta (ajustar si tu plan de cuentas es distinto)"
    ):
        st.caption(
            "Por defecto se asume por el primer digito de la cuenta (1/5=deudora, "
            "2/3/4=acreedora) -- es solo un supuesto, puede no aplicar a tu plan de "
            "cuentas real. Corrige la naturaleza si hace falta y marca 'confirmada' "
            "para las cuentas que ya verificaste; mientras no la marques, cualquier "
            "'saldo contrario' que salga para esa cuenta queda etiquetado como no "
            "confirmado en vez de darlo por bueno en silencio."
        )
        tabla_naturaleza = st.data_editor(
            tabla_naturaleza_base,
            column_config={
                "cuenta_contable": st.column_config.TextColumn("Cuenta", disabled=True),
                "naturaleza": st.column_config.SelectboxColumn(
                    "Naturaleza", options=["deudora", "acreedora", "desconocida"]
                ),
                "confirmada": st.column_config.CheckboxColumn("Confirmada"),
            },
            hide_index=True,
            use_container_width=True,
            key="tabla_naturaleza",
        )
    naturaleza_overrides = {
        row["cuenta_contable"]: {"naturaleza": row["naturaleza"], "confirmada": row["confirmada"]}
        for _, row in tabla_naturaleza.iterrows()
    }

    detalle, resumen = construir_resumen(df_validas, saldos_f01, naturaleza_overrides)
    detalle_marcado = identificar_compensaciones(detalle)
    n_compensadas = int(detalle_marcado["compensada"].sum())

    # --- Resumen ejecutivo ---
    st.subheader("Resumen ejecutivo")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Cuentas evaluadas", len(resumen))
    c2.metric("Cuentas Rojo/Negro", int(resumen["semaforo"].isin(["Rojo", "Negro"]).sum()))
    c3.metric("Duplicidades totales", int(resumen["duplicidades"].sum()))
    c4.metric("Partidas antiguas", int(resumen["partidas_antiguas"].sum()))
    c5.metric("Filas con datos faltantes", len(df_incompletas))
    c6.metric("Partidas compensadas", n_compensadas)
    if n_compensadas:
        st.caption(
            f"{n_compensadas} filas tienen su contraparte exacta (mismo monto, signo contrario) "
            f"dentro de la misma cuenta — se anulan entre si. Se sacaron de 'Detalle_Limpio' en "
            f"el Excel exportado, pero quedan intactas y trazables en 'Partidas_Compensadas'."
        )

    # --- Tabla resumen por cuenta ---
    st.subheader("Semaforo por cuenta")
    st.dataframe(
        resumen[COLUMNAS_RESUMEN_UI].style.map(pintar_semaforo, subset=["semaforo"]),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "⚠ en el comentario = aviso de confiabilidad (muestra chica o patron atipico "
        "frente a otras cuentas de este archivo), no cambia el color del semaforo. "
        "Detalle completo (n de filas, tasas) disponible en el Excel exportado."
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


try:
    if verificar_acceso():
        st.title("Analisis Inteligente de Cuentas — Piloto")
        st.caption(
            "\"Inteligente\" = aplica reglas y logica contable de forma sistematica — "
            "NO usa un modelo de IA/LLM en tiempo de ejecucion. Detecta duplicidades, "
            "saldos contrarios, partidas antiguas y diferencias de cuadratura con reglas "
            "fijas: no se inventa nada."
        )

        tab_tablero, tab_acerca = st.tabs(["Tablero", "Acerca de / Gobernanza"])

        with tab_tablero:
            render_tablero()

        with tab_acerca:
            render_acerca()
except Exception:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    registrar_error(
        exc_type, exc_value, exc_traceback,
        url_app="mdani6010-sys-analisis-inteligente-cuentas-app-4hvlat.streamlit.app"
    )
    st.error("❌ Error técnico en la aplicación. El equipo ha sido notificado. Reintenta en unos minutos.")
