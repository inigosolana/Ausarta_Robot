import os
import requests
from dotenv import load_dotenv

load_dotenv()

CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
VOICE_ID = "fb926b21-4d92-411a-85d0-9d06859e2171"
MODEL = "sonic-multilingual"

print("\n" + "="*50)
print("  DIAGNOSTICO CARTESIA TTS")
print("="*50)

# 1. Verificar API key
if not CARTESIA_API_KEY:
    print("[X] CARTESIA_API_KEY no esta definida en las variables de entorno")
    exit(1)
print(f"[OK] API Key encontrada: {CARTESIA_API_KEY[:8]}...{CARTESIA_API_KEY[-4:]}")

# 2. Listar voces disponibles
print("\n[i] Obteniendo lista de voces disponibles...")
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
        print(f"[OK] {len(voices)} voces disponibles en tu cuenta")
        voice_found = any(v.get("id") == VOICE_ID for v in voices)
        if voice_found:
            voice_name = next(v.get("name", "?") for v in voices if v.get("id") == VOICE_ID)
            print(f"[OK] Voice ID '{VOICE_ID}' ENCONTRADO: '{voice_name}'")
        else:
            print(f"[X] Voice ID '{VOICE_ID}' NO ENCONTRADO en tu cuenta!")
    elif resp.status_code == 401:
        print(f"[X] API Key INVALIDA o sin permisos (401 Unauthorized)")
    elif resp.status_code == 403:
        print(f"[X] API Key sin acceso (403 Forbidden)")
    else:
        print(f"[!] Respuesta inesperada: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"[X] Error de conexion con Cartesia: {e}")
    exit(1)

# 3. Probar generacion de audio HTTP
print(f"\n[i] Probando generacion de audio con voz '{VOICE_ID}'...")
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
        print(f"[OK] Audio generado correctamente: {audio_size} bytes")
    elif resp.status_code == 402:
        print(f"[X] Sin creditos/quota (402): Tu plan de Cartesia puede haber agotado los creditos")
    else:
        print(f"[X] Error {resp.status_code}: {resp.text[:200]}")
except Exception as e:
    print(f"[X] Error generando audio: {e}")

print("\n" + "="*50)
