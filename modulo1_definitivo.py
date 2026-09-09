"""
================================================================================
📜 LEXIA - SCJN EXTRACTOR DEFINITIVO (PROCESADOR EN LOTE Y AUDITORÍA)
================================================================================
Procesa de forma masiva todos los archivos PDF presentes en 'data/', consolida
sus datos en un JSON maestro y genera logs de visibilidad en consola y bitácora.
"""

import re
import json
import yaml
import logging
import pdfplumber
from pathlib import Path

# ------------------------------------------------------------------------------
# ⚙️ CARGA DE CONFIGURACIÓN Y CONFIGURACIÓN DE LOGS DUAL
# ------------------------------------------------------------------------------
CONFIG_PATH = Path("config.yaml")
if not CONFIG_PATH.exists():
    raise FileNotFoundError("❌ No se encontró 'config.yaml'. Créalo en la raíz del proyecto.")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

# Asegurar carpeta de salida
Path("output").mkdir(exist_ok=True)

# Configuración del Logger para auditoría fina y consola
logger = logging.getLogger("LEXIA_Batch")
logger.setLevel(logging.DEBUG)

log_formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# 1. File Handler (Bitácora detallada de auditoría en archivo)
file_handler = logging.FileHandler("output/extractor_auditoria.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_formatter)

# 2. Console Handler (Visibilidad limpia en tiempo real en la terminal)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_formatter)

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# ------------------------------------------------------------------------------
# 🧹 APLANADO Y LIMPIEZA DE IMPRENTA
# ------------------------------------------------------------------------------
def extraer_texto_plano_continuo(ruta_pdf: Path) -> str:
    """Extrae el flujo continuo de texto de un PDF eliminando pie de imprenta."""
    logger.debug(f"Iniciando extracción de texto plano para: {ruta_pdf.name}")
    texto_paginas = []
    
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            t = pagina.extract_text(layout=False)
            if t:
                texto_paginas.append(t)
                
    texto_unido = "\n".join(texto_paginas)
    
    # Limpieza de imprenta perimetral
    texto_limpio = re.sub(r'Pág\.\s+\d+\s+de\s+\d+.*?\n', '', texto_unido, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'Fecha\s+de\s+impresión\s+\d{2}/\d{2}/\d{4}.*?\n', '', texto_limpio, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'Semanario\s+Judicial\s+de\s+la\s+Federación.*?\n', '', texto_limpio, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'SJF\s+Semanal.*?\n', '', texto_limpio, flags=re.IGNORECASE)
    
    return re.sub(r'\n{3,}', '\n\n', texto_limpio)


# ------------------------------------------------------------------------------
# 📅 EXTRACTOR DE FECHAS DUAL
# ------------------------------------------------------------------------------
def extraer_fechas_dual(texto_bloque: str) -> dict:
    """Extrae la fecha de publicación en formato ISO (YYYY-MM-DD) y texto legible."""
    patron = r'publicó\s+el\s+viernes\s+(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})'
    match = re.search(patron, texto_bloque, re.IGNORECASE)
    
    if match:
        dia, mes_nombre, anio = match.groups()
        mes_num = CONFIG.get("meses", {}).get(mes_nombre.lower(), "01")
        dia_fmt = dia.zfill(2)
        return {
            "fecha_publicacion": f"{anio}-{mes_num}-{dia_fmt}",
            "fecha_publicacion_texto": f"{int(dia)} de {mes_nombre.lower()} de {anio}"
        }
    return {"fecha_publicacion": "1900-01-01", "fecha_publicacion_texto": "N/A"}


# ------------------------------------------------------------------------------
# 🧠 PARSER DE BLOQUE
# ------------------------------------------------------------------------------
def parsear_bloque_tesis(bloque: str, nombre_archivo: str) -> dict:
    """Extrae los 9 campos de la tesis notificando el estatus en consola y log."""
    
    reg_match = re.search(r'Registro digital:\s*(\d+)', bloque)
    registro = int(reg_match.group(1)) if reg_match else None
    
    if not registro:
        logger.warning(f"⚠️ [{nombre_archivo}] Bloque omitido por carecer de Registro Digital.")
        return {}

    # Metadatos de Cabecera
    tipo_match = re.search(r'Tipo:\s*(Jurisprudencia|Aislada)', bloque)
    tipo = tipo_match.group(1) if tipo_match else "N/A"
    
    epocas_pattern = "|".join(CONFIG.get("epocas_validas", []))
    epoca_match = re.search(rf'((?:{epocas_pattern})\s+Época)', bloque, re.IGNORECASE)
    epoca = epoca_match.group(1).title() if epoca_match else "N/A"
    
    materia_match = re.search(r'Materia\(s\):\s*([^\n]+?)(?=\s+Tesis:|\s+Fuente:|\s+Tipo:|\n)', bloque)
    materia = materia_match.group(1).strip() if materia_match else "N/A"
    
    clave_match = re.search(r'Tesis:\s*([^\n]+?)(?=\s+Fuente:|\s+Tipo:|\n)', bloque)
    clave_tesis = clave_match.group(1).strip() if clave_match else "N/A"
    
    instancia_match = re.search(
        r'Instancia:\s*([^\n]+?)(?=\s+(?:Undécima|Décima|Novena|Octava|Séptima|Sexta|Quinta)\s+Época|\s+Materia\(s\):|\s+Tesis:|\n)', 
        bloque
    )
    instancia = instancia_match.group(1).strip() if instancia_match else "N/A"
    
    fechas = extraer_fechas_dual(bloque)
    
    # Delimitación de Rubro y Texto
    rubro = "N/A"
    texto = "N/A"
    
    corte_cabecera = re.search(r'Federación\.', bloque)
    idx_inicio = corte_cabecera.end() if corte_cabecera else 0
    subtexto = bloque[idx_inicio:]

    match_texto = re.search(r'\n\s*([A-ZÁÉÍÓÚÑ][a-zñáéíóú0-9"“\s][^\n]+)', subtexto)
    
    if match_texto:
        idx_texto_relativo = match_texto.start()
        
        rubro_raw = subtexto[:idx_texto_relativo].strip()
        rubro = re.sub(r'\s+', ' ', rubro_raw)
        
        texto_desde_inicio = subtexto[idx_texto_relativo:].strip()
        
        fin_match = re.search(
            r'\n(?=(?:PRIMERA SALA|SEGUNDA SALA|PLENO|PLENO EN MATERIA|[A-ZÁÉÍÓÚÑ\s]+TRIBUNAL COLEGIADO|TRIBUNALES COLEGIADOS|Amparo\s+(?:en\s+revisión|directo)|Contradicción\s+de\s+tesis|Recurso\s+de|Queja|Solicitud\s+de|Tesis\s+de\s+jurisprudencia))',
            texto_desde_inicio
        )
        
        if fin_match:
            texto = texto_desde_inicio[:fin_match.start()].strip()
        else:
            texto = texto_desde_inicio.strip()

    datos = {
        "registro_digital": registro,
        "tipo": tipo,
        "epoca": epoca,
        "materia": materia,
        "clave_tesis": clave_tesis,
        "instancia": instancia,
        "fecha_publicacion": fechas["fecha_publicacion"],
        "fecha_publicacion_texto": fechas["fecha_publicacion_texto"],
        "rubro": rubro,
        "texto": texto,
        "archivo_origen": nombre_archivo
    }

    campos_faltantes = [k for k, v in datos.items() if v in ["N/A", None, ""]]
    if campos_faltantes:
        logger.warning(f"  ⚠️ Reg. {registro}: Presenta campos vacíos o 'N/A': {campos_faltantes}")
    else:
        logger.debug(f"  ✅ Reg. {registro}: Extraído correctamente ({len(texto)} caracteres).")

    return datos


# ------------------------------------------------------------------------------
# 🚀 PROCESAMIENTO EN LOTE (BATCH)
# ------------------------------------------------------------------------------
def ejecutar_modulo1():
    carpeta_data = Path("data")
    archivos_pdf = sorted(list(carpeta_data.glob("*.pdf")))
    
    total_archivos = len(archivos_pdf)
    if total_archivos == 0:
        logger.error("❌ No se encontraron archivos PDF en la carpeta 'data/'.")
        return
        
    logger.info("============================================================")
    logger.info(f"📂 BATCH INICIADO: Se procesarán {total_archivos} archivos PDF.")
    logger.info("============================================================\n")
    
    tesis_totales_consolidado = []
    
    for idx, pdf_fuente in enumerate(archivos_pdf, 1):
        logger.info(f"📄 [{idx}/{total_archivos}] Procesando archivo: {pdf_fuente.name}")
        
        texto_plano = extraer_texto_plano_continuo(pdf_fuente)
        bloques_raw = re.split(r'(?=\bTesis\s*\n\s*Registro digital:|\bRegistro digital:)', texto_plano)
        bloques_tesis = [b for b in bloques_raw if "Registro digital:" in b]
        
        tesis_archivo = []
        for b in bloques_tesis:
            datos = parsear_bloque_tesis(b, pdf_fuente.name)
            if datos.get("registro_digital"):
                tesis_archivo.append(datos)
                
        tesis_totales_consolidado.extend(tesis_archivo)
        logger.info(f"   ✔️ Extracción completada para {pdf_fuente.name}: {len(tesis_archivo)} tesis añadidas.\n")
        
    # Guardar archivo consolidado maestro
    archivo_salida = Path("output/tesis_definitivas_master.json")
    archivo_salida.write_text(json.dumps(tesis_totales_consolidado, indent=2, ensure_ascii=False), encoding="utf-8")
    
    logger.info("============================================================")
    logger.info(f"🎉 PROCESO EN LOTE CONCLUIDO CON ÉXITO")
    logger.info(f"📊 Total de tesis extraídas acumuladas: {len(tesis_totales_consolidado)}")
    logger.info(f"💾 JSON maestro guardado en: {archivo_salida}")
    logger.info(f"📑 Auditoría completa de logs en: output/extractor_auditoria.log")
    logger.info("============================================================\n")

if __name__ == "__main__":
    ejecutar_modulo1()