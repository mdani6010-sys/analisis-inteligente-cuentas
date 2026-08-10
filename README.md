# Análisis Inteligente de Cuentas — Tablero (piloto)

> **¿Por qué "Inteligente" si no usa IA?** Porque aplica lógica y reglas contables de forma
> sistemática — no porque corra un modelo de IA/LLM. El tablero funciona 100% con reglas
> fijas sobre los datos; no genera texto ni inventa nada. Ver guardrails en `prd-v2.md`.

**Por qué existe**: revisar cuentas contables a mano en Excel (duplicidades, saldos
contrarios, partidas antiguas, cuadratura) toma horas cada mes y deja pasar errores.
Este tablero automatiza esa revisión para analistas contables senior y de estados
financieros, sin reemplazar su criterio profesional — solo prioriza dónde mirar primero.

Tablero interactivo que detecta anomalías en movimientos contables: duplicidades,
saldos contrarios a su naturaleza, partidas antiguas (>90 días) y diferencias de
cuadratura contra un saldo de referencia (F.01). Muestra un semáforo por cuenta,
comentarios explicativos por reglas (sin IA) y permite exportar el resultado a Excel.

Ver [prd-v2.md](prd-v2.md) para el detalle completo del proyecto (problema, alcance,
guardrails, gobernanza, ficha económica y el plan de acción sobre puntos débiles).
Ver [SEGURIDAD-Y-DATOS.md](SEGURIDAD-Y-DATOS.md) para el resumen de flujo de datos
pendiente de aprobación de Seguridad TI y Legal.

## Acceso

La app pide una clave de acceso interina (uso exclusivo de las 3 analistas autorizadas,
ver PRD sección Gobernanza). La clave se configura como secreto `APP_PASSWORD` en
Streamlit Cloud — nunca vive en el código ni en este repo público.

## Uso local

```bash
pip install -r requirements.txt
python generar_datos.py   # genera datos ficticios de ejemplo en datos/
streamlit run app.py
```

Sin `.streamlit/secrets.toml` configurado localmente, la app no pide clave (para
desarrollo). Para probar el gate de acceso en local, crea `.streamlit/secrets.toml`
con `APP_PASSWORD = "tu-clave"` (ese archivo está en `.gitignore`, no se sube).
