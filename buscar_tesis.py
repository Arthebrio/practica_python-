import sys
import os
import psycopg2

DB_CONFIG = {
    "dbname": "practica_legal",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", "6419"),
    "host": "localhost",
    "port": 5432
}

def buscar():
    if len(sys.argv) < 2:
        print("\n❌ Uso: python buscar_tesis.py <registro_digital o palabra_clave>")
        print("   Ejemplo: python buscar_tesis.py 2011015\n")
        return

    parametro = sys.argv[1]

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        if parametro.isdigit():
            query = "SELECT * FROM jurisprudencias WHERE registro_digital = %s;"
            cur.execute(query, (int(parametro),))
        else:
            query = "SELECT * FROM jurisprudencias WHERE rubro ILIKE %s LIMIT 5;"
            cur.execute(query, (f"%{parametro}%",))

        columnas = [desc[0] for desc in cur.description]
        filas = cur.fetchall()
        cur.close()
        conn.close()

        if not filas:
            print(f"\n⚠️ No se encontraron registros para: '{parametro}'\n")
            return

        print("\n" + "="*80)
        print(f"🔎 DETALLE COMPLETO DE REGISTROS ({len(filas)} encontrado(s))")
        print("="*80)

        for fila in filas:
            datos = dict(zip(columnas, fila))
            
            # Evaluar cuál formato aplica según la restricción CHECK de tu BD
            es_tradicional = datos.get("texto") is not None

            print("\n")
            for col, val in datos.items():
                if col == "embedding":
                    val_str = f"Array vector (1536 dim)" if val else "NULL"
                    print(f"  🔹 {col.upper():<20}: {val_str}")
                    continue

                if val is None or str(val).strip() == "":
                    # Formato amigable según el Check Constraint
                    if es_tradicional and col in ["hechos", "criterio_juridico", "justificacion"]:
                        val_display = "➖ (N/A - Formato Tradicional)"
                    elif not es_tradicional and col == "texto":
                        val_display = "➖ (N/A - Formato Tripartito Moderno)"
                    else:
                        val_display = "❌ [SIN DATO]"
                else:
                    val_display = str(val)

                print(f"  🔹 {col.upper():<20}: {val_display}")
            print("\n" + "-"*80)

        print("\n")

    except Exception as e:
        print(f"❌ Error al consultar la base de datos: {e}")

if __name__ == "__main__":
    buscar()