"""
Evalua el tablero contra "casos reales" con respuesta conocida.

No mira la respuesta correcta antes de calcular: primero corre la deteccion
del tablero tal cual la ve un usuario (via los comentarios que genera), y
recien despues compara contra la respuesta correcta (datos/ground_truth.json,
que se genero al mismo tiempo que los datos ficticios en generar_datos.py).
"""
import json
from pathlib import Path

import pandas as pd

from app import construir_resumen, separar_filas_incompletas

CARPETA_DATOS = Path(__file__).parent / "datos"

ETIQUETAS = {
    "saldo_contrario": "Saldo contrario",
    "duplicados_alta": "Duplicidades",
    "antiguedad_alta": "Antiguedad",
    "descuadre": "Cuadratura",
}

# Que texto del comentario delata que el tablero SI reporto ese tipo de problema
# (es literalmente lo que el analista ve en pantalla, no un atajo interno)
PALABRA_CLAVE = {
    "saldo_contrario": "Saldo contrario",
    "duplicados_alta": "duplicadas",
    "antiguedad_alta": "antiguedad mayor",
    "descuadre": "Diferencia de",
}


def evaluar():
    df = pd.read_excel(CARPETA_DATOS / "movimientos.xlsx")
    saldos_f01 = pd.read_csv(CARPETA_DATOS / "saldos_f01.csv")
    df_validas, _ = separar_filas_incompletas(df)

    # 1) Correr la deteccion del tablero tal cual, SIN mirar la respuesta correcta
    _, resumen = construir_resumen(df_validas, saldos_f01)
    resultado_sistema = {
        row["cuenta_contable"]: row["comentario"] for _, row in resumen.iterrows()
    }

    # 2) Recien ahora se abre la respuesta correcta
    with open(CARPETA_DATOS / "ground_truth.json", encoding="utf-8") as f:
        ground_truth = json.load(f)

    todas_cuentas = sorted(resultado_sistema.keys())
    filas_tabla = []
    fallas = []

    def normalizar(cuenta):
        # cuenta_contable llega como float (1101.0) por los NaN de datos
        # faltantes; el ground truth lo guarda como string "1101".
        return str(int(cuenta))

    for cuenta in todas_cuentas:
        comentario = resultado_sistema[cuenta]
        cuenta_norm = normalizar(cuenta)

        esperado = {
            tipo for tipo, cuentas in ground_truth.items() if cuenta_norm in cuentas
        }
        detectado = {
            tipo for tipo, palabra in PALABRA_CLAVE.items() if palabra in comentario
        }

        acierta = esperado == detectado
        filas_tabla.append({
            "caso": cuenta_norm,
            "tu_resultado": ", ".join(sorted(ETIQUETAS[t] for t in detectado)) or "Sin observaciones",
            "correcto": ", ".join(sorted(ETIQUETAS[t] for t in esperado)) or "Sin observaciones",
            "acierta": "Si" if acierta else "No",
        })
        if not acierta:
            fallas.append({
                "cuenta": cuenta,
                "esperado": esperado,
                "detectado": detectado,
                "faltantes": esperado - detectado,
                "falsos_positivos": detectado - esperado,
            })

    return filas_tabla, fallas


def imprimir_tabla(filas_tabla):
    print("| caso | tu resultado | correcto | ¿acierta? |")
    print("|---|---|---|---|")
    for fila in filas_tabla:
        print(f"| {fila['caso']} | {fila['tu_resultado']} | {fila['correcto']} | {fila['acierta']} |")


def analizar_fallas(fallas):
    if not fallas:
        print("\nSin fallas: no hay nada que analizar.")
        return

    print(f"\n{len(fallas)} caso(s) fallado(s):")
    for f in fallas:
        detalle = []
        if f["faltantes"]:
            detalle.append(f"no detecto: {sorted(f['faltantes'])}")
        if f["falsos_positivos"]:
            detalle.append(f"marco de mas: {sorted(f['falsos_positivos'])}")
        print(f"  - Cuenta {f['cuenta']}: {'; '.join(detalle)}")

    tipos_faltantes = [t for f in fallas for t in f["faltantes"]]
    tipos_falsos = [t for f in fallas for t in f["falsos_positivos"]]
    if tipos_faltantes:
        comun = max(set(tipos_faltantes), key=tipos_faltantes.count)
        print(f"\nLo que mas se repite entre las fallas: no detectar '{ETIQUETAS[comun]}'.")
    if tipos_falsos:
        comun = max(set(tipos_falsos), key=tipos_falsos.count)
        print(f"Lo que mas se repite entre las fallas: marcar '{ETIQUETAS[comun]}' de mas (falso positivo).")


if __name__ == "__main__":
    filas_tabla, fallas = evaluar()
    imprimir_tabla(filas_tabla)
    aciertos = sum(1 for f in filas_tabla if f["acierta"] == "Si")
    print(f"\nAciertos: {aciertos}/{len(filas_tabla)} ({aciertos / len(filas_tabla):.0%})")
    analizar_fallas(fallas)
