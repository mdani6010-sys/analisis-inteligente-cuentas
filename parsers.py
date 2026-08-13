"""
Flexible CSV/XLSX parser con deteccion de formato y reconciliacion F.01.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict

def leer_archivo(ruta: str) -> pd.DataFrame:
    """Lee CSV o XLSX detectando metadata y encoding automaticamente."""
    ruta = Path(ruta)

    if ruta.suffix.lower() == '.csv':
        for enc in ['latin-1', 'utf-8', 'cp1252']:
            try:
                with open(ruta, encoding=enc) as f:
                    primera = f.readline().lower()
                if any(t in primera for t in ['balance', 'hoja', 'nom.', 'direc']):
                    return pd.read_csv(ruta, encoding=enc, sep=';', skiprows=8)
                else:
                    return pd.read_csv(ruta, encoding=enc, sep=';')
            except:
                continue
        raise ValueError(f"No se pudo leer {ruta}")

    elif ruta.suffix.lower() in ['.xlsx', '.xls']:
        xl = pd.ExcelFile(ruta)
        sheet = 'Data' if 'Data' in xl.sheet_names else xl.sheet_names[0]
        df_test = pd.read_excel(ruta, sheet_name=sheet, header=None, nrows=6)
        if len(df_test) > 5 and df_test.iloc[5].notna().sum() > len(df_test.columns) * 0.3:
            return pd.read_excel(ruta, sheet_name=sheet, skiprows=5)
        else:
            return pd.read_excel(ruta, sheet_name=sheet)
    else:
        raise ValueError(f"Formato no soportado: {ruta.suffix}")

def _limpiar_numero(val):
    """Convierte strings numericos SAP (6.793.771,71) a float."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    # Remueve todos los puntos (separador de miles SAP), reemplaza coma con punto (decimal)
    s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except:
        return np.nan

def normalizar_columnas(df: pd.DataFrame, tipo: str = 'auto') -> Tuple[pd.DataFrame, str]:
    """
    Normaliza nombres de columna. Detecta tipo automaticamente si tipo=='auto'.
    """
    # Detecta tipo automaticamente
    if tipo == 'auto':
        cols_lower = ' '.join(df.columns).lower()
        tipo = 'balance' if any(x in cols_lower for x in ['saldo debe', 'saldo haber']) else 'movimientos'

    # Mapeos directos: {nombre_nuevo: [sinonimos_exactos]}
    if tipo == 'balance':
        mapeos = {
            'cuenta': 'Cuenta de mayor',
            'descripcion': 'Texto explicativo',
            'debe': 'Debe',
            'haber': 'Haber',
            'saldo_debe': 'Saldo Debe',
            'saldo_haber': 'Saldo Haber',
            'moneda': 'Moneda transacci',  # Prefix match
        }
    else:  # movimientos
        mapeos = {
            'fecha': 'Fecha de documento',
            'monto': 'Importe en moneda local',
            'moneda': 'Moneda local',
            'glosa': 'Texto',
            'centro_costo': 'Centro de coste',
            'referencia': 'N',  # Prefix match: N° documento
            'cuenta_contable': 'Cuenta',
        }

    # Aplica mapeos flexibles
    cambios = {}
    for col_dest, col_src_patrón in mapeos.items():
        for col_actual in df.columns:
            col_lower = str(col_actual).lower()
            patrón_lower = col_src_patrón.lower()
            # Exact match o prefix match
            if col_lower == patrón_lower or col_lower.startswith(patrón_lower):
                cambios[col_actual] = col_dest
                break

    df = df.rename(columns=cambios)

    # Limpia numeros en columnas objetivo
    cols_num = ['monto', 'saldo_debe', 'saldo_haber', 'debe', 'haber']
    for col in cols_num:
        if col in df.columns:
            df[col] = df[col].apply(_limpiar_numero)

    # Limpia fechas
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')

    return df, tipo

def reconciliar_con_f01(df_aux: pd.DataFrame, df_balance: pd.DataFrame, cuenta: Optional[str] = None) -> Dict:
    """Reconcilia auxiliar vs F.01."""
    if cuenta is None and 'cuenta_contable' in df_aux.columns:
        val = df_aux['cuenta_contable'].iloc[0]
        # Convierte a string limpio (si es float, convierte a int primero para evitar .0)
        if isinstance(val, float):
            cuenta = str(int(val)).strip() if not pd.isna(val) else None
        else:
            cuenta = str(val).strip() if pd.notna(val) else None

    # Total auxiliar (filtrado por cuenta)
    col_monto = 'monto' if 'monto' in df_aux.columns else next((c for c in df_aux.columns if 'monto' in c.lower()), None)
    if 'cuenta_contable' in df_aux.columns and cuenta and col_monto:
        # Filtra por cuenta
        cuenta_norm_aux = str(int(float(cuenta))).strip() if isinstance(cuenta, (int, float, str)) else str(cuenta).strip()
        df_cuenta = df_aux[df_aux['cuenta_contable'].astype(str).str.replace('.0', '', regex=False).str.strip() == cuenta_norm_aux]
        total = df_cuenta[col_monto].sum()
    else:
        total = df_aux[col_monto].sum() if col_monto else 0

    # Saldo F.01
    saldo_f01 = None
    if 'cuenta' in df_balance.columns:
        # Normaliza tipo: si float, convierte a int
        cuenta_norm = str(int(float(cuenta))).strip() if cuenta and isinstance(cuenta, (int, float, str)) else str(cuenta).strip()
        fila = df_balance[df_balance['cuenta'].astype(str).str.replace('.0', '', regex=False).str.strip() == cuenta_norm]
        if not fila.empty:
            # Preferencia: saldo_debe > saldo_haber > saldo
            for col in ['saldo_debe', 'saldo_haber', 'saldo']:
                if col in fila.columns:
                    val = fila[col].iloc[0]
                    if pd.notna(val) and val != 0:
                        saldo_f01 = val
                        break

    if saldo_f01 is None:
        saldo_f01 = 0

    # Reconciliacion
    diff = abs(total - saldo_f01)
    pct = (diff / abs(saldo_f01) * 100) if saldo_f01 != 0 else 0
    estado = 'OK' if diff < 1 else 'DIFERENCIA'

    return {
        'cuenta': cuenta,
        'total_auxiliar': total,
        'saldo_f01': saldo_f01,
        'diferencia': diff,
        'pct_diferencia': pct,
        'estado': estado,
    }
