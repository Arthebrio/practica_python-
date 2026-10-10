import os
import psycopg2
from datetime import datetime

# Configuración de base de datos
DB_CONFIG = {
    "dbname": "practica_legal",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", "6419"),
    "host": "localhost",
    "port": 5432
}

# Palabras clave que delatan una cita cortada o extracción fallida en el Rubro
PATRONES_RUBRO_SOSPECHOSO = [
    "registro digital:", "registro digital", "gaceta", "tomo ", "página ", 
    "pagina ", "sala.", "pleno.", "semanario judicial"
]

def ejecutar_auditoria_forense():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"output/auditoria_forense_{timestamp}.txt"
    os.makedirs("output", exist_ok=True)

    print("\n🔍 INICIANDO AUDITORÍA FORENSE AVANZADA DE JURISPRUDENCIAS...")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 1. Total de tesis
        cur.execute("SELECT COUNT(*) FROM jurisprudencias;")
        total_tesis = cur.fetchone()[0]

        # 2. Criterio 1: Contenido Totalmente Nulo / Vacío (CRÍTICO)
        # Ambas ramas del Check Constraint fallan (sin texto y sin la tríada moderna)
        query_vacias = """
            SELECT registro_digital, rubro 
            FROM jurisprudencias 
            WHERE (texto IS NULL OR TRIM(texto) = '') 
              AND (hechos IS NULL OR TRIM(hechos) = '')
              AND (criterio_juridico IS NULL OR TRIM(criterio_juridico) = '')
              AND (justificacion IS NULL OR TRIM(justificacion) = '');
        """
        cur.execute(query_vacias)
        tesis_vacias = cur.fetchall()

        # 3. Criterio 2: Registros Parásitos / Citas Cortadas en Rubro (CRÍTICO)
        # Rubros que empiezan por texto típico de citas bibliográficas
        condiciones_rubro = " OR ".join([f"LOWER(rubro) LIKE '{patron}%'" for patron in PATRONES_RUBRO_SOSPECHOSO])
        query_parasitos = f"""
            SELECT registro_digital, rubro, archivo_origen 
            FROM jurisprudencias 
            WHERE {condiciones_rubro};
        """
        cur.execute(query_parasitos)
        tesis_parasitas = cur.fetchall()

        # 4. Criterio 3: Metadatos Incompletos en Épocas Modernas (ADVERTENCIA)
        # Tesis de Décima/Undécima Época con N/A en tipo, materia o instancia
        query_metadatos = """
            SELECT registro_digital, rubro, epoca, tipo, materia, instancia 
            FROM jurisprudencias 
            WHERE fecha_publicacion >= '2011-01-01'
              AND (LOWER(tipo) = 'n/a' OR LOWER(materia) = 'n/a' OR LOWER(instancia) = 'n/a');
        """
        cur.execute(query_metadatos)
        tesis_metadatos = cur.fetchall()

        # 5. Criterio 4: Integridad Vectorial (ADVERTENCIA)
        # Tesis sin embedding o sin texto vectorial generado
        query_vectores = """
            SELECT registro_digital, rubro 
            FROM jurisprudencias 
            WHERE embedding IS NULL 
               OR texto_vectorial IS NULL 
               OR TRIM(texto_vectorial) = '';
        """
        cur.execute(query_vectores)
        tesis_vectores = cur.fetchall()

        cur.close()
        conn.close()

        # GENERACIÓN DEL REPORTE DETALLADO
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("===================================================================\n")
            f.write("🛡️ REPORTE DE AUDITORÍA FORENSE - BASE DE DATOS JURISPRUDENCIAL\n")
            f.write(f"   Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"   Total de registros analizados: {total_tesis:,}\n")
            f.write("===================================================================\n\n")

            # SECCIÓN 1: HALLAZGOS CRÍTICOS
            f.write("🔴 HALLAZGOS CRÍTICOS (Atención Inmediata requerida)\n")
            f.write("-" * 67 + "\n")
            
            f.write(f"1. Registros sin contenido de texto (Total: {len(tesis_vacias)}):\n")
            if tesis_vacias:
                for reg, rubro in tesis_vacias:
                    f.write(f"   • Registro Digital: {reg} | Rubro: {rubro[:60]}...\n")
            else:
                f.write("   ✅ Ninguno. Todas las tesis contienen texto o estructura tripartita.\n")

            f.write(f"\n2. Posibles citas cortadas o registros parásitos (Total: {len(tesis_parasitas)}):\n")
            if tesis_parasitas:
                for reg, rubro, archivo in tesis_parasitas:
                    f.write(f"   • Registro Digital: {reg} | Archivo: {archivo} | Rubro: {rubro[:70]}...\n")
            else:
                f.write("   ✅ Ninguno. No se detectaron rubros que inicien con citas bibliográficas.\n")

            # SECCIÓN 2: ADVERTENCIAS DE METADATOS Y VECTORES
            f.write("\n\n🟡 ADVERTENCIAS DE CALIDAD Y BÚSQUEDA (Revisión opcional)\n")
            f.write("-" * 67 + "\n")

            f.write(f"3. Tesis modernas con metadatos en 'N/A' (Total: {len(tesis_metadatos)}):\n")
            if tesis_metadatos:
                for reg, rubro, ep, tp, mat, inst in tesis_metadatos:
                    f.write(f"   • Reg: {reg} [{ep}] | Tipo: {tp} | Mat: {mat} | Inst: {inst}\n")
            else:
                f.write("   ✅ Ninguno. Todos los metadatos modernos están correctamente clasificados.\n")

            f.write(f"\n4. Registros con fallas de Embedding / Vector (Total: {len(tesis_vectores)}):\n")
            if tesis_vectores:
                for reg, rubro in tesis_vectores:
                    f.write(f"   • Registro Digital: {reg} | Rubro: {rubro[:60]}...\n")
            else:
                f.write("   ✅ Ninguno. El 100% de las tesis cuenta con su vector de 1536 dimensiones.\n")

            # SALUD GENERAL
            total_criticos = len(tesis_vacias) + len(tesis_parasitas)
            porcentaje_salud = ((total_tesis - total_criticos) / total_tesis) * 100

            f.write("\n\n===================================================================\n")
            f.write(f"📊 ÍNDICE DE SALUD FORENSE: {porcentaje_salud:.2f}%\n")
            if total_criticos == 0:
                f.write("   ESTADO: EXCELENTE. La base de datos es 100% íntegra y confiable.\n")
            else:
                f.write(f"   ESTADO: REQUERE ATENCIÓN. Se detectaron {total_criticos} registros críticos.\n")
            f.write("===================================================================\n")

        print("\n" + "="*60)
        print("✅ AUDITORÍA FINALIZADA CON ÉXITO")
        print(f" 📄 Reporte guardado en: {report_path}")
        print(f" 📊 Salud general de la BD: {porcentaje_salud:.2f}%")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Error durante la auditoría forense: {e}")

if __name__ == "__main__":
    ejecutar_auditoria_forense()