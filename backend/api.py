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
    
    # Tabla de configuración de AI
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            llm_provider VARCHAR(50) DEFAULT 'groq',
            llm_model VARCHAR(100) DEFAULT 'llama-3.3-70b-versatile',
            tts_provider VARCHAR(50) DEFAULT 'cartesia',
            tts_model VARCHAR(100) DEFAULT 'sonic-3',
            tts_voice VARCHAR(200) DEFAULT '6511153f-72f9-4314-a204-8d8d8afd646a',
            stt_provider VARCHAR(50) DEFAULT 'deepgram',
            stt_model VARCHAR(100) DEFAULT 'nova-3',
            language VARCHAR(10) DEFAULT 'es',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insertar configuración por defecto si no existe
    cursor.execute('SELECT COUNT(*) FROM ai_config')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO ai_config (llm_provider, llm_model, tts_provider, tts_model, tts_voice, stt_provider, stt_model, language)
            VALUES ('groq', 'llama-3.3-70b-versatile', 'cartesia', 'sonic-3', '6511153f-72f9-4314-a204-8d8d8afd646a', 'deepgram', 'nova-3', 'es')
        ''')
    
    # Tabla de configuración del agente
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) DEFAULT 'Ausarta Agent',
            use_case VARCHAR(100) DEFAULT 'Encuestas de Calidad',
            description TEXT DEFAULT 'Realiza encuestas de satisfacción',
            instructions TEXT DEFAULT 'Eres un asistente de encuestas de calidad de Ausarta.',
            greeting TEXT DEFAULT 'Hola, soy Dakota de Ausarta. ¿Tiene un minuto para una encuesta rápida?',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insertar configuración del agente por defecto si no existe
    cursor.execute('SELECT COUNT(*) FROM agent_config')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO agent_config (name, use_case, description, instructions, greeting)
            VALUES (
                'Ausarta Survey Agent',
                'Encuestas de Calidad',
                'Realiza encuestas de satisfacción a clientes',
                """Eres un asistente de encuestas de calidad de Ausarta. Tu tono es profesional, amable y eficiente.

TU MISIÓN:
1. Preséntate como Dakota de Ausarta.
2. Pregunta si tienen un momento. ESPERA RESPUESTA.
3. Haz estas 3 preguntas UNA A UNA (espera a que respondan cada una):
   - "Del 1 al 10, ¿trato comercial?"
   - "Del 1 al 10, ¿instalador?"
   - "Del 1 al 10, ¿rapidez?"
4. Pide comentario final.

REGLAS:
- No inventes datos.
- Usa 'guardar_encuesta' al final.
- Despidete y usa 'finalizar_llamada'.""",
                'Hola, soy Dakota de Ausarta. ¿Tiene un minuto para una encuesta rápida de calidad?'
            )
        ''')

    # Tabla de plantillas de prompts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompt_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insertar Template por defecto (Ausarta) si no existe
    cursor.execute('SELECT COUNT(*) FROM prompt_templates')
    if cursor.fetchone()[0] == 0:
        default_prompt = """Eres un asistente de encuestas de calidad de Ausarta. Tu tono es profesional, amable y eficiente.

TU MISIÓN:
1. Saluda cordialmente y preséntate como Dakota de Ausarta.
2. Pregunta si tienen un momento para valorar el servicio reciente. ESPERA LA RESPUESTA.
3. Si aceptan, realiza las siguientes 3 preguntas UNA POR UNA (espera la respuesta del usuario entre cada una):
   
   - PREGUNTA A: "Del 1 al 10, ¿cómo valora la atención comercial recibida?"
   - PREGUNTA B: "Del 1 al 10, ¿qué puntuación le daría al trabajo del instalador?"
   - PREGUNTA C: "Del 1 al 10, ¿cómo califica la rapidez del servicio?"

4. Finalmente, pregunta: "¿Tiene algún comentario adicional o sugerencia para mejorar?"

REGLAS CRÍTICAS:
- NO TE INVENTES LOS DATOS. Solo usa la herramienta 'guardar_encuesta' cuando hayas obtenido las 3 notas numéricas.
- Si el usuario da una nota vaga ("muy bien"), pregunta: "¿Eso sería un 9 o un 10?".
- Una vez guardados los datos, despídete amablemente y usa la herramienta 'finalizar_llamada'.
- Si el usuario dice que NO quiere participar al principio, di "Lo entiendo, gracias por su tiempo" y corta la llamada."""
        
        cursor.execute('INSERT INTO prompt_templates (name, description, content) VALUES (?, ?, ?)', 
                      ('Encuesta Calidad Ausarta', 'Guion completo con preguntas explícitas', default_prompt))
        
        cursor.execute('INSERT INTO prompt_templates (name, description, content) VALUES (?, ?, ?)', 
                      ('Agente de Ventas', 'Para cualificar leads interesados', 'Eres un vendedor experto. Tu objetivo es descubrir las necesidades del cliente y agendar una reunión.'))

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

class AIConfig(BaseModel):
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    tts_provider: str = "cartesia"
    tts_model: str = "sonic-3"
    tts_voice: str = "6511153f-72f9-4314-a204-8d8d8afd646a"
    stt_provider: str = "deepgram"
    stt_model: str = "nova-3"
    language: str = "es"

class AgentConfigModel(BaseModel):
    name: str
    use_case: str
    description: str
    instructions: str
    greeting: str

class PromptTemplateModel(BaseModel):
    name: str
    description: str
    content: str

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
    """Obtiene el agente único configurado"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM agent_config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return [{
                "id": "1",
                "name": row[1],
                "callType": "Outbound",
                "useCase": row[2],
                "description": row[3],
                "instructions": row[4],
                "greeting": row[5]
            }]
        return []
    finally:
        cursor.close()
        conn.close()

@app.put("/api/agents/1")
async def update_agent(agent: AgentConfigModel):
    """Actualiza la configuración del agente"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE agent_config 
            SET name=?, use_case=?, description=?, instructions=?, greeting=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=1
        ''', (agent.name, agent.use_case, agent.description, agent.instructions, agent.greeting))
        conn.commit()
        print(f"✅ Configuración del agente actualizada: {agent.name}")
        return {"status": "success", "agent": agent}
    finally:
        cursor.close()
        conn.close()

@app.get("/api/prompts")
async def get_prompts():
    """Obtiene todas las plantillas de prompts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM prompt_templates ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        cursor.close()
        conn.close()

@app.post("/api/prompts")
async def create_prompt(template: PromptTemplateModel):
    """Crea una nueva plantilla de prompt"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO prompt_templates (name, description, content) VALUES (?, ?, ?)",
            (template.name, template.description, template.content)
        )
        conn.commit()
        return {"status": "success", "id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()

@app.post("/api/telephony/config")
async def save_telephony_config(config: TelephonyConfig):
    """Guarda la configuración de telefonía"""
    # Guardar en variables de entorno o DB
    return {"status": "success", "config": config}

@app.get("/api/ai/config")
async def get_ai_config():
    """Obtiene la configuración de AI actual"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM ai_config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return {
                "llm_provider": row[1],
                "llm_model": row[2],
                "tts_provider": row[3],
                "tts_model": row[4],
                "tts_voice": row[5],
                "stt_provider": row[6],
                "stt_model": row[7],
                "language": row[8]
            }
        return {}
    finally:
        cursor.close()
        conn.close()

@app.post("/api/ai/config")
async def save_ai_config(config: AIConfig):
    """Guarda la configuración de AI"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Actualizar o insertar
        cursor.execute("SELECT COUNT(*) FROM ai_config")
        if cursor.fetchone()[0] > 0:
            cursor.execute('''
                UPDATE ai_config 
                SET llm_provider=?, llm_model=?, tts_provider=?, tts_model=?, 
                    tts_voice=?, stt_provider=?, stt_model=?, language=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=1
            ''', (config.llm_provider, config.llm_model, config.tts_provider, config.tts_model,
                  config.tts_voice, config.stt_provider, config.stt_model, config.language))
        else:
            cursor.execute('''
                INSERT INTO ai_config (llm_provider, llm_model, tts_provider, tts_model, tts_voice, stt_provider, stt_model, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (config.llm_provider, config.llm_model, config.tts_provider, config.tts_model,
                  config.tts_voice, config.stt_provider, config.stt_model, config.language))
        
        conn.commit()
        print(f"✅ Configuración de AI guardada: LLM={config.llm_provider}, TTS={config.tts_provider}, STT={config.stt_provider}")
        return {"status": "success", "config": config}
    finally:
        cursor.close()
        conn.close()

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Obtiene estadísticas generales del dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Total de llamadas
        cursor.execute("SELECT COUNT(*) FROM encuestas")
        total_llamadas = cursor.fetchone()[0]
        
        # Llamadas completadas
        cursor.execute("SELECT COUNT(*) FROM encuestas WHERE completada = 1")
        completadas = cursor.fetchone()[0]
        
        # Promedio de puntuaciones
        cursor.execute("""
            SELECT 
                AVG(puntuacion_comercial) as avg_comercial,
                AVG(puntuacion_instalador) as avg_instalador,
                AVG(puntuacion_rapidez) as avg_rapidez
            FROM encuestas 
            WHERE completada = 1
        """)
        row = cursor.fetchone()
        
        return {
            "total_calls": total_llamadas,
            "completed_calls": completadas,
            "pending_calls": total_llamadas - completadas,
            "avg_scores": {
                "comercial": round(row[0], 2) if row[0] else 0,
                "instalador": round(row[1], 2) if row[1] else 0,
                "rapidez": round(row[2], 2) if row[2] else 0,
                "overall": round((row[0] + row[1] + row[2]) / 3, 2) if row[0] else 0
            }
        }
    finally:
        cursor.close()
        conn.close()

@app.get("/api/dashboard/recent-calls")
async def get_recent_calls():
    """Obtiene las últimas llamadas realizadas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, telefono, fecha, completada, 
                   puntuacion_comercial, puntuacion_instalador, puntuacion_rapidez
            FROM encuestas 
            ORDER BY fecha DESC 
            LIMIT 10
        """)
        rows = cursor.fetchall()
        
        calls = []
        for row in rows:
            calls.append({
                "id": row[0],
                "phone": row[1],
                "date": row[2],
                "status": "completed" if row[3] == 1 else "pending",
                "scores": {
                    "comercial": row[4],
                    "instalador": row[5],
                    "rapidez": row[6]
                }
            })
        
        return calls
    finally:
        cursor.close()
        conn.close()

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
