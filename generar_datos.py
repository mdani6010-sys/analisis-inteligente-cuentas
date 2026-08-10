"""
Genera datos ficticios de movimientos contables (estilo SAP FBL3N) con
anomalias insertadas a proposito, para probar el tablero (app.py).

No usa datos reales de ninguna empresa: todo es sintetico.
"""
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

random.seed(42)

HOY = date.today()
CARPETA_DATOS = Path(__file__).parent / "datos"
CARPETA_DATOS.mkdir(exist_ok=True)

# (codigo, nombre, naturaleza esperada: 'deudora' -> monto neto deberia ser >= 0,
#                                        'acreedora' -> monto neto deberia ser <= 0)
CUENTAS = [
    ("1101", "Caja", "deudora"),
    ("1102", "Bancos", "deudora"),
    ("1201", "Clientes", "deudora"),
    ("1301", "Inventario", "deudora"),
    ("2101", "Proveedores", "acreedora"),
    ("2102", "Impuestos por Pagar", "acreedora"),
    ("2201", "Prestamos Bancarios", "acreedora"),
    ("3101", "Capital", "acreedora"),
    ("4101", "Ventas", "acreedora"),
    ("5101", "Costo de Ventas", "deudora"),
    ("5102", "Gastos Administrativos", "deudora"),
    ("5103", "Gastos de Venta", "deudora"),
]

# Cuentas a las que les insertamos a proposito un saldo contrario a su naturaleza
CUENTAS_SALDO_CONTRARIO = {"2101", "4101", "5103"}

# Cuentas con muchas partidas antiguas (>90 dias) a proposito, ej. Clientes/Prestamos
# que en la vida real acumulan partidas abiertas sin cerrar
CUENTAS_ANTIGUEDAD_ALTA = {"1201", "2201"}

# Cuentas donde concentramos la mayoria de las duplicidades (errores de doble ingreso)
CUENTAS_DUPLICADOS_ALTA = {"1301", "4101", "5103"}

CENTROS_COSTO = [f"CC-{i:03d}" for i in range(1, 9)]

GLOSAS = [
    "Pago a proveedor", "Cobro cliente", "Ajuste contable", "Provision mensual",
    "Compra de mercaderia", "Pago de servicios", "Nomina", "Transferencia interna",
    "Regularizacion", "Anticipo", "Devolucion", "Nota de credito", "Nota de debito",
]

N_DUPLICADOS_ALTA = 45
N_DUPLICADOS_OTRAS = 15
N_DUPLICADOS = N_DUPLICADOS_ALTA + N_DUPLICADOS_OTRAS
N_MISSING = 35
N_TOTAL = 3000
N_BASE = N_TOTAL - N_DUPLICADOS

filas = []
for i in range(N_BASE):
    codigo, nombre, naturaleza = random.choice(CUENTAS)

    # La mayoria de las cuentas casi no tiene partidas antiguas; unas pocas
    # cuentas "problema" concentran muchas (>90 dias sin cerrar)
    prob_antigua = 0.35 if codigo in CUENTAS_ANTIGUEDAD_ALTA else 0.05
    if random.random() < prob_antigua:
        dias_atras = random.randint(91, 400)
    else:
        dias_atras = random.randint(0, 90)
    fecha = HOY - timedelta(days=dias_atras)

    monto_base = round(random.uniform(5_000, 3_000_000), 0)
    signo_natural = 1 if naturaleza == "deudora" else -1

    if codigo in CUENTAS_SALDO_CONTRARIO and random.random() < 0.75:
        signo = -signo_natural  # invertido a proposito
    else:
        signo = signo_natural

    monto = signo * monto_base
    moneda = "CLP" if random.random() < 0.9 else "USD"

    filas.append({
        "fecha_documento": fecha,
        "monto": monto,
        "moneda": moneda,
        "glosa": f"{random.choice(GLOSAS)} - {nombre}",
        "centro_costo": random.choice(CENTROS_COSTO),
        "referencia": f"DOC-{i:06d}",
        "cuenta_contable": codigo,
    })

df = pd.DataFrame(filas)

# --- Insertar duplicidades: copiamos filas existentes tal cual (mismo documento) ---
# La mayoria se concentra en unas pocas cuentas "problema"; el resto se reparte
# como ruido de fondo en cualquier cuenta.
idx_alta = df.index[df["cuenta_contable"].isin(CUENTAS_DUPLICADOS_ALTA)].tolist()
idx_otras = df.index[~df["cuenta_contable"].isin(CUENTAS_DUPLICADOS_ALTA)].tolist()
idx_a_duplicar = (
    random.sample(idx_alta, min(N_DUPLICADOS_ALTA, len(idx_alta)))
    + random.sample(idx_otras, min(N_DUPLICADOS_OTRAS, len(idx_otras)))
)
duplicados = df.loc[idx_a_duplicar].copy()
df = pd.concat([df, duplicados], ignore_index=True)

# --- Insertar datos faltantes en columnas clave ---
idx_missing = random.sample(range(len(df)), N_MISSING)
columnas_clave = ["monto", "fecha_documento", "cuenta_contable"]
for idx in idx_missing:
    col = random.choice(columnas_clave)
    df.at[idx, col] = None

# Barajar y guardar
df = df.sample(frac=1, random_state=42).reset_index(drop=True)
df.to_excel(CARPETA_DATOS / "movimientos.xlsx", index=False)
df.to_csv(CARPETA_DATOS / "movimientos.csv", index=False)

# --- Generar saldos_f01.csv (referencia "F.01" ficticia para chequeo de cuadratura) ---
saldos_reales = (
    df.dropna(subset=["monto", "fecha_documento", "cuenta_contable"])
    .groupby("cuenta_contable")["monto"].sum()
    .reset_index()
    .rename(columns={"monto": "saldo_f01_esperado"})
)

CUENTAS_CON_DESCUADRE = random.sample(list(saldos_reales["cuenta_contable"]), 3)
for codigo in CUENTAS_CON_DESCUADRE:
    delta = random.choice([-1, 1]) * random.uniform(50_000, 300_000)
    saldos_reales.loc[saldos_reales["cuenta_contable"] == codigo, "saldo_f01_esperado"] += delta

saldos_reales.to_csv(CARPETA_DATOS / "saldos_f01.csv", index=False)

print(f"Listo. {len(df)} filas generadas en {CARPETA_DATOS / 'movimientos.xlsx'}")
print(f"- Duplicidades insertadas: {N_DUPLICADOS} filas")
print(f"- Filas con datos faltantes: {N_MISSING}")
print(f"- Cuentas con saldo contrario a su naturaleza: {sorted(CUENTAS_SALDO_CONTRARIO)}")
print(f"- Cuentas con descuadre vs F.01 ficticio: {sorted(CUENTAS_CON_DESCUADRE)}")
