"""
Análisis Inteligente de Cuentas v2 - Dashboard Streamlit
Detección de anomalías y reconciliación de auxiliares vs F.01
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from io import BytesIO
import sys
from pathlib import Path

# Import parser
sys.path.insert(0, str(Path(__file__).parent))
from parsers import leer_archivo, normalizar_columnas, reconciliar_con_f01

# CONFIG
st.set_page_config(page_title="Análisis Inteligente de Cuentas", layout="wide")
PASSWORD = "Semaforo-Contable-2026!"

# THRESHOLDS
UMBRAL_DUPLICADOS_AMARILLO = 0.02
UMBRAL_DUPLICADOS_ROJO = 0.03
UMBRAL_ANTIGUEDAD = 0.20
UMBRAL_CUADRATURA_MODERADO = 500
UMBRAL_CUADRATURA_GRAVE = 50000
UMBRAL_MUESTRA_CHICA = 10

def verificar_acceso():
    """Gate con contraseña."""
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("🔐 Acceso Restringido")
        clave = st.text_input("Ingresa la clave:", type="password")
        if st.button("Acceder"):
            if clave == PASSWORD:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
        st.stop()

def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia y prepara datos."""
    if len(df) == 0:
        return df

    # Maneja valores faltantes
    df = df.fillna(0)

    # Fechas con errors='coerce'
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')

    return df

def detectar_anomalias(df: pd.DataFrame) -> pd.DataFrame:
    """Detecta 4 tipos de anomalías."""
    if len(df) < 2:
        return pd.DataFrame()

    anomalias = []

    # 1. DUPLICIDADES
    if 'glosa' in df.columns:
        duplicados = df[df.duplicated(subset=['glosa'], keep=False)]
        if len(duplicados) > 0:
            tasa = len(duplicados) / len(df)
            if tasa >= UMBRAL_DUPLICADOS_ROJO:
                nivel = "Rojo"
            elif tasa >= UMBRAL_DUPLICADOS_AMARILLO:
                nivel = "Amarillo"
            else:
                nivel = "Verde"

            anomalias.append({
                'tipo': 'Duplicidades',
                'cantidad': len(duplicados),
                'tasa': f"{tasa*100:.1f}%",
                'nivel': nivel,
                'detalle': f'{len(duplicados)} partidas duplicadas (tasa {tasa*100:.1f}% > umbral {UMBRAL_DUPLICADOS_AMARILLO*100}%)'
            })

    # 2. SALDOS CONTRARIOS (si hay columna de signo o se puede inferir)
    if 'monto' in df.columns:
        positivos = (df['monto'] > 0).sum()
        negativos = (df['monto'] < 0).sum()
        total = len(df)

        if total > 0:
            pct_negativos = negativos / total
            if pct_negativos > 0.4:  # Muchos valores negativos es sospechoso
                anomalias.append({
                    'tipo': 'Saldo Contrario',
                    'cantidad': negativos,
                    'tasa': f"{pct_negativos*100:.1f}%",
                    'nivel': 'Amarillo' if pct_negativos < 0.75 else 'Rojo',
                    'detalle': f'{negativos} partidas con signo opuesto ({pct_negativos*100:.1f}% del total)'
                })

    # 3. ANTIGUEDAD (>90 días)
    if 'fecha' in df.columns:
        df['dias_antiguedad'] = (datetime.now() - pd.to_datetime(df['fecha'], errors='coerce')).dt.days
        antiguas = df[df['dias_antiguedad'] > 90]
        if len(antiguas) > 0:
            tasa = len(antiguas) / len(df)
            if tasa > UMBRAL_ANTIGUEDAD:
                anomalias.append({
                    'tipo': 'Antiguedad',
                    'cantidad': len(antiguas),
                    'tasa': f"{tasa*100:.1f}%",
                    'nivel': 'Amarillo',
                    'detalle': f'{len(antiguas)} partidas mayores a 90 días ({tasa*100:.1f}% > umbral {UMBRAL_ANTIGUEDAD*100}%)'
                })

    return pd.DataFrame(anomalias)

def main():
    """Aplicación principal."""
    verificar_acceso()

    st.title("📊 Análisis Inteligente de Cuentas")
    st.markdown("Detección de anomalías + Reconciliación de auxiliares vs F.01")

    # TABS
    tab1, tab2, tab3 = st.tabs(["📥 Cargar Datos", "🔍 Análisis", "💾 Exportar"])

    with tab1:
        st.header("1. Cargar Datos")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Movimientos (Auxiliar)")
            archivo_aux = st.file_uploader("CSV o XLSX", type=["csv", "xlsx"], key="aux")
            if archivo_aux:
                try:
                    # Guarda temp
                    temp_path = f"/tmp/{archivo_aux.name}"
                    with open(temp_path, "wb") as f:
                        f.write(archivo_aux.getbuffer())

                    df_aux_raw = leer_archivo(temp_path)
                    df_aux, tipo_aux = normalizar_columnas(df_aux_raw)
                    df_aux = limpiar_datos(df_aux)

                    st.session_state.df_aux = df_aux
                    st.success(f"✓ {len(df_aux)} filas cargadas ({tipo_aux})")
                except Exception as e:
                    st.error(f"Error: {e}")

        with col2:
            st.subheader("Balance F.01")
            archivo_f01 = st.file_uploader("CSV o XLSX", type=["csv", "xlsx"], key="f01")
            if archivo_f01:
                try:
                    temp_path = f"/tmp/{archivo_f01.name}"
                    with open(temp_path, "wb") as f:
                        f.write(archivo_f01.getbuffer())

                    df_f01_raw = leer_archivo(temp_path)
                    df_f01, tipo_f01 = normalizar_columnas(df_f01_raw)
                    df_f01 = limpiar_datos(df_f01)

                    st.session_state.df_f01 = df_f01
                    st.success(f"✓ {len(df_f01)} filas cargadas ({tipo_f01})")
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab2:
        st.header("2. Análisis")

        if "df_aux" not in st.session_state:
            st.info("Carga datos en la pestaña anterior")
            st.stop()

        df_aux = st.session_state.df_aux

        # Selecciona cuenta
        if 'cuenta_contable' in df_aux.columns:
            cuentas = df_aux['cuenta_contable'].dropna().unique()
            cuenta_sel = st.selectbox("Selecciona cuenta", cuentas)

            df_cuenta = df_aux[df_aux['cuenta_contable'] == cuenta_sel]
        else:
            cuenta_sel = None
            df_cuenta = df_aux

        # ANOMALIAS
        st.subheader("Anomalías Detectadas")
        anomalias_df = detectar_anomalias(df_cuenta)

        if len(anomalias_df) > 0:
            for _, fila in anomalias_df.iterrows():
                color = {"Rojo": "🔴", "Amarillo": "🟡", "Verde": "🟢"}.get(fila['nivel'], "⚪")
                st.write(f"{color} **{fila['tipo']}** - {fila['detalle']}")
        else:
            st.success("✓ Sin anomalías detectadas")

        # RECONCILIACION
        if "df_f01" in st.session_state and cuenta_sel:
            st.subheader("Reconciliación vs F.01")
            recon = reconciliar_con_f01(df_aux, st.session_state.df_f01, cuenta_sel)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Auxiliar", f"${recon['total_auxiliar']:,.0f}")
            with col2:
                st.metric("Saldo F.01", f"${recon['saldo_f01']:,.0f}")
            with col3:
                st.metric("Diferencia", f"${recon['diferencia']:,.0f}")
            with col4:
                estado_color = "🟢" if recon['estado'] == 'OK' else "🔴"
                st.metric("Estado", f"{estado_color} {recon['estado']}")

    with tab3:
        st.header("3. Exportar")
        if "df_aux" in st.session_state:
            df_aux = st.session_state.df_aux
            csv = df_aux.to_csv(index=False)
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"analisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
