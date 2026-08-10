# Análisis Inteligente de Cuentas — Tablero (piloto)

**Por qué existe**: revisar cuentas contables a mano en Excel (duplicidades, saldos
contrarios, partidas antiguas, cuadratura) toma horas cada mes y deja pasar errores.
Este tablero automatiza esa revisión para analistas contables senior y de estados
financieros, sin reemplazar su criterio profesional — solo prioriza dónde mirar primero.

Tablero interactivo que detecta anomalías en movimientos contables: duplicidades,
saldos contrarios a su naturaleza, partidas antiguas (>90 días) y diferencias de
cuadratura contra un saldo de referencia (F.01). Muestra un semáforo por cuenta,
comentarios explicativos por reglas (sin IA) y permite exportar el resultado a Excel.

Ver [prd-v2.md](prd-v2.md) para el detalle completo del proyecto (problema, alcance,
guardrails, gobernanza y ficha económica).

## Uso local

```bash
pip install -r requirements.txt
python generar_datos.py   # genera datos ficticios de ejemplo en datos/
streamlit run app.py
```
