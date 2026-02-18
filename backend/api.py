import os
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Union, List
from dotenv import load_dotenv
from livekit import api
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import create_client, Client

load_dotenv()

# --- CONFIGURACIÓN SUPABASE ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR CRÍTICO: Faltan variables SUPABASE_URL o SUPABASE_KEY en .env")
    # No detenemos la ejecución para que al menos arranque la API, pero fallará al usar BD
    supabase: Client = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"✅ Conectado a Supabase: {SUPABASE_URL}")
    except Exception as e:
        print(f"❌ Error al conectar a Supabase: {e}")
        supabase = None

app = FastAPI(title="Ausarta Voice Agent API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS PYDANTIC ---
class VoiceAgentCreate(BaseModel):
    name: str

class VoiceAgentUpdate(BaseModel):
    instructions: Optional[str] = None
    greeting: Optional[str] = None
    agent_config: Optional[dict] = None # Para guardar configuraciones completas si se necesita

class CampaignCreate(BaseModel):
    name: str
    agent_id: int
    scheduled_time: Optional[datetime] = None
    leads_csv: Optional[str] = None # Contenido CSV en base64 o raw string
    retries_count: int = 3
    retry_interval: int = 180 # Segundos

class CampaignLeadModel(BaseModel):
    phone_number: str
    customer_name: str
    id: Optional[int] = None # ID opcional si viene de fuera

class CampaignModel(BaseModel):
    name: str
    agent_id: int
    status: str = "pending"
    scheduled_time: Optional[datetime] = None
    retries_count: int = 3
    retry_interval: int = 180

class LlmConfig(BaseModel):
    llm_provider: str
    llm_model: str
    stt_provider: str
    stt_model: str
    tts_provider: str
    tts_model: str
    tts_voice: str
    language: str

class EncuestaData(BaseModel):
    id_encuesta: int
    status: Optional[str] = None
    nota_comercial: Optional[int] = None
    nota_instalador: Optional[int] = None
    nota_rapidez: Optional[int] = None
    comentarios: Optional[str] = None
    transcription: Optional[str] = None
    seconds_used: Optional[int] = None
    llm_model: Optional[str] = None

class CallEndRequest(BaseModel):
    nombre_sala: str

# --- LIVEKIT SETUP ---
LIVEKIT_URL = os.getenv('LIVEKIT_URL')
LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY')
LIVEKIT_API_SECRET = os.getenv('LIVEKIT_API_SECRET')
lkapi = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)

# --- ENDPOINTS ---

@app.get("/")
async def root():
    return {"status": "ok", "service": "Ausarta Backend", "database": "Supabase"}

# --- DASHBOARD METRICS ---
@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    if not supabase: return {"error": "Database not connected"}
    
    try:
        # Total llamadas
        res_total = supabase.table("encuestas").select("count", count="exact").execute()
        total_calls = res_total.count if res_total.count is not None else 0
        
        # Completadas
        res_completed = supabase.table("encuestas").select("count", count="exact").eq("completada", 1).execute()
        completed_calls = res_completed.count if res_completed.count is not None else 0
        
        # Pendientes (Campaign Leads)
        res_pending = supabase.table("campaign_leads").select("count", count="exact").eq("status", "pending").execute()
        pending_calls = res_pending.count if res_pending.count is not None else 0
        
        # Promedios (Usando RPC o calculando en Python si no hay RPC creado)
        # Para simplificar y evitar crear funciones SQL complejas ahora, traemos los datos y calculamos
        # IMPORTANTE: En producción con muchos datos, usar funciones SQL (RPC)
        
        res_scores = supabase.table("encuestas").select("puntuacion_comercial, puntuacion_instalador, puntuacion_rapidez").not_.is_("puntuacion_comercial", "null").execute()
        
        avg_comercial = 0
        avg_instalador = 0
        avg_rapidez = 0
        avg_overall = 0
        count = len(res_scores.data)
        
        if count > 0:
            sum_com = sum(r['puntuacion_comercial'] or 0 for r in res_scores.data)
            sum_ins = sum(r['puntuacion_instalador'] or 0 for r in res_scores.data)
            sum_rap = sum(r['puntuacion_rapidez'] or 0 for r in res_scores.data)
            
            avg_comercial = sum_com / count
            avg_instalador = sum_ins / count
            avg_rapidez = sum_rap / count
            avg_overall = (avg_comercial + avg_instalador + avg_rapidez) / 3

        return {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "pending_calls": pending_calls,
            "avg_scores": {
                "comercial": round(float(avg_comercial), 1),
                "instalador": round(float(avg_instalador), 1),
                "rapidez": round(float(avg_rapidez), 1),
                "overall": round(float(avg_overall), 1)
            }
        }
    except Exception as e:
        print(f"Error stats: {e}")
        return {"total_calls": 0, "completed_calls": 0, "pending_calls": 0, "avg_scores": {}}

@app.get("/api/dashboard/recent-calls")
async def get_recent_calls():
    if not supabase: return []
    try:
        # Hacemos un join manual o usamos la relación si está definida en Supabase
        # Aquí asumimos que traemos datos y procesamos, o usamos stored procedure
        response = supabase.table("encuestas").select("*").order("fecha", desc=True).limit(50).execute()
        
        # Enriquecer con nombre de campaña si es posible (requiere call_id en leads)
        # Por simplicidad, devolvemos directo
        return response.data
    except Exception as e:
        print(f"Error recent calls: {e}")
        return []

# --- ALERTAS ---
@app.get("/api/alerts")
async def get_alerts():
    # Devuelve lista vacía por ahora para evitar error 404 en frontend
    return []

# --- CALL CONTROL ---

@app.post("/colgar")
async def finalizar_llamada(req: CallEndRequest):
    """Corta la llamada en LiveKit"""
    try:
        print(f"✂️ Solicitud de colgar sala: {req.nombre_sala}")
        await lkapi.room.delete_room(api.DeleteRoomRequest(room=req.nombre_sala))
        return {"status": "ok", "message": f"Sala {req.nombre_sala} cerrada"}
    except Exception as e:
        print(f"⚠️ Error al cerrar sala {req.nombre_sala}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/guardar-encuesta")
async def guardar_encuesta(datos: EncuestaData):
    if not supabase: return {"status": "error", "message": "No DB connection"}
    
    print(f"📝 Guardando datos encuesta {datos.id_encuesta}: {datos}")
    
    update_data = {}
    
    if datos.nota_comercial is not None: update_data["puntuacion_comercial"] = datos.nota_comercial
    if datos.nota_instalador is not None: update_data["puntuacion_instalador"] = datos.nota_instalador
    if datos.nota_rapidez is not None: update_data["puntuacion_rapidez"] = datos.nota_rapidez
    if datos.comentarios is not None: update_data["comentarios"] = datos.comentarios
    if datos.transcription is not None: update_data["transcription"] = datos.transcription
    if datos.seconds_used is not None: update_data["seconds_used"] = datos.seconds_used
    if datos.llm_model is not None: update_data["llm_model"] = datos.llm_model
    
    # Lógica de estados
    status_final = datos.status
    es_completada = False
    
    # Si viene status explícito (ej: 'rejected_opt_out' o 'completed'), lo respetamos
    if datos.status:
        update_data["status"] = datos.status
        if datos.status == 'completed':
            es_completada = True
            update_data["completada"] = 1 # TINYINT 1
    
    # Si NO viene status, deducimos 'incomplete' si hay datos parciales y no estaba ya terminada
    elif update_data: # Si hay algo que actualizar
         # Primero verificamos estado actual para no sobrescribir 'completed'
         curr = supabase.table("encuestas").select("status").eq("id", datos.id_encuesta).execute()
         if curr.data and curr.data[0]['status'] not in ('completed', 'rejected_opt_out'):
             update_data["status"] = 'incomplete'

    if not update_data:
        return {"status": "ignored", "message": "No data to update"}

    update_data["updated_at"] = datetime.utcnow().isoformat()

    try:
        supabase.table("encuestas").update(update_data).eq("id", datos.id_encuesta).execute()
        
        # Si la encuesta se completó o rechazó, actualizamos el LEAD asociado también
        # Buscamos el lead por call_id (que es el id_encuesta)
        if datos.status in ('completed', 'rejected_opt_out', 'incomplete'):
             lead_update = {"status": datos.status}
             supabase.table("campaign_leads").update(lead_update).eq("call_id", datos.id_encuesta).execute()

        return {"status": "ok", "updated": update_data}
    except Exception as e:
        print(f"❌ Error DB al guardar: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# --- CONFIGURACIÓN DEL AGENTE ---

@app.post("/api/calls/outbound")
async def make_outbound_call(request: dict):
    """Endpoint para llamadas de prueba desde el Dashboard"""
    phone = request.get("phoneNumber")
    agent_id = request.get("agentId", "1")
    
    if not phone:
        return JSONResponse(status_code=400, content={"error": "Phone number is required"})

    print(f"📞 Iniciando llamada de prueba a {phone}...")
    
    try:
        # 1. Crear registro en BD (aunque sea de prueba)
        if supabase:
            encuesta_data = {
                "telefono": phone,
                "nombre_cliente": "Prueba Dashboard",
                "fecha": datetime.utcnow().isoformat(),
                "status": "initiated",
                "completada": 0
            }
            res_enc = supabase.table("encuestas").insert(encuesta_data).execute()
            encuesta_id = res_enc.data[0]['id']
        else:
            encuesta_id = 9999 # Fallback si no hay DB
            
        # 2. Configurar LiveKit
        sip_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
        room_name = f"encuesta_{encuesta_id}"

        # Crear sala
        try:
            await lkapi.room.create_room(api.CreateRoomRequest(name=room_name))
        except: pass

        # 3. Dial Out
        await lkapi.sip.create_sip_participant(api.CreateSIPParticipantRequest(
            sip_trunk_id=sip_trunk_id,
            sip_call_to=phone,
            room_name=room_name,
            participant_identity=f"user_{phone}_test",
            participant_name="Test User"
        ))

        return {"status": "ok", "roomName": room_name, "callId": encuesta_id}
        
    except Exception as e:
        print(f"❌ Error llamada prueba: {e}")
        return JSONResponse(status_code=500, content={"error": str(e), "detail": str(e)})

@app.get("/api/agents")
async def get_agents():
    """Endpoint compatible con frontend que espera lista de agentes"""
    if not supabase: return [{"name": "Dakota", "instructions": "Default"}]
    try:
        res = supabase.table("agent_config").select("*").limit(1).execute()
        if res.data:
            # Frontend espera 'instructions' en el objeto principal
            # Y 'id' como string si es posible
            agent = res.data[0]
            agent['id'] = str(agent['id'])
            return [agent] # Devolvemos lista
        else:
            return [{"id": "1", "name": "Dakota", "use_case": "Encuesta", "instructions": "Default"}]
    except Exception as e:
        print(f"Error getting agents: {e}")
        return []

@app.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, config: dict):
    if not supabase: return {"error": "No DB"}
    try:
        # Ignoramos el ID de la URL y actualizamos el ÚNICO agente que tenemos
        curr = supabase.table("agent_config").select("id").limit(1).execute()
        
        # Mapeamos campos si el frontend manda nombres distintos (ej: cammelCase vs snake_case)
        # El frontend manda: name, useCase, description, instructions, greeting
        
        db_config = {}
        if "name" in config: db_config["name"] = config["name"]
        if "instructions" in config: db_config["instructions"] = config["instructions"]
        if "greeting" in config: db_config["greeting"] = config["greeting"]
        if "description" in config: db_config["description"] = config["description"]
        if "useCase" in config: db_config["use_case"] = config["useCase"] # CAMBIO IMPORTANTE
        
        db_config["updated_at"] = datetime.utcnow().isoformat()
        
        if not curr.data:
            supabase.table("agent_config").insert(db_config).execute()
        else:
            first_id = curr.data[0]['id']
            supabase.table("agent_config").update(db_config).eq("id", first_id).execute()
            
        return {"status": "ok", "message": "Agente actualizado"}
    except Exception as e:
        print(f"Error updating agent: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- CONFIGURACIÓN DE MODELOS (AI) ---

@app.get("/api/ai/config")
async def get_ai_config():
    if not supabase: return {"llm_provider": "groq"}
    try:
        res = supabase.table("ai_config").select("*").limit(1).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"Error AI config: {e}")
        return {}

@app.post("/api/ai/config")
async def update_ai_config(config: dict):
    if not supabase: return {"error": "No DB"}
    try:
        curr = supabase.table("ai_config").select("id").limit(1).execute()
        if not curr.data:
            supabase.table("ai_config").insert(config).execute()
        else:
            first_id = curr.data[0]['id']
            # Filtrar
            valid_fields = ["llm_provider", "llm_model", "tts_provider", "tts_model", "tts_voice", "stt_provider", "stt_model"]
            clean_config = {k: v for k, v in config.items() if k in valid_fields}
            clean_config["updated_at"] = datetime.utcnow().isoformat()
            
            supabase.table("ai_config").update(clean_config).eq("id", first_id).execute()
            
        return {"status": "ok", "message": "Modelos actualizados"}
    except Exception as e:
        print(f"Error updating AI config: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- CAMPAIGN MANAGEMENT ---

@app.post("/api/campaigns")
async def create_campaign(campaign: CampaignModel, leads: List[CampaignLeadModel]):
    if not supabase: return {"error": "No DB"}
    
    try:
        # 1. Crear Campaña
        camp_data = {
            "name": campaign.name,
            "agent_id": campaign.agent_id,
            "status": campaign.status,
            "scheduled_time": campaign.scheduled_time.isoformat() if campaign.scheduled_time else None,
            "retries_count": campaign.retries_count,
            "retry_interval": campaign.retry_interval,
            "created_at": datetime.utcnow().isoformat()
        }
        res_camp = supabase.table("campaigns").insert(camp_data).execute()
        campaign_id = res_camp.data[0]['id']
        
        # 2. Insertar Leads
        leads_data = []
        for lead in leads:
            leads_data.append({
                "campaign_id": campaign_id,
                "phone_number": lead.phone_number,
                "customer_name": lead.customer_name,
                "status": "pending",
                "retries_attempted": 0
            })
        
        if leads_data:
            supabase.table("campaign_leads").insert(leads_data).execute()
            
        # 3. Lanzar worker en background si es instantánea
        if campaign.status == 'active':
             asyncio.create_task(process_campaigns())
             
        return {"id": campaign_id, "message": f"Campaña creada con {len(leads_data)} leads"}
        
    except Exception as e:
        print(f"Error creando campaña: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- WORKER DE LLAMADAS (Background) ---

async def process_campaigns():
    """Bucle principal que busca leads pendientes y lanza llamadas"""
    print("🚀 Iniciando Worker de Campañas (Supabase)...")
    
    while True:
        try:
            # 1. Buscar campañas activas
            # SELECT * FROM campaigns WHERE status = 'active'
            res_camps = supabase.table("campaigns").select("*").eq("status", "active").execute()
            active_campaigns = res_camps.data
            
            for camp in active_campaigns:
                campaign_id = camp['id']
                max_retries = camp['retries_count']
                retry_interval = camp['retry_interval']
                agent_id = camp['agent_id']

                # 2. Buscar leads pendientes para esta campaña
                # status='pending' OR (status='failed' AND retries < max AND next_try < now)
                
                now_str = datetime.utcnow().isoformat()
                
                # Primero 'pending'
                res_leads = supabase.table("campaign_leads").select("*") \
                    .eq("campaign_id", campaign_id) \
                    .eq("status", "pending") \
                    .limit(5).execute() # Procesar de 5 en 5 para no saturar
                
                leads_to_call = res_leads.data
                
                # Si no hay pending, buscar retries
                if not leads_to_call:
                     # Supabase 'or' syntax is tricky inside python client for complex queries in one go without raw sql
                     # Hacemos query separada para failed/unreached retriables
                     res_retries = supabase.table("campaign_leads").select("*") \
                        .eq("campaign_id", campaign_id) \
                        .in_("status", ["failed", "unreached", "incomplete"]) \
                        .lt("retries_attempted", max_retries) \
                        .lt("next_retry_at", now_str) \
                        .limit(5).execute()
                     leads_to_call = res_retries.data

                if not leads_to_call:
                    continue # Siguiente campaña

                print(f"🔄 [Worker] Procesando {len(leads_to_call)} leads para campaña {campaign_id}")

                for lead in leads_to_call:
                    lead_id = lead['id']
                    phone = lead['phone_number']
                    name = lead['customer_name']
                    
                    # CHEQUEO DE CONCURRENCIA: Verificar que no haya llamadas activas en el SIP Trunk
                    # (Esto requiere lógica extra con LiveKit API para ver salas activas, 
                    #  por simplicidad asumimos que lanzamos 1 a 1 con pausas)
                    
                    # Actualizar a 'calling'
                    supabase.table("campaign_leads").update({
                        "status": "calling", 
                        "last_call_at": datetime.utcnow().isoformat(),
                        "retries_attempted": lead['retries_attempted'] + 1
                    }).eq("id", lead_id).execute()
                    
                    # 1. Crear entrada en 'encuestas' para tener ID
                    encuesta_data = {
                        "telefono": phone,
                        "nombre_cliente": name,
                        "fecha": datetime.utcnow().isoformat(),
                        "status": "initiated",
                        "completada": 0
                    }
                    res_enc = supabase.table("encuestas").insert(encuesta_data).execute()
                    encuesta_id = res_enc.data[0]['id']
                    
                    # 2. Vincular lead con encuesta
                    supabase.table("campaign_leads").update({"call_id": encuesta_id}).eq("id", lead_id).execute()

                    # 3. Lanzar Llamada
                    try:
                        print(f"📞 [Worker] Llamando a {phone} (Encuesta ID: {encuesta_id})...")
                        
                        sip_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
                        room_name = f"encuesta_{encuesta_id}"
                        
                        # Crear sala explícitamente para asegurar
                        try:
                            await lkapi.room.create_room(api.CreateRoomRequest(name=room_name))
                        except: pass # Si ya existe no pasa nada

                        # Dial Out
                        await lkapi.sip.create_sip_participant(api.CreateSIPParticipantRequest(
                            sip_trunk_id=sip_trunk_id,
                            sip_call_to=phone,
                            room_name=room_name,
                            participant_identity=f"user_{phone}",
                            participant_name=name or "Cliente"
                        ))
                        
                        # Esperamos un poco para no ametrallar al SIP Trunk
                        await asyncio.sleep(5)
                        
                        # Actualizar a 'called' si no dio error inmediato
                        supabase.table("campaign_leads").update({"status": "called"}).eq("id", lead_id).execute()
                        
                    except Exception as e:
                        print(f"❌ [Worker] Error al llamar {phone}: {e}")
                        # Marcar para retry
                        next_retry = (datetime.utcnow() + timedelta(seconds=retry_interval)).isoformat()
                        supabase.table("campaign_leads").update({
                            "status": "failed", 
                            "next_retry_at": next_retry
                        }).eq("id", lead_id).execute()

                # Verificar si campaña ha terminado
                # Count pending or retriable
                # Simplificación: si no encontramos leads arriba, podría haber terminado, 
                # pero mejor comprobamos cuenta exacta.
                
                
        except Exception as e:
            print(f"⚠️ [Worker Loop Error]: {e}")
            await asyncio.sleep(30) # Esperar antes de reintentar si hay error grave
            
        await asyncio.sleep(10) # Pausa entre ciclos

@app.on_event("startup")
async def startup_event():
    print("🌅 Iniciando API (Supabase Integration)...")
    asyncio.create_task(process_campaigns())

