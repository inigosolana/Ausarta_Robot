import asyncio
import os
import requests
import sys
from dotenv import load_dotenv
from livekit import api

load_dotenv()

# CONFIGURACIÓN
TRONCAL_ID = "ST_UBZcusTkNdtH"
AGENT_NAME = "Dakota-1ef9"
URL_SERVIDOR = "http://127.0.0.1:8001"

async def realizar_llamada(telefono):
    print(f"\n📞 --- PROCESANDO: {telefono} ---")

    # 1. Crear ficha en BD
    print("   💾 1. Creando ficha en base de datos...")
    try:
        resp = requests.post(f"{URL_SERVIDOR}/iniciar-encuesta", json={"telefono": telefono})
        if resp.status_code != 200:
            print(f"   ❌ Error del servidor: {resp.status_code} - {resp.text}")
            return False
        id_ficha = resp.json()["id"]
        print(f"   ✅ Ficha creada. ID: {id_ficha}")
    except Exception as e:
        print(f"   ❌ Error conexión DB: {e}")
        return False

    sala = f"encuesta_{id_ficha}"

    lkapi = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )

    try:
        # 2. Inyectar Agente
        print(f"   🤖 2. Inyectando Agente ({AGENT_NAME}) en sala: {sala}...")
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=sala
            )
        )
        print("   ✅ Agente inyectado.")

        print("   ⏳ Esperando 4 segundos a que el agente cargue...")
        await asyncio.sleep(4)

        # 3. Llamada SIP
        print("   📡 3. Marcando número SIP...")
        await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=sala,
                sip_trunk_id=TRONCAL_ID,
                sip_call_to=telefono,
                participant_identity="Cliente",
            )
        )
        print(f"   🚀 ¡Llamada lanzada a {telefono}!")
        return True

    except Exception as e:
        print(f"   ❌ Error en LiveKit API: {e}")
        return False

    finally:
        await lkapi.aclose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python lanzar_llamada.py +34600111222")
        sys.exit(1)

    telefono = sys.argv[1]
    try:
        asyncio.run(realizar_llamada(telefono))
    except KeyboardInterrupt:
        print("\n👋 Cancelado.")