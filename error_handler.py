"""
Manejo centralizado de errores y alertas.
- Envía correos a Nivel 1 (María Daniela) cuando hay un error técnico
- Guarda en error.log para auditoría y escalación manual a Nivel 2 (Gerencia)
"""
import logging
import smtplib
import traceback
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import streamlit as st

CARPETA_PROYECTO = Path(__file__).parent
ARCHIVO_LOG = CARPETA_PROYECTO / "error.log"

# Configurar logger que escriba a archivo
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(ARCHIVO_LOG, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

EMAIL_NIVEL_1 = "mdani6010@gmail.com"
EMAIL_NIVEL_2 = "eduardo.silva.h@gmail.com"


def enviar_correo_error(asunto, cuerpo, destinatario):
    """Envía correo SMTP usando Gmail (requiere contraseña de aplicación en st.secrets)."""
    try:
        smtp_user = st.secrets.get("GMAIL_USER", EMAIL_NIVEL_1)
        smtp_pass = st.secrets.get("GMAIL_APP_PASSWORD")

        if not smtp_pass:
            logger.error(f"No se configuró GMAIL_APP_PASSWORD en st.secrets — no se envió correo a {destinatario}")
            return False

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = destinatario
        msg["Subject"] = asunto
        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, destinatario, msg.as_string())

        logger.info(f"Correo enviado a {destinatario}: {asunto}")
        return True
    except Exception as e:
        logger.error(f"Error al enviar correo: {e}")
        return False


def registrar_error(exc_type, exc_value, exc_traceback, url_app=None):
    """
    Registra un error en error.log y envía correo de alerta a Nivel 1.

    Args:
        exc_type: tipo de excepción
        exc_value: valor de la excepción
        exc_traceback: traceback
        url_app: URL de la app en vivo (opcional)
    """
    timestamp = datetime.now().isoformat()
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    # Registrar en archivo
    logger.error(f"EXCEPCION:\n{tb_str}")

    # Preparar correo a Nivel 1
    cuerpo_nivel_1 = f"""
⚠️ ERROR TECNICO EN TABLERO ANALISIS INTELIGENTE DE CUENTAS

HORA: {timestamp}
TIPO DE ERROR: {exc_type.__name__}
MENSAJE: {exc_value}

UBICACION:
{tb_str}

URL DE LA APP: {url_app or "No disponible"}

SIGUIENTE PASO:
- Revisa el archivo error.log en el repositorio GitHub
- Si el error persiste después de 1 día, se escalará a Gerencia de Contabilidad
- Responde a este correo confirmando que viste el alerta

---
Este es un correo automático generado por Análisis Inteligente de Cuentas.
    """.strip()

    enviar_correo_error(
        asunto="🔴 ALERTA: Error técnico en Tablero de Cuentas",
        cuerpo=cuerpo_nivel_1,
        destinatario=EMAIL_NIVEL_1,
    )


def verificar_escalacion():
    """
    Verifica si hay errores en error.log de más de 1 día atrás.
    Usa esto con check_escalation.py o como GitHub Action diario.

    Returns:
        bool: True si hay errores antiguos que deben escalarse
    """
    if not ARCHIVO_LOG.exists():
        return False

    try:
        lineas_error = [l for l in ARCHIVO_LOG.read_text(encoding="utf-8").split("\n") if "EXCEPCION" in l]
        if not lineas_error:
            return False

        # Parsear timestamp de la primera línea de error (más antigua)
        # Formato esperado: "2026-08-10T19:30:45.123456"
        primera_linea = lineas_error[0]
        timestamp_str = primera_linea.split(" | ")[0]
        timestamp_error = datetime.fromisoformat(timestamp_str)
        tiempo_transcurrido = datetime.now() - timestamp_error

        return tiempo_transcurrido.days >= 1
    except Exception as e:
        logger.error(f"Error al verificar escalación: {e}")
        return False


def escalar_a_nivel_2():
    """Envía correo de escalación a Gerencia de Contabilidad."""
    if not ARCHIVO_LOG.exists():
        return False

    contenido_log = ARCHIVO_LOG.read_text(encoding="utf-8")
    cuerpo_nivel_2 = f"""
🔴 ESCALADA: Errores técnicos sin resolver en Tablero de Cuentas (>1 día)

El sistema de Análisis Inteligente de Cuentas ha presentado errores técnicos que no han sido resueltos en más de 1 día.

DETALLES DEL ERROR (últimas líneas del log):
---
{contenido_log[-1500:]}
---

ACCION REQUERIDA:
1. Contactar a María Daniela Salinas (mdani6010@gmail.com) para verificar estado
2. Si la app sigue inactiva, contactar al área de TI
3. Revisar el repositorio GitHub: github.com/mdani6010-sys/analisis-inteligente-cuentas

---
Correo de escalación automática. Generado por sistema de monitoreo.
    """.strip()

    return enviar_correo_error(
        asunto="🔴 ESCALADA: Errores en Tablero de Cuentas (>1 día sin resolver)",
        cuerpo=cuerpo_nivel_2,
        destinatario=EMAIL_NIVEL_2,
    )
