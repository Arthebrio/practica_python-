"""
================================================================================
🚀 ORQUESTADOR JURIS_PULSE - VERSIÓN DEFINITIVA CON LOGS DETALLADOS
================================================================================
Automatiza extracción, enriquecimiento y carga de tesis.
Visualización en tiempo real por tesis y registro de fechas.
"""

import os
import json
import subprocess
import logging
from pathlib import Path

# Configurar logs dobles: Consola y Archivo de Texto en output/
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler("output/orquestador.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ORQUESTADOR")

# Rutas
DATA_DIR = Path("data")
HISTORIAL = OUTPUT_DIR / "procesados.json"

def cargar_historial():
    if HISTORIAL.exists():
        try:
            with open(HISTORIAL, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def guardar_historial(historial):
    with open(HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=2, ensure_ascii=False)

def ya_procesado(nombre_archivo, historial):
    return nombre_archivo in historial

def ejecutar_modulo1_definitivo(archivos):
    logger.info("📂 [PASO 1/3] Ejecutando Módulo 1 (Extracción de tesis antiguas)...")
    try:
        cmd = ["python", "modulo1_definitivo.py"] + [str(a) for a in archivos]
        subprocess.run(cmd, check=True)
        logger.info("✅ Extracción de tesis antiguas completada exitosamente.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error crítico en Módulo 1 (Antiguo): {e}")
        return False

def ejecutar_modulo1_moderno(archivos):
    logger.info("📂 [PASO 1/3] Ejecutando Módulo 1 (Extracción de tesis modernas)...")
    try:
        cmd = ["python", "modulo1_moderno.py"] + [str(a) for a in archivos]
        subprocess.run(cmd, check=True)
        logger.info("✅ Extracción de tesis modernas completada exitosamente.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error crítico en Módulo 1 (Moderno): {e}")
        return False

def ejecutar_enriquecimiento():
    logger.info("🧠 [PASO 2/3] Ejecutando Módulo 1.5 (Enriquecimiento e Inteligencia Artificial)...")
    try:
        subprocess.run(["python", "modulo1_5_enriquecimiento.py"], check=True)
        logger.info("✅ Enriquecimiento de metadatos completado.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error crítico en Enriquecimiento: {e}")
        return False

def ejecutar_carga(script_carga, tipo_formato):
    logger.info(f"📥 [PASO 3/3] Iniciando carga e inserción a PostgreSQL ({tipo_formato.upper()})...")
    try:
        subprocess.run(["python", script_carga], check=True)
        logger.info(f"✅ Ingesta de tesis {tipo_formato}s en PostgreSQL completada.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error crítico en la carga ({tipo_formato}): {e}")
        return False

def auditar_json_generado():
    """Lee el último JSON procesado para imprimir el desglose fecha por fecha en los logs."""
    json_files = list(OUTPUT_DIR.glob("tesis_enriquecidas*.json"))
    if not json_files:
        return

    json_path = max(json_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"🔍 Auditando fechas en archivo generado: {json_path.name}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            tesis_lista = json.load(f)

        logger.info(f"📊 Registros a ingestar: {len(tesis_lista)} tesis.")
        for idx, t in enumerate(tesis_lista, 1):
            reg = t.get("registro_digital", "S/N")
            f_iso = t.get("fecha_publicacion", "N/A")
            f_txt = t.get("fecha_publicacion_texto", "N/A")
            rubro = t.get("rubro", "Sin rubro")[:50]
            
            logger.info(f"  📌 [{idx}/{len(tesis_lista)}] Reg: {reg} | Fecha ISO (DATE): {f_iso} | Fecha Texto (TEXT): '{f_txt}' | Rubro: {rubro}...")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo auditar el detalle visual de las tesis: {e}")

def preguntar_formato():
    """Pregunta al usuario qué tipo de tesis va a procesar."""
    while True:
        respuesta = input("📌 ¿Qué tipo de tesis vas a procesar? (antiguo / moderno): ").strip().lower()
        if respuesta in ["antiguo", "moderno"]:
            return respuesta
        print("❌ Opción inválida. Escribe 'antiguo' o 'moderno'.")

def main():
    logger.info("============================================================")
    logger.info("🚀 ORQUESTADOR JURIS_PULSE INICIADO (NV59 SERVER)")
    logger.info("============================================================")

    historial = cargar_historial()
    pdfs = list(DATA_DIR.glob("*.pdf"))
    
    if not pdfs:
        logger.warning("⚠️ No se encontraron archivos PDF en la carpeta 'data/'.")
        return

    # Filtrar solo archivos nuevos
    pdfs_nuevos = [p for p in pdfs if not ya_procesado(p.name, historial)]
    
    if not pdfs_nuevos:
        logger.info("✅ Todos los PDFs en 'data/' ya se encuentran en el historial.")
        return

    logger.info(f"📄 Se detectaron {len(pdfs_nuevos)} lote(s) de PDF nuevos por procesar:")
    for p in pdfs_nuevos:
        logger.info(f"   • {p.name}")

    formato = preguntar_formato()
    logger.info(f"🎯 Modalidad seleccionada: {formato.upper()}")

    # ------------------------------------------------------------
    # PASO 1: EXTRACCIÓN
    # ------------------------------------------------------------
    if formato == "antiguo":
        if not ejecutar_modulo1_definitivo(pdfs_nuevos):
            return
    else:
        if not ejecutar_modulo1_moderno(pdfs_nuevos):
            return

    # ------------------------------------------------------------
    # PASO 2: ENRIQUECIMIENTO
    # ------------------------------------------------------------
    if not ejecutar_enriquecimiento():
        return

    # Auditoría visual en log antes de escribir en Postgres
    auditar_json_generado()

    # ------------------------------------------------------------
    # PASO 3: CARGA A BASE DE DATOS
    # ------------------------------------------------------------
    script_poblar = "poblar_antiguo.py" if formato == "antiguo" else "poblar_moderno.py"
    if not ejecutar_carga(script_poblar, formato):
        return

    # ------------------------------------------------------------
    # ACTUALIZACIÓN DE HISTORIAL
    # ------------------------------------------------------------
    for pdf in pdfs_nuevos:
        historial.append(pdf.name)
    guardar_historial(historial)

    logger.info("============================================================")
    logger.info(f"🎉 PROCESO FINALIZADO CON ÉXITO PARA {len(pdfs_nuevos)} LOTE(S)")
    logger.info("============================================================")

if __name__ == "__main__":
    main()