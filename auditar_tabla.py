"""
================================================================================
🔍 AUDITORÍA COMPLETA DE LA TABLA 'jurisprudencias'
================================================================================
Genera un reporte exhaustivo en un archivo de texto con:
- Conteos totales y por formato (antiguo/moderno).
- Distribución por época y tipo.
- Campos críticos vacíos.
- Registros duplicados.
- Inconsistencias de la restricción CHECK.
- Últimos registros insertados.
- Estado de los embeddings.
- Resumen ejecutivo al final.
"""

import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "practica_legal"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "6419"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

def conectar():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Conectado a PostgreSQL.")
        return conn
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def main():
    conn = conectar()
    if not conn:
        return

    cur = conn.cursor()
    reporte = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ============================================================
    # ENCABEZADO
    # ============================================================
    reporte.append("="*100)
    reporte.append(f"🔍 AUDITORÍA DE LA TABLA 'jurisprudencias' - {timestamp}")
    reporte.append("="*100)
    reporte.append("")

    # ============================================================
    # 1. TOTAL DE REGISTROS
    # ============================================================
    cur.execute("SELECT COUNT(*) FROM jurisprudencias;")
    total = cur.fetchone()[0]
    reporte.append(f"📊 TOTAL DE REGISTROS: {total}")
    reporte.append("")

    # ============================================================
    # 2. CONTEOS POR FORMATO
    # ============================================================
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE texto IS NOT NULL) AS antiguas,
            COUNT(*) FILTER (WHERE hechos IS NOT NULL) AS modernas,
            COUNT(*) FILTER (WHERE texto IS NULL AND hechos IS NULL) AS sin_contenido
        FROM jurisprudencias;
    """)
    antiguas, modernas, sin_contenido = cur.fetchone()
    reporte.append("📌 DISTRIBUCIÓN POR FORMATO:")
    reporte.append(f"   Antiguas (campo 'texto'): {antiguas}")
    reporte.append(f"   Modernas (campos 'hechos'): {modernas}")
    reporte.append(f"   Sin contenido: {sin_contenido}")
    reporte.append("")

    # ============================================================
    # 3. DISTRIBUCIÓN POR ÉPOCA
    # ============================================================
    cur.execute("""
        SELECT epoca, COUNT(*) 
        FROM jurisprudencias 
        GROUP BY epoca 
        ORDER BY COUNT(*) DESC;
    """)
    reporte.append("📅 DISTRIBUCIÓN POR ÉPOCA:")
    for epoca, count in cur.fetchall():
        reporte.append(f"   {epoca}: {count}")
    reporte.append("")

    # ============================================================
    # 4. DISTRIBUCIÓN POR TIPO
    # ============================================================
    cur.execute("""
        SELECT tipo, COUNT(*) 
        FROM jurisprudencias 
        GROUP BY tipo;
    """)
    reporte.append("⚖️ DISTRIBUCIÓN POR TIPO:")
    for tipo, count in cur.fetchall():
        reporte.append(f"   {tipo}: {count}")
    reporte.append("")

    # ============================================================
    # 5. REGISTROS DUPLICADOS
    # ============================================================
    cur.execute("""
        SELECT registro_digital, COUNT(*) 
        FROM jurisprudencias 
        GROUP BY registro_digital 
        HAVING COUNT(*) > 1;
    """)
    duplicados = cur.fetchall()
    if duplicados:
        reporte.append("⚠️ REGISTROS DUPLICADOS ENCONTRADOS:")
        for reg, count in duplicados:
            reporte.append(f"   Registro {reg}: {count} veces")
    else:
        reporte.append("✅ NO HAY REGISTROS DUPLICADOS.")
    reporte.append("")

    # ============================================================
    # 6. CAMPOS CRÍTICOS VACÍOS
    # ============================================================
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE rubro IS NULL OR rubro = '') AS rubro_vacio,
            COUNT(*) FILTER (WHERE resumen_ia IS NULL OR resumen_ia = '') AS resumen_vacio,
            COUNT(*) FILTER (WHERE texto_vectorial IS NULL OR texto_vectorial = '') AS vectorial_vacio,
            COUNT(*) FILTER (WHERE embedding IS NULL) AS embedding_vacio
        FROM jurisprudencias;
    """)
    rubro_vacio, resumen_vacio, vectorial_vacio, embedding_vacio = cur.fetchone()
    reporte.append("🔍 CAMPOS CRÍTICOS VACÍOS:")
    reporte.append(f"   Rubro vacío: {rubro_vacio}")
    reporte.append(f"   Resumen IA vacío: {resumen_vacio}")
    reporte.append(f"   Texto vectorial vacío: {vectorial_vacio}")
    reporte.append(f"   Embedding vacío: {embedding_vacio}")
    reporte.append("")

    # ============================================================
    # 7. INCONSISTENCIAS DE FORMATO (CHECK)
    # ============================================================
    cur.execute("""
        SELECT registro_digital, rubro,
               CASE 
                   WHEN texto IS NOT NULL AND hechos IS NULL AND criterio_juridico IS NULL AND justificacion IS NULL THEN 'Antiguo'
                   WHEN texto IS NULL AND hechos IS NOT NULL AND criterio_juridico IS NOT NULL AND justificacion IS NOT NULL THEN 'Moderno'
                   ELSE '⚠️ INCONSISTENTE'
               END AS formato
        FROM jurisprudencias
        WHERE (texto IS NOT NULL AND hechos IS NOT NULL) 
           OR (texto IS NULL AND hechos IS NULL)
           OR (texto IS NULL AND (criterio_juridico IS NULL OR justificacion IS NULL));
    """)
    inconsistencias = cur.fetchall()
    if inconsistencias:
        reporte.append("⚠️ REGISTROS CON FORMATO INCONSISTENTE (CHECK VIOLADO):")
        for reg, rubro, formato in inconsistencias:
            reporte.append(f"   REG {reg}: {formato} - {rubro[:60]}...")
    else:
        reporte.append("✅ TODOS LOS REGISTROS CUMPLEN CON LA ESTRUCTURA CHECK.")
    reporte.append("")

    # ============================================================
    # 8. ÚLTIMOS REGISTROS INSERTADOS
    # ============================================================
    cur.execute("""
        SELECT registro_digital, rubro, created_at
        FROM jurisprudencias
        ORDER BY created_at DESC
        LIMIT 5;
    """)
    reporte.append("🕒 ÚLTIMOS 5 REGISTROS INSERTADOS:")
    for reg, rubro, fecha in cur.fetchall():
        reporte.append(f"   REG {reg} - {fecha} - {rubro[:60]}...")
    reporte.append("")

    # ============================================================
    # 9. MUESTRA DE 10 REGISTROS CON EMBEDDING
    # ============================================================
    cur.execute("""
        SELECT registro_digital, rubro, 
               CASE WHEN texto IS NOT NULL THEN 'Antiguo' ELSE 'Moderno' END AS formato,
               CASE WHEN embedding IS NOT NULL THEN '✅' ELSE '❌' END AS tiene_embedding
        FROM jurisprudencias
        ORDER BY registro_digital DESC
        LIMIT 10;
    """)
    reporte.append("📋 MUESTRA DE 10 REGISTROS RECIENTES CON EMBEDDING:")
    for reg, rubro, formato, tiene in cur.fetchall():
        reporte.append(f"   REG {reg} ({formato}) - {tiene} - {rubro[:60]}...")
    reporte.append("")

    # ============================================================
    # 10. RESUMEN EJECUTIVO
    # ============================================================
    reporte.append("="*100)
    reporte.append("🎯 RESUMEN EJECUTIVO")
    reporte.append("="*100)
    reporte.append(f"✅ Total de registros: {total}")
    reporte.append(f"✅ Antiguas: {antiguas} | Modernas: {modernas}")
    reporte.append(f"✅ Registros sin contenido: {sin_contenido}")
    reporte.append(f"✅ Registros sin embedding: {embedding_vacio}")
    reporte.append(f"✅ Inconsistencias de formato: {len(inconsistencias)}")
    reporte.append("="*100)

    # ============================================================
    # GUARDAR REPORTE
    # ============================================================
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    ruta_reporte = output_dir / f"auditoria_{fecha_archivo}.txt"

    with open(ruta_reporte, "w", encoding="utf-8") as f:
        f.write("\n".join(reporte))

    print(f"\n✅ Reporte de auditoría guardado en: {ruta_reporte}")
    print(f"📄 Total de registros: {total}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()