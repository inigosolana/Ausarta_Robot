import os
import aiohttp
import asyncio
from datetime import datetime, timedelta, timezone
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
    retry_interval: int = 60 # Minutos - Default 1 hora

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
        response = supabase.table("encuestas").select("*").order("fecha", desc=True).limit(50).execute()
        # Mapeamos los campos de la BD al formato que espera el frontend
        mapped = []
        for r in response.data:
            mapped.append({
                "id": r.get("id"),
                "phone": r.get("telefono", ""),
                "campaign": r.get("campaign_name", r.get("nombre_cliente", "—")),
                "date": r.get("fecha", ""),
                "status": r.get("status", "pending"),
                "llm_model": r.get("llm_model"),
                "scores": {
                    "comercial": r.get("puntuacion_comercial"),
                    "instalador": r.get("puntuacion_instalador"),
                    "rapidez": r.get("puntuacion_rapidez")
                }
            })
        return mapped
    except Exception as e:
        print(f"Error recent calls: {e}")
        return []

@app.get("/api/results")
async def get_all_results():
    if not supabase: return []
    try:
        # Traemos todos los resultados de encuestas
        response = supabase.table("encuestas").select("*").order("fecha", desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Error getting results: {e}")
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
    
    print(f"📥 [API] Recibiendo datos encuesta {datos.id_encuesta}: {datos.model_dump(exclude_none=True)}")
    
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

    # update_data["updated_at"] = datetime.utcnow().isoformat()

    try:
        supabase.table("encuestas").update(update_data).eq("id", datos.id_encuesta).execute()
        
        # Si la encuesta se completó o rechazó, actualizamos el LEAD asociado también
        # Buscamos el lead por call_id (que es el id_encuesta)
        if datos.status in ('completed', 'rejected_opt_out', 'incomplete', 'failed'):
             lead_update = {"status": datos.status}
             
             # Si es fallo o incompleta, programamos reintento automático
             if datos.status in ('incomplete', 'failed'):
                 # Intentar obtener el intervalo de reintento de la campaña
                 retry_seconds = 3600 # Default 1 hora
                 try:
                     # Obtener campaign_id del lead
                     lead_res = supabase.table("campaign_leads").select("campaign_id").eq("call_id", datos.id_encuesta).limit(1).execute()
                     if lead_res.data:
                         camp_id = lead_res.data[0]['campaign_id']
                         # Obtener retry_interval de la campaña
                         camp_res = supabase.table("campaigns").select("retry_interval").eq("id", camp_id).limit(1).execute()
                         if camp_res.data:
                             camp_retry = camp_res.data[0]['retry_interval']
                             # Asegurarse que sea un valor razonable
                             if camp_retry and camp_retry > 0:
                                 retry_seconds = camp_retry
                 except Exception as ex_interval:
                     print(f"⚠️ Error fetching campaign retry interval: {ex_interval}")

                 next_retry = (datetime.utcnow() + timedelta(seconds=retry_seconds)).isoformat()
                 lead_update["next_retry_at"] = next_retry
             
             supabase.table("campaign_leads").update(lead_update).eq("call_id", datos.id_encuesta).execute()

        return {"status": "ok", "updated": update_data}
    except Exception as e:
        print(f"❌ Error DB al guardar: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# --- CONFIGURACIÓN DEL AGENTE ---

import time
import random

@app.post("/api/calls/outbound")
async def make_outbound_call(request: dict):
    """Endpoint para llamadas de prueba desde el Dashboard"""
    phone = request.get("phoneNumber")
    agent_id = request.get("agentId", "1")
    
    if not phone:
        return JSONResponse(status_code=400, content={"error": "Phone number is required"})

    print(f"📞 [API] Iniciando solicitud de llamada a {phone} (Agent ID: {agent_id})...")
    
    try:
        # 1. Crear registro en BD
        if supabase:
            encuesta_data = {
                "telefono": phone,
                "nombre_cliente": "Prueba Dashboard",
                "fecha": datetime.now(timezone.utc).isoformat(),
                "status": "initiated",
                "completada": 0
            }
            res_enc = supabase.table("encuestas").insert(encuesta_data).execute()
            encuesta_id = res_enc.data[0]['id']
        else:
            encuesta_id = random.randint(1000, 9999)
            
        # 2. Configurar LiveKit con nombre de sala ÚNICO
        sip_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
        room_name = f"encuesta_{encuesta_id}_{int(time.time())}"

        print(f"📡 [API] Creando sala: {room_name}")
        try:
            await lkapi.room.create_room(api.CreateRoomRequest(name=room_name))
        except Exception as e:
            print(f"⚠️ [API] Aviso al crear sala (puede que ya exista): {e}")

        # 3. Dial Out
        print(f"☎️ [API] Marcando vía SIP a {phone} en sala {room_name}...")
        await lkapi.sip.create_sip_participant(api.CreateSIPParticipantRequest(
            sip_trunk_id=sip_trunk_id,
            sip_call_to=phone,
            room_name=room_name,
            participant_identity=f"user_{phone}_{int(time.time())}",
            participant_name="Test User"
        ))

        # 4. FORZAR UNIÓNN DEL AGENTE (Job Dispatch)
        # Esto asegura que LiveKit mande al agente Dakota-1ef9 a la sala inmediatamente
        print(f"🚀 [API] Solicitando despacho de agente 'Dakota-1ef9' a sala {room_name}...")
        try:
            await lkapi.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(
                agent_name="Dakota-1ef9",
                room=room_name
            ))
        except Exception as e:
            print(f"⚠️ [API] No se pudo forzar despacho (puede que ya exista regla): {e}")

        return {"status": "ok", "roomName": room_name, "callId": encuesta_id}
        
    except Exception as e:
        print(f"❌ [API] Error fatal en outbound call: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

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

@app.get("/api/prompts")
async def get_prompts_alias():
    """Alias para que el frontend pueda cargar las instrucciones si usa este endpoint"""
    return await get_agents()

@app.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, config: dict):
    if not supabase: return {"error": "No DB"}
    try:
        # Ignoramos el ID de la URL y actualizamos el ÚNICO agente que tenemos
        curr = supabase.table("agent_config").select("id").limit(1).execute()
        
        db_config = {}
        if "name" in config: db_config["name"] = config["name"]
        if "instructions" in config: db_config["instructions"] = config["instructions"]
        if "greeting" in config: db_config["greeting"] = config["greeting"]
        if "description" in config: db_config["description"] = config["description"]
        if "useCase" in config: db_config["use_case"] = config["useCase"] 
        
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

# --- ALIAS FOR FRONTEND COMPATIBILITY ---
@app.get("/api/settings")
async def get_settings_alias():
    return await get_ai_config()

@app.post("/api/settings")
async def update_settings_alias(config: dict):
    return await update_ai_config(config)

# --- CAMPAIGN MANAGEMENT ---

@app.delete("/api/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: int):
    if not supabase: return {"error": "No DB"}
    try:
        # Borrar leads primero (aunque Cascade delete en DB debería hacerlo, mejor asegurar)
        supabase.table("campaign_leads").delete().eq("campaign_id", campaign_id).execute()
        # Borrar campaña
        supabase.table("campaigns").delete().eq("id", campaign_id).execute()
        return {"status": "ok", "message": f"Campaña {campaign_id} eliminada"}
    except Exception as e:
        print(f"Error deleting campaign: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/campaigns")
async def create_campaign(campaign: CampaignModel, leads: List[CampaignLeadModel]):
    if not supabase: return {"error": "No DB"}
    
    try:
        # Lógica de auto-activación
        status_final = campaign.status
        if not campaign.scheduled_time and status_final == 'pending':
            status_final = 'active'

        # 1. Crear Campaña
        camp_data = {
            "name": campaign.name,
            "agent_id": campaign.agent_id,
            "status": status_final,
            "scheduled_time": campaign.scheduled_time.isoformat() if campaign.scheduled_time else None,
            "retries_count": campaign.retries_count,
            "retry_interval": campaign.retry_interval * 60, # Convertir minutos a segundos para consistencia interna
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
            
        # El worker ya está corriendo en background desde el startup y detectará la nueva campaña activa
        # No lanzamos otro process_campaigns() aquí para evitar concurrencia duplicada.
             
        return {"id": campaign_id, "message": f"Campaña creada con {len(leads_data)} leads"}
        
    except Exception as e:
        print(f"Error creando campaña: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/campaigns")
async def list_campaigns():
    if not supabase: return []
    try:
        # Traer campañas ordenadas por fecha reciente
        res = supabase.table("campaigns").select("*").order("created_at", desc=True).limit(20).execute()
        return res.data
    except Exception as e:
        print(f"Error listing campaigns: {e}")
        return []

@app.get("/api/campaigns/{campaign_id}")
async def get_campaign_details(campaign_id: int):
    if not supabase: return {"error": "No DB"}
    try:
        # 1. Obtener datos de la campaña
        res_camp = supabase.table("campaigns").select("*").eq("id", campaign_id).execute()
        if not res_camp.data:
            return JSONResponse(status_code=404, content={"error": "Campaign not found"})
        
        campaign = res_camp.data[0]
        
        # 2. Obtener leads asociados
        res_leads = supabase.table("campaign_leads").select("*").eq("campaign_id", campaign_id).execute()
        leads = res_leads.data
        
        # 3. Obtener encuestas asociadas para enriquecer datos
        call_ids = [l['call_id'] for l in leads if l.get('call_id')]
        surveys_map = {}
        if call_ids:
            try:
                # Traer encuestas en batch (puede requerir paginación si son muchas, pero para MVP vale)
                res_surveys = supabase.table("encuestas").select("*").in_("id", call_ids).execute()
                for s in res_surveys.data:
                    surveys_map[s['id']] = s
            except Exception as e:
                print(f"Error fetching surveys for campaign: {e}")

        # 4. Calcular estadísticas y enriquecer leads
        stats = {
            "total": len(leads),
            "pending": 0,
            "calling": 0,
            "called": 0,
            "completed": 0,
            "failed": 0,
            "incomplete": 0
        }
        
        # Métricas de calidad (Promedios)
        sum_com = 0; count_com = 0
        sum_ins = 0; count_ins = 0
        sum_rap = 0; count_rap = 0
        
        enriched_leads = []
        
        for l in leads:
            status = l['status']
            if status in stats:
                stats[status] += 1
            else:
                # Fallback para estados raros
                stats["pending"] += 1
            
            # Enriquecer con datos de encuesta
            call_id = l.get("call_id")
            survey = surveys_map.get(call_id)
            
            l["encuesta"] = survey # Mantener anidado por si acaso
            
            if survey:
                # Aplanar datos para el frontend (CampaignsView.tsx espera las keys en la raíz del objeto lead)
                l['puntuacion_comercial'] = survey.get('puntuacion_comercial')
                l['puntuacion_instalador'] = survey.get('puntuacion_instalador')
                l['puntuacion_rapidez'] = survey.get('puntuacion_rapidez')
                l['comentarios'] = survey.get('comentarios')
                l['transcription_preview'] = survey.get('transcription') # Ojo: Frontend puede usar 'transcription_preview'

                # Acumular para promedios si hay nota
                if survey.get('puntuacion_comercial') is not None:
                    sum_com += survey['puntuacion_comercial']
                    count_com += 1
                if survey.get('puntuacion_instalador') is not None:
                    sum_ins += survey['puntuacion_instalador']
                    count_ins += 1
                if survey.get('puntuacion_rapidez') is not None:
                    sum_rap += survey['puntuacion_rapidez']
                    count_rap += 1
            
            enriched_leads.append(l)

        metrics = {
            "avg_comercial": round(sum_com / count_com, 1) if count_com > 0 else 0,
            "avg_instalador": round(sum_ins / count_ins, 1) if count_ins > 0 else 0,
            "avg_rapidez": round(sum_rap / count_rap, 1) if count_rap > 0 else 0,
            "avg_overall": round((sum_com + sum_ins + sum_rap) / (count_com + count_ins + count_rap), 1) if (count_com + count_ins + count_rap) > 0 else 0
        }
        
        return {
            "campaign": campaign,
            "stats": stats,
            "metrics": metrics,
            "leads": enriched_leads
        }
        
    except Exception as e:
        print(f"Error getting campaign details {campaign_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- WORKER DE LLAMADAS (Background) ---

async def process_campaigns():
    """Bucle principal que busca leads pendientes y lanza llamadas DE UNA EN UNA (Secuencial)"""
    global supabase  # Necesario para poder recrear el cliente si se pierde la conexión
    print("🚀 Iniciando Worker de Campañas SECUENCIAL (Supabase)...")
    
    while True:
        try:
            # 1. Buscar campañas activas
            res_camps = supabase.table("campaigns").select("*").eq("status", "active").execute()
            active_campaigns = res_camps.data
            
            for camp in active_campaigns:
                campaign_id = camp['id']
                max_retries = camp['retries_count']
                retry_interval = camp['retry_interval'] or 3600 # Fallback

                # 2. Buscar 1 LEAD pendiente (Limit 1 para secuencialidad estricta)
                now_str = datetime.utcnow().isoformat()
                
                # Prioridad 1: Pending
                res_leads = supabase.table("campaign_leads").select("*") \
                    .eq("campaign_id", campaign_id) \
                    .eq("status", "pending") \
                    .limit(1).execute()
                
                leads_to_call = res_leads.data
                
                # Prioridad 2: Retries (si no hay pending)
                # NOTA: 'rejected' NO se reintenta (el usuario dijo que no quiere).
                # Solo se reintentan: failed (móvil apagado/buzón/ocupado), unreached (no contesta/cuelga antes), incomplete (encuesta a medias)
                if not leads_to_call:
                     res_retries = supabase.table("campaign_leads").select("*") \
                        .eq("campaign_id", campaign_id) \
                        .in_("status", ["failed", "unreached", "incomplete"]) \
                        .lt("retries_attempted", max_retries) \
                        .lt("next_retry_at", now_str) \
                        .limit(1).execute()
                     leads_to_call = res_retries.data

                if not leads_to_call:
                    continue # Siguiente campaña

                # Procesar EL lead (solo 1)
                lead = leads_to_call[0]
                lead_id = lead['id']
                phone = lead['phone_number']
                name = lead['customer_name']
                initial_status = lead['status']
                
                call_type = "REINTENTO" if initial_status in ['failed', 'unreached', 'incomplete'] else "LLAMADA NUEVA"
                
                print(f"🔄 [Worker] Procesando lead {phone} (Campaña {campaign_id}) | Tipo: {call_type}...")

                # Actualizar a 'calling'
                supabase.table("campaign_leads").update({
                    "status": "calling", 
                    "last_call_at": datetime.utcnow().isoformat(),
                    "retries_attempted": lead['retries_attempted'] + 1
                }).eq("id", lead_id).execute()
                
                # 1. Crear entrada en 'encuestas'
                encuesta_data = {
                    "telefono": phone,
                    "nombre_cliente": name,
                    "fecha": datetime.now(timezone.utc).isoformat(),
                    "status": "initiated",
                    "completada": 0
                }
                res_enc = supabase.table("encuestas").insert(encuesta_data).execute()
                encuesta_id = res_enc.data[0]['id']
                
                # 2. Vincular lead
                supabase.table("campaign_leads").update({"call_id": encuesta_id}).eq("id", lead_id).execute()

                # 3. Lanzar Llamada y ESPERAR
                try:
                    print(f"📞 [Worker] Llamando a {phone} (Encuesta ID: {encuesta_id})...")
                    
                    sip_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
                    room_name = f"encuesta_{encuesta_id}"
                    
                    try:
                        await lkapi.room.create_room(api.CreateRoomRequest(name=room_name))
                    except: pass 

                    await lkapi.sip.create_sip_participant(api.CreateSIPParticipantRequest(
                        sip_trunk_id=sip_trunk_id,
                        sip_call_to=phone,
                        room_name=room_name,
                        participant_identity=f"user_{phone}",
                        participant_name=name or "Cliente"
                    ))

                    # 4. FORZAR UNIÓNN DEL AGENTE (Igual que en llamada de prueba)
                    # Esto asegura que LiveKit mande al agente a la sala inmediatamente
                    print(f"🚀 [Worker] Despachando agente 'Dakota-1ef9' a sala {room_name}...")
                    try:
                        await lkapi.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(
                            agent_name="Dakota-1ef9",
                            room=room_name
                        ))
                    except Exception as e:
                        print(f"⚠️ [Worker] No se pudo despachar agente (ya existe?): {e}")
                    
                    # --- WAIT LOOP (ESPERA ACTIVA) ---
                    print(f"⏳ [Worker] Esperando finalización de llamada {encuesta_id}...")
                    
                    max_wait_seconds = 600 # 10 minutos máximo de llamada
                    waited = 0
                    call_finished = False
                    room_gone_count = 0  # Contador de veces consecutivas que la sala no existe
                    
                    while waited < max_wait_seconds:
                        await asyncio.sleep(5) # Polling cada 5s
                        waited += 5
                        
                        try:
                            # --- CHECK 1: Verificar si la sala LiveKit aún existe ---
                            # Si la sala ya no existe, la llamada terminó (cuelgue temprano, no contesta, etc.)
                            try:
                                rooms = await lkapi.room.list_rooms(api.ListRoomsRequest(names=[room_name]))
                                room_exists = len(rooms.rooms) > 0 if rooms and rooms.rooms else False
                            except:
                                room_exists = False  # Error consultando = asumimos que no existe
                            
                            if not room_exists:
                                room_gone_count += 1
                                # Esperamos 2 checks consecutivos (10s) para confirmar que realmente se fue
                                if room_gone_count >= 2:
                                    print(f"🔍 [Worker] Sala {room_name} NO existe (confirmado). Verificando estado final...")
                                    # Dar 5s extra para que el fallback del agente grabe el status
                                    await asyncio.sleep(5)
                            else:
                                room_gone_count = 0  # Reset si la sala existe
                            
                            # --- CHECK 2: Consultar estado en Supabase ---
                            r_status = supabase.table("encuestas").select("status, completada").eq("id", encuesta_id).execute()
                            if r_status.data:
                                s = r_status.data[0]
                                st = s.get('status')
                                comp = s.get('completada')
                                
                                # Criterio de fin: status final O completada=1
                                if comp == 1 or st in ['completed', 'failed', 'rejected', 'rejected_opt_out', 'incomplete', 'unreached']:
                                    print(f"✅ [Worker] Llamada {encuesta_id} terminó con estado: {st}")
                                    call_finished = True
                                    
                                    # --- PROPAGACIÓN DE ESTADO ---
                                    lead_update_payload = {"status": st}
                                    
                                    # Solo reintentar: failed (apagado/buzón/ocupado), unreached (no contesta), incomplete (a medias)
                                    # NO reintentar: rejected (usuario dijo no), completed (encuesta terminada)
                                    if st in ['failed', 'unreached', 'incomplete']:
                                        next_retry_time = (datetime.utcnow() + timedelta(seconds=retry_interval)).isoformat()
                                        lead_update_payload["next_retry_at"] = next_retry_time
                                        print(f"🔄 [Worker] Programando reintento para {phone} en {retry_interval}s")
                                    
                                    supabase.table("campaign_leads").update(lead_update_payload).eq("id", lead_id).execute()
                                    break
                                
                                # Si la sala desapareció pero el status sigue en 'initiated', el agente no guardó nada
                                # Esto pasa cuando cuelgan antes de coger (USER_REJECTED)
                                if room_gone_count >= 2 and st == 'initiated':
                                    print(f"⚠️ [Worker] Sala desaparecida + status 'initiated' = No contesta/Colgó antes")
                                    # Marcar como unreached
                                    supabase.table("encuestas").update({
                                        "status": "unreached",
                                        "comentarios": "No contestó o colgó antes de responder"
                                    }).eq("id", encuesta_id).execute()
                                    
                                    lead_update_payload = {
                                        "status": "unreached",
                                        "next_retry_at": (datetime.utcnow() + timedelta(seconds=retry_interval)).isoformat()
                                    }
                                    supabase.table("campaign_leads").update(lead_update_payload).eq("id", lead_id).execute()
                                    print(f"🔄 [Worker] Programando reintento para {phone} en {retry_interval}s (unreached)")
                                    call_finished = True
                                    break
                        
                        except Exception as poll_error:
                            error_msg = str(poll_error)
                            if 'ConnectionTerminated' in error_msg or 'ConnectionReset' in error_msg:
                                print(f"⚠️ [Worker] Conexión Supabase perdida, reconectando...")
                                # Recrear cliente Supabase
                                try:
                                    from supabase import create_client
                                    supabase = create_client(
                                        os.getenv("SUPABASE_URL"),
                                        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                                    )
                                    print("✅ [Worker] Supabase reconectado")
                                except Exception as reconn_err:
                                    print(f"❌ [Worker] Error reconectando Supabase: {reconn_err}")
                            else:
                                print(f"⚠️ [Worker] Error en polling: {poll_error}")
                    
                    if not call_finished:
                        print(f"⚠️ [Worker] Timeout esperando llamada {encuesta_id} (force break)")
                        # Forzar status update
                        try:
                            supabase.table("encuestas").update({"status": "unreached"}).eq("id", encuesta_id).execute()
                            supabase.table("campaign_leads").update({
                                "status": "unreached",
                                "next_retry_at": (datetime.utcnow() + timedelta(seconds=retry_interval)).isoformat()
                            }).eq("id", lead_id).execute()
                        except Exception as timeout_err:
                            print(f"❌ [Worker] Error actualizando timeout: {timeout_err}")

                except Exception as e:
                    print(f"❌ [Worker] Error al llamar {phone}: {e}")
                    # Marcar retry
                    next_retry = (datetime.utcnow() + timedelta(seconds=retry_interval)).isoformat()
                    supabase.table("campaign_leads").update({
                        "status": "failed", 
                        "next_retry_at": next_retry
                    }).eq("id", lead_id).execute()

                # --- COOLDOWN ENTRE LLAMADAS ---
                # Esperamos 120s (2 min) para asegurar que Asterisk/LiveKit liberen totalmente los recursos
                # y para dar tiempo entre llamadas.
                print("⏳ [Worker] Cooldown de 120s (2 min) antes del siguiente lead...")
                await asyncio.sleep(120)

        except Exception as e:
            print(f"⚠️ [Worker Loop Error]: {e}")
            await asyncio.sleep(30)
            
        await asyncio.sleep(2) # Pequeña pausa entre iteraciones de campañas

@app.on_event("startup")
async def startup_event():
    print("🌅 Iniciando API (Supabase Integration)...")
    asyncio.create_task(process_campaigns())
