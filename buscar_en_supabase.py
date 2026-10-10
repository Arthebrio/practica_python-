"""
================================================================================
🔍 BÚSQUEDA SEMÁNTICA EN SUPABASE
================================================================================
Genera el embedding de una consulta con OpenAI y busca las tesis más
similares en Supabase usando la función RPC match_jurisprudencias.

Uso:
    python buscar_en_supabase.py "despido injustificado"
    python buscar_en_supabase.py "tortura" --limite 20
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

MODELO = "text-embedding-3-small"
DIMS = 512


def log(msg, tipo="info"):
    iconos = {"info": "ℹ️ ", "ok": "✅", "warn": "⚠️ ", "err": "❌"}
    print(f"{iconos.get(tipo, '')} {msg}")


def generar_embedding(client_openai, texto):
    """Genera embedding de 512 dims con OpenAI."""
    log(f"Generando embedding ({DIMS} dims) para: \"{texto[:60]}...\"")
    resp = client_openai.embeddings.create(
        model=MODELO,
        input=texto[:8000],
        dimensions=DIMS,
    )
    emb = resp.data[0].embedding
    log(f"Embedding OK · {len(emb)} dims", "ok")
    return emb


def buscar(client_supa, embedding, limite=10):
    """Llama a la función RPC match_jurisprudencias."""
    log(f"Buscando top {limite} en Supabase...")
    resp = client_supa.rpc(
        "match_jurisprudencias",
        {
            "query_embedding": embedding,
            "match_count": limite,
        },
    ).execute()
    log(f"Resultados: {len(resp.data)}", "ok")
    return resp.data


def mostrar(consulta, resultados):
    print()
    print("=" * 80)
    print(f"🔍 {consulta}")
    print("=" * 80)

    for i, t in enumerate(resultados, 1):
        sim = t.get("similarity", 0)
        sim_escala = sim * 10 + 3 if sim else 0
        reg = t["registro_digital"]
        tipo = t.get("tipo", "?")
        materia = t.get("materia", "?")
        fecha = t.get("fecha_publicacion", "?")
        rubro = (t.get("rubro") or "")[:100]

        print()
        print(f"{i:2d}. [{sim_escala:.1f}] REG {reg} · {tipo} · {materia} · {fecha}")
        print(f"    {rubro}...")


def main():
    parser = argparse.ArgumentParser(description="Búsqueda semántica en Supabase")
    parser.add_argument("consulta", type=str, help="Texto a buscar")
    parser.add_argument("--limite", type=int, default=10, help="Cuántos resultados (default: 10)")
    args = parser.parse_args()

    print("=" * 80)
    print("🔍 BÚSQUEDA SEMÁNTICA · SUPABASE")
    print("=" * 80)
    print()

    # Validar credenciales
    if not OPENAI_API_KEY:
        log("Falta OPENAI_API_KEY", "err")
        sys.exit(1)
    if not SUPABASE_URL or not SUPABASE_KEY:
        log("Faltan credenciales de Supabase", "err")
        sys.exit(1)

    # Clientes
    log("Conectando a OpenAI...")
    client_openai = OpenAI(api_key=OPENAI_API_KEY)
    log("OpenAI OK", "ok")

    log("Conectando a Supabase...")
    client_supa = create_client(SUPABASE_URL, SUPABASE_KEY)
    log("Supabase OK", "ok")
    print()

    # Generar embedding
    embedding = generar_embedding(client_openai, args.consulta)

    # Buscar
    resultados = buscar(client_supa, embedding, args.limite)

    # Mostrar
    mostrar(args.consulta, resultados)


if __name__ == "__main__":
    main()