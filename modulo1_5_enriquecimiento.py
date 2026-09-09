"""
================================================================================
🧠 LEXIA - MÓDULO 1.5: ENRIQUECIMIENTO CON IA Y PREPARACIÓN VECTORIAL
================================================================================
Lee el JSON maestro extraído por Módulo 1 (tradicional o moderno), procesa cada
tesis con OpenAI para generar:
  1. 'resumen_ia': Resumen humano estricto (85 - 110 palabras).
  2. 'texto_vectorial': Cerebro oculto optimizado para embeddings y RAG.

Incluye soporte para archivo .env, sistema de logs dual y reintentos.
"""

import os
import json
import yaml
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# ------------------------------------------------------------------------------
# ⚙️ CARGA DE VARIABLES DE ENTORNO (.env) Y CONFIGURACIÓN
# ------------------------------------------------------------------------------
# Cargar variables desde el archivo .env de la raíz
load_dotenv()

CONFIG_PATH = Path("config.yaml")
if not CONFIG_PATH.exists():
    raise FileNotFoundError("❌ No se encontró 'config.yaml'. Créalo en la raíz del proyecto.")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

# Buscar la API Key primero en .env (OPENAI_API_KEY) y luego en config.yaml
api_key = os.getenv("OPENAI_API_KEY") or CONFIG.get("openai", {}).get("api_key")

if not api_key:
    raise ValueError("❌ No se encontró la API Key de OpenAI. Verifique que 'OPENAI_API_KEY' esté definida en su archivo .env.")

client = OpenAI(api_key=api_key)

Path("output").mkdir(exist_ok=True)

# Configuración del Logger para auditoría fina y consola
logger = logging.getLogger("LEXIA_Enriquecimiento")
logger.setLevel(logging.DEBUG)

log_formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# 1. File Handler (Bitácora detallada de llamadas a la IA en archivo)
file_handler = logging.FileHandler("output/enriquecimiento_ia_auditoria.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_formatter)

# 2. Console Handler (Visibilidad en vivo en la terminal)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_formatter)

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# ------------------------------------------------------------------------------
# 🤖 FUNCIONES DE GENERACIÓN CON OPENAI
# ------------------------------------------------------------------------------
def generar_resumen_humano(texto_completo: str, rubro: str, modelo: str, temp: float, prompt_sys: str) -> str:
    """Genera el resumen ejecutivo para la interfaz web (85-110 palabras) con reintento."""
    contenido_entrada = f"RUBRO:\n{rubro}\n\nTEXTO/CRITERIO COMPLETO:\n{texto_completo}"
    
    for intento in range(1, 3):
        try:
            response = client.chat.completions.create(
                model=modelo,
                temperature=temp,
                messages=[
                    {"role": "system", "content": prompt_sys},
                    {"role": "user", "content": contenido_entrada}
                ]
            )
            resumen = response.choices[0].message.content.strip()
            num_palabras = len(resumen.split())
            
            if 80 <= num_palabras <= 115:
                logger.debug(f"  [Resumen IA OK] Palabras: {num_palabras} (Intento {intento})")
                return resumen
            else:
                logger.warning(f"  ⚠️ Resumen con {num_palabras} palabras fuera de rango (85-110). Reintentando...")
        except Exception as e:
            logger.error(f"  ❌ Error al llamar API para resumen (Intento {intento}): {e}")
            
    return resumen


def generar_texto_vectorial(texto_completo: str, rubro: str, modelo: str, temp: float, prompt_sys: str) -> str:
    """Genera el cerebro oculto denso para embeddings en Supabase."""
    contenido_entrada = f"RUBRO OFICIAL:\n{rubro}\n\nCONTENIDO DE LA TESIS:\n{texto_completo}"
    
    try:
        response = client.chat.completions.create(
            model=modelo,
            temperature=temp,
            messages=[
                {"role": "system", "content": prompt_sys},
                {"role": "user", "content": contenido_entrada}
            ]
        )
        texto_vec = response.choices[0].message.content.strip()
        logger.debug(f"  [Texto Vectorial OK] Caracteres generados: {len(texto_vec)}")
        return texto_vec
    except Exception as e:
        logger.error(f"  ❌ Error al generar texto vectorial: {e}")
        return f"{rubro}. {texto_completo}"


# ------------------------------------------------------------------------------
# 🚀 PROCESO PRINCIPAL DE ENRIQUECIMIENTO
# ------------------------------------------------------------------------------
def ejecutar_enriquecimiento():
    ruta_master = Path("output/tesis_modernas_master.json")
    if not ruta_master.exists():
        ruta_master = Path("output/tesis_definitivas_master.json")
        
    if not ruta_master.exists():
        logger.error("❌ No se encontró ningún JSON maestro en 'output/'. Ejecuta Módulo 1 primero.")
        return

    logger.info("============================================================")
    logger.info(f"📖 Cargando archivo fuente: {ruta_master.name}")
    
    tesis_lista = json.loads(ruta_master.read_text(encoding="utf-8"))
    total_tesis = len(tesis_lista)
    
    logger.info(f"🧠 INICIANDO ENRIQUECIMIENTO CON IA: {total_tesis} tesis a procesar.")
    logger.info("============================================================\n")

    cfg_openai = CONFIG.get("openai", {})
    cfg_prompts = CONFIG.get("prompts", {})
    
    modelo = cfg_openai.get("modelo", "gpt-4o-mini")
    temperatura = cfg_openai.get("temperatura", 0.2)
    prompt_resumen = cfg_prompts.get("resumen_ia")
    prompt_vectorial = cfg_prompts.get("texto_vectorial")

    tesis_enriquecidas = []

    for idx, tesis in enumerate(tesis_lista, 1):
        reg = tesis.get("registro_digital", "S/N")
        rubro = tesis.get("rubro", "")
        
        if "texto" in tesis:
            texto_fuente = tesis["texto"]
        else:
            texto_fuente = f"HECHOS:\n{tesis.get('hechos','')}\n\nCRITERIO JURÍDICO:\n{tesis.get('criterio_juridico','')}\n\nJUSTIFICACIÓN:\n{tesis.get('justificacion','')}"

        logger.info(f"⚡ [{idx}/{total_tesis}] Procesando Reg. Digital: {reg}...")

        resumen_ia = generar_resumen_humano(texto_fuente, rubro, modelo, temperatura, prompt_resumen)
        num_palabras_resumen = len(resumen_ia.split())

        texto_vec = generar_texto_vectorial(texto_fuente, rubro, modelo, temperatura, prompt_vectorial)

        tesis_modificada = dict(tesis)
        tesis_modificada["resumen_ia"] = resumen_ia
        tesis_modificada["texto_vectorial"] = texto_vec
        
        tesis_enriquecidas.append(tesis_modificada)
        
        logger.info(f"   ✔️ Reg. {reg} completado | Resumen: {num_palabras_resumen} palabras | Vectorial: {len(texto_vec)} chars.\n")

    archivo_salida = Path("output/tesis_enriquecidas_master.json")
    archivo_salida.write_text(json.dumps(tesis_enriquecidas, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("============================================================")
    logger.info("🎉 ENRIQUECIMIENTO CON IA CONCLUIDO CON ÉXITO")
    logger.info(f"📊 Total de tesis enriquecidas: {len(tesis_enriquecidas)}")
    logger.info(f"💾 JSON final enriquecido guardado en: {archivo_salida}")
    logger.info(f"📑 Bitácora completa de llamadas en: output/enriquecimiento_ia_auditoria.log")
    logger.info("============================================================\n")

if __name__ == "__main__":
    ejecutar_enriquecimiento()