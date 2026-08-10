# Contexto del proyecto (léeme, agente)

Tablero (Streamlit) que detecta anomalías en movimientos contables — duplicidades,
saldos contrarios, partidas antiguas (>90 días) y diferencias de cuadratura contra F.01.
Piloto interno para analistas contables. El **PRD (`prd-v2.md`) es la fuente de verdad**:
problema, alcance, guardrails, gobernanza y ficha económica.

## Archivos clave
- `app.py` — el tablero: UI + lógica de detección (4 anomalías, semáforo, comentarios, export a Excel)
- `generar_datos.py` — genera datos ficticios de prueba y la "respuesta correcta" (`datos/ground_truth.json`)
- `test_deteccion.py` — evalúa la detección contra la respuesta correcta, sin verla antes de calcular
- `datos/` — datos ficticios generados (no son datos reales de ninguna empresa)

## Reglas para trabajar en este proyecto
- **Sin IA/LLM**: los comentarios del tablero salen de reglas fijas sobre los datos, no de un modelo generativo. No agregar llamadas a un LLM sin que el usuario lo pida explícitamente (tiene costo, se evaluó y se descartó para el piloto).
- **No inventar ni suponer**: si falta un dato o es dudoso (ej. fecha mal escrita), se marca como tal — no se omite, no se asume, y no debe reventar la app.
- **Después de cualquier cambio a la lógica de detección** (`app.py`), correr `python test_deteccion.py` y confirmar que sigue en 100% antes de subir el cambio.
- **El PRD siempre se actualiza y se sube a GitHub** junto con cada cambio relevante (`git add` + `commit` + `push` en el mismo paso, sin esperar a que se pida).
- **El repo es público pero el proyecto es de uso interno** del área contable — no subir datos reales, ni archivos personales (PDFs de brief, notas del alumno) al repo.
