"""
Script de demostracion del sistema con datos reales.
Simula flujo de app.py sin necesidad de Streamlit.
"""
import pandas as pd
from parsers import leer_archivo, normalizar_columnas, reconciliar_con_f01
from datetime import datetime

def analizar_cuenta(ruta_aux, ruta_balance, cuenta_id):
    """Analisis completo de una cuenta."""
    print(f"\n{'='*70}")
    print(f"ANALISIS CUENTA {cuenta_id}")
    print(f"{'='*70}")

    # 1. Load
    print("\n[1/5] Cargando datos...")
    try:
        df_aux_raw = leer_archivo(ruta_aux)
        df_aux, _ = normalizar_columnas(df_aux_raw)
        print(f"  OK Auxiliar: {len(df_aux)} movimientos")

        df_bal_raw = leer_archivo(ruta_balance)
        df_bal, _ = normalizar_columnas(df_bal_raw)
        print(f"  OK Balance: {len(df_bal)} cuentas")
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    # 2. Filter by account
    print(f"\n[2/5] Filtrando cuenta {cuenta_id}...")
    if 'cuenta_contable' in df_aux.columns:
        cuenta_norm = str(int(float(cuenta_id))).strip()
        df_cuenta = df_aux[df_aux['cuenta_contable'].astype(str).str.replace('.0', '', regex=False).str.strip() == cuenta_norm]
        print(f"  OK {len(df_cuenta)} movimientos encontrados")
    else:
        print(f"  ERROR Columna 'cuenta_contable' no existe")
        return

    # 3. Anomalies
    print(f"\n[3/5] Detectando anomalias...")
    anomalias = []

    # 3a. Duplicities
    if 'glosa' in df_cuenta.columns:
        dup = df_cuenta[df_cuenta.duplicated(subset=['glosa'], keep=False)]
        if len(dup) > 0:
            tasa = len(dup) / len(df_cuenta)
            nivel = "ROJO" if tasa > 0.03 else ("AMARILLO" if tasa > 0.02 else "VERDE")
            anomalias.append({
                'tipo': 'Duplicidades',
                'cantidad': len(dup),
                'tasa': f"{tasa*100:.1f}%",
                'nivel': nivel
            })
            print(f"  ANOMALIA Duplicidades: {len(dup)} partidas ({tasa*100:.1f}%) [{nivel}]")

    # 3b. Aged items
    if 'fecha' in df_cuenta.columns:
        df_cuenta['dias'] = (datetime.now() - pd.to_datetime(df_cuenta['fecha'])).dt.days
        aged = df_cuenta[df_cuenta['dias'] > 90]
        if len(aged) > 0:
            tasa = len(aged) / len(df_cuenta)
            anomalias.append({
                'tipo': 'Antiguedad >90d',
                'cantidad': len(aged),
                'tasa': f"{tasa*100:.1f}%",
                'nivel': 'AMARILLO' if tasa > 0.20 else 'VERDE'
            })
            print(f"  ANOMALIA Antiguedad: {len(aged)} partidas ({tasa*100:.1f}%) mayores a 90 dias")

    # 3c. Amount signs
    if 'monto' in df_cuenta.columns:
        positivos = (df_cuenta['monto'] > 0).sum()
        negativos = (df_cuenta['monto'] < 0).sum()
        if negativos > 0:
            tasa_neg = negativos / len(df_cuenta)
            if tasa_neg > 0.4:
                anomalias.append({
                    'tipo': 'Saldos Contrarios',
                    'cantidad': negativos,
                    'tasa': f"{tasa_neg*100:.1f}%",
                    'nivel': 'ROJO' if tasa_neg > 0.75 else 'AMARILLO'
                })
                print(f"  ANOMALIA Saldos contrarios: {negativos} partidas negativas ({tasa_neg*100:.1f}%)")

    # 4. Reconciliation
    print(f"\n[4/5] Reconciliacion vs F.01...")
    recon = reconciliar_con_f01(df_aux, df_bal, cuenta_id)
    print(f"  Total auxiliar:  ${recon['total_auxiliar']:>15,.2f}")
    print(f"  Saldo F.01:      ${recon['saldo_f01']:>15,.2f}")
    print(f"  Diferencia:      ${recon['diferencia']:>15,.2f}")
    if recon['diferencia'] > 50000:
        print(f"  ADVERTENCIA GRAVE diferencia ({recon['pct_diferencia']:.0f}%)")
        anomalias.append({
            'tipo': 'Diferencia de Cuadratura',
            'cantidad': recon['diferencia'],
            'tasa': f"{recon['pct_diferencia']:.1f}%",
            'nivel': 'ROJO'
        })

    # 5. Summary
    print(f"\n[5/5] Resumen...")
    print(f"  Total anomalias detectadas: {len(anomalias)}")
    for a in anomalias:
        print(f"    - {a['tipo']}: {a['cantidad']} ({a['tasa']}) [{a['nivel']}]")

    return {
        'cuenta': cuenta_id,
        'movimientos': len(df_cuenta),
        'anomalias': anomalias,
        'reconciliacion': recon
    }

if __name__ == "__main__":
    # Demo con datos reales
    resultado = analizar_cuenta(
        ruta_aux=r"C:\Users\eduar\Downloads\234101 2025.xlsx",
        ruta_balance=r"C:\Users\eduar\Downloads\BALANCE MLL PR.csv",
        cuenta_id="234101"
    )

    print(f"\n{'='*70}")
    print("LISTO PARA PRESENTACION")
    print(f"{'='*70}")
    print("\nResultado exportable en:")
    print("  - Dashboard Streamlit (app.py)")
    print("  - Excel con 5 hojas (proxima feature)")
    print("  - CSV con detalle (descargable)")
