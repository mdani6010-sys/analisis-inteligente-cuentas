#!/usr/bin/env python3
"""
Script para verificar si hay errores en error.log de >1 día y escalar a Nivel 2.

Uso:
  python3 check_escalation.py

Esto puede ejecutarse:
- Manualmente cada mañana (cron job local)
- Como GitHub Action diario
- Como parte de un script de monitoreo externo
"""
import sys
from error_handler import verificar_escalacion, escalar_a_nivel_2, ARCHIVO_LOG

if __name__ == "__main__":
    if not ARCHIVO_LOG.exists():
        print("✓ error.log no existe — no hay errores registrados.")
        sys.exit(0)

    print("Verificando si hay errores de >1 día...")
    if verificar_escalacion():
        print("⚠️  Se detectaron errores de más de 1 día sin resolver.")
        print("Enviando correo de escalación a Gerencia de Contabilidad...")
        if escalar_a_nivel_2():
            print("✓ Correo de escalación enviado a Gerencia de Contabilidad.")
            sys.exit(0)
        else:
            print("✗ Error al enviar correo de escalación.")
            sys.exit(1)
    else:
        print("✓ No hay errores antiguos. Sistema en orden.")
        sys.exit(0)
