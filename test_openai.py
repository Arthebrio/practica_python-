"""
================================================================================
🧪 TEST DE CONEXIÓN CON OPENAI - LEXIA
================================================================================
Verifica la lectura del archivo .env y prueba la respuesta del modelo gpt-4o-mini.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. Cargar variables del archivo .env
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

# 2. Validar que la variable de entorno exista
if not api_key:
    print("❌ ERROR: No se encontró 'OPENAI_API_KEY' en el archivo .env")
    print("👉 Asegúrate de que el archivo .env exista y tenga el formato: OPENAI_API_KEY=tu_key")
    exit(1)

print(f"🔑 Key detectada: {api_key[:8]}...{api_key[-4:]}")

# 3. Instanciar cliente de OpenAI
client = OpenAI(api_key=api_key)

# 4. Probar llamada mínima al API
try:
    print("\n📡 Conectando con la API de OpenAI...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente de pruebas de conexión."},
            {"role": "user", "content": "Responde con la frase: 'Conexión exitosa con LEXIA'"}
        ],
        max_tokens=20
    )
    
    mensaje = response.choices[0].message.content.strip()
    print("\n✅ ¡RESPUESTA RECIBIDA CON ÉXITO!")
    print(f"💬 Respuesta del modelo: '{mensaje}'")

except Exception as e:
    print(f"\n❌ ERROR AL CONECTAR CON OPENAI:\n{e}")