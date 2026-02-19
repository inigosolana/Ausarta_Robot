from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import asyncio 
from datetime import datetime
from typing import Optional, Union
from dotenv import load_dotenv
from livekit import api
from supabase import create_client, Client

load_dotenv()
app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONEXIÓN SUPABASE ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Conectado a Supabase correctamente.")
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")

# --- MODELOS ---
class InicioEncuesta(BaseModel):
    telefono: str

class FinEncuesta(BaseModel):
    id_encuesta: Union[int, str, None] = None
    nota_comercial: Union[int, str, None] = None
    nota_instalador: Union[int, str, None] = None
    nota_rapidez: Union[int, str, None] = None
    comentarios: Optional[str] = None 
    status: Optional[str] = None

class ColgarLlamada(BaseModel):
    nombre_sala: str 

@app.exception_handler(Exception)
async def validation_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

# --- UTILS DASHBOARD (SUPABASE) ---
def get_dashboard_stats_supabase():
    if not supabase: return {}
    try:
        # 1. Total Calls
        res_total = supabase.table("encuestas").select("count", count="exact").execute()
        total = res_total.count if res_total.count is not None else 0
        
        # 2. Completed Calls
        res_completed = supabase.table("encuestas").select("count", count="exact").eq("completada", 1).execute()
        completed = res_completed.count if res_completed.count is not None else 0
        
        # 3. Pending
        # Consideramos pending si status es initiated/pending
        res_pending = supabase.table("encuestas").select("count", count="exact").eq("completada", 0).execute()
        pending = res_pending.count if res_pending.count is not None else 0
        
        # 4. Averages
        # Supabase doesn't do aggregations easily in one query without RPC.
        # Fetching all non-null scores to calculate average in python (fine for <10k records)
        res_scr = supabase.table("encuestas").select("puntuacion_comercial, puntuacion_instalador, puntuacion_rapidez").execute()
        data = res_scr.data
        
        avg_com, avg_ins, avg_rap = 0, 0, 0
        count_com, count_ins, count_rap = 0, 0, 0
        
        for r in data:
            if r['puntuacion_comercial'] is not None:
                avg_com += r['puntuacion_comercial']
                count_com += 1
            if r['puntuacion_instalador'] is not None:
                avg_ins += r['puntuacion_instalador']
                count_ins += 1
            if r['puntuacion_rapidez'] is not None:
                avg_rap += r['puntuacion_rapidez']
                count_rap += 1
                
        avg_com = round(avg_com / count_com, 1) if count_com else 0
        avg_ins = round(avg_ins / count_ins, 1) if count_ins else 0
        avg_rap = round(avg_rap / count_rap, 1) if count_rap else 0
        overall = round((avg_com + avg_ins + avg_rap) / 3, 1)

        return {
            "total_calls": total,
            "completed_calls": completed,
            "pending_calls": pending,
            "avg_scores": {
                "comercial": avg_com,
                "instalador": avg_ins,
                "rapidez": avg_rap,
                "overall": overall
            }
        }
    except Exception as e:
        print(f"Error stats: {e}")
        return {"total_calls": 0, "completed_calls": 0, "pending_calls": 0, "avg_scores": {}}

def get_calls_supabase(limit=50):
    if not supabase: return []
    try:
        res = supabase.table("encuestas").select("*").order("fecha", desc=True).limit(limit).execute()
        calls = res.data
        mapped = []
        for c in calls:
            # Map status nicely
            raw_status = c.get('status', 'initiated')
            if c.get('completada'): raw_status = 'completed'
            
            mapped.append({
                "id": c['id'],
                "telefono": c.get('telefono'),
                "phone": c.get('telefono'),
                "campaign": "Ausarta", 
                "campaign_name": "Ausarta",
                "fecha": c.get('fecha'),
                "date": c.get('fecha'),
                "completada": c.get('completada'),
                "status": raw_status,
                "scores": {
                    "comercial": c.get('puntuacion_comercial'),
                    "instalador": c.get('puntuacion_instalador'),
                    "rapidez": c.get('puntuacion_rapidez')
                },
                "puntuacion_comercial": c.get('puntuacion_comercial'),
                "puntuacion_instalador": c.get('puntuacion_instalador'),
                "puntuacion_rapidez": c.get('puntuacion_rapidez'),
                
                "llm_model": c.get('llm_model', "Unknown"),
                "comentarios": c.get('comentarios'),
                "transcription": c.get('transcription')
            })
        return mapped
    except Exception as e:
        print(f"Error recent calls: {e}")
        return []

# 1. INICIO
@app.post("/iniciar-encuesta")
async def iniciar_encuesta(datos: InicioEncuesta):
    print(f"📝 1. Creando ficha (Supabase) para: {datos.telefono}")
    if not supabase: return {"error": "No DB"}
    try:
        data = {
            "telefono": datos.telefono,
            "fecha": datetime.now().isoformat(),
            "completada": 0,
            "status": "initiated"
        }
        res = supabase.table("encuestas").insert(data).execute()
        if res.data:
            nuevo_id = res.data[0]['id']
            print(f"✅ Ficha creada con ID: {nuevo_id}")
            return {"id": nuevo_id}
        else:
            return {"error": "No ID returned"}
    except Exception as e:
        print(f"Error DB: {e}")
        return {"error": str(e)}

# 2. GUARDAR
@app.post("/guardar-encuesta")
async def guardar_encuesta(datos: FinEncuesta):
    print(f"📥 Recibiendo datos parciales/finales para ID: {datos.id_encuesta}")
    if not supabase: return {"error": "No DB"}
    
    def clean_nota(val):
        try:
            num = int(val)
            if 1 <= num <= 10: return num
            return None 
        except: return None
    
    val_comercial = clean_nota(datos.nota_comercial) if datos.nota_comercial is not None else None
    val_instalador = clean_nota(datos.nota_instalador) if datos.nota_instalador is not None else None
    val_rapidez = clean_nota(datos.nota_rapidez) if datos.nota_rapidez is not None else None
    val_comentarios = datos.comentarios

    # Extract ID logic
    id_final = None
    try:
        # Try as int direct
        if isinstance(datos.id_encuesta, int):
            id_final = datos.id_encuesta
        # Try parsing string
        elif datos.id_encuesta:
             import re
             nums = re.findall(r'\d+', str(datos.id_encuesta))
             if nums and int(nums[0]) > 0: id_final = int(nums[0])
    except: pass

    if not id_final:
        # Fallback: get last id
        try:
            res = supabase.table("encuestas").select("id").order("id", desc=True).limit(1).execute()
            if res.data: id_final = res.data[0]['id']
        except: pass
    
    if not id_final: return {"status": "error", "msg": "No ID found"}

    updates = {}
    if val_comercial is not None: updates["puntuacion_comercial"] = val_comercial
    if val_instalador is not None: updates["puntuacion_instalador"] = val_instalador
    if val_rapidez is not None: updates["puntuacion_rapidez"] = val_rapidez
    if val_comentarios is not None:
        updates["comentarios"] = val_comentarios
    
    # Lógica de estados
    if datos.status:
        print(f"🔄 Actualizando status a: {datos.status}")
        updates["status"] = datos.status
        if datos.status == "completed":
             updates["completada"] = 1
    elif val_comentarios is not None:
         # Implicit completion if comments are passed locally (fallback)
         pass

    if not updates:
        print("⚠️ Llamada a guardar sin datos nuevos.")
        return {"status": "no_changes"}

    try:
        supabase.table("encuestas").update(updates).eq("id", id_final).execute()
        print(f"💾 Guardado incremental en ficha {id_final}: {updates}")
        return {"status": "success"}
    except Exception as e:
        print(f"Error updating Supabase: {e}")
        return {"error": str(e)}

# 3. COLGAR
@app.post("/colgar")
async def colgar(datos: ColgarLlamada):
    print(f"✂️  Petición de colgar.")
    lkapi = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )
    try:
        await lkapi.room.delete_room(api.DeleteRoomRequest(room=datos.nombre_sala))
        return {"status": "success"}
    except:
        return {"status": "error"} 
    finally:
        await lkapi.aclose()


# --- FRONTEND ENDPOINTS ---

@app.get("/api/dashboard/stats")
async def dashboard_stats():
    return get_dashboard_stats_supabase()

@app.get("/dashboard/stats") 
async def dashboard_stats_alias():
    return get_dashboard_stats_supabase()

@app.get("/api/dashboard/recent-calls")
async def recent_calls():
    return get_calls_supabase(limit=50)

@app.get("/dashboard/recent-calls")
async def recent_calls_alias():
    return get_calls_supabase(limit=50)

@app.get("/api/results")
async def results():
    return get_calls_supabase(limit=1000)

@app.get("/dashboard/integrations")
async def integrations_alias():
    return [
        {"name": "Database", "provider": "Supabase", "active": bool(supabase), "env_var": "SUPABASE_URL"},
        {"name": "LiveKit", "provider": "LiveKit Cloud", "active": bool(os.getenv("LIVEKIT_URL")), "env_var": "LIVEKIT_URL"},
        {"name": "Voice Agent", "provider": "Dakota", "active": True, "model": "Llama 3.3"},
        {"name": "TTS", "provider": "Cartesia", "active": bool(os.getenv("CARTESIA_API_KEY")), "env_var": "CARTESIA_API_KEY"}
    ]

@app.get("/")
async def root():
    return {"status": "ok", "message": "Ausarta Voice Agent Bridge Server Running (Supabase)"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)