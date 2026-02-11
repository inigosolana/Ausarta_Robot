import os
import asyncio
from dotenv import load_dotenv
from livekit.plugins import google

async def list_models():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: No se encontró GOOGLE_API_KEY en el .env")
        return

    print(f"🔍 Investigando modelos para la clave: {api_key[:5]}...{api_key[-4:]}")
    
    try:
        # Intentamos usar el cliente interno para listar
        from google import genai
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
        
        print("\n--- Modelos Disponibles en tu Cuenta ---")
        async for model in client.models.list():
            if "gemini" in model.name.lower():
                print(f"✅ {model.name} (Soportado: {model.supported_generation_methods})")
        
        print("\n---------------------------------------")
        print("💡 CONSEJO: El nombre que ves arriba es el que debemos poner EXACTAMENTE en el código.")

    except Exception as e:
        print(f"❌ Falló la autodetección: {e}")
        print("\nIntentando prueba de fuego con nombres comunes...")
        
        for test_name in ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-1.5-flash-latest"]:
            try:
                llm = google.LLM(model=test_name, api_key=api_key)
                print(f"❓ Probando '{test_name}'...")
                # No podemos hacer una petición real sin room, pero el error 404 suele saltar al init o al primer uso.
            except Exception as e2:
                print(f"   ❌ '{test_name}' falla: {e2}")

if __name__ == "__main__":
    asyncio.run(list_models())
