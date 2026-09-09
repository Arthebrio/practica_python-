"""
================================================================================
🔍 BÚSQUEDA SEMÁNTICA EN JURISPRUDENCIAS (VERSIÓN REPORTE)
================================================================================
Uso: python buscar_semantica.py "concepto de búsqueda" [limite]
Ejemplo: python buscar_semantica.py "amparo contra actos de autoridad" 15
"""

import os
import sys
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "practica_legal"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "6419"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

def buscar(concepto: str, limite: int = 10):
    """Realiza una búsqueda semántica y genera un reporte detallado."""
    print(f"\n🔍 BÚSQUEDA SEMÁNTICA: \"{concepto}\"")
    print("=" * 100)

    # 1. Generar embedding del concepto
    print("📡 Generando embedding de la consulta...")
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=concepto
    )
    embedding_busqueda = response.data[0].embedding

    # 2. Conectar a PostgreSQL y ejecutar la consulta
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            registro_digital,
            tipo,
            epoca,
            materia,
            rubro,
            resumen_ia,
            fecha_publicacion,
            (1 - (embedding <=> %s::vector)) AS similitud
        FROM jurisprudencias
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """, (embedding_busqueda, embedding_busqueda, limite))

    resultados = cur.fetchall()
    if not resultados:
        print("❌ No se encontraron resultados.")
        return

    # 3. Preparar el reporte
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    ruta_reporte = output_dir / f"busqueda_{timestamp}.txt"

    # ============================================================
    # ENCABEZADO DEL REPORTE
    # ============================================================
    with open(ruta_reporte, "w", encoding="utf-8") as f:
        f.write("=" * 120 + "\n")
        f.write(f"🔍 BÚSQUEDA SEMÁNTICA: \"{concepto}\"\n")
        f.write(f"📅 Fecha de consulta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"📊 Total de resultados: {len(resultados)}\n")
        f.write("=" * 120 + "\n\n")

        # ============================================================
        # DETALLE DE CADA RESULTADO
        # ============================================================
        for idx, (reg, tipo, epoca, materia, rubro, resumen, fecha, sim) in enumerate(resultados, 1):
            # Encabezado del resultado
            f.write(f"📌 RESULTADO {idx}\n")
            f.write("-" * 120 + "\n")
            f.write(f"📌 REGISTRO DIGITAL: {reg}\n")
            f.write(f"📌 TIPO: {tipo}\n")
            f.write(f"📌 ÉPOCA: {epoca}\n")
            f.write(f"📌 MATERIA: {materia or 'No especificada'}\n")
            f.write(f"📅 FECHA DE PUBLICACIÓN: {fecha if fecha else 'Sin fecha'}\n")
            f.write(f"🎯 SIMILITUD SEMÁNTICA: {sim:.4f}\n")
            f.write("\n")

            # RUBRO (Completo)
            f.write("📖 RUBRO COMPLETO:\n")
            f.write(f"{rubro}\n")
            f.write("\n")

            # RESUMEN IA (Completo)
            f.write("🤖 RESUMEN IA:\n")
            f.write(f"{resumen}\n")
            f.write("\n")
            f.write("-" * 120 + "\n\n")

        # ============================================================
        # RESUMEN EJECUTIVO AL FINAL
        # ============================================================
        f.write("=" * 120 + "\n")
        f.write("📊 RESUMEN EJECUTIVO DE LA BÚSQUEDA\n")
        f.write("=" * 120 + "\n")
        f.write(f"📌 Concepto buscado: \"{concepto}\"\n")
        f.write(f"📅 Fecha de consulta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"📊 Total de resultados: {len(resultados)}\n")

        if resultados:
            # Estadísticas de similitud
            similitudes = [r[7] for r in resultados]
            f.write(f"🎯 Similitud máxima: {max(similitudes):.4f}\n")
            f.write(f"🎯 Similitud mínima: {min(similitudes):.4f}\n")
            f.write(f"🎯 Similitud promedio: {sum(similitudes)/len(similitudes):.4f}\n")

            # Distribución por tipo
            tipos = {}
            for r in resultados:
                tipo = r[1]
                tipos[tipo] = tipos.get(tipo, 0) + 1
            f.write(f"📋 Distribución por tipo: {dict(tipos)}\n")

            # Distribución por época
            epocas = {}
            for r in resultados:
                epoca = r[2]
                epocas[epoca] = epocas.get(epoca, 0) + 1
            f.write(f"📋 Distribución por época: {dict(epocas)}\n")

        f.write("=" * 120 + "\n")

    # ============================================================
    # MOSTRAR EN CONSOLA (RESUMEN)
    # ============================================================
    print(f"\n✅ Resultados guardados en: {ruta_reporte}")
    print(f"📊 Total de resultados: {len(resultados)}")
    print("\n📌 Vista previa de los 3 primeros resultados:\n")
    for idx, (reg, tipo, epoca, materia, rubro, resumen, fecha, sim) in enumerate(resultados[:3], 1):
        print(f"📌 {idx}. REG: {reg} | Similitud: {sim:.4f}")
        print(f"   📖 RUBRO: {rubro[:80]}...")
        print(f"   🤖 RESUMEN: {resumen[:80]}...")
        print("-" * 80)

    cur.close()
    conn.close()

def main():
    args = sys.argv[1:]
    if not args:
        concepto = "amparo contra actos de autoridad que vulneran derechos humanos"
        limite = 10
    else:
        try:
            limite = int(args[-1])
            concepto = " ".join(args[:-1])
        except ValueError:
            concepto = " ".join(args)
            limite = 10

    buscar(concepto, limite)

if __name__ == "__main__":
    main()