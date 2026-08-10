# Monitoreo y Alertas — Sistema de Dos Niveles

Cuando la app crashea o tiene un error técnico, se genera automáticamente un proceso de notificación en dos niveles.

## Nivel 1: Alerta Inmediata (María Daniela Salinas)

**Cuándo**: inmediatamente después de que ocurra el error
**Quién recibe**: mdani6010@gmail.com
**Contenido del correo**:
- Hora exacta del error (ISO timestamp)
- Tipo de error (ej. ValueError, KeyError)
- Mensaje de error + stack trace completo
- URL de la app donde ocurrió
- Archivo y línea de código donde falló

**Acción esperada**: verificar y corregir el error, o reportarlo al equipo técnico si es un problema de infraestructura.

## Nivel 2: Escalación a Gerencia (>1 día sin resolver)

**Cuándo**: si el error no se resuelve en más de 24 horas
**Quién recibe**: eduardo.silva.h@gmail.com (Gerencia de Contabilidad)
**Contenido del correo**: resumen del error + solicitud de contactar a María Daniela

**Cómo se activa**:
```bash
# Ejecutar manualmente
python3 check_escalation.py

# O configurar como cron job diario (ej. 09:00 cada mañana)
0 9 * * * cd /ruta/al/proyecto && python3 check_escalation.py
```

## Archivo de Log

Todos los errores se guardan en `error.log`:
```
2026-08-10T19:30:45.123456 | ERROR | EXCEPCION:
Traceback (most recent call last):
  File "app.py", line 498, in <module>
    render_tablero()
  File "app.py", line 334, in render_tablero
    ...
KeyError: 'column_name'
```

El archivo se commitea a GitHub para auditoría + trazabilidad histórica.

## Configuración (Una única vez)

### En tu máquina local (para pruebas):

1. Obtén una contraseña de aplicación de Google:
   - Ve a https://myaccount.google.com/apppasswords
   - Selecciona "Mail" y "Windows (o tu SO)"
   - Google genera una contraseña de 16 caracteres

2. Crea `.streamlit/secrets.toml` (archivo local, nunca se commitea):
   ```toml
   GMAIL_USER = "mdani6010@gmail.com"
   GMAIL_APP_PASSWORD = "tu-contraseña-de-16-caracteres"
   APP_PASSWORD = "Semaforo-Contable-2026!"
   ```

### En Streamlit Cloud:

1. Ve a Settings → Secrets
2. Agrega la misma configuración:
   ```
   GMAIL_USER = "mdani6010@gmail.com"
   GMAIL_APP_PASSWORD = "tu-contraseña-de-16-caracteres"
   APP_PASSWORD = "Semaforo-Contable-2026!"
   ```

**Importante**: la contraseña de aplicación es diferente de tu contraseña de Gmail. Google la genera específicamente para apps que no pueden acceder a 2FA. Nunca uses tu contraseña real de Gmail.

## Verificar que funciona

### Prueba local:
```bash
streamlit run app.py
# (No debería haber errores si está todo bien)

# Para forzar un error de prueba:
python3 -c "import error_handler; error_handler.registrar_error(Exception, Exception('Error de prueba'), None)"
```

### Verificar escalación:
```bash
python3 check_escalation.py
# Salida esperada:
# ✓ No hay errores antiguos. Sistema en orden.
```

## Mantenimiento

- **Limpiar error.log periódicamente**: después de resolver un error, puedes truncar el archivo o eliminarlo para que no crezca indefinidamente
- **Revisar el log antes de cada push**: `git log error.log` para ver qué errores se registraron en el último período
- **Actualizar emails** si cambia quién es María Daniela o el Gerente de Contabilidad: editar `error_handler.py` líneas EMAIL_NIVEL_1 y EMAIL_NIVEL_2

---

**Responsable del monitoreo**: María Daniela Salinas  
**Escalación**: Gerencia de Contabilidad  
**Documentación completa**: ver `prd-v2.md` sección "Monitoreo y Alertas"
