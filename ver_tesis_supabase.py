"""
================================================================================
📄 VER TESIS DESDE SUPABASE
================================================================================
Consulta una tesis por su registro_digital en Supabase y la exporta a un
archivo Markdown con todos sus datos legibles.

Uso:
    python ver_tesis_supabase.py 2032687

Genera:
    output/tesis/2032687.md
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

CARPETA_TESIS = Path("output/tesis")
CARPETA_TESIS.mkdir(parents=True, exist_ok=True)


# =============================================================================
# UTILIDADES
# =============================================================================
def log(msg, tipo="info"):
    iconos = {"info": "ℹ️ ", "ok": "✅", "warn": "⚠️ ", "err": "❌"}
    print(f"{iconos.get(tipo, '')} {msg}")


def v(valor, default="N/A"):
    """Devuelve el valor o N/A si está vacío."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return default
    return valor


def formatear_fecha(fecha_str):
    """Convierte '2026-09-25' a '25 de septiembre de 2026'."""
    if not fecha_str:
        return "N/A"
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        return f"{fecha.day} de {meses[fecha.month - 1]} de {fecha.year}"
    except Exception:
        return fecha_str


# =============================================================================
# CONSULTA A SUPABASE
# =============================================================================
def consultar_tesis(client, registro):
    log(f"Consultando REG {registro} en Supabase...")
    resp = (
        client.table("jurisprudencias")
        .select("*")
        .eq("registro_digital", registro)
        .limit(1)
        .execute()
    )
    if not resp.data:
        log(f"No se encontró la tesis {registro}", "err")
        return None
    log("Tesis encontrada", "ok")
    return resp.data[0]


# =============================================================================
# CONSTRUCCIÓN DEL MARKDOWN
# =============================================================================
def construir_md(t):
    lineas = []

    # Encabezado
    lineas.append(f"# Tesis · REG: {t['registro_digital']}")
    lineas.append("")

    # Metadatos
    lineas.append("## 📋 Metadatos")
    lineas.append("")
    lineas.append(f"- **Tipo:** {v(t.get('tipo'))}")
    lineas.append(f"- **Materia:** {v(t.get('materia'))}")
    lineas.append(f"- **Época:** {v(t.get('epoca'))}")
    lineas.append(f"- **Instancia:** {v(t.get('instancia'))}")
    lineas.append(f"- **Clave tesis:** {v(t.get('clave_tesis'))}")
    lineas.append(f"- **Expediente:** {v(t.get('expediente'))}")
    lineas.append(f"- **Fecha de publicación:** {formatear_fecha(t.get('fecha_publicacion'))}")
    lineas.append(f"- **Fecha normalizada:** {v(t.get('fecha_normalizada'))}")
    lineas.append(f"- **Archivo origen:** {v(t.get('archivo_origen'))}")
    lineas.append("")

    # Rubro
    lineas.append("## 📌 Rubro")
    lineas.append("")
    lineas.append(v(t.get("rubro")))
    lineas.append("")

    # Resumen IA
    lineas.append("## 🤖 Resumen IA")
    lineas.append("")
    lineas.append(v(t.get("resumen_ia")))
    lineas.append("")

    # Contenido (formato moderno o antiguo)
    lineas.append("## 📜 Contenido")
    lineas.append("")

    if t.get("hechos") or t.get("criterio_juridico") or t.get("justificacion"):
        lineas.append("### Hechos")
        lineas.append("")
        lineas.append(v(t.get("hechos")))
        lineas.append("")
        lineas.append("### Criterio Jurídico")
        lineas.append("")
        lineas.append(v(t.get("criterio_juridico")))
        lineas.append("")
        lineas.append("### Justificación")
        lineas.append("")
        lineas.append(v(t.get("justificacion")))
        lineas.append("")
    else:
        lineas.append("### Texto")
        lineas.append("")
        lineas.append(v(t.get("texto")))
        lineas.append("")

    # Embedding (solo primeros 10 valores)
    lineas.append("## 🧠 Embedding (primeros 10 valores de 512)")
    lineas.append("")
    emb = t.get("embedding")
    if emb:
        if isinstance(emb, str):
            emb = [float(x) for x in emb.strip("[]").split(",")]
        primeros = ", ".join(f"{x:.6f}" for x in emb[:10])
        lineas.append(f"```")
        lineas.append(f"[{primeros}, ...]")
        lineas.append(f"```")
    else:
        lineas.append("N/A")
    lineas.append("")

    return "\n".join(lineas)


# =============================================================================
# MAIN
# =============================================================================
def main():
    if len(sys.argv) < 2:
        print("Uso: python ver_tesis_supabase.py <registro_digital>")
        print("Ejemplo: python ver_tesis_supabase.py 2032687")
        sys.exit(1)

    try:
        registro = int(sys.argv[1])
    except ValueError:
        log(f"El registro debe ser un número: {sys.argv[1]}", "err")
        sys.exit(1)

    print("=" * 70)
    print(f"📄 VER TESIS · REG {registro}")
    print("=" * 70)
    print()

    # Conectar
    if not SUPABASE_URL or not SUPABASE_KEY:
        log("Faltan SUPABASE_URL o SUPABASE_ANON_KEY en el .env", "err")
        sys.exit(1)
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    log("Cliente Supabase OK", "ok")

    # Consultar
    t = consultar_tesis(client, registro)
    if not t:
        sys.exit(1)

    # Construir MD
    contenido = construir_md(t)

    # Guardar
    ruta = CARPETA_TESIS / f"{registro}.md"
    ruta.write_text(contenido, encoding="utf-8")

    print()
    log(f"Archivo guardado: {ruta}", "ok")
    print()


if __name__ == "__main__":
    main()