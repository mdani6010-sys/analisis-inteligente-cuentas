# Análisis Inteligente de Cuentas — Resumen para Seguridad TI y Legal

**Objetivo de este documento**: dar la información mínima necesaria para autorizar (o rechazar)
el uso de este tablero con datos reales de la empresa. 1 página, sin tecnicismos.

## Qué es

Un tablero web (Streamlit) que revisa movimientos contables y marca posibles errores
(documentos duplicados, saldos con signo invertido, partidas abiertas hace mucho tiempo,
diferencias entre el auxiliar y el balance). Lo usa el equipo de Contabilidad para acelerar
la revisión mensual. Detalle completo del proyecto: `prd-v2.md` en este mismo repositorio.

## Dónde corre

- **Hosting**: Streamlit Community Cloud (servicio de Streamlit / Snowflake, EE.UU.).
- **Código**: público en GitHub — el código en sí no contiene datos, solo lógica.
- **Datos**: NO hay base de datos. El archivo que un analista sube se procesa en memoria
  durante esa sesión y se descarga como Excel. No queda guardado en el servidor entre usos.

## Qué datos entran

Un archivo Excel/CSV exportado de SAP (FBL3N) con: fecha, monto, moneda, glosa, centro de
costo, referencia y cuenta contable — sin datos personales de clientes ni empleados, es
información contable de la empresa (montos y cuentas).

## Qué pasa con esos datos, paso a paso

1. El analista sube el archivo desde su navegador.
2. El archivo viaja (cifrado, HTTPS) a los servidores de Streamlit Cloud.
3. Se procesa ahí — filtros y sumas, nada de IA externa ni envío a otro servicio.
4. El resultado se muestra en pantalla y se puede descargar como Excel.
5. Al cerrar la sesión, los datos subidos no quedan almacenados en el servidor.

## Riesgos que identificamos nosotros mismos (no esperamos a que los encuentren)

- Los datos SÍ salen de la infraestructura de la empresa mientras se procesan (aunque no
  queden guardados). Esto requiere evaluación de Seguridad TI antes de usar con datos reales.
- El acceso a la URL tiene una clave interina compartida entre los 3 analistas autorizados
  (ver lista en `prd-v2.md`, sección Gobernanza) — no es un login individual con auditoría
  por usuario. Es una mitigación temporal, no una solución definitiva.
- No hay cifrado de los datos "en reposo" porque no hay reposo: no se guardan.

## Qué pedimos

- Confirmar si este flujo (datos saliendo a un proveedor cloud externo, sin almacenamiento
  persistente) cumple con la política de seguridad de la información de la empresa.
- Indicar si se requiere algún control adicional (ej. acuerdo de confidencialidad con
  Streamlit/Snowflake, anonimizar montos, restringir a un ambiente interno) antes de
  autorizar su uso con datos reales de cierre contable.

**Mientras no haya respuesta**: el tablero solo se usa con datos ficticios de ejemplo.

---
Responsable: María Daniela Salinas (dueña del sistema) · Escala: Gerente de Contabilidad
