import logging
import sqlite3
from typing import Optional
import os
import aiohttp
import asyncio
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AudioConfig,
    BackgroundAudioPlayer,
    BuiltinAudioClip,
    JobContext,
    JobProcess,
    RunContext,
    ToolError,
    cli,
    function_tool,
    inference,
    room_io,
    utils,
)
from livekit.plugins import (
    silero,
    openai,
    cartesia,
    deepgram,
)

logger = logging.getLogger("agent-Dakota-1ef9")

# Carga el archivo .env de la carpeta actual
load_dotenv()
DB_PATH = os.getenv('DB_PATH', '/app/data/encuestas.db')

def get_config():
    """Lee la configuración de la base de datos"""
    print("🔍 [Agent] Intentando leer configuración de BD...")
    try:
        if not os.path.exists(DB_PATH):
            print(f"⚠️ [Agent] BD no encontrada en {DB_PATH}, usando defaults")
            return {}, {}

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Leer ai_config
        cursor.execute("SELECT * FROM ai_config ORDER BY id DESC LIMIT 1")
        ai_row = cursor.fetchone()
        
        # Leer agent_config
        cursor.execute("SELECT * FROM agent_config ORDER BY id DESC LIMIT 1")
        agent_row = cursor.fetchone()
        
        conn.close()
        
        ai_config = dict(ai_row) if ai_row else {}
        agent_config = dict(agent_row) if agent_row else {}
        
        print(f"✅ [Agent] Config leída: Model={ai_config.get('llm_model', 'default')}, Agent={agent_config.get('name', 'default')}")
        return ai_config, agent_config
    except Exception as e:
        logger.error(f"❌ [Agent] Error leyendo config DB: {e}")
        print(f"❌ [Agent] Error crítico DB: {e}")
        return {}, {}

class DefaultAgent(Agent):
    def __init__(self, instructions: str, greeting: str) -> None:
        # Puerto 8001 para el Bridge local
        self.server_url = os.getenv("BRIDGE_SERVER_URL", "http://127.0.0.1:8001")
        self.greeting = greeting
        self.current_scores = {} # Cache de seguridad
        self.is_completed = False # Flag de encuesta terminada
        
        super().__init__(instructions=instructions)

    # Eliminado on_enter para evitar saludos duplicados con el entrypoint



    @function_tool(name="guardar_encuesta")
    async def _http_tool_guardar_encuesta(
        self, 
        context: RunContext, 
        id_encuesta: int, 
        nota_comercial: Optional[str | int] = None, 
        nota_instalador: Optional[str | int] = None, 
        nota_rapidez: Optional[str | int] = None, 
        comentarios: Optional[str] = None,
        status: Optional[str] = None
    ) -> str | None:
        """
        Guarda los datos de la encuesta. 
        LLAMAR SIEMPRE que se obtenga una nota o comentario.
        Si el cliente dice que NO quiere dejar comentario, llamar con status='completed'.
        """
        print(f"🛠️ [Tool] Ejecutando guardar_encuesta: ID={id_encuesta}, status={status}")
        context.disallow_interruptions()
        url = f"{self.server_url}/guardar-encuesta"
        
        # Enviar también la transcripción acumulada hasta ahora
        transcript = ""
        if hasattr(self, 'full_transcript'):
            transcript = self.full_transcript

        # Guardar en local para el cleanup
        if nota_comercial: self.current_scores["nota_comercial"] = nota_comercial
        if nota_instalador: self.current_scores["nota_instalador"] = nota_instalador
        if nota_rapidez: self.current_scores["nota_rapidez"] = nota_rapidez
        if comentarios: self.current_scores["comentarios"] = comentarios
        if status == 'completed': self.is_completed = True

        payload = {
            "id_encuesta": id_encuesta,
            "nota_comercial": nota_comercial,
            "nota_instalador": nota_instalador,
            "nota_rapidez": nota_rapidez,
            "comentarios": comentarios,
            "transcription": transcript,
            "status": status
        }
        try:
            session = utils.http_context.http_session()
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=10), json=payload) as resp:
                resultado = await resp.text()
                return resultado
        except Exception as e:
            print(f"❌ [Tool] Error en guardar_encuesta: {e}")
            return f"error: {e}"

    @function_tool(name="finalizar_llamada")
    async def _http_tool_finalizar_llamada(
        self, context: RunContext, nombre_sala: str
    ) -> str | None:
        """Corta la llamada inmediatamente. Usar tras despedirse."""
        print(f"🛠️ [Tool] Finalizando llamada en sala: {nombre_sala}")
        context.disallow_interruptions()
        
        # Intentar guardar una última vez con la transcripción completa antes de colgar
        try:
             # Buscar el ID de encuesta en las instrucciones o contexto si fuera posible, 
             # pero aquí confiamos en que ya se ha ido guardando.
             pass
        except: pass

        url = f"{self.server_url}/colgar"
        payload = {"nombre_sala": nombre_sala}
        try:
            session = utils.http_context.http_session()
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=10), json=payload) as resp:
                return await resp.text()
        except:
            return "error"

def prewarm(proc: JobProcess):
    # Ajustamos VAD para que sea menos sensible al ruido de fondo (más robusto)
    proc.userdata["vad"] = silero.VAD.load(min_speech_duration=0.35, min_silence_duration=0.8)

server = AgentServer(setup_fnc=prewarm)

@server.rtc_session(agent_name="Dakota-1ef9")
async def entrypoint(ctx: JobContext):
    pid = os.getpid()
    start_time = asyncio.get_event_loop().time()
    print(f"🔍 [DEBUG] Entrypoint llamado para sala: {ctx.room.name} (PID: {pid})")
    ai_config, agent_config = get_config()
    
    # Usamos llama-3.3-70b-versatile que es el que mejor funciona
    db_model = ai_config.get('llm_model')
    print(f"🔍 [Config] Modelo solicitado en DB: {db_model}")
    
    # Lista blanca básica de modelos Groq
    groq_models = ['llama', 'mixtral', 'gemma', 'groq']
    if db_model and not any(m in db_model.lower() for m in groq_models):
        print(f"⚠️ [Warning] El modelo '{db_model}' no parece ser de Groq via OpenAI. Forzando 'llama-3.3-70b-versatile' para evitar errores.")
        llm_model = 'llama-3.3-70b-versatile'
    else:
        llm_model = db_model or 'llama-3.3-70b-versatile'
    tts_model = ai_config.get('tts_model') or 'sonic-multilingual'
    tts_voice = ai_config.get('tts_voice') or 'fb926b21-4d92-411a-85d0-9d06859e2171'
    stt_model = ai_config.get('stt_model') or 'nova-2'
    
    print(f"🛠️ [Agent] Usando modelos: LLM={llm_model}, TTS={tts_model}, STT={stt_model}")
    
    instructions = """Tu nombre es Dakota. Le llamas de Ausarta para realizar una breve encuesta de satisfacción sobre un servicio reciente.
    
    REGLAS DE ORO (MANDATORIAS):
    1. PRIVACIDAD: NUNCA menciones nombres de salas, IDs técnicos ni bases de datos.
    2. NO REPETIR: No repitas las notas (ej: no digas "He anotado un 8"). Pasa directo a la siguiente.
    3. FLUJO DE PREGUNTAS (UNA A UNA):
       - Pregunta 1: Trato comercial. Tras recibir respuesta -> LLAMA A guardar_encuesta(nota_comercial=nota).
       - Pregunta 2: Instalador. Tras recibir respuesta -> LLAMA A guardar_encuesta(nota_instalador=nota).
       - Pregunta 3: Rapidez. Tras recibir respuesta -> LLAMA A guardar_encuesta(nota_rapidez=nota).
    4. CIERRE: Si no hay más comentarios o dicen que NO, di la despedida final y usa 'finalizar_llamada'.
    5. GUARDADO CRÍTICO: Debes llamar a 'guardar_encuesta' DESPUÉS DE CADA NOTA recibida.
    6. NÚMERO 1: Di siempre "UNO".
    """

    # Extraer ID de la sala
    import re
    survey_id = None
    match = re.search(r'encuesta_(\d+)', ctx.room.name)
    if match:
        survey_id = int(match.group(1))
        instructions += f"\n- IMPORTANTE: El ID de esta encuesta es {survey_id}."

    greeting = "Hola, le llamo de Ausarta por el servicio reciente. ¿Tiene un minuto para una encuesta rápida?"
    customer_name = ctx.job.metadata.strip() if ctx.job.metadata else None
    if customer_name:
        greeting = f"Hola {customer_name}, le llamo de Ausarta. ¿Tiene un minuto para una encuesta rápida?"

    # Inicialización temprana para seguridad del closure
    agent_instance = DefaultAgent(instructions=instructions, greeting=greeting)
    agent_instance.full_transcript = ""
    agent_instance.interaction_count = 0
    agent_instance.total_tokens = 0
    agent_instance.total_seconds = 0
    agent_instance.last_client_text = ""

    # Sincronización en tiempo real (evita perder datos si cuelgan de golpe)
    async def sync_data():
        if not survey_id: return
        url = f"http://127.0.0.1:8001/guardar-encuesta"
        payload = {
            "id_encuesta": survey_id,
            "transcription": agent_instance.full_transcript,
            "tokens_used": agent_instance.total_tokens,
            **agent_instance.current_scores
        }
        try:
            session_http = utils.http_context.http_session()
            async with session_http.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=2)) as r:
                pass
        except: pass

    async def cleanup():
        print(f"🛑 [Shutdown] Iniciando limpieza para sala: {ctx.room.name}")
        # Calcular duración aproximada si hubo intercambio
        duration = 0
        if agent_instance.interaction_count > 0:
            duration = int(asyncio.get_event_loop().time() - start_time)
        
        if survey_id:
            # Si el agente marcó completada explícitamente, status='completed'
            # Si no, mandamos None para que api.py NO marque como completada (Pendiente)
            final_status = 'completed' if agent_instance.is_completed else None
            
            print(f"🔍 [Cleanup] Preparando guardado. interaction_count={agent_instance.interaction_count}, scores={agent_instance.current_scores}")
            
            # Intentar usar la URL del Bridge detectada o 127.0.0.1
            url = f"http://127.0.0.1:8001/guardar-encuesta"
            payload = {
                "id_encuesta": survey_id, 
                "transcription": agent_instance.full_transcript,
                "status": final_status,
                "tokens_used": agent_instance.total_tokens,
                "seconds_used": duration,
                **agent_instance.current_scores
            }
            try:
                # Aumentamos un poco el timeout y usamos aiohttp directamente de forma segura
                print(f"💾 [Shutdown] Guardando {len(agent_instance.full_transcript)} chars de transcripción y notas: {agent_instance.current_scores}")
                async with aiohttp.ClientSession() as s:
                    async with s.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as r:
                        txt = await r.text()
                        print(f"✅ [Shutdown] Respuesta DB: {txt}")
            except Exception as e:
                print(f"⚠️ [Shutdown] No se pudo guardar survey_id={survey_id}: {e}")
        
        print(f"👋 [Shutdown] Limpieza completada.")

    ctx.add_shutdown_callback(cleanup)

    try:
        # VAD ajustado para ignorar ruidos cortos y no interrumpir por ruidos de fondo
        vad = silero.VAD.load(min_speech_duration=0.35, min_silence_duration=0.8)
        
        # Usar los plugins directamente (inference.STT/TTS
        stt = deepgram.STT(model=stt_model, language="es")
        # Forzar language='es' para evitar acento "chino/americano" en modelo multilingual
        tts = cartesia.TTS(model=tts_model, voice=tts_voice, language="es")
        
        # Validar API Key
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
             print("❌ [Error FATAL] NO SE ENCONTRÓ GROQ_API_KEY EN VARIABLES DE ENTORNO. El agente fallará.")
        else:
             print(f"🔑 [Security] GROQ_API_KEY encontrada (termina en ...{groq_key[-4:] if len(groq_key)>4 else '****'})")

        print(f"🤖 [Init] Configurando LLM con modelo: {llm_model}")

        try:
            llm_plugin = openai.LLM(
                model=llm_model, 
                base_url="https://api.groq.com/openai/v1", 
                api_key=groq_key
            )
        except Exception as e:
            print(f"❌ [Error Init] Falló al crear instancia LLM: {e}")
            raise e
        session = AgentSession(
            stt=stt,
            llm=llm_plugin,
            tts=tts,
            vad=vad
        )

        @session.on("transcription_received")
        def on_transcription(transcript):
            if transcript.is_final:
                role = "Agente" if transcript.participant == ctx.room.local_participant else "Cliente"
                msg = f"{role}: {transcript.text}"
                print(f"🎤 {msg}")
                if role == "Cliente":
                    agent_instance.interaction_count += 1
                agent_instance.full_transcript += f"{msg}\n"
                
                if role == "Cliente":
                    asyncio.create_task(sync_data())

        @session.on("llm_response_finished")
        def on_llm_done(resp):
            if hasattr(resp, 'usage') and resp.usage:
                agent_instance.total_tokens += getattr(resp.usage, 'total_tokens', 0)
        
        print(f"🚀 [Agent] Conectando sala {ctx.room.name}...")
        await session.start(agent=agent_instance, room=ctx.room)
        
        # Saludo forzado inicial
        await session.generate_reply(
            instructions=f"Saluda ahora mismo diciendo exactamente: '{greeting}'. No uses herramientas.",
            allow_interruptions=True
        )

        # Eliminamos ruido de fondo para una voz más limpia
        pass
        
    except Exception as e:
        import traceback
        print(f"❌ [Error Crítico] Dakota: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    cli.run_app(server)