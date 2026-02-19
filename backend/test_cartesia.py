"""
Script de diagnóstico para verificar que Cartesia TTS funciona correctamente.
Ejecutar DENTRO del contenedor:
  docker exec -it <nombre_contenedor_agente> python /app/test_cartesia.py

O localmente si tienes las dependencias:
  python backend/test_cartesia.py
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
VOICE_ID = "fb926b21-4d92-411a-85d0-9d06859e2171"
MODEL = "sonic-multilingual"

print("\n" + "="*50)
print("  DIAGNÓSTICO CARTESIA TTS")
print("="*50)

# 1. Verificar API key
if not CARTESIA_API_KEY:
    print("❌ CARTESIA_API_KEY no está definida en las variables de entorno")
    exit(1)
print(f"✅ API Key encontrada: {CARTESIA_API_KEY[:8]}...{CARTESIA_API_KEY[-4:]}")

# 2. Listar voces disponibles
print("\n📋 Obteniendo lista de voces disponibles...")
try:
    resp = requests.get(
        "https://api.cartesia.ai/voices",
        headers={
            "X-API-Key": CARTESIA_API_KEY,
            "Cartesia-Version": "2024-06-10"
        },
        timeout=10
    )
    if resp.status_code == 200:
        voices = resp.json()
        print(f"✅ {len(voices)} voces disponibles en tu cuenta")
        # Buscar el voice ID que usamos
        voice_found = any(v.get("id") == VOICE_ID for v in voices)
        if voice_found:
            voice_name = next(v.get("name", "?") for v in voices if v.get("id") == VOICE_ID)
            print(f"✅ Voice ID '{VOICE_ID}' ENCONTRADO: '{voice_name}'")
        else:
            print(f"❌ Voice ID '{VOICE_ID}' NO ENCONTRADO en tu cuenta!")
            print("   Voces disponibles:")
            for v in voices[:5]:
                print(f"   - {v.get('id')} → {v.get('name')}")
    elif resp.status_code == 401:
        print(f"❌ API Key INVÁLIDA o sin permisos (401 Unauthorized)")
        print(f"   Respuesta: {resp.text[:200]}")
    elif resp.status_code == 403:
        print(f"❌ API Key sin acceso (403 Forbidden) - puede ser plan gratuito expirado")
        print(f"   Respuesta: {resp.text[:200]}")
    else:
        print(f"⚠️ Respuesta inesperada: {resp.status_code} - {resp.text[:200]}")
except Exception as e:
    print(f"❌ Error de conexión con Cartesia: {e}")
    exit(1)

# 3. Probar generación de audio HTTP
print(f"\n🎙️ Probando generación de audio con voz '{VOICE_ID}'...")
try:
    resp = requests.post(
        "https://api.cartesia.ai/tts/bytes",
        headers={
            "X-API-Key": CARTESIA_API_KEY,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json"
        },
        json={
            "model_id": MODEL,
            "transcript": "Hola, esto es una prueba.",
            "voice": {"mode": "id", "id": VOICE_ID},
            "output_format": {"container": "wav", "encoding": "pcm_f32le", "sample_rate": 44100},
            "language": "es"
        },
        timeout=15
    )
    if resp.status_code == 200:
        audio_size = len(resp.content)
        print(f"✅ Audio generado correctamente: {audio_size} bytes ({audio_size//1024} KB)")
        # Guardar para verificar
        with open("/tmp/cartesia_test.wav", "wb") as f:
            f.write(resp.content)
        print("✅ Audio guardado en /tmp/cartesia_test.wav")
    elif resp.status_code == 422:
        print(f"❌ Error de validación (422): {resp.text[:300]}")
        print("   Posible causa: voice ID inválido o parámetros incorrectos")
    elif resp.status_code == 402:
        print(f"❌ Sin créditos/quota (402): {resp.text[:300]}")
        print("   Tu plan de Cartesia puede haber agotado los créditos")
    else:
        print(f"❌ Error {resp.status_code}: {resp.text[:300]}")
except Exception as e:
    print(f"❌ Error generando audio: {e}")

print("\n" + "="*50)
