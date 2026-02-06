import asyncio
import os
import subprocess
import requests
from dotenv import load_dotenv
from livekit import api

load_dotenv()

MI_MOVIL = "+34686024728"
TRONCAL_ID = "ST_UBZcusTkNdtH"
AGENT_NAME = "Dakota-1ef9" 

# USAMOS LOCALHOST PORQUE ESTAMOS EN LA MISMA MÁQUINA
URL_SERVIDOR = "http://127.0.0.1:8001"

async def lanzar_todo():
    print(f"\n💾 1. Contactando con servidor local para guardar {MI_MOVIL}...")
    
    id_ficha = None
    try:
        # Petición al endpoint /iniciar-encuesta
        resp = requests.post(f"{URL_SERVIDOR}/iniciar-encuesta", json={"telefono": MI_MOVIL})
        
        # --- DEBUG: VER QUÉ RESPONDE EL SERVIDOR ---
        print(f"   📡 Respuesta del servidor: {resp.text}") 
        
        if resp.status_code != 200:
            print("   ❌ El servidor devolvió un error (No es 200 OK).")
            return

        data = resp.json()
        
        if "id" not in data:
            print(f"   ❌ ERROR CLAVE: El servidor respondió JSON pero falta la clave 'id'. Datos: {data}")
            return

        id_ficha = data["id"]
        print(f"   ✅ ID Recibido: {id_ficha}")

    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return

    # 2. Sala con el ID
    sala = f"encuesta_{id_ficha}"
    
    print(f"🤖 2. Despertando agente en sala: {sala}...")
    try:
        subprocess.run(["lk", "dispatch", "create", "--room", sala, "--agent-name", AGENT_NAME], check=True, capture_output=True)
    except: pass

    # 3. Llamada
    print(f"📞 3. Llamando...")
    lkapi = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )

    await lkapi.sip.create_sip_participant(
        api.CreateSIPParticipantRequest(
            room_name=sala,
            sip_trunk_id=TRONCAL_ID,
            sip_call_to=MI_MOVIL,
            participant_identity="Cliente",
        )
    )
    await lkapi.aclose()
    print("🚀 ¡Llamada en curso!")

if __name__ == "__main__":
    asyncio.run(lanzar_todo())