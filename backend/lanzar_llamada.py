import asyncio
import os
import requests
import sys
from dotenv import load_dotenv
from livekit import api

load_dotenv()

# CONFIGURACIÓN
TRONCAL_ID = "ST_UBZcusTkNdtH"
# ¡IMPORTANTE! Este nombre debe ser EXACTAMENTE el mismo que pusiste en agent.py
AGENT_NAME = "Dakota-1ef9" 
URL_SERVIDOR = "http://127.0.0.1:8001"
TIEMPO_ENTRE_LLAMADAS = 60  # Segundos de espera entre llamadas masivas (para que termine la anterior)

async def realizar_llamada(telefono):
    """Función que ejecuta UNA llamada individual"""
    print(f"\n📞 --- PROCESANDO: {telefono} ---")
    
    # 1. Crear ficha en BD
    print(f"   💾 1. Creando ficha en base de datos...")
    id_ficha = None
    try:
        resp = requests.post(f"{URL_SERVIDOR}/iniciar-encuesta", json={"telefono": telefono})
        if resp.status_code != 200:
            print(f"   ❌ Error Servidor: {resp.text}")
            return False
        data = resp.json()
        id_ficha = data["id"]
        print(f"   ✅ Ficha creada. ID: {id_ficha}")
    except Exception as e:
        print(f"   ❌ Error conexión DB: {e}")
        return False

    sala = f"encuesta_{id_ficha}"
    
    # Abrimos conexión con LiveKit una sola vez para ambas acciones (Inyectar y Llamar)
    lkapi = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )
    
    try:
        # 2. Inyectar Agente a la fuerza (Evita que el compañero robe la llamada)
        print(f"   🤖 2. Inyectando Agente ({AGENT_NAME}) en sala: {sala}...")
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=sala
            )
        )
        print("   ✅ Agente inyectado con éxito.")
        
        # 3. Dar tiempo al agente para respirar (importante para que no falle el primer audio)
        print("   ⏳ Esperando 4 segundos a que el agente cargue...")
        await asyncio.sleep(4)

        # 4. Ejecutar llamada SIP
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
        # Cerramos la conexión API limpiamente
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
        
        print(f"\n📂 Se han cargado {len(numeros)} números.")
        confirm = input("¿Empezar secuencia? (s/n): ")
        if confirm.lower() != "s": return

        print("\n🚀 INICIANDO SECUENCIA AUTOMÁTICA...")
        for i, num in enumerate(numeros, 1):
            print(f"\n🔸 Llamada {i} de {len(numeros)}")
            exito = await realizar_llamada(num)
            
            if i < len(numeros):
                print(f"💤 Esperando {TIEMPO_ENTRE_LLAMADAS} segundos para asegurar finalización antes de la siguiente...")
                await asyncio.sleep(TIEMPO_ENTRE_LLAMADAS)
        
        print("\n✨ ¡LISTA MASIVA COMPLETADA! ✨")

    elif opcion == "3":
        sys.exit()
    else:
        print("Opción no válida.")


if __name__ == "__main__":
    try:
        asyncio.run(menu_principal())
    except KeyboardInterrupt:
        print("\n👋 Saliendo...")