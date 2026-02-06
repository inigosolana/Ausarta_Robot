from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import mysql.connector
import os
import re
import asyncio # <--- IMPORTANTE: Necesario para la pausa
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

# --- MODELOS ---
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

# --- DEBUGGING ---
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
        cursor.execute("INSERT INTO encuestas (telefono, fecha, completada) VALUES (%s, %s, 0)", (datos.telefono, datetime.now()))
        conn.commit()
        nuevo_id = cursor.lastrowid
        print(f"✅ Ficha creada con ID: {nuevo_id} (Esperando a la IA...)")
        return {"id": nuevo_id}
    finally:
        cursor.close()
        conn.close()

# 2. GUARDAR
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
               SET puntuacion_comercial=%s, puntuacion_instalador=%s, puntuacion_rapidez=%s, comentarios=%s, completada=1
               WHERE id=%s""",
            (clean_nota(datos.nota_comercial), clean_nota(datos.nota_instalador), clean_nota(datos.nota_rapidez), datos.comentarios, id_final)
        )
        conn.commit()
        print(f"🚀 ¡EXITO! Datos guardados en ficha {id_final}.")
        return {"status": "success"}
    finally:
        cursor.close()
        conn.close()

# 3. COLGAR CON CORTESÍA ⏳
@app.post("/colgar")
async def colgar(datos: ColgarLlamada):
    print(f"✂️  Petición de colgar recibida.")
    
    # --- PAUSA DRAMÁTICA ---
    # Esperamos 3 segundos para que la IA termine de decir "Adiós"
    print("⏳ Esperando 3 segundos para dar tiempo a la despedida...")
    await asyncio.sleep(2) 
    # -----------------------

    lkapi = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )
    
    try:
        # INTENTO 1
        await lkapi.room.delete_room(api.DeleteRoomRequest(room=datos.nombre_sala))
        print("✅ Llamada cortada.")
        return {"status": "success"}
    except Exception as e:
        print(f"⚠️ Falló borrar '{datos.nombre_sala}'. Buscando la sala REAL...")
        
        # INTENTO 2: AUTO-REPARACIÓN
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