from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import mysql.connector
import os
import re
import asyncio 
from datetime import datetime
from typing import Optional, Union
from dotenv import load_dotenv
from livekit import api

load_dotenv()
app = FastAPI()

# --- CONEXIÓN DB ---
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'ausarta_user'),
        password=os.getenv('DB_PASSWORD', 'Noruega.15'),
        database=os.getenv('DB_NAME', 'encuestas_ausarta')
    )

def init_mysql():
    """Asegura que las columnas necesarias existen en MySQL"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Añadir status si no existe
        try:
            cursor.execute("ALTER TABLE encuestas ADD COLUMN status VARCHAR(20) DEFAULT 'pending'")
            print("📦 [MySQL] Columna 'status' añadida.")
        except: pass
        
        # Añadir llm_model si no existe
        try:
            cursor.execute("ALTER TABLE encuestas ADD COLUMN llm_model VARCHAR(50) DEFAULT NULL")
            print("📦 [MySQL] Columna 'llm_model' añadida.")
        except: pass
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Error inicializando MySQL: {e}")

# Inicializar al arrancar
init_mysql()

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
    llm_model: Optional[str] = "llama-3.3-70b-versatile"

class ColgarLlamada(BaseModel):
    nombre_sala: str 

@app.exception_handler(Exception)
async def validation_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

# 1. INICIO
@app.post("/iniciar-encuesta")
async def iniciar_encuesta(datos: InicioEncuesta):
    print(f"📝 1. Creando ficha para: {datos.telefono}")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO encuestas (telefono, fecha, completada, status) VALUES (%s, %s, 0, 'pending')", (datos.telefono, datetime.now()))
        conn.commit()
        nuevo_id = cursor.lastrowid
        print(f"✅ Ficha creada con ID: {nuevo_id}")
        return {"id": nuevo_id}
    finally:
        cursor.close()
        conn.close()

# 2. GUARDAR (VERSIÓN INCREMENTAL INTELIGENTE)
@app.post("/guardar-encuesta")
async def guardar_encuesta(datos: FinEncuesta):
    print(f"📥 Recibiendo datos para ID: {datos.id_encuesta} (Status: {datos.status})")
    
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
    val_status = datos.status
    val_llm = datos.llm_model

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Recuperamos ID
        id_final = None
        try:
            nums = re.findall(r'\d+', str(datos.id_encuesta))
            if nums and int(nums[0]) > 0: id_final = int(nums[0])
        except: pass

        if not id_final:
            cursor.execute("SELECT id FROM encuestas ORDER BY id DESC LIMIT 1")
            res = cursor.fetchone()
            if res: id_final = res[0]
        
        if not id_final: return {"status": "error", "msg": "No ID found"}

        updates = []
        values = []

        if val_comercial is not None:
            updates.append("puntuacion_comercial=%s")
            values.append(val_comercial)
        
        if val_instalador is not None:
            updates.append("puntuacion_instalador=%s")
            values.append(val_instalador)
            
        if val_rapidez is not None:
            updates.append("puntuacion_rapidez=%s")
            values.append(val_rapidez)

        if val_comentarios is not None:
            # Aceptamos 'Ninguno' como comentario válido para cerrar
            updates.append("comentarios=%s")
            values.append(val_comentarios)

        if val_status is not None:
            updates.append("status=%s")
            values.append(val_status)
            if val_status == 'completed':
                updates.append("completada=1")
            elif val_status == 'rejected_opt_out':
                updates.append("completada=0") # Opcional: marcar como procesada pero no completada

        if val_llm:
            updates.append("llm_model=%s")
            values.append(val_llm)

        if not updates:
            print("⚠️ Sin cambios para guardar.")
            return {"status": "no_changes"}

        query_sql = f"UPDATE encuestas SET {', '.join(updates)} WHERE id=%s"
        values.append(id_final)

        cursor.execute(query_sql, tuple(values))
        conn.commit()
        print(f"💾 Guardado incremental en ficha {id_final} (updates: {len(updates)})")
        return {"status": "success"}
    finally:
        cursor.close()
        conn.close()

# 3. COLGAR
@app.post("/colgar")
async def colgar(datos: ColgarLlamada):
    print(f"✂️  Petición de colgar recibida.")
    # Espera un poco para que la IA termine la despedida
    await asyncio.sleep(2) 
    
    lkapi = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )
    try:
        await lkapi.room.delete_room(api.DeleteRoomRequest(room=datos.nombre_sala))
        print(f"✅ Sala {datos.nombre_sala} eliminada.")
        return {"status": "success"}
    except Exception as e:
        print(f"⚠️ Error colgando: {e}")
        return {"status": "error"}
    finally:
        await lkapi.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)