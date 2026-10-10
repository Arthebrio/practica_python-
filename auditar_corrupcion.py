"""
================================================================================
🔍 AUDITORÍA Y DEPURACIÓN v2 - TABLA 'jurisprudencias'
================================================================================
Mejoras sobre v1:
  - No depende de umbrales de longitud fijos (evita falsos positivos)
  - Detecta rubros que en realidad son metadata, fechas o fragmentos
  - Distingue formato ANTIGUO (texto) vs MODERNO (hechos/criterio/justif)
  - Clasifica por severidad: OK / MEDIO / ALTO / CRÍTICO
  - Exporta JSON con IDs a reprocesar (para alimentar al extractor)

Uso: python auditar_y_depurar_v2.py
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "practica_legal"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "6419"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}

# ------------------------------------------------------------------------------
# 🧠 PATRONES DE DETECCIÓN SEMÁNTICA
# ------------------------------------------------------------------------------
# Rubro que en realidad es una línea de metadata (leaked desde la cabecera)
PATRON_METADATA = re.compile(
    r'^\s*(Tipo|Fuente|Publicación|Materia(?:\(s\))?|Instancia|'
    r'Registro\s+digital|Tesis|Época|Ponente|Secretari[oa])\s*:',
    re.IGNORECASE,
)

# Rubro que en realidad es una fecha (leaked desde la línea "Publicación:")
PATRON_FECHA = re.compile(
    r'^\s*(?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)?\s*'
    r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',
    re.IGNORECASE,
)

# Rubro que es solo la palabra "Tesis" o similar
PATRON_RUBRO_BASURA = re.compile(
    r'^\s*(Tesis|Jurisprudencia|Aislada|Rubro|Texto)\s*$',
    re.IGNORECASE,
)


# ------------------------------------------------------------------------------
# 📊 CLASIFICACIÓN DE CADA REGISTRO
# ------------------------------------------------------------------------------
def clasificar_registro(row: dict) -> tuple:
    """
    Devuelve (severidad, lista_problemas).
    Severidad: 0=OK, 1=MEDIO, 2=ALTO, 3=CRÍTICO
    """
    problemas = []
    sev = 0

    rubro = (row["rubro"] or "").strip()
    texto = row["texto"] or ""
    hechos = row["hechos"] or ""
    criterio = row["criterio_juridico"] or ""
    justif = row["justificacion"] or ""
    fecha = str(row["fecha_publicacion"]) if row["fecha_publicacion"] else ""

    # --- 1. Detección de formato ---
    tiene_texto = len(texto.strip()) > 0
    tiene_estructurado = any(len(c.strip()) > 0 for c in (hechos, criterio, justif))

    if not tiene_texto and not tiene_estructurado:
        problemas.append("SIN_CONTENIDO")
        sev = 3

    # --- 2. Validación semántica del rubro ---
    if not rubro:
        problemas.append("RUBRO_VACIO")
        sev = max(sev, 3)
    else:
        if PATRON_METADATA.match(rubro):
            problemas.append("RUBRO_ES_METADATA")
            sev = max(sev, 3)
        if PATRON_FECHA.match(rubro):
            problemas.append("RUBRO_ES_FECHA")
            sev = max(sev, 3)
        if PATRON_RUBRO_BASURA.match(rubro):
            problemas.append("RUBRO_BASURA")
            sev = max(sev, 3)

        largo = len(rubro)
        if largo < 5:
            problemas.append(f"RUBRO_MUY_CORTO({largo})")
            sev = max(sev, 3)
        elif largo < 15:
            problemas.append(f"RUBRO_CORTO({largo})")
            sev = max(sev, 2)
        elif largo < 25:
            # Solo sospechoso si además no termina en punto o mayúscula
            if not rubro.endswith((".", "?", "!", "”", '"')):
                problemas.append(f"RUBRO_POSIBLE_TRUNCADO({largo})")
                sev = max(sev, 1)

        # Rubro que empieza en minúscula (fragmento, no título)
        if rubro and rubro[0].islower():
            problemas.append("RUBRO_INICIA_MINUSCULA")
            sev = max(sev, 1)

    # --- 3. Validación de contenido ---
    if tiene_texto and len(texto.strip()) < 200:
        problemas.append(f"TEXTO_CORTO({len(texto.strip())})")
        sev = max(sev, 2)
    if tiene_texto and len(texto.strip()) < 50:
        problemas.append("TEXTO_MUY_CORTO")
        sev = max(sev, 3)

    if tiene_estructurado:
        for nombre, val in [("HECHOS", hechos), ("CRITERIO", criterio), ("JUSTIF", justif)]:
            if val and 0 < len(val.strip()) < 30:
                problemas.append(f"{nombre}_CORTO({len(val.strip())})")
                sev = max(sev, 2)
            # Campos que deberían existir en formato moderno
            if not val:
                problemas.append(f"{nombre}_VACIO")
                sev = max(sev, 1)

    # --- 4. Fecha ---
    if fecha.startswith("1900") or fecha == "":
        problemas.append("FECHA_FALLIDA")
        sev = max(sev, 1)

    # --- 5. Embedding ---
    if not row["tiene_emb"]:
        problemas.append("SIN_EMBEDDING")
        sev = max(sev, 1)

    return sev, problemas


# ------------------------------------------------------------------------------
# 🚀 MAIN
# ------------------------------------------------------------------------------
def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sufijo = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 80)
    print(f"🔍 AUDITORÍA v2 - {timestamp}")
    print("=" * 80)

    # --- Traer todo de un solo golpe ---
    cur.execute("""
        SELECT
            registro_digital, tipo, epoca, materia, clave_tesis, instancia,
            fecha_publicacion, rubro, texto, hechos, criterio_juridico,
            justificacion, (embedding IS NOT NULL) AS tiene_emb
        FROM jurisprudencias
        ORDER BY registro_digital;
    """)
    columnas = [d[0] for d in cur.description]
    filas = [dict(zip(columnas, r)) for r in cur.fetchall()]
    total = len(filas)
    print(f"📊 Total de registros: {total}\n")

    # --- Clasificar ---
    buckets = {0: [], 1: [], 2: [], 3: []}
    for row in filas:
        sev, probs = clasificar_registro(row)
        buckets[sev].append({"row": row, "problemas": probs})

    etiquetas = {0: "✅ OK", 1: "🟡 MEDIO", 2: "🟠 ALTO", 3: "🔴 CRÍTICO"}
    print("📊 DISTRIBUCIÓN POR SEVERIDAD:")
    for sev in (3, 2, 1, 0):
        print(f"   {etiquetas[sev]}: {len(buckets[sev])}")
    print()

    # --- Distribución de problemas (top) ---
    from collections import Counter
    contador = Counter()
    for sev in (1, 2, 3):
        for item in buckets[sev]:
            for p in item["problemas"]:
                tipo_prob = p.split("(")[0]
                contador[tipo_prob] += 1

    print("📊 TOP PROBLEMAS DETECTADOS:")
    for prob, cant in contador.most_common(15):
        print(f"   {prob}: {cant}")
    print()

    # --- Muestra de críticos y altos ---
    print("🔴 MUESTRA DE CRÍTICOS (primeros 20):")
    for item in buckets[3][:20]:
        r = item["row"]
        print(f"   REG {r['registro_digital']} | {r['tipo']} | {r['epoca']}")
        print(f"      problemas: {', '.join(item['problemas'])}")
        print(f"      rubro[:60]={r['rubro'][:60]!r}")
    print()

    # --- Exportar JSON de IDs a reprocesar ---
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    ids_reprocesar = sorted({item["row"]["registro_digital"] for item in buckets[3]})
    ids_revisar = sorted({item["row"]["registro_digital"] for item in buckets[2]})

    reporte = {
        "timestamp": timestamp,
        "total": total,
        "resumen": {
            "criticos": len(buckets[3]),
            "altos": len(buckets[2]),
            "medios": len(buckets[1]),
            "ok": len(buckets[0]),
        },
        "ids_reprocesar": ids_reprocesar,   # CRÍTICOS (rubro vacío, sin contenido)
        "ids_revisar": ids_revisar,         # ALTOS (revisión manual)
    }

    ruta_json = output_dir / f"auditoria_v2_{sufijo}.json"
    ruta_json.write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # --- Reporte de texto legible ---
    ruta_txt = output_dir / f"auditoria_v2_{sufijo}.txt"
    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write(f"AUDITORÍA v2 - {timestamp}\n{'=' * 80}\n\n")
        f.write(f"Total: {total}\n")
        f.write(f"Críticos: {len(buckets[3])}\n")
        f.write(f"Altos: {len(buckets[2])}\n")
        f.write(f"Medios: {len(buckets[1])}\n")
        f.write(f"OK: {len(buckets[0])}\n\n")

        for sev in (3, 2):
            f.write(f"\n{etiquetas[sev]} ({len(buckets[sev])})\n")
            f.write("-" * 80 + "\n")
            for item in buckets[sev]:
                r = item["row"]
                f.write(
                    f"REG {r['registro_digital']} | {r['tipo']} | {r['epoca']} | "
                    f"problemas: {', '.join(item['problemas'])}\n"
                )
                f.write(f"   rubro: {r['rubro'][:120]!r}\n")

    print("=" * 80)
    print("✅ Reportes generados:")
    print(f"   📄 JSON: {ruta_json}")
    print(f"   📄 TXT:  {ruta_txt}")
    print(f"   🔴 IDs a REPROCESAR (críticos): {len(ids_reprocesar)}")
    print(f"   🟠 IDs a REVISAR   (altos):    {len(ids_revisar)}")
    print("=" * 80)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()