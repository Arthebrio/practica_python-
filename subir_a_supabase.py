"""
================================================================================
🚀 SUBIR TESIS A SUPABASE
================================================================================
Sube N tesis de la base local a Supabase vía REST API.

Detecta automáticamente qué ya está en Supabase y sube solo las pendientes.
Genera un archivo de auditoría con los registros subidos.

Uso:
    python subir_a_supabase.py --cantidad 10
    python subir_a_supabase.py --cantidad 100
    python subir_a_supabase.py --cantidad 500
    python subir_a_supabase.py --dry-run
    python subir_a_supabase.py --dry-run --cantidad 50

Argumentos:
    --cantidad N     Cuántas tesis subir en esta corrida (por defecto: 100)
    --lote N         Tamaño del lote por petición (por defecto: 50)
    --dry-run        Simular sin subir nada
"""

import os
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
DB_LOCAL = {
    "dbname": os.getenv("DB_NAME", "practica_legal"),
    "user": os.getenv("DB_USER", "agr"),
    "password": os.getenv("DB_PASSWORD", "6419"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

CARPETA_LOGS = Path("output/migraciones")
CARPETA_LOGS.mkdir(parents=True, exist_ok=True)


# =============================================================================
# UTILIDADES
# =============================================================================
def log(msg, tipo="info"):
    iconos = {"info": "ℹ️ ", "ok": "✅", "warn": "⚠️ ", "err": "❌"}
    print(f"{iconos.get(tipo, '')} {msg}")


def formatear_tiempo(seg):
    if seg < 60:
        return f"{seg:.1f}s"
    return f"{int(seg // 60)}m {int(seg % 60)}s"


# =============================================================================
# CONEXIONES
# =============================================================================
def conectar_local():
    log("Conectando a la base local...")
    conn = psycopg2.connect(**DB_LOCAL)
    log("Base local OK", "ok")
    return conn


def conectar_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        log("Faltan SUPABASE_URL o SUPABASE_ANON_KEY en el .env", "err")
        sys.exit(1)
    log("Conectando a Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    log("Supabase OK", "ok")
    return client


# =============================================================================
# DETECTAR PENDIENTES
# =============================================================================
def obtener_registros_supabase(client):
    """Lee todos los registro_digital que ya están en Supabase."""
    log("Leyendo registros existentes en Supabase...")
    todos = []
    offset = 0
    while True:
        resp = (
            client.table("jurisprudencias")
            .select("registro_digital")
            .range(offset, offset + 999)
            .execute()
        )
        if not resp.data:
            break
        todos.extend(r["registro_digital"] for r in resp.data)
        if len(resp.data) < 1000:
            break
        offset += 1000
    log(f"Registros en Supabase: {len(todos)}", "ok")
    return set(todos)


def obtener_pendientes(conn, ya_en_supabase, cantidad):
    """Devuelve los próximos N registro_digital pendientes (de mayor a menor)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT registro_digital FROM jurisprudencias "
        "ORDER BY registro_digital DESC"
    )
    todos = [r[0] for r in cur.fetchall()]
    pendientes = [r for r in todos if r not in ya_en_supabase]
    return pendientes[:cantidad]


# =============================================================================
# CARGAR Y SUBIR
# =============================================================================
def cargar_tesis(conn, registros):
    """Lee las tesis completas de la BD local, listas para Supabase."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = """
        SELECT
            registro_digital,
            tipo,
            materia,
            expediente,
            fecha_publicacion::text AS fecha_publicacion,
            fecha_normalizada,
            epoca,
            instancia,
            rubro,
            resumen_ia,
            hechos,
            criterio_juridico,
            justificacion,
            embedding_512::text AS embedding,
            clave_tesis,
            archivo_origen,
            texto
        FROM jurisprudencias
        WHERE registro_digital = ANY(%s)
        ORDER BY registro_digital DESC
    """
    cur.execute(query, (registros,))
    tesis = [dict(r) for r in cur.fetchall()]

    for t in tesis:
        if t["embedding"]:
            t["embedding"] = [float(x) for x in t["embedding"].strip("[]").split(",")]

    return tesis


def subir_lote(client, lote):
    """Sube un lote completo a Supabase en una sola petición."""
    client.table("jurisprudencias").upsert(lote).execute()
    return len(lote)


# =============================================================================
# AUDITORÍA
# =============================================================================
def escribir_auditoria(registros_subidos, cantidad_total_pendiente, duracion):
    """Genera un archivo con la lista de registros subidos."""
    ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = CARPETA_LOGS / f"migracion_{ahora}.txt"

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(f"AUDITORÍA DE MIGRACIÓN A SUPABASE\n")
        f.write("=" * 70 + "\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Registros subidos en esta corrida: {len(registros_subidos)}\n")
        f.write(f"Registros pendientes restantes: {cantidad_total_pendiente}\n")
        f.write(f"Duración: {formatear_tiempo(duracion)}\n")
        f.write("=" * 70 + "\n\n")
        f.write("REGISTROS SUBIDOS (de mayor a menor):\n")
        f.write("-" * 70 + "\n")
        for reg in registros_subidos:
            f.write(f"{reg}\n")

    return ruta


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Subir tesis a Supabase")
    parser.add_argument("--cantidad", type=int, default=100,
                        help="Cuántas tesis subir en esta corrida (default: 100)")
    parser.add_argument("--lote", type=int, default=50,
                        help="Tamaño del lote por petición (default: 50)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simular sin subir nada")
    args = parser.parse_args()

    print("=" * 70)
    print("🚀 SUBIR TESIS A SUPABASE")
    print("=" * 70)
    print()

    # 1. Conectar
    conn = conectar_local()
    client = conectar_supabase()
    print()

    # 2. Detectar pendientes
    ya_en_supabase = obtener_registros_supabase(client)
    pendientes_totales = obtener_pendientes(conn, ya_en_supabase, cantidad=999999)
    cantidad_pendiente_total = len(pendientes_totales)
    pendientes = pendientes_totales[:args.cantidad]

    print()
    log(f"Pendientes totales:      {cantidad_pendiente_total}")
    log(f"A subir en esta corrida: {len(pendientes)}")

    if not pendientes:
        log("Todo está sincronizado.", "ok")
        conn.close()
        return

    if args.dry_run:
        print()
        log("MODO DRY-RUN: no se subirá nada", "warn")
        log(f"Primeros 10 registros: {pendientes[:10]}")
        conn.close()
        return

    # 3. Cargar las tesis
    print()
    log(f"Cargando {len(pendientes)} tesis desde local...")
    t0 = time.time()
    tesis = cargar_tesis(conn, pendientes)
    log(f"Cargadas en {formatear_tiempo(time.time() - t0)}", "ok")

    # 4. Subir por lotes
    print()
    log(f"Subiendo a Supabase en lotes de {args.lote}...")
    print()

    t0 = time.time()
    registros_subidos = []
    total_lotes = (len(tesis) + args.lote - 1) // args.lote

    for i in range(0, len(tesis), args.lote):
        lote = tesis[i:i + args.lote]
        num_lote = i // args.lote + 1
        try:
            subidos = subir_lote(client, lote)
            registros_subidos.extend(t["registro_digital"] for t in lote)
            print(f"   Lote {num_lote}/{total_lotes}: {subidos} tesis ✅")
        except Exception as e:
            log(f"Error en lote {num_lote}: {str(e)[:200]}", "err")
            log(f"Se subieron {len(registros_subidos)} hasta ahora. Abortando.", "err")
            break

    duracion = time.time() - t0
    restantes = cantidad_pendiente_total - len(registros_subidos)

    # 5. Reporte final
    print()
    print("=" * 70)
    log(f"Subidas en esta corrida:  {len(registros_subidos)}", "ok")
    log(f"Pendientes restantes:     {restantes}", "info")
    log(f"Duración:                 {formatear_tiempo(duracion)}", "info")
    print("=" * 70)

    # 6. Auditoría
    ruta = escribir_auditoria(registros_subidos, restantes, duracion)
    print()
    log(f"Auditoría guardada en: {ruta}", "ok")

    conn.close()


if __name__ == "__main__":
    main()