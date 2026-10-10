import os
import psycopg2
from datetime import datetime

# Configuración de la base de datos
DB_CONFIG = {
    "dbname": "practica_legal",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", "6419"),
    "host": "localhost",
    "port": 5432
}

# Consulta para obtener la secuencia de faltantes ordenada cronológicamente
QUERY_SECUENCIA = """
WITH rangos AS (
    SELECT 
        registro_digital AS actual,
        LEAD(registro_digital) OVER (ORDER BY registro_digital) AS siguiente
    FROM jurisprudencias
)
SELECT 
    actual + 1 AS faltante_desde,
    siguiente - 1 AS faltante_hasta,
    (siguiente - actual - 1) AS cantidad_faltante
FROM rangos
WHERE siguiente - actual > 1
ORDER BY faltante_desde ASC;
"""

def generar_tabla_bloque(filas):
    if not filas:
        return "   ✅ Sin huecos detectados en esta serie.\n"
    
    lineas = []
    lineas.append(f"   {'Rango Faltante (Registro Digital)':^40} | {'Tesis Faltantes':^18}")
    lineas.append("   " + "-" * 61)
    
    for desde, hasta, cantidad in filas:
        rango_str = f"{desde}" if desde == hasta else f"{desde} ➔ {hasta}"
        lineas.append(f"   {rango_str:^40} | {cantidad:^18,}")
    
    lineas.append("   " + "-" * 61 + "\n")
    return "\n".join(lineas)

def auditar_huecos():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Conteo total
        cur.execute("SELECT COUNT(*) FROM jurisprudencias;")
        total_registros = cur.fetchone()[0]
        
        # Consulta de huecos ordenados
        cur.execute(QUERY_SECUENCIA)
        filas = cur.fetchall()
        
        cur.close()
        conn.close()

        # Separar filas por los dos bloques de interés
        # Bloque 1: Serie antigua / Novena Época (165,035 hasta 2,000,000)
        bloque_165k = [f for f in filas if f[0] < 2005026]
        
        # Bloque 2: Serie moderna / Décima y Undécima Época (2,005,026 en adelante)
        bloque_2M = [f for f in filas if f[0] >= 2005026]

        # Crear la carpeta 'output' si no existe
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, "reporte_huecos.txt")

        # Generar el contenido del reporte
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lineas = []
        lineas.append("=" * 67)
        lineas.append(" 📊 AUDITORÍA DE REGISTROS CONSECUTIVOS - JURISPRUDENCIAS")
        lineas.append(f"    Fecha de reporte: {fecha_hora}")
        lineas.append(f"    Total de tesis en BD: {total_registros:,}")
        lineas.append("=" * 67 + "\n")

        lineas.append("📌 SERIE 1: NOVENA ÉPOCA Y ANTERIORES (165,035 ➔ 2,000,000)")
        lineas.append("=" * 67)
        lineas.append(generar_tabla_bloque(bloque_165k))

        lineas.append("📌 SERIE 2: DÉCIMA Y UNDÉCIMA ÉPOCA (2,005,026 EN ADELANTE)")
        lineas.append("=" * 67)
        lineas.append(generar_tabla_bloque(bloque_2M))

        contenido = "\n".join(lineas)

        # Guardar en el archivo de texto
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(contenido)

        print(f"\n✅ Auditoría consecutiva completada. Reporte actualizado en: {filepath}\n")

    except Exception as e:
        print(f"❌ Error al ejecutar la auditoría: {e}")

if __name__ == "__main__":
    auditar_huecos()