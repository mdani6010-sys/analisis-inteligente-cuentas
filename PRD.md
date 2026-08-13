# PRD - Análisis Inteligente de Cuentas v2

## 1. Resumen Ejecutivo
Sistema de detección de anomalías contables + reconciliación de auxiliares vs F.01 (estado financiero). Automatiza el análisis de cuentas contables para identificar inconsistencias sin usar modelos de IA en tiempo de ejecución.

**Versión**: 2.0 (Reconciliación)  
**Dueño**: María Daniela Salinas (Analista Contable Senior)  
**Escalación**: Gerencia de Contabilidad  
**Fecha**: 2025-08-12

## 2. Problema
- Analysts manualmente revisan 10+ cuentas contables (10h/mes cada uno, 3 analysts = 30h/mes)
- Errores humanos: duplicaciones, saldos invertidos, partidas antiguas no conciliadas
- Costo: $2.7M CLP/año (10h × 3 × $7.5k/h, 40h/week en Chile)
- **Nuevo**: No hay validación de que el total del auxiliar concuerde con el saldo en F.01

## 3. Solución
Dashboard Streamlit que:
1. **Carga** movimientos (CSV/XLSX) + balance F.01 con parsing flexible (SAP, Excel, etc.)
2. **Detecta** 4 anomalías: duplicidades, saldos contrarios, antiguedad >90d, diferencias de cuadratura
3. **Reconcilia** total auxiliar vs saldo F.01 por cuenta
4. **Exporta** Excel con resumen, detalle, compensaciones
5. **Monitorea** errores técnicos con 2 niveles de alertas (inmediata + escalación >1d)

## 4. Formato de Entrada
Acepta:
- **Movimientos**: CSV/XLSX con columnas (flexible): fecha documento, importe, moneda, glosa, centro costo, referencia, cuenta
- **Balance F.01**: CSV/XLSX SAP export (BALANCE MLL PR format) con: Cuenta, Saldo Debe, Saldo Haber, Moneda
- **Encoding**: Latin-1, UTF-8, CP1252 (auto-detect)

## 5. Lógica de Detección
### Duplicidades
- % de glosas duplicadas > 2% = Amarillo, > 3% = Rojo

### Saldos Contrarios
- >40% partidas con signo opuesto = Amarillo, >75% = Rojo

### Antiguedad
- >20% partidas >90 días = Amarillo

### Diferencia de Cuadratura
- Total auxiliar vs Saldo F.01 > $500 = Moderado, > $50k = Grave

## 6. Formato de Salida
**Excel (5 hojas)**:
1. Resumen: cuenta, anomalías, estado (semáforo)
2. Detalle Limpio: sin datos faltantes
3. Detalle Completo: con valores nulos marcados
4. Partidas Compensadas: pares de monto opuesto (crédito-débito)
5. Reconciliación: cuenta, total auxiliar, saldo F.01, diferencia

## 7. Monitoreo & Alertas (2 Niveles)
**Nivel 1** (inmediata): Email a María Daniela (mdani6010@gmail.com)  
**Nivel 2** (si >1 día sin resolver): Email a Gerencia de Contabilidad (eduardo.silva.h@gmail.com)  

Usa SMTP Gmail con app-password (via st.secrets: GMAIL_USER, GMAIL_APP_PASSWORD)

## 8. Guardrails / Limitaciones
1. **No usa IA/LLM en tiempo de ejecución**: Reglas fijas + lógica contable, no ML
2. **No persiste datos**: Procesamiento en memoria, no almacenamiento en BD
3. **Usuarios anónimos**: Todos comparten clave "Semaforo-Contable-2026!" (interim, no login per-user)
4. **Datos externos**: Carga manual (no API automática) - requiere aprobación Seguridad TI + Legal
5. **Errores se notifican**: 2 niveles de alertas, auditoría en error.log
6. **Reconciliación manual**: No valida si F.01 es correcta, solo detecta discrepancias

## 9. Economía
- **Ahorro**: 10h/mes × 3 analysts × $7.5k/hora = $2.7M CLP/año
- **Costo**: $0 por corrida (Streamlit Cloud, no infraestructura)
- **Payback**: Inmediato
- **Próxima fase**: Piloto 2 meses con Pluxee, si éxito → despliegue empresa

## 10. Métricas de Éxito (Confiabilidad S19)
- ✓ Detección: 100% en blind evaluation (12/12 test accounts)
- ✓ Funciona de verdad: Probado con datos reales (BALANCE MLL PR, 234101 movimientos)
- ✓ No suena a magia: Reglas explícitas, trazables a umbral exacto
- ✓ Recuperación de fallos: Alertas automáticas, escalación a 24h

## 11. Riesgos & Mitigación
| Riesgo | Impacto | Mitigación |
|--------|---------|-----------|
| Datos no persistidos | Pérdida si crash | Exporta Excel cada sesión |
| Usuarios anónimos | Seguridad débil | Login per-user en v3 (futuro) |
| Errores no detectados | Falsos negativos | Blind eval 12/12, alertas nivel 1-2 |
| F.01 incorrecta | Reconciliación falsa | Comparación manual con Sistema |
| Carga manual | Baja adopción | Integración API SAP en v3 |

## 12. Casos de Uso
1. **Audit diario**: María Daniela carga auxiliar + F.01 → ve anomalías en 2 min
2. **Cierre mensual**: Valida que todos auxiliares cuadren con balance antes de enviar
3. **Investigación**: Filtra cuenta, ve partidas duplicadas/antiguas/sospechosas
4. **Escalación**: Error técnico → alerta Nivel 1 → si perdura → Nivel 2 a Gerencia

## 13. Hoja de Ruta
- **v2.0 (HOY)**: Reconciliación + parsing flexible
- **v2.1**: Outlier detection (statistical anomalies)
- **v3.0**: Login per-user + API SAP automática
- **v4.0**: ML basado en histórico (si datos suficientes)

---
**Última actualización**: 2025-08-12  
**Próxima revisión**: 2025-09-12
