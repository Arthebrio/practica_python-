import os
import json
import gzip
import psycopg2
import pandas as pd
from datetime import datetime, date

# Configuración de base de datos
DB_CONFIG = {
    "dbname": "practica_legal",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", "6419"),
    "host": "localhost",
    "port": 5432
}

def convertidor_json(obj):
    """Convierte objetos de fecha y hora a cadena de texto para JSON."""
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def exportar_respaldos():
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d")
    jsonl_path = os.path.join(output_dir, f"backup_jurisprudencias_{timestamp}.jsonl.gz")
    parquet_path = os.path.join(output_dir, f"backup_jurisprudencias_{timestamp}.parquet")

    print("\n📦 INICIANDO EXPORTACIÓN DUAL DE BASE DE DATOS...")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # 1. Cargar datos en un DataFrame de Pandas
        print(" -> Leyendo registros desde PostgreSQL...")
        query = "SELECT * FROM jurisprudencias ORDER BY registro_digital ASC;"
        df = pd.read_sql_query(query, conn)
        conn.close()

        total_filas = len(df)
        print(f" -> Cargados {total_filas:,} registros en memoria.")

        # 2. Exportar a JSONL comprimido (.jsonl.gz)
        print(f" -> Generando copia transparente legible: {jsonl_path}")
        registros = df.to_dict(orient="records")
        
        with gzip.open(jsonl_path, "wt", encoding="utf-8") as f:
            for reg in registros:
                f.write(json.dumps(reg, default=convertidor_json, ensure_ascii=False) + "\n")

        # 3. Exportar a Parquet (.parquet)
        print(f" -> Generando copia binaria ultrarrápida: {parquet_path}")
        df.to_parquet(parquet_path, engine="pyarrow", index=False)

        # 4. Mostrar tamaños finales
        size_jsonl = os.path.getsize(jsonl_path) / (1024 * 1024)
        size_parquet = os.path.getsize(parquet_path) / (1024 * 1024)

        print("\n" + "="*60)
        print("✅ RESPALDOS GENERADOS CON ÉXITO")
        print(f" 📄 JSONL.gz (Legible): {size_jsonl:.2f} MB")
        print(f" ⚡ Parquet  (Binario): {size_parquet:.2f} MB")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Error durante el respaldo: {e}")

if __name__ == "__main__":
    exportar_respaldos()