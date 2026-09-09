"""
================================================================================
📜 LEXIA - SCJN EXTRACTOR MODERNO (UNDÉCIMA Y DUODÉCIMA ÉPOCA)
================================================================================
Procesa en lote los listados semanales con formato estructurado (Hechos, 
Criterio jurídico y Justificación), generando salida en JSON y logs de auditoría.
"""

import re
import json
import yaml
import logging
import pdfplumber
from pathlib import Path

# ------------------------------------------------------------------------------
# ⚙️ CARGA DE CONFIGURACIÓN Y SISTEMA DE LOGS
# ------------------------------------------------------------------------------
CONFIG_PATH = Path("config.yaml")
if not CONFIG_PATH.exists():
    raise FileNotFoundError("❌ No se encontró 'config.yaml'. Créalo en la raíz del proyecto.")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

Path("output").mkdir(exist_ok=True)

logger = logging.getLogger("LEXIA_Moderno")
logger.setLevel(logging.DEBUG)

log_formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# File Handler para la bitácora del extractor moderno
file_handler = logging.FileHandler("output/extractor_moderno_auditoria.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_formatter)

# Console Handler para seguimiento en vivo en la terminal
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
    """Extrae la corriente de texto eliminando elementos de imprenta."""
    logger.debug(f"Iniciando lectura de PDF moderno: {ruta_pdf.name}")
    texto_paginas = []
    
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            t = pagina.extract_text(layout=False)
            if t:
                texto_paginas.append(t)
                
    texto_unido = "\n".join(texto_paginas)
    
    # Limpieza perimetral de imprenta
    texto_limpio = re.sub(r'Pág\.\s+\d+\s+de\s+\d+.*?\n', '', texto_unido, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'Fecha\s+de\s+impresión\s+\d{2}/\d{2}/\d{4}.*?\n', '', texto_limpio, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'Semanario\s+Judicial\s+de\s+la\s+Federación.*?\n', '', texto_limpio, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'SJF\s+Semanal.*?\n', '', texto_limpio, flags=re.IGNORECASE)
    
    return re.sub(r'\n{3,}', '\n\n', texto_limpio)


# ------------------------------------------------------------------------------
# 📅 EXTRACTOR DE FECHAS DUAL
# ------------------------------------------------------------------------------
def extraer_fechas_dual(texto_bloque: str) -> dict:
    """Extrae la fecha de publicación en formato ISO YYYY-MM-DD y texto."""
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
# 🧠 PARSER DE TESIS ESTRUCTURADAS (NUEVO FORMATO)
# ------------------------------------------------------------------------------
def parsear_bloque_estructurado(bloque: str, nombre_archivo: str) -> dict:
    """Extrae los 13 campos dorados desglosando Hechos, Criterio jurídico y Justificación."""
    
    reg_match = re.search(r'Registro digital:\s*(\d+)', bloque)
    registro = int(reg_match.group(1)) if reg_match else None
    
    if not registro:
        logger.warning(f"⚠️ [{nombre_archivo}] Bloque omitido por carecer de Registro Digital.")
        return {}

    # Metadatos de Cabecera
    tipo_match = re.search(r'Tipo:\s*(Jurisprudencia|Aislada)', bloque)
    tipo = tipo_match.group(1) if tipo_match else "N/A"
    
    epoca_match = re.search(r'((?:Undécima|Duodécima|Décima)\s+Época)', bloque, re.IGNORECASE)
    epoca = epoca_match.group(1).title() if epoca_match else "N/A"
    
    materia_match = re.search(r'Materia\(s\):\s*([^\n]+?)(?=\s+Tesis:|\s+Fuente:|\s+Tipo:|\n)', bloque)
    materia = materia_match.group(1).strip() if materia_match else "N/A"
    
    clave_match = re.search(r'Tesis:\s*([^\n]+?)(?=\s+Fuente:|\s+Tipo:|\n)', bloque)
    clave_tesis = clave_match.group(1).strip() if clave_match else "N/A"
    
    instancia_match = re.search(
        r'Instancia:\s*([^\n]+?)(?=\s+(?:Undécima|Duodécima|Décima)\s+Época|\s+Materia\(s\):|\s+Tesis:|\n)', 
        bloque
    )
    instancia = instancia_match.group(1).strip() if instancia_match else "N/A"
    
    fechas = extraer_fechas_dual(bloque)
    
    # -------------------------------------------------------------------------
    # 📐 DELIMITACIÓN Y EXTRACCIÓN DE SECCIONES ESTRUCTURADAS
    # -------------------------------------------------------------------------
    rubro = "N/A"
    hechos = "N/A"
    criterio_juridico = "N/A"
    justificacion = "N/A"
    
    corte_cabecera = re.search(r'Federación\.', bloque)
    idx_inicio = corte_cabecera.end() if corte_cabecera else 0
    subtexto = bloque[idx_inicio:]

    # El Rubro va desde el fin de la cabecera hasta la etiqueta "Hechos:"
    match_hechos = re.search(r'\n\s*Hechos:\s*', subtexto, re.IGNORECASE)
    
    if match_hechos:
        rubro_raw = subtexto[:match_hechos.start()].strip()
        rubro = re.sub(r'\s+', ' ', rubro_raw)
        
        texto_desde_hechos = subtexto[match_hechos.end():]
        
        # Búsqueda de ancla para Criterio jurídico
        match_criterio = re.search(r'\n\s*Criterio jurídico:\s*', texto_desde_hechos, re.IGNORECASE)
        
        if match_criterio:
            hechos = texto_desde_hechos[:match_criterio.start()].strip()
            hechos = re.sub(r'\s+', ' ', hechos)
            
            texto_desde_criterio = texto_desde_hechos[match_criterio.end():]
            
            # Búsqueda de ancla para Justificación
            match_justificacion = re.search(r'\n\s*Justificación:\s*', texto_desde_criterio, re.IGNORECASE)
            
            if match_justificacion:
                criterio_juridico = texto_desde_criterio[:match_justificacion.start()].strip()
                criterio_juridico = re.sub(r'\s+', ' ', criterio_juridico)
                
                texto_desde_justificacion = texto_desde_criterio[match_justificacion.end():]
                
                # La Justificación termina en la firma del órgano jurisdiccional o precedentes
                match_fin = re.search(
                    r'\n(?=(?:PRIMERA SALA|SEGUNDA SALA|PLENO|PLENO REGIONAL|PLENOS DE CIRCUITO|[A-ZÁÉÍÓÚÑ\s]+TRIBUNAL COLEGIADO|Amparo\s+|Contradicción\s+|Recurso\s+de|Tesis\s+de\s+jurisprudencia))',
                    texto_desde_justificacion
                )
                
                if match_fin:
                    justificacion_raw = texto_desde_justificacion[:match_fin.start()].strip()
                else:
                    justificacion_raw = texto_desde_justificacion.strip()
                    
                justificacion = re.sub(r'\s+', ' ', justificacion_raw)

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
        "hechos": hechos,
        "criterio_juridico": criterio_juridico,
        "justificacion": justificacion,
        "archivo_origen": nombre_archivo
    }

    # Control de calidad y logging por tesis
    campos_criticos = ["rubro", "hechos", "criterio_juridico", "justificacion"]
    incompletos = [k for k in campos_criticos if datos[k] == "N/A"]
    
    if incompletos:
        logger.warning(f"  ⚠️ Reg. {registro}: Falta extraer la(s) sección(es): {incompletos}")
    else:
        logger.debug(f"  ✅ Reg. {registro}: Estructura completa (H:{len(hechos)}, C:{len(criterio_juridico)}, J:{len(justificacion)} chars).")

    return datos


# ------------------------------------------------------------------------------
# 🚀 PROCESAMIENTO EN LOTE (BATCH MODERNO)
# ------------------------------------------------------------------------------
def ejecutar_modulo1_moderno():
    carpeta_data = Path("data")
    archivos_pdf = sorted(list(carpeta_data.glob("*.pdf")))
    
    total_archivos = len(archivos_pdf)
    if total_archivos == 0:
        logger.error("❌ No se encontraron archivos PDF en la carpeta 'data/'.")
        return
        
    logger.info("============================================================")
    logger.info(f"🚀 BATCH MODERNO INICIADO: {total_archivos} archivo(s) a procesar.")
    logger.info("============================================================\n")
    
    tesis_totales_consolidado = []
    
    for idx, pdf_fuente in enumerate(archivos_pdf, 1):
        logger.info(f"📄 [{idx}/{total_archivos}] Procesando archivo moderno: {pdf_fuente.name}")
        
        texto_plano = extraer_texto_plano_continuo(pdf_fuente)
        bloques_raw = re.split(r'(?=\bTesis\s*\n\s*Registro digital:|\bRegistro digital:)', texto_plano)
        bloques_tesis = [b for b in bloques_raw if "Registro digital:" in b]
        
        tesis_archivo = []
        for b in bloques_tesis:
            datos = parsear_bloque_estructurado(b, pdf_fuente.name)
            if datos.get("registro_digital"):
                tesis_archivo.append(datos)
                
        tesis_totales_consolidado.extend(tesis_archivo)
        logger.info(f"   ✔️ Completado {pdf_fuente.name}: {len(tesis_archivo)} tesis estructuradas extraídas.\n")
        
    archivo_salida = Path("output/tesis_modernas_master.json")
    archivo_salida.write_text(json.dumps(tesis_totales_consolidado, indent=2, ensure_ascii=False), encoding="utf-8")
    
    logger.info("============================================================")
    logger.info(f"🎉 PROCESO MODERNO CONCLUIDO CON ÉXITO")
    logger.info(f"📊 Total de tesis estructuradas acumuladas: {len(tesis_totales_consolidado)}")
    logger.info(f"💾 JSON maestro guardado en: {archivo_salida}")
    logger.info(f"📑 Auditoría completa en: output/extractor_moderno_auditoria.log")
    logger.info("============================================================\n")

if __name__ == "__main__":
    ejecutar_modulo1_moderno()



    