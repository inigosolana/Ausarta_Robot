import logging
import sqlite3
from typing import Optional
import os
import aiohttp
import asyncio
import traceback
import re
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
    google,
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
    finally:
        if 'conn' in locals(): conn.close()

def get_app_settings():
    """Lee configuración global de la tabla app_settings"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM app_settings")
        d = {row['key']: row['value'] for row in cursor.fetchall()}
        conn.close()
        return d
    except Exception as e:
        print(f"⚠️ [Agent] Error leyendo settings: {e}")
        return {}

def log_system_alert(type, message):
    """Registra una alerta en la BD para que el frontend la muestre"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO system_alerts (type, message) VALUES (?, ?)", (type, message))
        conn.commit()
        conn.close()
        print(f"🚨 [Alert System] Nueva alerta registrada: {type} - {message}")
    except Exception as e:
        print(f"❌ [Alert System] Fallo al registrar alerta: {e}")


class DefaultAgent(Agent):
    def __init__(self, instructions: str, greeting: str) -> None:
        # Puerto 8001 para el Bridge local
        self.server_url = os.getenv("BRIDGE_SERVER_URL", "http://127.0.0.1:8001")
        self.greeting = greeting
        self.current_scores = {} # Cache de seguridad
        self.is_completed = False # Flag de encuesta terminada
        
        # Metrics
        self.total_tokens = 0
        self.start_time = asyncio.get_event_loop().time()
        
        super().__init__(instructions=instructions)

    async def helper_save_survey(self, id_encuesta, nota_comercial=None, nota_instalador=None, nota_rapidez=None, comentarios=None, transcript=None, status="pending"):
        """Helper para guardar encuesta con métricas de uso"""
        
        # Actualizar cache local
        if nota_comercial: self.current_scores["nota_comercial"] = nota_comercial
        if nota_instalador: self.current_scores["nota_instalador"] = nota_instalador
        if nota_rapidez: self.current_scores["nota_rapidez"] = nota_rapidez
        if comentarios: self.current_scores["comentarios"] = comentarios
        if status == 'completed': self.is_completed = True

        seconds_used = int(asyncio.get_event_loop().time() - self.start_time)

        payload = {
            "id_encuesta": id_encuesta,
            "nota_comercial": nota_comercial,
            "nota_instalador": nota_instalador,
            "nota_rapidez": nota_rapidez,
            "comentarios": comentarios,
            "transcription": transcript,
            "status": status,
            "tokens_used": self.total_tokens,
            "seconds_used": seconds_used
        }
        
        url = f"{self.server_url}/guardar-encuesta"
        try:
             # Usar un session efímero o gestionado
             async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=aiohttp.ClientTimeout(total=10), json=payload) as resp:
                    return await resp.text()
        except Exception as e:
            print(f"❌ [Agent] Error guardando encuesta: {e}")
            return f"error: {e}"

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

        return await self.helper_save_survey(
            id_encuesta=id_encuesta,
            nota_comercial=nota_comercial,
            nota_instalador=nota_instalador,
            nota_rapidez=nota_rapidez,
            comentarios=comentarios,
            transcript=transcript,
            status=status
        )

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
    
    # Hacer la lectura de DB no bloqueante
    ai_config, agent_config = await asyncio.get_event_loop().run_in_executor(None, get_config)

    
    # Leer modelos de la configuración (ya sincronizados)
    llm_model = ai_config.get('llm_model') or 'llama-3.3-70b-versatile'
    tts_model = ai_config.get('tts_model') or 'sonic-multilingual'
    tts_voice = ai_config.get('tts_voice') or 'fb926b21-4d92-411a-85d0-9d06859e2171'
    stt_model = ai_config.get('stt_model') or 'nova-2'
    
    print(f"🛠️ [Agent] Modelos detectados en DB: LLM={llm_model}")
    
    instructions = """Tu nombre es Dakota. Le llamas de Ausarta para realizar una breve encuesta de satisfacción sobre un servicio reciente.
    
    REGLAS:
    1. Pregunta uno a uno.
    2. Al recibir UNA respuesta, llama a `guardar_encuesta` SOLO con ese dato.
    3. NO inventes ni rellenes las otras notas si el usuario no las ha dicho aún.
    4. Si el usuario dice un número suelto, asúmelo para la pregunta actual.
    5. Preguntas:
       - Comercial (0-10) -> guardar_encuesta(nota_comercial=X)
       - Instalador (0-10) -> guardar_encuesta(nota_instalador=X)
       - Rapidez (0-10) -> guardar_encuesta(nota_rapidez=X)
    6. Al final, despídete y usa `finalizar_llamada`.
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
    agent_instance.pending_client_text = "" # Buffer para lo último dicho (aunque no sea final)
    agent_instance.start_time = asyncio.get_event_loop().time() # Track start time


    # Sincronización en tiempo real (evita perder datos si cuelgan de golpe)
    async def sync_data():
        if not survey_id: return
        
        # Use the helper method for consistency
        await agent_instance.helper_save_survey(
            id_encuesta=survey_id,
            transcript=agent_instance.full_transcript,
            **agent_instance.current_scores
        )

    async def cleanup():
        print(f"🛑 [Shutdown] Iniciando limpieza para sala: {ctx.room.name}")
        # Calcular duración aproximada si hubo intercambio
        duration = 0
        if agent_instance.pending_client_text:
            print(f"✂️ [Cleanup] Rescatando texto final no procesado: '{agent_instance.pending_client_text}'")
            agent_instance.full_transcript += f"Cliente (Corte): {agent_instance.pending_client_text}\n"

        if survey_id:
            # Si el agente marcó completada explícitamente, o si tenemos AL MENOS UNA NOTA guardada
            has_data = any(v is not None for v in agent_instance.current_scores.values())
            # Si hay datos O texto pendiente rescatado, intentamos marcar como completada
            final_status = 'completed' if (agent_instance.is_completed or has_data or agent_instance.pending_client_text) else None
            
            print(f"🔍 [Cleanup] Preparando guardado. has_data={has_data}, pending={bool(agent_instance.pending_client_text)}, final_status={final_status}")
            
            # Use the helper method for consistency
            await agent_instance.helper_save_survey(
                id_encuesta=survey_id,
                transcript=agent_instance.full_transcript,
                status=final_status,
                **agent_instance.current_scores
            )
        
        print(f"👋 [Shutdown] Limpieza completada.")

    ctx.add_shutdown_callback(cleanup)

    try:
        # VAD ajustado: 0.1s para detectar rápido, 0.5s paradas cortas (más ágil)
        vad = silero.VAD.load(min_speech_duration=0.1, min_silence_duration=0.5)
        
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

        print(f"🤖 [Init] Configurando LLM...")
        
        # 1. Leer configuración dinámica
        app_settings = get_app_settings()
        
        # Priorizar lo que venga en app_settings (ModelsView)
        provider = app_settings.get("llm_provider", "groq")
        model_name = app_settings.get("llm_model", "llama-3.3-70b-versatile")
        
        # Auto-corrección de seguridad para evitar 404s cruzados
        if provider == "google":
            if "gemini" not in model_name.lower():
                 print(f"⚠️ [Correction] Se pidió Google pero el modelo era '{model_name}'. Forzando 'models/gemini-1.5-flash'.")
                 model_name = "models/gemini-1.5-flash"
            elif not model_name.startswith("models/"):
                 print(f"⚠️ [Correction] Añadiendo prefijo 'models/' a {model_name}")
                 model_name = f"models/{model_name}"
        elif provider == "groq":
            if "gemini" in model_name.lower():
                 print(f"⚠️ [Correction] Se pidió Groq pero el modelo era '{model_name}'. Forzando 'llama-3.3-70b-versatile'.")
                 model_name = "llama-3.3-70b-versatile"

        print(f"⚙️ [LLM Config] Final -> Provider: {provider} | Model: {model_name}")

        try:
            if provider == "google":
                # Google Gemini (NATIVO - Mucho más estable)
                google_key = os.getenv("GOOGLE_API_KEY")
                if not google_key:
                    raise ValueError("Falta GOOGLE_API_KEY")
                      
                llm_plugin = google.LLM(model=model_name, api_key=google_key)
            else:
                # Default: Groq (via OpenAI)
                if not groq_key:
                    raise ValueError("Falta GROQ_API_KEY")
                
                llm_plugin = openai.LLM(
                    model=model_name, 
                    base_url="https://api.groq.com/openai/v1", 
                    api_key=groq_key
                )
        except Exception as e:
            print(f"❌ [Error LLM Init] {e}")
            raise e
        session = AgentSession(
            stt=stt,
            llm=llm_plugin,
            tts=tts,
            vad=vad
        )

        @session.on("transcription_received")
        def on_transcription(transcript):
            role = "Agente" if transcript.participant == ctx.room.local_participant else "Cliente"
            
            if not transcript.is_final:
                # Guardamos lo que se está diciendo por si se corta la llamada AHORA MISMO
                if role == "Cliente":
                    agent_instance.pending_client_text = transcript.text
            else:
                # Finalizado
                msg = f"{role}: {transcript.text}"
                # print(f"🎤 {msg}") # Reducir logs para rendimiento

                
                if role == "Cliente":
                    agent_instance.interaction_count += 1
                    agent_instance.pending_client_text = "" # Limpiamos buffer
                
                agent_instance.full_transcript += f"{msg}\n"
                
                if role == "Cliente":
                    asyncio.create_task(sync_data())

        @session.on("metrics_collected")
        def on_metrics(metrics):
             # Hook para capturar métricas si el plugin las emite
             pass

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
        import re
        
        # Capturar traza completa para buscar errores anidados (causes)
        full_error = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        print(f"❌ [Error Crítico] Dakota: {e}")
        traceback.print_exc()
        
        # Detectar Rate Limits (buscando en el error y sus causas)
        if "429" in full_error or "Rate limit" in full_error or "Quota exceeded" in full_error:
            # Intentar extraer info de límite
            limit_info = ""
            match = re.search(r"Limit (\d+), Used (\d+)", full_error)
            if match:
                limit_val = int(match.group(1))
                used_val = int(match.group(2))
                percent = (used_val / limit_val) * 100
                limit_info = f" | Uso: {used_val}/{limit_val} ({percent:.1f}%)"
            
            log_system_alert("api_limit", f"⛔ API Groq/OpenAI Límite Alcanzado{limit_info}. Revise UsageView o cambie la API Key.")

if __name__ == "__main__":
    cli.run_app(server)