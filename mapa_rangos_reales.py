import os
import psycopg2
from datetime import datetime

DB_CONFIG = {
    "dbname": "practica_legal",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", "6419"),
    "host": "localhost",
    "port": 5432
}

def obtener_bloques_consecutivos(registros):
    """
    Agrupa una lista ordenada de enteros en bloques continuos (islas de datos).
    Devuelve una lista de tuplas: (inicio_bloque, fin_bloque, cantidad)
    """
    if not registros:
        return []

    bloques = []
    inicio = registros[0]
    prev = registros[0]

    for num in registros[1:]:
        if num == prev + 1:
            prev = num
        else:
            bloques.append((inicio, prev, (prev - inicio) + 1))
            inicio = num
            prev = num

    bloques.append((inicio, prev, (prev - inicio) + 1))
    return bloques

def generar_mapa_real():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"output/mapa_rangos_reales_{timestamp}.txt"
    os.makedirs("output", exist_ok=True)

    print("\n🗺️ GENERANDO MAPA DE RANGOS REALES DE LA BASE DE DATOS...")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Extraer el 100% de los registros digitales ordenados
        cur.execute("SELECT registro_digital FROM jurisprudencias ORDER BY registro_digital ASC;")
        registros = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()

        total_registros_bd = len(registros)
        bloques = obtener_bloques_consecutivos(registros)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("===================================================================\n")
            f.write("🗺️ MAPA REAL Y ABSOLUTO DE RANGOS EXISTENTES EN LA BASE DE DATOS\n")
            f.write(f"   Fecha de reporte: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"   Total de registros en BD: {total_registros_bd:,}\n")
            f.write("===================================================================\n\n")

            f.write("   N°  | Rango Real Existente (Registro Digital)   | Tesis en el Bloque\n")
            f.write("  --------------------------------------------------------------------\n")

            suma_comprobada = 0
            for idx, (inicio, fin, cant) in enumerate(bloques, start=1):
                suma_comprobada += cant
                if inicio == fin:
                    f.write(f"  {idx:^4} |                   {inicio:^19}     |  {cant:^16,}\n")
                else:
                    f.write(f"  {idx:^4} |        {inicio} ➔ {fin}        |  {cant:^16,}\n")

            f.write("  --------------------------------------------------------------------\n\n")

            # MATEMÁTICA EXACTA
            f.write("===================================================================\n")
            f.write("🧮 VERIFICACIÓN MATEMÁTICA RIGUROSA:\n")
            f.write(f"   • Total de bloques/islas continuas encontradas: {len(bloques)}\n")
            f.write(f"   • Suma total de elementos de los bloques:       {suma_comprobada:,}\n")
            f.write(f"   • Registros contados directamente en la BD:    {total_registros_bd:,}\n")
            f.write(f"   -------------------------------------------------------------------\n")

            if suma_comprobada == total_registros_bd:
                f.write("   ✅ MATEMÁTICA EXACTA Y CUADRE PERFECTO (100% verificado).\n")
            else:
                f.write("   ❌ DISCREPANCIA DETECTADA EN EL CONTEO.\n")

            f.write("===================================================================\n")

        print("\n" + "="*60)
        print("✅ MAPA GENERADO CON ÉXITO")
        print(f" 📄 Reporte guardado en: {report_path}")
        print(f" 📊 Suma verificada: {suma_comprobada:,} de {total_registros_bd:,} tesis")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Error al generar el mapa de rangos: {e}")

if __name__ == "__main__":
    generar_mapa_real()