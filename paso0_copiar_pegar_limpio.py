"""
================================================================================
📜 LEXIA - SIMULADOR DE "COPIAR Y PEGAR SIN FORMATO" (FASE DE PRUEBA)
================================================================================
Extrae el texto continuo del PDF, elimina encabezados/pies repetitivos 
y genera un archivo de texto plano auditable para inspección visual.
"""

import pdfplumber
import re
from pathlib import Path

def simular_copiar_pegar(ruta_pdf: str, ruta_salida_txt: str):
    print(f"\n📖 Leyendo PDF fuente: {ruta_pdf}")
    
    texto_acumulado = []
    
    with pdfplumber.open(ruta_pdf) as pdf:
        total_paginas = len(pdf.pages)
        for i, pagina in enumerate(pdf.pages, 1):
            # extract_text() sin layout mantiene el flujo continuo tipo portapapeles
            texto_pagina = pagina.extract_text(layout=False)
            if texto_pagina:
                texto_acumulado.append(texto_pagina)
            print(f"   Leyendo página [{i}/{total_paginas}]...", end="\r")

    print("\n\n📋 Uniendo todo el texto (Simulando 'Seleccionar todo y Copiar')...")
    texto_completo = "\n".join(texto_acumulado)

    print("🧹 Aplicando borrado de Encabezados y Pies de página...")
    
    # 1. Eliminar pies de página: "Pág. X de Y" y "Fecha de impresión DD/MM/AAAA"
    texto_limpio = re.sub(
        r'Pág\.\s+\d+\s+de\s+\d+.*?\n', 
        '', 
        texto_completo, 
        flags=re.IGNORECASE
    )
    texto_limpio = re.sub(
        r'Fecha\s+de\s+impresión\s+\d{2}/\d{2}/\d{4}.*?\n', 
        '', 
        texto_limpio, 
        flags=re.IGNORECASE
    )
    
    # 2. Eliminar encabezados: "Semanario Judicial de la Federación" y marcas de imprenta
    texto_limpio = re.sub(
        r'Semanario\s+Judicial\s+de\s+la\s+Federación.*?\n', 
        '', 
        texto_limpio, 
        flags=re.IGNORECASE
    )
    texto_limpio = re.sub(
        r'SJF\s+Semanal.*?\n', 
        '', 
        texto_limpio, 
        flags=re.IGNORECASE
    )

    # 3. Normalizar saltos de línea triples o excesivos
    texto_limpio = re.sub(r'\n{3,}', '\n\n', texto_limpio)

    # Guardar archivo de auditoría visual
    salida_path = Path(ruta_salida_txt)
    salida_path.parent.mkdir(exist_ok=True)
    salida_path.write_text(texto_limpio, encoding="utf-8")

    print("\n============================================================")
    print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
    print(f"💾 Archivo de texto plano generado en: {salida_path}")
    print("============================================================\n")

if __name__ == "__main__":
    carpeta_data = Path("data")
    pdfs = list(carpeta_data.glob("*.pdf"))
    
    if not pdfs:
        print("❌ No se encontró ningún archivo PDF en la carpeta 'data/'")
    else:
        simular_copiar_pegar(str(pdfs[0]), "output/texto_plano_auditable.txt")