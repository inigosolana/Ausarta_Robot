from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sqlite3
import os
import re
import asyncio
from datetime import datetime
from typing import Optional, Union, List
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
            transcription TEXT DEFAULT NULL,
            tokens_used INTEGER DEFAULT 0,
            seconds_used INTEGER DEFAULT 0,
            nombre_cliente VARCHAR(100) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # NEW: Campaigns Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            agent_id INTEGER,
            status VARCHAR(20) DEFAULT 'pending',
            scheduled_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaign_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            phone_number VARCHAR(20),
            status VARCHAR(20) DEFAULT 'pending', -- pending, called, failed, completed
            call_id INTEGER, -- ID de la encuesta asociada
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
        )
    ''')

    # Tabla de configuración de AI
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            llm_provider VARCHAR(50) DEFAULT 'groq',
            llm_model VARCHAR(100) DEFAULT 'llama-3.3-70b-versatile',
            tts_provider VARCHAR(50) DEFAULT 'cartesia',
            tts_model VARCHAR(100) DEFAULT 'sonic-multilingual',
            tts_voice VARCHAR(200) DEFAULT 'fb926b21-4d92-411a-85d0-9d06859e2171',
            stt_provider VARCHAR(50) DEFAULT 'deepgram',
            stt_model VARCHAR(100) DEFAULT 'nova-2',
            language VARCHAR(10) DEFAULT 'es',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insertar configuración por defecto si no existe
    cursor.execute('SELECT COUNT(*) FROM ai_config')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO ai_config (llm_provider, llm_model, tts_provider, tts_model, tts_voice, stt_provider, stt_model, language)
            VALUES ('groq', 'llama-3.3-70b-versatile', 'cartesia', 'sonic-multilingual', 'fb926b21-4d92-411a-85d0-9d06859e2171', 'deepgram', 'nova-2', 'es')
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
1. Saluda cordialmente y preséntate como Dakota de Ausarta.
2. Pregunta si tienen un momento. ESPERA RESPUESTA.
3. Haz estas 3 preguntas UNA A UNA (espera a que respondan cada una):
   - "Del 1 al 10, ¿trato comercial?" -> TRAS RECIBIR NOTA, usa 'guardar_encuesta(nota_comercial=X)'.
   - "Del 1 al 10, ¿instalador?" -> TRAS RECIBIR NOTA, usa 'guardar_encuesta(nota_instalador=X)'.
   - "Del 1 al 10, ¿rapidez?" -> TRAS RECIBIR NOTA, usa 'guardar_encuesta(nota_rapidez=X)'.
4. Pide comentario final. Tras recibirlo, usa 'guardar_encuesta(comentarios=X, status="completed")'.

REGLAS CRÍTICAS:
- NUNCA digas números de sala ni IDs técnicos.
- NO REPITAS las notas que te diga el cliente.
- Tras guardar con status='completed', di "Gracias, que tenga un buen día. Adiós" y usa 'finalizar_llamada'.
- Usa 'guardar_encuesta' INMEDIATAMENTE tras cada dato obtenido.
- Di siempre "UNO" para el número 1.""",
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

    # Tabla de alertas del sistema (ej: API Limits)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type VARCHAR(50) NOT NULL, -- 'api_limit', 'error', 'info'
            message TEXT NOT NULL,
            is_active TINYINT(1) DEFAULT 1,
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
- NO TE INVENTES LOS DATOS. Solo usa la herramienta 'guardar_encuesta' cuando hayas obtenido las notas.
- NO REPITAS las notas del cliente. Pasa a la siguiente pregunta de forma fluida.
- Si el usuario da una nota vaga ("muy bien"), pregunta: "¿Eso sería un 9 o un 10?".
- Una vez guardados los datos o si no hay comentario adicional, di "Muchas gracias por su tiempo. Que tenga un buen día. Adiós" y usa la herramienta 'finalizar_llamada'.
- NUNCA digas el ID de la encuesta ni el nombre de la sala.
- Si el usuario dice que NO quiere participar al principio, di "Lo entiendo, gracias por su tiempo. Adiós" y corta la llamada."""
        
        cursor.execute('INSERT INTO prompt_templates (name, description, content) VALUES (?, ?, ?)', 
                      ('Encuesta Calidad Ausarta', 'Guion completo con preguntas explícitas', default_prompt))
        
        cursor.execute('INSERT INTO prompt_templates (name, description, content) VALUES (?, ?, ?)', 
                      ('Agente de Ventas', 'Para cualificar leads interesados', 'Eres un vendedor experto. Tu objetivo es descubrir las necesidades del cliente y agendar una reunión.'))

    # Crear índices
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_telefono ON encuestas(telefono)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fecha ON encuestas(fecha)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_completada ON encuestas(completada)')
    
    # Migración: Añadir campo cliente a tablas existentes si no existe
    migraciones = [
        ("ALTER TABLE campaign_leads ADD COLUMN customer_name VARCHAR(100)", "camp_leads_cust"),
        ("ALTER TABLE encuestas ADD COLUMN nombre_cliente VARCHAR(100)", "enc_cust"),
        ("ALTER TABLE campaigns ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "camp_upd"),
        ("ALTER TABLE campaign_leads ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "lead_upd"),
        ("ALTER TABLE encuestas ADD COLUMN transcription TEXT", "enc_trans"),
        ("ALTER TABLE encuestas ADD COLUMN tokens_used INTEGER DEFAULT 0", "enc_tok"),
        ("ALTER TABLE encuestas ADD COLUMN seconds_used INTEGER DEFAULT 0", "enc_sec"),
        ("ALTER TABLE campaigns ADD COLUMN retries_count INTEGER DEFAULT 3", "camp_retry_count"),
        ("ALTER TABLE campaigns ADD COLUMN retry_interval INTEGER DEFAULT 180", "camp_retry_interval"),
        ("ALTER TABLE campaign_leads ADD COLUMN retries_attempted INTEGER DEFAULT 0", "lead_tries"),
        ("ALTER TABLE campaign_leads ADD COLUMN last_call_at TIMESTAMP DEFAULT NULL", "lead_last"),
        ("ALTER TABLE campaign_leads ADD COLUMN next_retry_at TIMESTAMP DEFAULT NULL", "lead_next")
    ]
    
    for sql, name in migraciones:
        try:
            cursor.execute(sql)
            print(f"📦 [DB] Migración aplicada: {name}")
        except sqlite3.OperationalError:
            pass # Ya existe
        except Exception as e:
            print(f"⚠️ [DB] Error en migración {name}: {e}")

    # ARREGLAR MODELOS SI ESTÁN MAL (MIGRACIÓN MANUAL)
    cursor.execute("UPDATE ai_config SET llm_model = 'llama-3.3-70b-versatile' WHERE llm_model = 'llama-3.1-8b-instant'")
    cursor.execute("UPDATE ai_config SET tts_model = 'sonic-multilingual' WHERE tts_model LIKE 'sonic-3%'")
    cursor.execute("UPDATE ai_config SET stt_model = 'nova-2' WHERE stt_model LIKE 'nova-3%'")
    
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
    customerName: Optional[str] = None
    agentName: Optional[str] = "Dakota-1ef9"

class TelephonyConfig(BaseModel):
    provider: str
    fromNumbers: str
    sipTrunkId: Optional[str] = None

class AIConfig(BaseModel):
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    tts_provider: str = "cartesia"
    tts_model: str = "sonic-multilingual"
    tts_voice: str = "fb926b21-4d92-411a-85d0-9d06859e2171"
    stt_provider: str = "deepgram"
    stt_model: str = "nova-2"
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
    
class CampaignModel(BaseModel):
    name: str
    agent_id: Optional[int] = 1
    scheduled_time: Optional[str] = None # ISO format
    status: str = "pending" # pending, running, completed, paused
    retries_count: Optional[int] = 3
    retry_interval: Optional[int] = 180 # minutes


class CampaignUpdateModel(BaseModel):
    name: Optional[str] = None
    agent_id: Optional[int] = None
    scheduled_time: Optional[str] = None
    status: Optional[str] = None

class CampaignLeadModel(BaseModel):
    phone_number: str
    customer_name: Optional[str] = None

class InicioEncuesta(BaseModel):
    telefono: str
    nombre_cliente: Optional[str] = None

class FinEncuesta(BaseModel):
    id_encuesta: Union[int, str, None] = None
    nota_comercial: Union[int, str, None] = None
    nota_instalador: Union[int, str, None] = None
    nota_rapidez: Union[int, str, None] = None
    comentarios: Optional[str] = None
    transcription: Optional[str] = None
    status: Optional[str] = None # 'completed', 'failed', etc.
    tokens_used: Optional[int] = 0
    seconds_used: Optional[int] = 0

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

# --- DASHBOARD ENDPOINTS ---

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM encuestas")
    total_calls = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM encuestas WHERE completada = 1")
    completed_calls = cursor.fetchone()[0]
    
    # Pendientes: contar leads en estado 'pending' de todas las campañas
    cursor.execute("SELECT COUNT(*) FROM campaign_leads WHERE status = 'pending'")
    pending_calls = cursor.fetchone()[0]

    # Scores
    cursor.execute("SELECT AVG((puntuacion_comercial + puntuacion_instalador + puntuacion_rapidez) / 3.0) FROM encuestas WHERE completada = 1")
    avg_overall = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT AVG(puntuacion_comercial) FROM encuestas WHERE completada = 1")
    avg_comercial = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT AVG(puntuacion_instalador) FROM encuestas WHERE completada = 1")
    avg_instalador = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT AVG(puntuacion_rapidez) FROM encuestas WHERE completada = 1")
    avg_rapidez = cursor.fetchone()[0] or 0

    conn.close()
    
    # Adaptado a la interfaz DashboardStats de DashboardView.tsx
    return {
        "total_calls": total_calls,
        "completed_calls": completed_calls,
        "pending_calls": pending_calls,
        "avg_scores": {
            "comercial": round(avg_comercial, 1),
            "instalador": round(avg_instalador, 1),
            "rapidez": round(avg_rapidez, 1),
            "overall": round(avg_overall, 1)
        }
    }

@app.get("/api/dashboard/recent-calls")
async def get_recent_calls():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, telefono, fecha, completada,
               puntuacion_comercial, puntuacion_instalador, puntuacion_rapidez,
               comentarios, transcription
        FROM encuestas 
        ORDER BY fecha DESC LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    
    # Adaptado a la interfaz Call de DashboardView.tsx
    results = []
    for row in rows:
        results.append({
            "id": row['id'],
            "phone": row['telefono'],
            "date": f"{row['fecha']}Z" if not str(row['fecha']).endswith('Z') else row['fecha'],
            "status": "completed" if row['completada'] else "pending",
            "scores": {
                "comercial": row['puntuacion_comercial'],
                "instalador": row['puntuacion_instalador'],
                "rapidez": row['puntuacion_rapidez']
            }
        })
    return results

@app.get("/api/dashboard/usage-stats")
async def get_usage_stats():
    """Retorna estadísticas agregadas de uso de tokens y minutos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(tokens_used), SUM(seconds_used) FROM encuestas")
    res = cursor.fetchone()
    conn.close()
    
    total_tokens = res[0] or 0
    total_seconds = res[1] or 0
    
    return {
        "total_tokens": total_tokens,
        "total_minutes": round(total_seconds / 60.0, 2),
        "total_seconds": total_seconds
    }

@app.get("/api/dashboard/integrations")
async def get_dashboard_integrations():
    """Retorna el estado de las integraciones externas"""
    return [
        {"name": "LLM Provider", "provider": "Groq", "active": bool(os.getenv("GROQ_API_KEY")), "model": "llama-3.3-70b-versatile"},
        {"name": "TTS Provider", "provider": "Cartesia", "active": bool(os.getenv("CARTESIA_API_KEY")), "model": "sonic-multilingual"},
        {"name": "STT Provider", "provider": "Deepgram", "active": bool(os.getenv("DEEPGRAM_API_KEY")), "model": "nova-2"},
        {"name": "LiveKit", "provider": "Cloud", "active": bool(os.getenv("LIVEKIT_API_KEY")), "url": os.getenv("LIVEKIT_URL")}
    ]

@app.get("/api/alerts")
async def get_system_alerts():
    """Devuelve las alertas activas del sistema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM system_alerts WHERE is_active = 1 ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Marca una alerta como resuelta"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE system_alerts SET is_active = 0 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- AGENT CONFIG ENDPOINTS ---

@app.get("/api/agents")
async def get_agents():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_config")
    rows = cursor.fetchall()
    # Mapeo de campos DB -> Frontend (camelCase)
    results = []
    for row in rows:
        results.append({
            "id": row['id'],
            "name": row['name'],
            "useCase": row['use_case'],
            "description": row['description'],
            "instructions": row['instructions'],
            "greeting": row['greeting']
        })
    conn.close()
    return results

@app.put("/api/agents/{agent_id}")
async def update_agent(agent_id: int, config: AgentConfigModel):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si existe
    cursor.execute("SELECT id FROM agent_config WHERE id = ?", (agent_id,))
    if not cursor.fetchone():
        # Si es el ID 1 y no existe, crearlo
        if agent_id == 1:
             cursor.execute("INSERT INTO agent_config (id, name, use_case, description, instructions, greeting) VALUES (1, ?, ?, ?, ?, ?)",
                           (config.name, config.use_case, config.description, config.instructions, config.greeting))
        else:
             conn.close()
             raise HTTPException(status_code=404, detail="Agent not found")
    else:
        cursor.execute("""
            UPDATE agent_config 
            SET name=?, use_case=?, description=?, instructions=?, greeting=?, updated_at=CURRENT_TIMESTAMP
            WHERE id = ?
        """, (config.name, config.use_case, config.description, config.instructions, config.greeting, agent_id))
    
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- AI CONFIG ENDPOINTS ---

@app.get("/api/ai/config")
async def get_ai_config():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_config ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

@app.post("/api/ai/config")
async def update_ai_config(config: AIConfig):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE ai_config 
        SET llm_provider=?, llm_model=?, tts_provider=?, tts_model=?, tts_voice=?, stt_provider=?, stt_model=?, language=?, updated_at=CURRENT_TIMESTAMP
        WHERE id = (SELECT id FROM ai_config ORDER BY id DESC LIMIT 1)
    """, (config.llm_provider, config.llm_model, config.tts_provider, config.tts_model, config.tts_voice, config.stt_provider, config.stt_model, config.language))
    if cursor.rowcount == 0:
        cursor.execute("INSERT INTO ai_config (llm_provider, llm_model, tts_provider, tts_model, tts_voice, stt_provider, stt_model, language) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (config.llm_provider, config.llm_model, config.tts_provider, config.tts_model, config.tts_voice, config.stt_provider, config.stt_model, config.language))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- PROMPTS ENDPOINTS ---

@app.get("/api/prompts")
async def get_prompts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prompt_templates ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/prompts")
async def create_prompt(prompt: PromptTemplateModel):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO prompt_templates (name, description, content) VALUES (?, ?, ?)",
                  (prompt.name, prompt.description, prompt.content))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- CAMPAIGNS ENDPOINTS ---

@app.post("/api/campaigns")
async def create_campaign(campaign: CampaignModel, leads: List[CampaignLeadModel]):
    """Crea una nueva campaña con leads"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO campaigns (name, agent_id, status, scheduled_time, retries_count, retry_interval) VALUES (?, ?, ?, ?, ?, ?)",
                      (campaign.name, campaign.agent_id, campaign.status, campaign.scheduled_time, campaign.retries_count, campaign.retry_interval))
        campaign_id = cursor.lastrowid
        
        # Insert leads
        for lead in leads:
            cursor.execute("INSERT INTO campaign_leads (campaign_id, phone_number, customer_name) VALUES (?, ?, ?)",
                          (campaign_id, lead.phone_number, lead.customer_name))
        
        conn.commit()
        return {"status": "success", "campaign_id": campaign_id, "leads_count": len(leads)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/campaigns")
async def get_campaigns():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Join con subqueries para contar leads
    cursor.execute("""
        SELECT 
            c.*,
            (SELECT COUNT(*) FROM campaign_leads WHERE campaign_id = c.id) as total_leads,
            (SELECT COUNT(*) FROM campaign_leads WHERE campaign_id = c.id AND status IN ('called', 'completed')) as called_leads,
            (SELECT COUNT(*) FROM campaign_leads WHERE campaign_id = c.id AND status = 'failed') as failed_leads,
            (SELECT COUNT(*) FROM campaign_leads WHERE campaign_id = c.id AND status = 'pending') as pending_leads
        FROM campaigns c
        ORDER BY c.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        d = dict(row)
        
        # Corregir STATUS: Si hay fallidos, no está completed
        # Prioridad: running > failed > completed > pending
        # Pero conservamos el status original si es 'running' o 'paused' explícitamente
        
        real_status = d['status']
        if d['pending_leads'] == 0:
            if d['failed_leads'] > 0:
                # Si todo terminó pero hubo fallos
                real_status = 'completed_with_errors' # Ojo, frontend quizas no tenga color para esto
            else:
                 real_status = 'completed'
        elif d['called_leads'] > 0:
             if real_status == 'pending': real_status = 'running'
        
        # Simplificación para el frontend existente:
        if d['failed_leads'] > 0 and d['pending_leads'] == 0:
            d['status'] = 'paused' # Para indicar que requiere atención (Retry)
        elif d['pending_leads'] == 0:
            d['status'] = 'completed'
        
        # Corregir HORA: Asegurar formato ISO con Z si no la tiene
        if d.get('created_at') and not str(d['created_at']).endswith('Z'):
            d['created_at'] = f"{d['created_at']}Z"
        if d.get('scheduled_time') and not str(d['scheduled_time']).endswith('Z'):
            # Si viene del frontend como local (sin Z), NO le añadimos Z aquí 
            # porque el navegador la interpretaría como UTC y sumaría el desfase.
            # Solo añadimos Z si estamos seguros de que es UTC.
            pass # Dejamos que el frontend maneje la interpretación local si no hay Z
        
        results.append(d)
        
    return results

@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.*,
            (SELECT COUNT(*) FROM campaign_leads WHERE campaign_id = c.id) as total_leads,
            (SELECT COUNT(*) FROM campaign_leads WHERE campaign_id = c.id AND status IN ('called', 'completed')) as called_leads,
            (SELECT COUNT(*) FROM campaign_leads WHERE campaign_id = c.id AND status = 'failed') as failed_leads,
            (SELECT COUNT(*) FROM campaign_leads WHERE campaign_id = c.id AND status = 'pending') as pending_leads
        FROM campaigns c
        WHERE c.id = ?
    """, (campaign_id,))
    campaign = cursor.fetchone()
    
    if not campaign:
        conn.close()
        raise HTTPException(status_code=404, detail="Campaign not found")

    cursor.execute("""
        SELECT 
            cl.*,
            e.puntuacion_comercial,
            e.puntuacion_instalador,
            e.puntuacion_rapidez,
            e.comentarios,
            e.transcription as transcription_preview
        FROM campaign_leads cl
        LEFT JOIN encuestas e ON cl.call_id = e.id
        WHERE cl.campaign_id = ?
    """, (campaign_id,))
    leads = cursor.fetchall()
    conn.close()
    
    camp_dict = dict(campaign)
    
    # Logic STATUS corregida
    if camp_dict['pending_leads'] == 0 and camp_dict['failed_leads'] > 0:
        camp_dict['status'] = 'paused' # Marca visual "Amarillo/Gris" en vez de Verde
    elif camp_dict['pending_leads'] == 0:
        camp_dict['status'] = 'completed'

    # Logic HORA corregida
    if camp_dict.get('created_at') and not str(camp_dict['created_at']).endswith('Z'):
        camp_dict['created_at'] = f"{camp_dict['created_at']}Z"
    # scheduled_time lo dejamos tal cual venga de la DB para que el browser no asuma UTC si no tiene Z
    if camp_dict.get('scheduled_time') and not str(camp_dict['scheduled_time']).endswith('Z'):
        pass 

    return {"campaign": camp_dict, "leads": [dict(l) for l in leads]}

@app.delete("/api/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM campaign_leads WHERE campaign_id = ?", (campaign_id,))
    cursor.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.put("/api/campaigns/{campaign_id}")
async def update_campaign(campaign_id: int, config: CampaignUpdateModel):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Verificar existencia
    cursor.execute("SELECT id FROM campaigns WHERE id = ?", (campaign_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # 2. Build Query
    update_fields = []
    params = []
    
    if config.name is not None:
        update_fields.append("name = ?")
        params.append(config.name)
    
    if config.agent_id is not None:
        update_fields.append("agent_id = ?")
        params.append(config.agent_id)
        
    if config.scheduled_time is not None:
        update_fields.append("scheduled_time = ?")
        params.append(config.scheduled_time)
        
    if config.status is not None:
        update_fields.append("status = ?")
        params.append(config.status)
        
    if update_fields:
        update_fields.append("created_at = created_at") # Hack para actualizar timestamp si es necesario, aunque falta updated_at en tabla campaigns
        sql = f"UPDATE campaigns SET {', '.join(update_fields)} WHERE id = ?"
        params.append(campaign_id)
        cursor.execute(sql, tuple(params))
        conn.commit()
        
    conn.close()
    return {"status": "success", "updated_fields": update_fields}

@app.post("/api/campaigns/{campaign_id}/retry")
async def retry_campaign_failed(campaign_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Resetear leads fallidos a pending
    cursor.execute("""
        UPDATE campaign_leads 
        SET status = 'pending', retries_attempted = 0, next_retry_at = NULL
        WHERE campaign_id = ? AND status = 'failed'
    """, (campaign_id,))
    
    count = cursor.rowcount
    
    # 2. Reactivar selección
    if count > 0:
        cursor.execute("UPDATE campaigns SET status = 'pending' WHERE id = ?", (campaign_id,))
    
    conn.commit()
    conn.close()
    return {"status": "success", "retried_count": count}
    
@app.get("/api/results")
async def get_results():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM encuestas ORDER BY fecha DESC")
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        if d.get('fecha') and not str(d['fecha']).endswith('Z'):
            d['fecha'] = f"{d['fecha']}Z"
        results.append(d)
    return results

@app.post("/api/calls/outbound")
async def make_outbound_call(call_request: OutboundCallRequest):
    """
    Lanza una llamada outbound usando el sistema del AgenteLocal
    """
    try:
        print(f"📞 Iniciando llamada outbound a {call_request.phoneNumber} ({call_request.customerName or 'Anon'})")
        
        # 1. Crear ficha en DB
        id_ficha = None
        try:
            resp_inicio = await iniciar_encuesta(InicioEncuesta(
                telefono=call_request.phoneNumber,
                nombre_cliente=call_request.customerName
            ))
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
                    agent_name="Dakota-1ef9", # Nombre interno del worker registrado en agent.py
                    metadata=call_request.customerName or "" # Pasar nombre en metadata por si acaso
                )
            )
            print(f"✅ Agente despachado correctamente")
        except Exception as e:
            print(f"⚠️ Warning al despachar agente: {e}")
        
        # 5. Crear llamada SIP
        print(f"📞 Creando participante SIP...")
        
        trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID", "ST_UBZcusTkNdtH")
        
        try:
            await lkapi.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    room_name=sala,
                    sip_trunk_id=trunk_id,
                    sip_call_to=call_request.phoneNumber,
                    participant_identity=f"Cliente {id_ficha}",
                )
            )
            print("🚀 ¡Llamada en curso!")
        except Exception as e:
            print(f"❌ Error SIP: {e}")
            raise HTTPException(status_code=500, detail=f"Error iniciando SIP: {e}")
        finally:
            await lkapi.aclose()
        
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
    print(f"📝 1. Creando ficha para: {datos.telefono} - {datos.nombre_cliente}")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Usamos UTC para que el frontend (con Z) lo muestre bien en hora local
        cursor.execute("INSERT INTO encuestas (telefono, nombre_cliente, fecha, completada) VALUES (?, ?, ?, 0)", 
                      (datos.telefono, datos.nombre_cliente, datetime.utcnow()))
        conn.commit()
        nuevo_id = cursor.lastrowid
        print(f"✅ Ficha creada con ID: {nuevo_id}")
        return {"id": nuevo_id}
    finally:
        cursor.close()
        conn.close()

@app.post("/guardar-encuesta")
async def guardar_encuesta(datos: FinEncuesta):
    print(f"📥 2. Recibiendo datos. La IA dice ID: {datos.id_encuesta}")
    
    num_map = {
        "cero": 0, "uno": 1, "un": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
        "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10
    }

    def clean_nota(val):
        if val is None: return None
        s_val = str(val).lower().strip()
        
        # 1. Intentar número directo
        match = re.search(r'\b(10|[0-9])\b', s_val)
        if match:
            num = int(match.group())
            if 0 <= num <= 10: return num
            
        # 2. Intentar palabra escrita
        for word, num in num_map.items():
            if f" {word} " in f" {s_val} ":
                return num
        return None
    
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

        update_fields = []
        params = []

        if datos.nota_comercial is not None:
            val = clean_nota(datos.nota_comercial)
            if val is not None:
                update_fields.append("puntuacion_comercial = ?")
                params.append(val)
        
        if datos.nota_instalador is not None:
            val = clean_nota(datos.nota_instalador)
            if val is not None:
                update_fields.append("puntuacion_instalador = ?")
                params.append(val)

        if datos.nota_rapidez is not None:
            val = clean_nota(datos.nota_rapidez)
            if val is not None:
                update_fields.append("puntuacion_rapidez = ?")
                params.append(val)

        if datos.transcription:
            lines = datos.transcription.split('\n')
            mapping = {
                "puntuacion_comercial": ["comercial", "atencion", "trato"],
                "puntuacion_instalador": ["instalador", "tecnico", "técnico", "montaje"],
                "puntuacion_rapidez": ["rapidez", "velocidad", "tiempo", "rápido"]
            }
            
            for col, keywords in mapping.items():
                if not any(col in f for f in update_fields):
                    for i in range(len(lines) - 1):
                        agente_line = lines[i].lower()
                        if "agente:" in agente_line and any(k in agente_line for k in keywords):
                            cliente_line = lines[i+1].lower()
                            if "cliente:" in cliente_line:
                                val = clean_nota(cliente_line)
                                if val is not None:
                                    update_fields.append(f"{col} = ?")
                                    params.append(val)
                                    print(f"🕵️ [Rescue] Extraído {col}={val} de la transcripción.")
                                    break

        if datos.comentarios is not None and datos.comentarios != "Sin comentarios":
            update_fields.append("comentarios = ?")
            params.append(datos.comentarios)

        if datos.transcription is not None:
            update_fields.append("transcription = ?")
            params.append(datos.transcription)

        if datos.tokens_used:
            update_fields.append("tokens_used = ?")
            params.append(datos.tokens_used)

        if datos.seconds_used:
            update_fields.append("seconds_used = ?")
            params.append(datos.seconds_used)

        if datos.status is not None:
            # Si status es 'completed', marcamos la encuesta como completada en BD
            final_complete = 1 if datos.status == 'completed' else 0
            
            # Mapeamos status del agente a status del lead
            lead_status = 'completed' if datos.status == 'completed' else 'failed'
            if datos.status == 'failed': lead_status = 'failed'

            update_fields.append("completada = ?")
            params.append(final_complete)
            
            # Actualizar lead asociado a este call_id
            cursor.execute("UPDATE campaign_leads SET status = ? WHERE call_id = ?", (lead_status, id_final))
            
            # Actualizar también por teléfono si quedó pending (fallback)
            cursor.execute("SELECT telefono FROM encuestas WHERE id = ?", (id_final,))
            phone_res = cursor.fetchone()
            if phone_res:
                cursor.execute("UPDATE campaign_leads SET status = ? WHERE phone_number = ? AND status IN ('pending', 'called')", (lead_status, phone_res[0]))
        elif len(update_fields) > 1:
            notas_rescatadas = [f for f in update_fields if 'puntuacion' in f]
            # Si hay AL MENOS UNA nota rescatada o comentario, damos la ficha por válida (completada)
            if len(notas_rescatadas) >= 1 or "comentarios" in str(update_fields):
                print(f"✅ [Auto-Close] Marcando ficha {id_final} como completada por rescate exitoso.")
                update_fields.append("completada = 1")
                # Al rescatar datos, la damos por completada
                cursor.execute("UPDATE campaign_leads SET status = 'completed' WHERE call_id = ?", (id_final,))
                
                cursor.execute("SELECT telefono FROM encuestas WHERE id = ?", (id_final,))
                phone_res = cursor.fetchone()
                if phone_res:
                    cursor.execute("UPDATE campaign_leads SET status = 'completed' WHERE phone_number = ? AND status IN ('pending', 'called')", (phone_res[0],))

        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        if not update_fields:
            return {"status": "skipped", "msg": "No data to update"}

        sql = f"UPDATE encuestas SET {', '.join(update_fields)} WHERE id = ?"
        params.append(id_final)

        cursor.execute(sql, tuple(params))
        conn.commit()
        print(f"🚀 [Guardar] ID {id_final}: status_sent={datos.status}")
        return {"status": "success"}
    finally:
        cursor.close()
        conn.close()

@app.post("/colgar")
async def colgar(datos: ColgarLlamada):
    print(f"✂️  Petición de colgar recibida.")
    
    # Pausa para dar tiempo a la despedida
    print("⏳ Esperando 3 segundos para dar tiempo a la despedida...")
    await asyncio.sleep(3.0) 

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

# --- BACKGROUND WORKER PARA CAMPAÑAS ---

async def process_campaigns():
    """Worker mejorado: gestiona campañas activas, llamadas nuevas y reintentos automáticos"""
    from datetime import timedelta
    
    while True:
        lkapi_worker = None
        try:
            # Inicializar API para comprobar estado de salas
            lkapi_worker = api.LiveKitAPI(
                os.getenv("LIVEKIT_URL"),
                os.getenv("LIVEKIT_API_KEY"),
                os.getenv("LIVEKIT_API_SECRET"),
            )
            
            # --- 0. CONTROL DE CONCURRENCIA ESTRICTO (1 LLAMADA A LA VEZ) ---
            # Listamos las salas activas. Si hay ALGUNA, no lanzamos más.
            active_rooms = await lkapi_worker.room.list_rooms(api.ListRoomsRequest())
            # Filtramos solo las que parecen de encuestas (encuesta_XX o similares)
            ongoing_calls = [r for r in active_rooms.rooms if "encuesta_" in r.name]
            
            if len(ongoing_calls) > 0:
                print(f"⏳ [Worker] Hay {len(ongoing_calls)} llamadas en curso. Esperando a que terminen para lanzar la siguiente...")
                await lkapi_worker.aclose()
                await asyncio.sleep(5) 
                continue # Saltamos ciclo hasta que se libere

            conn = get_db_connection()

            cursor = conn.cursor()
            
            # --- 1. ACTIVAR CAMPAÑAS PENDIENTES ---
            now_iso = datetime.utcnow().isoformat()
            now_dt = datetime.utcnow()
            
            # Buscar pending y marcarlas como running si es hora
            cursor.execute("""
                SELECT id, name FROM campaigns 
                WHERE status = 'pending' 
                AND (scheduled_time IS NULL OR scheduled_time <= ? OR scheduled_time <= ?)
            """, (now_iso, now_iso + "Z"))
            
            pending_campaigns = cursor.fetchall()
            for cmp in pending_campaigns:
                print(f"🚀 [Worker] Activando campaña '{cmp['name']}' (ID: {cmp['id']})...")
                cursor.execute("UPDATE campaigns SET status = 'running' WHERE id = ?", (cmp['id'],))
            conn.commit()

            # --- 2. PROCESAR CAMPAÑAS ACTIVAS (RUNNING) ---
            cursor.execute("SELECT * FROM campaigns WHERE status = 'running'")
            running_campaigns = cursor.fetchall()
            
            for campaign in running_campaigns:
                campaign_id = campaign['id']
                agent_id = campaign['agent_id']
                
                # Configuración de reintentos (defaults si es null)
                max_retries = campaign['retries_count'] if campaign['retries_count'] is not None else 3
                retry_interval_min = campaign['retry_interval'] if campaign['retry_interval'] is not None else 180
                
                # Buscar leads candidatos:
                # - PENDING: Nuevos
                # - FAILED: Para reintentar si no han superado el límite
                cursor.execute("""
                    SELECT * FROM campaign_leads 
                    WHERE campaign_id = ? 
                    AND (
                        status = 'pending' 
                        OR (status = 'failed' AND retries_attempted < ?)
                    )
                """, (campaign_id, max_retries))
                
                potential_leads = cursor.fetchall()
                leads_to_call = []
                
                for lead in potential_leads:
                    # Si es pending, siempre se llama
                    if lead['status'] == 'pending':
                        leads_to_call.append(lead)
                        continue
                        
                    # Si es failed, verificar si ya pasó el tiempo de espera (next_retry_at)
                    if lead['status'] == 'failed':
                        next_retry = lead['next_retry_at']
                        if not next_retry:
                            leads_to_call.append(lead) # Si no tiene fecha proxima, reintentar ya
                        else:
                            try:
                                # Parseo básico de fecha ISO que puede venir de SQLite
                                s_retry = str(next_retry).replace('Z', '')
                                # Manejo de formatos con/sin microsegundos
                                if '.' in s_retry:
                                    target_time = datetime.strptime(s_retry, "%Y-%m-%d %H:%M:%S.%f")
                                else:
                                    target_time = datetime.strptime(s_retry, "%Y-%m-%d %H:%M:%S")
                                    
                                if now_dt >= target_time:
                                    leads_to_call.append(lead)
                            except Exception as e:
                                # Ante duda de formato, procesar
                                leads_to_call.append(lead)

                if leads_to_call:
                    print(f"📋 [Worker] Campaña {campaign_id}: {len(leads_to_call)} leads listos para llamar (inc. reintentos).")
                
                for lead in leads_to_call:
                    phone = lead['phone_number']
                    lead_id = lead['id']
                    customer_name = lead['customer_name']
                    current_retries = lead['retries_attempted'] or 0
                    
                    print(f"📞 [Worker] Llamando a {phone} (Intento {current_retries + 1}/{max_retries + 1})...")
                    
                    try:
                        # Calcular próxima fecha de reintento POR ADELANTADO (estrategia pesimista)
                        next_retry_dt = now_dt + timedelta(minutes=retry_interval_min)
                        
                        # Actualizar estado a 'intentando' incrementando el contador
                        cursor.execute("""
                            UPDATE campaign_leads 
                            SET retries_attempted = retries_attempted + 1, 
                                last_call_at = CURRENT_TIMESTAMP,
                                next_retry_at = ?
                            WHERE id = ?
                        """, (next_retry_dt, lead_id))
                        conn.commit()
                        
                        # Lanzar llamada
                        req = OutboundCallRequest(
                            agentId=str(agent_id),
                            phoneNumber=phone,
                            customerName=customer_name,
                            agentName=f"Agent-{agent_id}"
                        )
                        await make_outbound_call(req)
                        
                        # Si SIP OK -> Status 'called'
                        cursor.execute("UPDATE campaign_leads SET status = 'called' WHERE id = ?", (lead_id,))
                        conn.commit()
                        
                        print("⏸️ [Worker] Llamada lanzada. Pausando 10s para asegurar estabilidad...")
                        await asyncio.sleep(10) # Pausa solicitada por el usuario
                        
                        # IMPORTANTE: Romper el bucle de leads para volver a comprobar concurrencia arriba
                        # Así garantizamos que no se lance la siguiente del array sin chequear rooms
                        break 
                        
                    except Exception as e:
                        print(f"❌ [Worker] Fallo técnico al llamar {phone}: {e}")
                        # Marcar failed inmediatamente para que entre en ciclo de retry luego
                        cursor.execute("UPDATE campaign_leads SET status = 'failed' WHERE id = ?", (lead_id,))
                        conn.commit()

                # --- 3. VERIFICAR FIN DE CAMPAÑA ---

                # Una campaña acaba cuando NO hay leads en: pending, called, o (failed con intentos restantes)
                cursor.execute("""
                    SELECT COUNT(*) FROM campaign_leads 
                    WHERE campaign_id = ? 
                    AND (
                        status = 'pending' 
                        OR status = 'called' 
                        OR (status = 'failed' AND retries_attempted < ?)
                    )
                """, (campaign_id, max_retries))
                pending_count = cursor.fetchone()[0]
                
                if pending_count == 0:
                    print(f"✅ [Worker] Campaña {campaign_id} (retries={max_retries}) completada definitivamente.")
                    cursor.execute("UPDATE campaigns SET status = 'completed' WHERE id = ?", (campaign_id,))
                    conn.commit()

            cursor.close()
            conn.close()
            if lkapi_worker: await lkapi_worker.aclose()
            
        except Exception as e:
            print(f"⚠️ [Worker] Error en ciclo de campañas: {e}")
            import traceback
            traceback.print_exc()
            if lkapi_worker: await lkapi_worker.aclose()

            
        # Esperar 20 segundos para no saturar comprobando reintentos
        await asyncio.sleep(20)

@app.on_event("startup")
async def startup_event():
    print("🌅 Iniciando API y Background Workers...")
    asyncio.create_task(process_campaigns())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
