# Análisis Inteligente de Cuentas — Tablero (piloto)

Tablero interactivo que detecta anomalías en movimientos contables: duplicidades,
saldos contrarios a su naturaleza, partidas antiguas (>90 días) y diferencias de
cuadratura contra un saldo de referencia (F.01). Muestra un semáforo por cuenta,
comentarios explicativos por reglas (sin IA) y permite exportar el resultado a Excel.

Ver [prd-v2.md](prd-v2.md) para el detalle del proyecto.

## Uso local

```bash
pip install -r requirements.txt
python generar_datos.py   # genera datos ficticios de ejemplo en datos/
streamlit run app.py
```
