import os
from groq import Groq

API_KEY = os.environ.get("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Set the GROQ_API_KEY environment variable before running this test.")

client = Groq(api_key=API_KEY)

try:
    print("🔍 Consultando modelos disponibles en tu cuenta de Groq...")
    modelos = client.models.list()
    
    lista_modelos = [m.id for m in modelos.data]
    print("\n✅ Modelos activos encontrados en tu API Key:")
    for m in lista_modelos:
        print(f" - {m}")

    # Seleccionar el primer modelo disponible para probar
    modelo_prueba = lista_modelos[0]
    print(f"\n🚀 Probando inferencia con: {modelo_prueba}...")
    
    res = client.chat.completions.create(
        messages=[{"role": "user", "content": "Hola"}],
        model=modelo_prueba
    )
    print(f"✅ ¡ÉXITO! Respuesta: {res.choices[0].message.content}")

except Exception as e:
    print(f"\n❌ Error al consultar la API: {e}")