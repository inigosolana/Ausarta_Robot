import asyncio
import os
import requests
import sys
from dotenv import load_dotenv
from livekit import api

load_dotenv()

# CONFIGURACIÓN
TRONCAL_ID = "ST_UBZcusTkNdtH"
AGENT_NAME = "Dakota-1ef9" # <--- TU NOMBRE DE AGENTE
URL_SERVIDOR = "http://127.0.0.1:8001"
TIEMPO_ENTRE_LLAMADAS = 60

async def realizar_llamada(telefono):
    print(f"\n📞 --- PROCESANDO: {telefono} ---")
    
    # 1. Crear ficha en BD
    print(f"   💾 1. Creando ficha en base de datos...")
    id_ficha = None
    try:
        resp = requests.post(f"{URL_SERVIDOR}/iniciar-encuesta", json={"telefono": telefono})
        if resp.status_code != 200:
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
        # 2. Inyectar Agente a la fuerza (NUEVO MÉTODO)
        print(f"   🤖 2. Inyectando Agente ({AGENT_NAME}) en sala: {sala}...")
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=sala
            )
        )
        print("   ✅ Agente inyectado con éxito.")
        
        print("   ⏳ Esperando 4 segundos a que el agente cargue...")
        await asyncio.sleep(4)

        # 3. Ejecutar llamada SIP
        print(f"   📡 3. Marcando número SIP...")
        sip_trunk = TRONCAL_ID if TRONCAL_ID else "ST_UBZcusTkNdtH"

        await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=sala,
                sip_trunk_id=sip_trunk,
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

async def menu_principal():
    print("\n" + "="*40)
    print(" 📞  CENTRALITA DE ENCUESTAS AUSARTA")
    print("="*40)
    print("1. 👤 Encuesta INDIVIDUAL (Introducir número)")
    print("2. 📋 Encuesta MASIVA (Desde lista_telefonos.txt)")
    print("3. ❌ Salir")
    
    opcion = input("\n👉 Elige una opción (1-3): ")

    if opcion == "1":
        numero = input("Introduce el número (ej: +34600111222): ").strip()
        if not numero: return
        await realizar_llamada(numero)

    elif opcion == "2":
        archivo = "lista_telefonos.txt"
        if not os.path.exists(archivo):
            print(f"❌ No encuentro el archivo '{archivo}'. Créalo primero.")
            return

        with open(archivo, "r") as f:
            numeros = [line.strip() for line in f if line.strip()]
        
        confirm = input(f"\n📂 Se han cargado {len(numeros)} números. ¿Empezar secuencia? (s/n): ")
        if confirm.lower() != "s": return

        print("\n🚀 INICIANDO SECUENCIA AUTOMÁTICA...")
        exitosas = 0
        fallidas = 0
        for i, num in enumerate(numeros, 1):
            print(f"\n🔸 Llamada {i} de {len(numeros)}")
            ok = await realizar_llamada(num)
            if ok:
                exitosas += 1
            else:
                fallidas += 1
            if i < len(numeros):
                print(f"💤 Esperando {TIEMPO_ENTRE_LLAMADAS} segundos...")
                await asyncio.sleep(TIEMPO_ENTRE_LLAMADAS)
        
        print(f"\n✨ ¡LISTA MASIVA COMPLETADA! ✅ Exitosas: {exitosas} | ❌ Fallidas: {fallidas}")

    elif opcion == "3":
        sys.exit()

if __name__ == "__main__":
    try:
        asyncio.run(menu_principal())
    except KeyboardInterrupt:
        print("\n👋 Saliendo...")