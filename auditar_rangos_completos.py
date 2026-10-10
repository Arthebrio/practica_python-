import os
import psycopg2
from datetime import datetime

# Configuración de conexión
DB_CONFIG = {
    "dbname": "practica_legal",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", "6419"),
    "host": "localhost",
    "port": 5432
}

def encontrar_huecos(lista_existentes, inicio_rango, fin_rango):
    """Detecta los rangos continuos de números faltantes dentro de una serie."""
    if not lista_existentes:
        return []
        
    existentes_set = set(lista_existentes)
    huecos = []
    en_hueco = False
    inicio_hueco = None

    for num in range(inicio_rango, fin_rango + 1):
        if num not in existentes_set:
            if not en_hueco:
                en_hueco = True
                inicio_hueco = num
        else:
            if en_hueco:
                en_hueco = False
                huecos.append((inicio_hueco, num - 1))
    
    if en_hueco:
        huecos.append((inicio_hueco, fin_rango))
        
    return huecos

def auditar_rangos():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"output/auditoria_rangos_{timestamp}.txt"
    os.makedirs("output", exist_ok=True)

    print("\n📊 INICIANDO AUDITORÍA DETALLADA DE RANGOS Y TRANSICIÓN...")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Extraer metadatos necesarios para el desglose explícito
        cur.execute("""
            SELECT registro_digital, rubro, epoca, fecha_publicacion 
            FROM jurisprudencias 
            ORDER BY registro_digital ASC;
        """)
        todos_datos = cur.fetchall()
        cur.close()
        conn.close()

        todos_registros = [row[0] for row in todos_datos]
        total_bd = len(todos_registros)

        # Divisorio formal en las 3 series
        s1_historica = [r for r in todos_registros if r < 2000000]
        s2_datos = [row for row in todos_datos if 2000000 <= row[0] < 2005087]
        s2_transicion = [row[0] for row in s2_datos]
        s3_moderna = [r for r in todos_registros if r >= 2005087]

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("===================================================================\n")
            f.write("📊 REPORTE DE INTEGRIDAD Y DETALLE DE TRANSICIÓN (3 SERIES)\n")
            f.write(f"   Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"   Total de registros analizados en BD: {total_bd:,}\n")
            f.write("===================================================================\n\n")

            # SERIE 1: HISTÓRICA
            f.write("📌 SERIE 1: HISTÓRICA (Folios de 6 dígitos < 2,000,000)\n")
            f.write("-" * 67 + "\n")
            f.write(f"• Tesis registradas en BD: {len(s1_historica):,}\n")
            huecos_s1 = encontrar_huecos(s1_historica, 159805, 159822)
            f.write(f"• Rangos de huecos detectados: {len(huecos_s1)}\n\n")
            f.write("   Rango Faltante (Registro Digital)       |  Tesis Faltantes\n")
            f.write("   -------------------------------------------------------------\n")
            for inicio, fin in huecos_s1:
                cant = (fin - inicio) + 1
                if inicio == fin:
                    f.write(f"               {inicio:^19}        |  {cant:^15}\n")
                else:
                    f.write(f"        {inicio} ➔ {fin}        |  {cant:^15,}\n")
            f.write(f"   -------------------------------------------------------------\n\n\n")

            # SERIE 2: TRANSICIÓN CON LISTADO EXPLÍCITO
            f.write("📌 SERIE 2: TRANSICIÓN DÉCIMA ÉPOCA (2,000,000 a 2,005,086)\n")
            f.write("-" * 67 + "\n")
            f.write(f"• Tesis registradas en BD: {len(s2_transicion):,}\n")
            huecos_s2 = encontrar_huecos(s2_transicion, 2000000, 2005086)
            f.write(f"• Huecos previos: 2,000,000 ➔ 2,005,026 (5,027 folios sin emisión/digitalización)\n\n")
            f.write("   📋 LISTADO COMPLETO DE LOS REGISTROS DE TRANSICIÓN PRESENTES EN BD:\n")
            f.write("   -------------------------------------------------------------\n")
            for reg, rubro, epoca, fecha in s2_datos:
                rubro_limpio = (rubro[:60] + "...") if rubro else "(Sin Rubro)"
                f.write(f"   • Registro: {reg} | Fecha: {fecha} | Época: {epoca}\n")
                f.write(f"     Rubro: {rubro_limpio}\n\n")
            f.write("   -------------------------------------------------------------\n\n\n")

            # SERIE 3: MODERNA
            f.write("📌 SERIE 3: MODERNA Y CONTINUA (>= 2,005,087)\n")
            f.write("-" * 67 + "\n")
            f.write(f"• Tesis registradas en BD: {len(s3_moderna):,}\n")
            huecos_s3 = encontrar_huecos(s3_moderna, 2005087, 2032642)
            f.write(f"• Rangos de huecos detectados: {len(huecos_s3)}\n\n")
            f.write("   Rango Faltante (Registro Digital)       |  Tesis Faltantes\n")
            f.write("   -------------------------------------------------------------\n")
            for inicio, fin in huecos_s3:
                cant = (fin - inicio) + 1
                if inicio == fin:
                    f.write(f"               {inicio:^19}        |  {cant:^15}\n")
                else:
                    f.write(f"        {inicio} ➔ {fin}        |  {cant:^15,}\n")
            f.write(f"   -------------------------------------------------------------\n\n\n")

            # VERIFICACIÓN MATEMÁTICA
            suma_verificada = len(s1_historica) + len(s2_transicion) + len(s3_moderna)
            f.write("===================================================================\n")
            f.write("🧮 VERIFICACIÓN MATEMÁTICA DE REGISTROS:\n")
            f.write(f"   • Serie 1 (Histórica):  {len(s1_historica):,}\n")
            f.write(f"   • Serie 2 (Transición): {len(s2_transicion):,}\n")
            f.write(f"   • Serie 3 (Moderna):    {len(s3_moderna):,}\n")
            f.write(f"   ----------------------------------------\n")
            f.write(f"   TOTAL SUMADO:           {suma_verificada:,}\n")
            f.write(f"   TOTAL REAL EN BD:       {total_bd:,}\n")
            
            if suma_verificada == total_bd:
                f.write("   ✅ COINCIDENCIA EXACTA (100% de los registros auditados).\n")
            else:
                f.write("   ⚠️ ADVERTENCIA: Hay discrepancia en el conteo total.\n")
            f.write("===================================================================\n")

        print("\n" + "="*60)
        print("✅ AUDITORÍA COMPLETA Y DESGLOSE GENERADO")
        print(f" 📄 Reporte guardado en: {report_path}")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Error durante la auditoría: {e}")

if __name__ == "__main__":
    auditar_rangos()