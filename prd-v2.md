# PRD v2 — Análisis Inteligente de Cuentas (Tablero Piloto)

**Estado:** A — listo para construir

1. **Problema** (1 frase):
   El análisis de cuentas contables (conciliaciones, duplicidades, saldos contrarios, partidas antiguas) se hace manualmente en Excel, consumiendo mucho tiempo y generando errores no detectados a tiempo.

2. **Usuario** (para quién):
   Analistas Contables Senior y Analistas de Estados Financieros (principal). Supervisores Contables, Auditoría Interna, Finanzas y Control de Gestión (secundario).

3. **Solución / propuesta de valor**:
   Un tablero interactivo (Streamlit) que carga un Excel/CSV con movimientos contables, detecta automáticamente 4 tipos de anomalías, las muestra con un sistema de semáforo (verde/amarillo/rojo/negro) y genera comentarios explicativos basados en reglas — todo exportable a Excel. Se publica con una URL propia (Streamlit Community Cloud) para que otros usuarios lo usen sin instalar nada, y el código vive en GitHub para tener historial de versiones.

4. **Decisiones con evidencia** (qué dicen tus datos):
   Aún no hay datos reales — se parte con **datos ficticios** (3000 registros, últimos 3 meses + algunas fechas más antiguas intercaladas) para construir y probar el piloto antes de conectar con SAP real.

5. **Métrica de éxito** (verificable):
   - El tablero detecta correctamente las 4 anomalías sobre el set de datos ficticios (verificable comparando contra los casos que se insertaron a propósito).
   - Los comentarios generados por reglas son coherentes con cada anomalía (no genéricos ni inventados).
   - El Excel exportado refleja exactamente lo mostrado en el tablero.

6. **Guardrails / estilo**:
   - No inventar ni suponer: los comentarios se basan solo en reglas fijas sobre los datos, nunca en inferencias no verificables.
   - Ser crítico: alertar activamente cuando falten datos necesarios para evaluar una anomalía (ej. columna vacía, fecha inválida).
   - Marcar explícitamente cualquier caso dudoso en vez de omitirlo.

7. **Si automatizas** — disparador + pasos:
   Disparador: el usuario sube un archivo Excel/CSV al tablero.
   Pasos: 1) cargar y validar columnas mínimas → 2) correr las 4 detecciones de anomalías → 3) asignar semáforo por fila/cuenta → 4) generar comentario por regla → 5) mostrar resumen ejecutivo → 6) permitir exportar a Excel.

8. **Alcance** — qué SÍ / qué NO (piloto):
   **SÍ:**
   - Datos ficticios (3000 filas: fecha documento, monto, moneda, glosa, centro de costo, referencia, cuenta contable)
   - Detección de las 4 anomalías: duplicidades, saldos contrarios, partidas antiguas (>90 días), diferencias de cuadratura
   - Sistema de semáforos (verde/amarillo/rojo/negro)
   - Comentarios explicativos basados en reglas (sin IA/API de pago)
   - Alertas de datos faltantes o dudosos
   - Exportar resultados a Excel

   **NO (por ahora):**
   - Conexión real a SAP (FBL3N / F.01)
   - Comentarios generados con IA vía API (se evalúa a futuro, tiene costo)
   - Login / usuarios / permisos
   - Comparación automática contra el balance F.01 real
   - Rearmar como Frontend (Netlify) + Backend (Supabase) — se evaluó y se descartó por ahora: Streamlit ya cumple frontend+backend en uno, y alcanza para que otros usuarios lo usen vía URL. Se reconsidera si el proyecto necesita guardar datos persistentes entre sesiones (ahí sí conviene Supabase).

9. **Publicación y versionado**:
   - **Código fuente**: repositorio en GitHub — cada cambio queda como un commit, se puede volver a una versión anterior si algo se rompe.
   - **Despliegue**: Streamlit Community Cloud, conectado directo al repo de GitHub. Cada vez que se sube un cambio (`git push`), la app publicada se actualiza sola.
   - **Acceso**: URL pública gratuita tipo `tu-usuario-nombre-app.streamlit.app`, sin login (cualquiera con el link entra).

---
**Próximo paso** (lo más chico que demuestra valor):
Tablero construido y probado localmente ✅. Sigue: crear cuenta de GitHub (si no tiene), subir el proyecto a un repositorio, y publicarlo en Streamlit Community Cloud para que otros usuarios entren por URL.

**Qué falta para empezar** (datos / insumos):
- Cuenta de GitHub (la crea el alumno; el agente no puede crear cuentas por él).
- Confirmar el nombre del repositorio.
- Cuando haya datos reales de SAP (FBL3N/F.01), se reemplaza el dataset ficticio por el real sin cambiar la lógica del tablero.
