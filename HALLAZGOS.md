# Hallazgos - Análisis Cuenta 234101 (Datos Reales)

## Resumen Ejecutivo
El análisis de la cuenta 234101 con datos reales de Pluxee revela **anomalías GRAVES** que requieren investigación inmediata.

**Fecha de análisis**: 2025-08-12  
**Datos**: BALANCE MLL PR.csv + 234101 2025.xlsx (movimientos SAP)

---

## Anomalías Detectadas

### 1. Duplicidades [ROJO]
**Resultado**: 2,528 de 2,528 partidas duplicadas (100%)  
**Problema**: Todas las partidas tienen la MISMA glosa exacta:  
`&BUKRS - Valoracion por 20250131`

**Hipótesis**:
- Dato agregado/consolidado de SAP (no es un error, sino un reporte consolidado)
- Las partidas individuales se perdieron en la exportación
- Posible problema de exportación SAP donde solo se exportó la descripción del batch

**Acción recomendada**:
- Verificar con TI/SAP si 234101 2025.xlsx es un dump consolidado o detallado
- Pedir exportación "sin agregar" o "detail mode"

---

### 2. Antiguedad >90 Días [AMARILLO]
**Resultado**: 2,528 de 2,528 partidas (100%) mayores a 90 días  
**Fecha más reciente**: 2025-01-31 (201 días atrás desde hoy 2025-08-12)

**Problema**: Todas las partidas son de hace 7+ meses sin actualización.

**Hipótesis**:
- Datos históricos no conciliados
- Auxiliar no se actualiza desde enero 2025
- Posible cuenta en suspensión o cerrada operativamente

**Acción recomendada**:
- Verificar si la cuenta 234101 está activa en febrero-agosto 2025
- Pedir movimientos más recientes para validación

---

### 3. Saldos Contrarios [AMARILLO]
**Resultado**: 1,237 de 2,528 partidas (48.9%) con signo negativo

**Detalle**:
- Positivos: 1,291 partidas (51.1%)
- Negativos: 1,237 partidas (48.9%)

**Problema**: Distribución casi perfectamente inversa sugiere compensaciones.

**Hipótesis**:
- Partidas de débito-crédito ya compensadas, no pendientes
- Movimientos de ajuste contable (reversiones, amortizaciones)

**Acción recomendada**:
- Filtrar partidas compensadas (monto opuesto, misma fecha)
- Verificar si son ajustes válidos o errores contables

---

### 4. Diferencia de Cuadratura [ROJO GRAVE]
**Resultado**:
- Total auxiliar: $639,108,696.00
- Saldo F.01: $6,793,771.71
- **Diferencia: $632,314,924.29 (9,307%)**

**Problema**: El auxiliar es 94x más grande que el saldo en balance.

**Hipótesis**:
- Auxiliar incluye movimientos no registrados en F.01
- F.01 es de otro período (cierre anterior)
- Problema en mapeo de datos (divisa, conversión, etc.)
- Error en exportación SAP (multiplicidad de datos)

**Acción recomendada**:
- Verificar fechas de corte en F.01 vs auxiliar
- Validar si hay divisas diferentes (CLP vs USD)
- Comparar totales manuales en SAP (FBL3N vs BALANCE)
- Investigar si hay registros de compensación no aplicados

---

## Conclusiones

### Lo que Funciona Bien
✓ Sistema detecta anomalías REALES en datos REALES  
✓ Identifica patrones sospechosos (100% duplicidad, todas >90d)  
✓ Reconciliación funciona y expone discrepancias graves  
✓ Parser flexible maneja formato SAP correctamente  

### Lo que Requiere Acción
✗ Datos de 234101 parecen un consolidado, no un auxiliar transaccional  
✗ Diferencia de cuadratura es tan grande que sugiere error de exportación  
✗ Todas las partidas son de enero → posible datos obsoletos  

### Recomendación Inmediata
**No se recomienda usar esta cuenta como piloto hasta que:**
1. Se valide formato y fechas de exportación SAP
2. Se consiga auxiliar transaccional (no consolidado) con movimientos recientes
3. Se verifique que F.01 es del mismo período que el auxiliar

**Sugerencia**: Usar otra cuenta (ej: 100011) que tenga más reciente distribución de movimientos.

---

## Datos Técnicos

| Métrica | Valor |
|---------|-------|
| Movimientos totales | 2,528 |
| Movimientos cuenta 234101 | 2,528 (100%) |
| Período | 2025-01-31 a 2025-01-31 |
| Glosas únicas | 1 |
| Monedas | CLP |
| Días desde último movimiento | 201 |
| Total acumulado | $639,108,696.00 |
| Balance según F.01 | $6,793,771.71 |
| Diferencia | $632,314,924.29 |

---

**Contacto para validación**: María Daniela Salinas (mdani6010@gmail.com)  
**Fecha sugerida de revisión**: 2025-08-13
