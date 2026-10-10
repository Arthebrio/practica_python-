"""
================================================================================
📜 LEXIA - LIMPIADOR EN BLOQUE DE PDFs (FASE DE DIAGNÓSTICO)
================================================================================
Procesa todos los PDFs de una carpeta, aplica limpieza de encabezados/pies,
y guarda TODO el texto limpio en un único archivo .txt con marcadores
para identificar cada PDF.

Uso:
    python limpiar_pdfs_corruptos.py [carpeta_entrada] [archivo_salida]

Ejemplo:
    python limpiar_pdfs_corruptos.py data/corruptos output/corruptos_limpio.txt
"""

import re
import sys
import pdfplumber
from pathlib import Path


def limpiar_texto_pdf(texto_completo: str) -> str:
    """Aplica la limpieza de encabezados y pies de página."""
    # Pies de página
    texto_limpio = re.sub(r'Pág\.\s+\d+\s+de\s+\d+.*?\n', '', texto_completo, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'Fecha\s+de\s+impresión\s+\d{2}/\d{2}/\d{4}.*?\n', '', texto_limpio, flags=re.IGNORECASE)

    # Encabezados
    texto_limpio = re.sub(r'Semanario\s+Judicial\s+de\s+la\s+Federación.*?\n', '', texto_limpio, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'SJF\s+Semanal.*?\n', '', texto_limpio, flags=re.IGNORECASE)

    # Normalizar saltos
    texto_limpio = re.sub(r'\n{3,}', '\n\n', texto_limpio)

    return texto_limpio


def procesar_pdf(ruta_pdf: Path) -> str | None:
    """Procesa un PDF y devuelve el texto limpio (o None si falla)."""
    print(f"\n📖 Procesando: {ruta_pdf.name}")

    texto_acumulado = []
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            total = len(pdf.pages)
            for i, pagina in enumerate(pdf.pages, 1):
                texto_pagina = pagina.extract_text(layout=False)
                if texto_pagina:
                    texto_acumulado.append(texto_pagina)
                print(f"   Página [{i}/{total}]...", end="\r")
    except Exception as e:
        print(f"\n   ❌ Error al leer PDF: {e}")
        return None

    print()
    texto_completo = "\n".join(texto_acumulado)
    texto_limpio = limpiar_texto_pdf(texto_completo)
    return texto_limpio


def main():
    # Leer argumentos
    carpeta_entrada = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/corruptos")
    archivo_salida = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output/corruptos_limpio.txt")

    if not carpeta_entrada.exists():
        print(f"❌ No existe la carpeta: {carpeta_entrada}")
        return

    archivo_salida.parent.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(carpeta_entrada.glob("*.pdf"))

    if not pdfs:
        print(f"❌ No hay PDFs en: {carpeta_entrada}")
        return

    print("=" * 70)
    print(f"📚 LIMPIADOR EN BLOQUE (ARCHIVO ÚNICO)")
    print(f"   Entrada: {carpeta_entrada}")
    print(f"   Salida:  {archivo_salida}")
    print(f"   PDFs:    {len(pdfs)}")
    print("=" * 70)

    partes = []
    procesados = 0
    fallidos = 0

    for pdf in pdfs:
        texto = procesar_pdf(pdf)
        if texto is None:
            fallidos += 1
            continue

        # Añadir marcador de inicio y fin del PDF
        marcador = "=" * 80
        encabezado = f"\n{marcador}\n📄 ARCHIVO: {pdf.name}\n{marcador}\n"
        pie = f"\n{marcador}\n🏁 FIN DE: {pdf.name}\n{marcador}\n"

        partes.append(encabezado)
        partes.append(texto)
        partes.append(pie)
        procesados += 1

    # Guardar todo en un solo archivo
    contenido = "\n".join(partes)
    archivo_salida.write_text(contenido, encoding="utf-8")

    print()
    print("=" * 70)
    print(f"🎉 PROCESO COMPLETADO")
    print(f"✅ Procesados: {procesados}")
    print(f"❌ Fallidos:   {fallidos}")
    print(f"💾 Archivo:   {archivo_salida}")
    print("=" * 70)


if __name__ == "__main__":
    main()