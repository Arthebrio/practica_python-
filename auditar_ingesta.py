"""
================================================================================
🔍 AUDITOR DE INGESTA DE TESIS (EL INSPECTOR DE CALIDAD)
================================================================================
Revisa las tesis recién insertadas en la base local para asegurar que:
  1. No tengan campos críticos vacíos (rubro, resumen, embedding).
  2. Tengan el embedding_512 generado (o avise si falta).

Uso:
    python auditar_ingesta.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

DB_LOCAL = {
    "dbname": os.getenv("DB_NAME", "practica_legal"),
    "user": os.getenv("DB_USER", "agr"),
    "password": os.getenv("DB_PASSWORD", "6419"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}

def log(msg, tipo="info"):
    iconos = {"info": "ℹ️ ", "ok": "✅", "warn": "⚠️ ", "err": "❌"}
    print(f"{iconos.get(tipo, '')} {msg}")

def auditar():
    print("=" * 70)
    print("🔍 INICIANDO AUDITORÍA DE CALIDAD (ÚLTIMAS 24 HORAS)")
    print("=" * 70)
    
    try:
        conn = psycopg2.connect(**DB_LOCAL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
    except Exception as e:
        log(f"No se pudo conectar a la base local: {e}", "err")
        sys.exit(1)

    # Consulta 1: ¿Cuántas tesis entraron hoy?
    # Buscamos las que tengan created_at en el último día
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM jurisprudencias
        WHERE created_at >= NOW() - INTERVAL '1 day';
    """)
    total_nuevas = cur.fetchone()["total"]
    
    if total_nuevas == 0:
        log("No se detectaron tesis nuevas en las últimas 24 horas.", "warn")
        conn.close()
        return

    log(f"Se detectaron {total_nuevas} tesis nuevas para auditar.", "info")
    print()

    # Consulta 2: Buscar campos vacíos o nulos en las tesis nuevas
    cur.execute("""
        SELECT registro_digital, rubro, resumen_ia, embedding
        FROM jurisprudencias
        WHERE created_at >= NOW() - INTERVAL '1 day'
          AND (
              rubro IS NULL OR TRIM(rubro) = '' OR
              resumen_ia IS NULL OR TRIM(resumen_ia) = '' OR
              embedding IS NULL
          );
    """)
    corruptas = cur.fetchall()
    
    # Consulta 3: ¿Cuántas no tienen el embedding_512?
    cur.execute("""
        SELECT COUNT(*) AS sin_512
        FROM jurisprudencias
        WHERE created_at >= NOW() - INTERVAL '1 day'
          AND embedding_512 IS NULL;
    """)
    sin_512 = cur.fetchone()["sin_512"]

    # --- REPORTE ---
    print("-" * 70)
    if len(corruptas) > 0:
        log(f"¡ALERTA! Se encontraron {len(corruptas)} tesis con campos vacíos:", "err")
        for t in corruptas:
            log(f"  - Reg {t['registro_digital']}: rubro={'X' if not t['rubro'] else 'OK'}, "
                f"resumen={'X' if not t['resumen_ia'] else 'OK'}, "
                f"embedding={'X' if not t['embedding'] else 'OK'}", "err")
    else:
        log("Todas las tesis nuevas tienen rubro, resumen y embedding completos.", "ok")

    if sin_512 > 0:
        log(f"Hay {sin_512} tesis sin embedding_512.", "warn")
        log("El script 'subir_a_supabase.py' se encargará de rellenarlas automáticamente.", "info")
    else:
        log("Todas las tesis nuevas ya tienen su embedding_512.", "ok")

    print("-" * 70)
    
    if len(corruptas) == 0:
        print("\n✅ AUDITORÍA EXITOSA: Los datos están limpios y listos para subir.")
    else:
        print("\n❌ AUDITORÍA FALLIDA: Revisa los errores antes de subir a Supabase.")
        
    conn.close()

if __name__ == "__main__":
    auditar()