"""
================================================================================
🔍 AUDITORÍA EXHAUSTIVA DE BASE DE DATOS - LEXIA_mx (NV59 SERVER)
================================================================================
Genera un diagnóstico completo de salud, integridad y métricas de la tabla 'jurisprudencias'.
"""

import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "practica_legal"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "6419"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = OUTPUT_DIR / "auditoria_jurisprudencias.txt"

def ejecutar_consulta(cursor, sql, params=None):
    cursor.execute(sql, params)
    return cursor.fetchall()

def generar_auditoria():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        return

    lineas_reporte = []

    def log(texto=""):
        print(texto)
        lineas_reporte.append(texto)

    log("=" * 75)
    log(f"📋 REPORTE DE AUDITORÍA EXHAUSTIVA - LEXIA_mx")
    log(f"📅 Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 75)

    # 1. MÉTRICAS DE ALMACENAMIENTO Y REGISTROS
    total_registros = ejecutar_consulta(cur, "SELECT COUNT(*) FROM jurisprudencias;")[0][0]
    tamano_tabla = ejecutar_consulta(cur, "SELECT pg_size_pretty(pg_total_relation_size('jurisprudencias'));")[0][0]
    
    log("\n1. METRICAS GENERALES DE ALMACENAMIENTO")
    log(f"   • Total de jurisprudencias alojadas: {total_registros:,}")
    log(f"   • Peso total de tabla + índices HNSW: {tamano_tabla}")

    if total_registros == 0:
        log("\n⚠️ La tabla está vacía. No hay registros que auditar.")
        conn.close()
        return

    # 2. AUDITORÍA DE RANGOS DE REGISTRO DIGITAL E IDs
    min_reg, max_reg = ejecutar_consulta(cur, "SELECT MIN(registro_digital), MAX(registro_digital) FROM jurisprudencias;")[0]
    min_id, max_id = ejecutar_consulta(cur, "SELECT MIN(id), MAX(id) FROM jurisprudencias;")[0]
    
    log("\n2. RANGOS Y LIMITES DE NAVEGACION")
    log(f"   • Primer Registro Digital: {min_reg}")
    log(f"   • Último Registro Digital: {max_reg}")
    log(f"   • Rango de IDs secuenciales: {min_id} ➔ {max_id}")

    # 3. CONTROL DE INTEGRIDAD Y DUPLICADOS
    duplicados_reg = ejecutar_consulta(cur, """
        SELECT registro_digital, COUNT(*) 
        FROM jurisprudencias 
        GROUP BY registro_digital 
        HAVING COUNT(*) > 1;
    """)
    
    log("\n3. AUDITORIA DE INTEGRIDAD Y REGLAS BINDADAS")
    log(f"   • Registros Digitales duplicados: {len(duplicados_reg)}")
    
    # Evaluar nulos en campos obligatorios
    nulos_criticos = ejecutar_consulta(cur, """
        SELECT COUNT(*) FROM jurisprudencias 
        WHERE registro_digital IS NULL OR tipo IS NULL OR epoca IS NULL 
           OR materia IS NULL OR fecha_publicacion IS NULL OR embedding IS NULL;
    """)[0][0]
    log(f"   • Registros con campos obligatorios vacíos (NOT NULL): {nulos_criticos}")

    # Validar el cumplimiento de la restricción CHECK
    violaciones_check = ejecutar_consulta(cur, """
        SELECT COUNT(*) FROM jurisprudencias 
        WHERE NOT (
            (hechos IS NOT NULL AND criterio_juridico IS NOT NULL AND justificacion IS NOT NULL AND texto IS NULL)
            OR 
            (texto IS NOT NULL AND hechos IS NULL AND criterio_juridico IS NULL AND justificacion IS NULL)
        );
    """)[0][0]
    log(f"   • Violaciones a la restricción de estructura (CHECK): {violaciones_check}")

    # 4. DESGLOSE POR ESTRUCTURA DE CONTENIDO
    tradicionales = ejecutar_consulta(cur, "SELECT COUNT(*) FROM jurisprudencias WHERE texto IS NOT NULL;")[0][0]
    modernas = ejecutar_consulta(cur, "SELECT COUNT(*) FROM jurisprudencias WHERE hechos IS NOT NULL;")[0][0]
    
    log("\n4. DESGLOSE POR FORMATO Y ESTRUCTURA YURIDICA")
    log(f"   • Tesis Tradicionales (Bloque de texto único): {tradicionales} ({tradicionales/total_registros*100:.1f}%)")
    log(f"   • Tesis Modernas (Tripartitas: Hechos/Criterio/Justificación): {modernas} ({modernas/total_registros*100:.1f}%)")

    # 5. DESGLOSE POR MATERIA
    materias = ejecutar_consulta(cur, "SELECT materia, COUNT(*) FROM jurisprudencias GROUP BY materia ORDER BY 2 DESC;")
    log("\n5. DISTRIBUCION POR MATERIA")
    for mat, cant in materias:
        log(f"   • {mat or 'Sin Materia'}: {cant:,}")

    # 6. DESGLOSE POR ÉPOCA Y TIPO
    epocas = ejecutar_consulta(cur, "SELECT epoca, COUNT(*) FROM jurisprudencias GROUP BY epoca ORDER BY 2 DESC;")
    log("\n6. DISTRIBUCION POR EPOCA")
    for ep, cant in epocas:
        log(f"   • {ep}: {cant:,}")

    tipos = ejecutar_consulta(cur, "SELECT tipo, COUNT(*) FROM jurisprudencias GROUP BY tipo ORDER BY 2 DESC;")
    log("\n7. DISTRIBUCION POR TIPO DE CRITERIO")
    for tp, cant in tipos:
        log(f"   • {tp}: {cant:,}")

    # 8. AUDITORÍA DE CAMPOS DE FECHA
    fechas_inconsistentes = ejecutar_consulta(cur, """
        SELECT COUNT(*) FROM jurisprudencias 
        WHERE fecha_publicacion IS NULL OR fecha_normalizada IS NULL;
    """)[0][0]
    log("\n8. SALUD DE COLUMNAS DE FECHA")
    log(f"   • Inconsistencias en formato de fechas: {fechas_inconsistentes}")

    log("\n" + "=" * 75)
    log("🎉 AUDITORÍA FINALIZADA EXITOSAMENTE")
    log("=" * 75)

    cur.close()
    conn.close()

    # Guardar reporte en archivo de texto
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas_reporte))
    
    print(f"\n📄 Reporte detallado exportado en: {REPORT_PATH}\n")

if __name__ == "__main__":
    generar_auditoria()