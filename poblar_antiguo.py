"""
================================================================================
📥 POBLAR Y EMBEDEAR - CARGA MASIVA A POSTGRESQL CON EMBEDDINGS (ANTIGUO)
================================================================================
Versión definitiva para tesis tradicionales (bloque continuo de texto).
"""

import os
import json
import time
import logging
import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

# Cargar variables de entorno
load_dotenv()

# Configuración de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ FALTA OPENAI_API_KEY en el archivo .env")
client = OpenAI(api_key=OPENAI_API_KEY)

# Configuración de PostgreSQL
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "practica_legal"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "6419"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler("output/poblar_embedear.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("POBLAR_EMBEDEAR_ANTIGUO")

def limpiar_materia(materia_raw: str) -> str:
    """Limpia comas, puntos y espacios extras en las materias."""
    if not materia_raw:
        return "Sin materia"
    materia = materia_raw.strip().rstrip(",.")
    partes = [p.strip().capitalize() for p in materia.split(",") if p.strip()]
    return ", ".join(partes) if partes else "Sin materia"

def generar_embedding(texto: str) -> list:
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texto[:8000]
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generando embedding: {e}")
        return None

def insertar_tesis(conn, tesis_data: dict, embedding: list):
    cur = conn.cursor()
    try:
        cur.execute("""
        INSERT INTO jurisprudencias (
            registro_digital, tipo, epoca, materia, clave_tesis, instancia,
            fecha_publicacion, fecha_normalizada, rubro, archivo_origen,
            resumen_ia, hechos, criterio_juridico, justificacion, texto,
            texto_vectorial, expediente, embedding
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
        ON CONFLICT (registro_digital) DO UPDATE SET
            tipo = EXCLUDED.tipo,
            epoca = EXCLUDED.epoca,
            materia = EXCLUDED.materia,
            fecha_publicacion = EXCLUDED.fecha_publicacion,
            fecha_normalizada = EXCLUDED.fecha_normalizada,
            rubro = EXCLUDED.rubro,
            hechos = EXCLUDED.hechos,
            criterio_juridico = EXCLUDED.criterio_juridico,
            justificacion = EXCLUDED.justificacion,
            texto = EXCLUDED.texto,
            resumen_ia = EXCLUDED.resumen_ia,
            texto_vectorial = EXCLUDED.texto_vectorial,
            embedding = EXCLUDED.embedding
        """, (
            tesis_data["registro_digital"],
            tesis_data["tipo"],
            tesis_data["epoca"],
            tesis_data["materia"],
            tesis_data["clave_tesis"],
            tesis_data["instancia"],
            tesis_data["fecha_publicacion"],
            tesis_data["fecha_normalizada"],
            tesis_data["rubro"],
            tesis_data["archivo_origen"],
            tesis_data["resumen_ia"],
            tesis_data["hechos"],
            tesis_data["criterio_juridico"],
            tesis_data["justificacion"],
            tesis_data["texto"],
            tesis_data["texto_vectorial"],
            tesis_data["expediente"],
            embedding
        ))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error insertando registro {tesis_data.get('registro_digital')}: {e}")
        return False
    finally:
        cur.close()

def main():
    output_dir = Path("output")
    json_files = list(output_dir.glob("tesis_enriquecidas*.json"))
    if not json_files:
        logger.error("❌ No se encontró JSON en 'output/'.")
        return

    json_path = max(json_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"📖 Leyendo: {json_path.name}")

    with open(json_path, "r", encoding="utf-8") as f:
        tesis_lista = json.load(f)

    conn = psycopg2.connect(**DB_CONFIG)
    logger.info(f"✅ Conectado a PostgreSQL.")

    procesadas = 0
    fallidas = 0

    for idx, tesis in enumerate(tesis_lista, 1):
        logger.info(f"⚡ [{idx}/{len(tesis_lista)}] Procesando registro {tesis.get('registro_digital', 'S/N')}...")

        datos_tesis = {
            "registro_digital": tesis.get("registro_digital"),
            "tipo": tesis.get("tipo", "Aislada"),
            "epoca": tesis.get("epoca", "No especificada"),
            "materia": limpiar_materia(tesis.get("materia")),
            "clave_tesis": tesis.get("clave_tesis"),
            "instancia": tesis.get("instancia", "Sin instancia"),
            "fecha_publicacion": tesis.get("fecha_publicacion"),            # Columna DATE (ISO)
            "fecha_normalizada": tesis.get("fecha_publicacion_texto"),      # Columna TEXT ("12 de septiembre...")
            "rubro": tesis.get("rubro", "Sin rubro"),
            "archivo_origen": tesis.get("archivo_origen"),
            "resumen_ia": tesis.get("resumen_ia", "Resumen no disponible."),
            "hechos": None,                                                 # Nulos para cumplir regla CHECK en tradicionales
            "criterio_juridico": None,
            "justificacion": None,
            "texto": tesis.get("texto") or tesis.get("texto_tesis"),        # Texto continuo tradicional
            "texto_vectorial": tesis.get("texto_vectorial") or tesis.get("texto") or tesis.get("rubro"),
            "expediente": tesis.get("expediente")
        }

        txt_emb = datos_tesis["texto_vectorial"] or datos_tesis["rubro"]
        embedding = generar_embedding(txt_emb)
        
        if embedding is None:
            fallidas += 1
            continue

        if insertar_tesis(conn, datos_tesis, embedding):
            procesadas += 1
        else:
            fallidas += 1

        time.sleep(0.1)

    logger.info("============================================================")
    logger.info(f"🎉 CARGA ANTIGUA COMPLETADA")
    logger.info(f"✅ Procesadas: {procesadas}")
    logger.info(f"❌ Fallidas: {fallidas}")
    logger.info("============================================================")
    conn.close()

if __name__ == "__main__":
    main()