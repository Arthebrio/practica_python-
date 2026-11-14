"""
================================================================================
🤖 PROCESO SEMANAL AUTOMATIZADO (EL BOTÓN MÁGICO)
================================================================================
Ejecuta el pipeline completo de un solo golpe:
  1. Extrae y enriquece (Orquestador en modo moderno)
  2. Rellena embedding_512 y sube a Supabase (subir_a_supabase.py)

Uso:
    python proceso_semanal.py
    python proceso_semanal.py --dry-run  (Para probar sin subir a Supabase)
"""

import subprocess
import sys
import time
import argparse

def ejecutar_paso(nombre, comando, input_automatico=None):
    print("\n" + "=" * 70)
    print(f"🚀 INICIANDO: {nombre}")
    print("=" * 70)
    
    t0 = time.time()
    
    try:
        subprocess.run(
            comando, 
            input=input_automatico, 
            text=True, 
            check=True
        )
        duracion = time.time() - t0
        print(f"\n✅ {nombre} COMPLETADO en {duracion:.1f}s")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERROR CRÍTICO en {nombre}. Código de salida: {e.returncode}")
        return False

def main():
    # Configurar los argumentos de la terminal
    parser = argparse.ArgumentParser(description="Proceso semanal automatizado")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Simula la subida a Supabase sin subir nada realmente")
    args = parser.parse_args()

    print("============================================================")
    print("🤖 INICIANDO PROCESO SEMANAL AUTOMATIZADO")
    if args.dry_run:
        print("⚠️  MODO DRY-RUN ACTIVADO: La subida a Supabase será una simulación.")
    print("============================================================")
    
    # PASO 1: Orquestador
    exito_orquestador = ejecutar_paso(
        nombre="PASO 1: Orquestador (Extraer y Enriquecer)",
        comando=["python", "orquestador.py"],
        input_automatico="moderno\n"
    )
    
    if not exito_orquestador:
        print("\n🛑 Proceso abortado porque el orquestador falló.")
        sys.exit(1)
        
    # PASO 2: Subida a Supabase
    # Preparamos el comando base
    comando_subida = ["python", "subir_a_supabase.py", "--cantidad", "100", "--lote", "5"]
    
    # Si el usuario puso --dry-run, se lo agregamos al comando de subida
    if args.dry_run:
        comando_subida.append("--dry-run")

    exito_subida = ejecutar_paso(
        nombre="PASO 2: Subida a Supabase",
        comando=comando_subida
    )
    
    if not exito_subida:
        print("\n🛑 Proceso abortado porque la subida falló.")
        sys.exit(1)
        
    # RESUMEN FINAL
    print("\n" + "🎉" * 30)
    if args.dry_run:
        print("✅ SIMULACIÓN (DRY-RUN) FINALIZADA CON ÉXITO.")
        print("Todo listo. Cuando estés seguro, corre el script sin --dry-run.")
    else:
        print("🎉 PROCESO SEMANAL FINALIZADO CON ÉXITO TOTAL")
        print("Ya puedes ir por un café. Tu base local y Supabase están sincronizadas.")
    print("🎉" * 30)

if __name__ == "__main__":
    main()