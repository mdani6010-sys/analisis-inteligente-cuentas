# Análisis Inteligente de Cuentas

Dashboard Streamlit para detección de anomalías contables + reconciliación de auxiliares vs F.01.

## Inicio Rápido

```bash
pip install -r requirements.txt
streamlit run app.py
```

Contraseña: `Semaforo-Contable-2026!`

## Características

- 📥 **Carga flexible**: CSV/XLSX con auto-detección de formato (SAP, Excel, etc.)
- 🔍 **4 anomalías**: duplicidades, saldos contrarios, antiguedad, diferencia de cuadratura
- 💰 **Reconciliación**: total auxiliar vs saldo F.01 por cuenta
- 💾 **Exporta**: Excel con resumen, detalle, partidas compensadas
- 🚨 **Alertas**: 2 niveles si errores técnicos

## Archivos

- `app.py` - Dashboard Streamlit (entrada principal)
- `parsers.py` - Parser flexible para CSV/XLSX (detecta SAP exports)
- `PRD.md` - Especificación de requisitos
- `requirements.txt` - Dependencias Python

## Datos de Entrada

### Movimientos (Auxiliar)
CSV/XLSX con columnas (flexible):
- Fecha documento
- Importe
- Moneda
- Glosa/descripción
- Centro de costo
- Referencia
- Cuenta contable

### Balance (F.01)
CSV/XLSX SAP export:
- Cuenta de mayor
- Saldo Debe
- Saldo Haber
- Moneda

## Encoding
Auto-detecta: Latin-1, UTF-8, CP1252

## Notas
- Reglas sin IA/LLM en tiempo de ejecución (100% auditables)
- Procesamiento en memoria (no persiste datos)
- Email de alertas vía SMTP Gmail (config en `st.secrets`)
