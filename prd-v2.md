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

5. **Métrica de éxito** (verificable) — ✅ verificado con `test_deteccion.py`:
   - El tablero detecta correctamente las 4 anomalías sobre el set de datos ficticios: **12/12 cuentas (100%)** coinciden con la respuesta correcta (`datos/ground_truth.json`, generada junto con los datos). Evaluación ciega: primero corre la detección, recién después se compara contra la respuesta conocida.
   - Los comentarios generados por reglas son coherentes con cada anomalía (no genéricos ni inventados).
   - El Excel exportado refleja exactamente lo mostrado en el tablero.
   - Correr `python test_deteccion.py` después de cualquier cambio a la lógica de detección, para confirmar que sigue en 100% antes de subir el cambio.

6. **Guardrails / estilo** — auditados con revisión adversarial (ver nota al final):
   - No inventar ni suponer: los comentarios se basan solo en reglas fijas sobre los datos, nunca en inferencias no verificables. ✅
   - Ser crítico: alertar activamente cuando falten datos necesarios para evaluar una anomalía (ej. columna vacía, fecha inválida). ✅ (fecha inválida corregida — antes tumbaba la app, ver nota).
   - Marcar explícitamente cualquier caso dudoso en vez de omitirlo. ✅ (misma corrección).
   - **Ajustado a un perfil senior** (analista contable con +13 años de experiencia): sin explicaciones básicas de contabilidad ni lenguaje introductorio — el comentario va directo al hallazgo y su magnitud.
   - Cada comentario debe ser trazable a la regla exacta que lo generó (ej. "tasa de duplicidad > 3%"), para que el analista pueda auditar la lógica y no tenga que confiar a ciegas. ✅ (antes el comentario mostraba solo el conteo, no el umbral cruzado — corregido).
   - El sistema no reemplaza el criterio profesional del analista: es apoyo para priorizar dónde mirar primero, no un veredicto final.
   - **Umbrales calibrados con datos ficticios, no reales**: los porcentajes que definen el semáforo (ej. duplicidad > 3%, antigüedad > 20%) se ajustaron mirando cómo se comportaba el dataset sintético. Antes de usarlo en producción, los umbrales deben recalibrarse con datos reales. ⚠ **Parcialmente mitigado**: el tablero ahora sí avisa cuando un caso es "raro" — ver el punto siguiente.
   - **Aviso de confiabilidad por caso atípico o muestra chica** ✅: cada cuenta se compara contra las demás del mismo archivo (rango intercuartílico sobre tasa de duplicidad y de antigüedad); si su patrón se sale de lo común, o si tiene muy pocas filas (<10) para que un porcentaje sea confiable, el comentario suma un aviso `⚠` explícito — sin cambiar el color del semáforo, para no ocultar el hallazgo real pero sí bajarle la confianza. Resuelve directamente el riesgo de "el sistema suena igual de seguro sepa o no sepa" (práctica del módulo, "Momento de la duda").
   - **Naturaleza deudora/acreedora confirmable, no asumida en silencio** ✅: por defecto se sigue infiriendo por el primer dígito de la cuenta (supuesto, igual que antes), pero ahora el analista puede corregirla y marcarla "confirmada" en una tabla editable dentro del tablero. Mientras una cuenta no esté confirmada, cualquier "saldo contrario" que salga para ella queda etiquetado en el comentario como basado en un supuesto sin verificar — nunca se da por bueno en silencio.

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
   - Exportar resultados a Excel: **Detalle_Limpio** (con columna `antiguedad_dias` y `monto_duplicado`, y con las partidas que se compensan entre sí ya sacadas), **Partidas_Compensadas** (mismo monto, signo contrario, misma cuenta — se anulan, pero quedan trazables con `par_compensacion` para auditarlas), **Detalle_Completo** (todo, sin filtrar) y **Datos_faltantes**
   - Tabla editable para confirmar/corregir la naturaleza (deudora/acreedora) por cuenta, en vez de confiar ciegamente en el supuesto por prefijo
   - Aviso `⚠` de confiabilidad por muestra chica (<10 filas) o patrón atípico frente a otras cuentas del mismo archivo (no cambia el color del semáforo, solo baja la confianza del hallazgo)

   **NO (por ahora):**
   - Conexión real a SAP (FBL3N / F.01)
   - Comentarios generados con IA vía API (se evalúa a futuro, tiene costo)
   - Login / usuarios / permisos
   - Comparación automática contra el balance F.01 real
   - Rearmar como Frontend (Netlify) + Backend (Supabase) — se evaluó y se descartó por ahora: Streamlit ya cumple frontend+backend en uno, y alcanza para que otros usuarios lo usen vía URL. Se reconsidera si el proyecto necesita guardar datos persistentes entre sesiones (ahí sí conviene Supabase).

9. **Publicación y versionado** — ✅ hecho:
   - **Código fuente**: [github.com/mdani6010-sys/analisis-inteligente-cuentas](https://github.com/mdani6010-sys/analisis-inteligente-cuentas) — cada cambio queda como un commit, se puede volver a una versión anterior si algo se rompe.
   - **App en vivo**: [mdani6010-sys-analisis-inteligente-cuentas-app-4hvlat.streamlit.app](https://mdani6010-sys-analisis-inteligente-cuentas-app-4hvlat.streamlit.app/) — sin login, cualquiera con el link entra.
   - **Despliegue**: Streamlit Community Cloud, conectado directo al repo de GitHub (rama `main`, archivo `app.py`). Cada vez que se sube un cambio (`git push`), la app publicada se actualiza sola en 1-2 minutos.

10. **Gobernanza**:
    - **Quién puede usarlo**: María Daniela Salinas, Grace Rebolledo y Alejandra Cabrera (analistas contables autorizadas). ✅ **Mitigado parcialmente**: la app ahora pide una clave de acceso interina compartida entre las 3 (configurada en Streamlit Cloud, nunca en el código público). Sigue sin ser un login individual con auditoría por usuario — es una barrera básica, no una solución definitiva (ver plan de acción, punto 3, sección 12).
    - **Dueño del sistema**: María Daniela Salinas (Analista Contable). Decide si el proceso cambia o se detiene. Si cambia el dueño, es el **Gerente de Contabilidad** quien asigna a la nueva persona responsable.
    - **Quién se entera si falla**: María Daniela Salinas — el aviso le llega directamente a ella (no queda solo registrado en el Excel o en GitHub sin que nadie lo vea).
    - **Quién autoriza escalarlo**: el **Gerente de Contabilidad** da el visto bueno para que el tablero se use fuera del equipo actual (ej. que lo use Auditoría Interna u otra área).
    - **Rol del sistema vs. rol humano**: el tablero **detecta y prioriza** (semáforo + comentarios por reglas); **no decide ni ejecuta** ninguna acción contable. La decisión final y el ajuste en el sistema contable siempre los hace el analista humano.
    - **Trazabilidad**: cada análisis queda respaldado en el Excel exportado (fecha, reglas aplicadas, resultado por cuenta) — sirve como evidencia ante auditoría interna o externa. Los cambios al código y la lógica de detección quedan versionados en GitHub (quién cambió qué y cuándo).
    - **Manejo de resultados**: no hay base de datos ni almacenamiento en servidor — cada análisis se descarga como Excel y cada analista guarda su propia copia como respaldo. Los datos ficticios/reales que se suben al tablero no quedan guardados en Streamlit Cloud entre sesiones.
    - **Límite explícito**: el sistema no debe usarse como única fuente para cerrar o certificar un período contable — es una herramienta de apoyo para acelerar la revisión, no un reemplazo del proceso de cierre.

11. **Ficha económica** (estimación con datos entregados por el usuario, no verificada contra nómina real):

    | # | Pregunta | Respuesta |
    |---|---|---|
    | 1 | Qué tarea reemplaza | Revisión manual en Excel de movimientos contables para detectar duplicidades, saldos contrarios, partidas antiguas (>90 días) y diferencias de cuadratura contra F.01. |
    | 2 | Cuánto demora hoy a mano | 30-60 min por cuenta, ~10 cuentas por analista → 5 a 10 horas/mes por analista (revisión mensual). |
    | 3 | Cuánto demora con el agente | ~2-3 minutos de punta a punta — procesa las 10 cuentas en una sola corrida (no cuenta por cuenta). Procesamiento puro medido: 0.57s para 3000 filas / 12 cuentas. |
    | 4 | Cuánto cuesta una corrida completa | $0 — reglas fijas sin IA de pago, hosting gratuito (Streamlit Community Cloud). |
    | 5 | Horas liberadas al mes | ~10 horas/analista (usando el extremo superior del rango; el tiempo del agente, 2-3 min, es marginal frente al ahorro). |

    **Conversión a dinero** (supuestos: tarifa día $60.000 CLP para Analista Contable senior, jornada de 8 horas/día, equipo de 3 analistas):
    - Valor hora: $60.000 ÷ 8 = **$7.500 CLP/hora**
    - Horas liberadas (equipo): 10 horas × 3 analistas = **30 horas/mes**
    - **Valor mensual liberado: $225.000 CLP**
    - **Valor anual liberado: $2.700.000 CLP**

12. **Debrief — interrogatorio del "gerente escéptico"** (ejercicio de pitch, práctica del módulo) y plan de acción:

    | # | Pregunta que destapó el punto débil | Por qué es débil | Acción concreta | Responsable | Estado |
    |---|---|---|---|---|---|
    | 1 | ¿Por qué se llama "Inteligente" si no corre IA? | El nombre sugiere IA; el producto usa reglas fijas. Nunca se justificó bien en el interrogatorio. | Aclarado explícitamente en el subtítulo de la app, el README y este PRD: "Inteligente" = lógica contable sistemática, no modelo de IA. | María Daniela Salinas | ✅ Hecho |
    | 2 | ¿Ya lo revisó Seguridad TI / Legal, dado que datos reales viajarían a un servidor externo (Streamlit/Snowflake)? | No se ha hecho esa revisión — hoy es un riesgo real, no solo teórico, en cuanto se suba un archivo real. | Documento de 1 página listo (`SEGURIDAD-Y-DATOS.md` en el repo) para llevar a Seguridad TI y Legal. La app ahora avisa explícitamente al subir un archivo propio que se necesita esa aprobación antes de usar datos reales. | María Daniela Salinas (redacta) / Gerente de Contabilidad (escala) | ⏳ Documento listo — falta la reunión y aprobación real, eso no lo puede hacer el agente |
    | 3 | ¿Quién responde si alguien sube datos reales sin autorización, antes de tener login? | Solo existe una política escrita (sección Gobernanza); no hay control técnico que la haga cumplir. | Clave de acceso interina implementada en la app (vía `st.secrets`, nunca en el código público) + lista de las 3 analistas autorizadas en Gobernanza. Login individual real queda como mediano plazo. | Gerente de Contabilidad (responsable del uso hasta login real) | ✅ Clave interina lista — falta que se configure el secreto en Streamlit Cloud (paso manual, no lo puede hacer el agente) |
    | 4 | Las horas liberadas, ¿en qué se convierten realmente? Sin datos medidos, dos veces. | La ficha económica ($2.7M CLP/año) es un supuesto, no una medición — no hay caso real que lo respalde todavía. | Correr un piloto de 1-2 meses con un analista real: medir tiempo real ahorrado y documentar en qué se usó ese tiempo. Revisar la ficha económica con ese dato. | María Daniela Salinas | ⏳ Pendiente — requiere un piloto real, no se puede simular |

    **Prioridad**: (2) y (3) primero — son riesgo real de la empresa hoy. (4) después, con el piloto medido. (1) resuelto.

---
**Próximo paso** (lo más chico que demuestra valor):
Tablero construido, probado y **publicado** ✅ (código en GitHub, app en vivo en Streamlit Cloud). Sigue: conseguir datos reales de SAP (aunque sea de una sola cuenta) para validar el tablero contra un caso real, no solo ficticio.

**Qué falta para empezar** (datos / insumos):
- Datos reales de SAP (FBL3N/F.01) — cuando estén, se reemplaza el dataset ficticio por el real sin cambiar la lógica del tablero.
