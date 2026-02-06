from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sqlite3
import os
import re
import asyncio
from datetime import datetime
from typing import Optional, Union
from dotenv import load_dotenv
from livekit import api

load_dotenv()
app = FastAPI(title="Ausarta Voice Agent API", version="1.0.0")

# CORS para permitir requests del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica el dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONEXIÓN DB SQLite ---
DB_PATH = os.getenv('DB_PATH', '/app/data/encuestas.db')

def get_db_connection():
    """Obtiene conexión a SQLite"""
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Inicializa la base de datos SQLite si no existe"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS encuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono VARCHAR(20) NOT NULL,
            fecha DATETIME NOT NULL,
            completada INTEGER DEFAULT 0,
            puntuacion_comercial INTEGER DEFAULT NULL,
            puntuacion_instalador INTEGER DEFAULT NULL,
            puntuacion_rapidez INTEGER DEFAULT NULL,
            comentarios TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crear índices
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_telefono ON encuestas(telefono)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fecha ON encuestas(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_completada ON encuestas(completada)')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos SQLite inicializada correctamente")

# Inicializar BD al arrancar
init_database()

# --- MODELOS PYDANTIC ---
class VoiceAgentCreate(BaseModel):
    name: str
    callType: str  # 'Inbound' o 'Outbound'
    useCase: str
    description: str

class OutboundCallRequest(BaseModel):
    agentId: str
    phoneNumber: str
    agentName: Optional[str] = "Dakota-1ef9"

class TelephonyConfig(BaseModel):
    provider: str
    fromNumbers: str
    sipTrunkId: Optional[str] = None

class InicioEncuesta(BaseModel):
    telefono: str

class FinEncuesta(BaseModel):
    id_encuesta: Union[int, str, None] = None
    nota_comercial: Union[int, str, None] = None
    nota_instalador: Union[int, str, None] = None
    nota_rapidez: Union[int, str, None] = None
    comentarios: Optional[str] = "Sin comentarios"

class ColgarLlamada(BaseModel):
    nombre_sala: str

# --- EXCEPTION HANDLER ---
@app.exception_handler(Exception)
async def validation_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

# --- ENDPOINTS DEL FRONTEND ---

@app.get("/")
async def root():
    return {"message": "Ausarta Voice Agent API", "status": "running"}

@app.get("/api/agents")
async def get_agents():
    """Lista todos los agentes de voz configurados"""
    # Por ahora devolvemos un mock, luego podemos persistir en DB
    return [
        {
            "id": "1",
            "name": "Real Estate Qualifier",
            "callType": "Outbound",
            "useCase": "Lead Gen",
            "description": "Qualifies leads for real estate investment."
        }
    ]

@app.post("/api/agents")
async def create_agent(agent: VoiceAgentCreate):
    """Crea un nuevo agente de voz"""
    # Aquí podríamos guardarlo en la DB
    return {
        "id": "generated-id",
        "name": agent.name,
        "callType": agent.callType,
        "useCase": agent.useCase,
        "description": agent.description,
        "status": "created"
    }

@app.post("/api/telephony/config")
async def save_telephony_config(config: TelephonyConfig):
    """Guarda la configuración de telefonía"""
    # Guardar en variables de entorno o DB
    return {"status": "success", "config": config}

@app.post("/api/calls/outbound")
async def make_outbound_call(call_request: OutboundCallRequest):
    """
    Lanza una llamada outbound usando el sistema del AgenteLocal
    """
    try:
        print(f"📞 Iniciando llamada outbound a {call_request.phoneNumber}")
        
        # 1. Crear ficha en DB
        id_ficha = None
        try:
            resp_inicio = await iniciar_encuesta(InicioEncuesta(telefono=call_request.phoneNumber))
            id_ficha = resp_inicio["id"]
            print(f"✅ Ficha creada con ID: {id_ficha}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creando ficha: {e}")
        
        # 2. Crear sala
        sala = f"encuesta_{id_ficha}"
        
        # 3. Crear API de LiveKit
        lkapi = api.LiveKitAPI(
            os.getenv("LIVEKIT_URL"),
            os.getenv("LIVEKIT_API_KEY"),
            os.getenv("LIVEKIT_API_SECRET"),
        )
        
        # 4. Despertar agente usando la API
        print(f"🤖 Despertando agente en sala: {sala}")
        try:
            await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    room=sala,
                    agent_name=call_request.agentName,
                )
            )
            print(f"✅ Agente despachado correctamente")
        except Exception as e:
            print(f"⚠️ Warning al despachar agente: {e}")
        
        # 5. Crear llamada SIP
        print(f"📞 Creando participante SIP...")
        
        trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID", "ST_UBZcusTkNdtH")
        
        await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=sala,
                sip_trunk_id=trunk_id,
                sip_call_to=call_request.phoneNumber,
                participant_identity="Cliente",
            )
        )
        await lkapi.aclose()
        
        print("🚀 ¡Llamada en curso!")
        
        return {
            "status": "success",
            "callId": id_ficha,
            "roomName": sala,
            "phoneNumber": call_request.phoneNumber
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al lanzar llamada: {str(e)}")

# --- ENDPOINTS DEL BRIDGE SERVER (para el agente) ---

@app.post("/iniciar-encuesta")
async def iniciar_encuesta(datos: InicioEncuesta):
    print(f"📝 1. Creando ficha para: {datos.telefono}")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO encuestas (telefono, fecha, completada) VALUES (?, ?, 0)", (datos.telefono, datetime.now()))
        conn.commit()
        nuevo_id = cursor.lastrowid
        print(f"✅ Ficha creada con ID: {nuevo_id} (Esperando a la IA...)")
        return {"id": nuevo_id}
    finally:
        cursor.close()
        conn.close()

@app.post("/guardar-encuesta")
async def guardar_encuesta(datos: FinEncuesta):
    print(f"📥 2. Recibiendo datos. La IA dice ID: {datos.id_encuesta}")
    
    def clean_nota(val):
        try:
            num = int(val)
            if 1 <= num <= 10: return num
            return None 
        except: return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        id_final = None
        try:
            nums = re.findall(r'\d+', str(datos.id_encuesta))
            if nums and int(nums[0]) > 0: id_final = int(nums[0])
        except: pass

        if not id_final:
            print("🔍 ID IA no válido. Buscando última ficha abierta...")
            cursor.execute("SELECT id FROM encuestas WHERE completada = 0 ORDER BY id DESC LIMIT 1")
            res = cursor.fetchone()
            if res:
                id_final = res[0]
                print(f"💡 ¡ENCONTRADO! Usaremos la ficha {id_final}.")
            else:
                cursor.execute("SELECT id FROM encuestas ORDER BY id DESC LIMIT 1")
                res_last = cursor.fetchone()
                if res_last: id_final = res_last[0]

        if not id_final: return {"status": "error", "msg": "No ID found"}

        cursor.execute(
            """UPDATE encuestas 
               SET puntuacion_comercial=?, puntuacion_instalador=?, puntuacion_rapidez=?, comentarios=?, completada=1
               WHERE id=?""",
            (clean_nota(datos.nota_comercial), clean_nota(datos.nota_instalador), clean_nota(datos.nota_rapidez), datos.comentarios, id_final)
        )
        conn.commit()
        print(f"🚀 ¡EXITO! Datos guardados en ficha {id_final}.")
        return {"status": "success"}
    finally:
        cursor.close()
        conn.close()

@app.post("/colgar")
async def colgar(datos: ColgarLlamada):
    print(f"✂️  Petición de colgar recibida.")
    
    # Pausa para dar tiempo a la despedida
    print("⏳ Esperando 2 segundos para dar tiempo a la despedida...")
    await asyncio.sleep(2) 

    lkapi = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )
    
    try:
        await lkapi.room.delete_room(api.DeleteRoomRequest(room=datos.nombre_sala))
        print("✅ Llamada cortada.")
        return {"status": "success"}
    except Exception as e:
        print(f"⚠️ Falló borrar '{datos.nombre_sala}'. Buscando la sala REAL...")
        
        # Auto-reparación
        conn = get_db_connection()
        cursor = conn.cursor()
        sala_real = None
        try:
            cursor.execute("SELECT id FROM encuestas ORDER BY id DESC LIMIT 1")
            resultado = cursor.fetchone()
            if resultado:
                sala_real = f"encuesta_{resultado[0]}"
        except: pass
        finally:
            cursor.close()
            conn.close()

        if sala_real and sala_real != datos.nombre_sala:
            print(f"💡 Re-intentando con sala real: {sala_real}...")
            try:
                await lkapi.room.delete_room(api.DeleteRoomRequest(room=sala_real))
                print(f"✅ ¡SALVADO! Llamada {sala_real} cortada.")
                return {"status": "success_repaired"}
            except: pass
            
        return {"status": "error"}
    finally:
        await lkapi.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
