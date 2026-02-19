import logging
# Silenciar logs HTTP internos muy verbosos
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("hpack.hpack").setLevel(logging.WARNING)
logging.getLogger("hpack.table").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
from typing import Optional
import os
import aiohttp
import asyncio
import sys
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
    RunContext,
    ToolError,
    cli,
    function_tool,
    room_io,
    utils,
    stt
)
from livekit.plugins import (
    noise_cancellation,
    silero,
    openai,
    deepgram, # <--- NUEVO: Oídos directos
    cartesia,  # <--- NUEVO: Boca directa
    google
)
from supabase import create_client, Client

# --- CONFIGURACIÓN DE LOGS ---
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log", mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("agent-Dakota")
load_dotenv()

# --- CONFIGURACIÓN DE BASE DE DATOS (Supabase) ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info(f"✅ Agente conectado a Supabase para configuración dinámica")
    except Exception as e:
        logger.error(f"❌ Error conectando a Supabase desde el agente: {e}")

class DefaultAgent(Agent):
    def __init__(self, room_name: str, instructions: Optional[str] = None, llm_model_name: Optional[str] = None) -> None:
        self.server_url = os.getenv("BRIDGE_SERVER_URL", "http://127.0.0.1:8001")
        self.llm_model_name = llm_model_name
        
        try:
            # Sala format: 'encuesta_ID_TIMESTAMP'
            parts = room_name.split('_')
            if len(parts) >= 2:
                self.survey_id = parts[1]
            else:
                self.survey_id = parts[-1] 
        except:
            self.survey_id = "0"

        logger.info(f"🏠 [INIT] Agente iniciado para sala='{room_name}' | survey_id={self.survey_id} | llm={llm_model_name}")

        # Si vienen instrucciones de la DB, reemplazamos el placeholder con el ID real
        if instructions:
            final_instructions = instructions.replace("{{survey_id}}", str(self.survey_id))
        else:
            # Fallback completo con guíon obligatorio de guardar
            final_instructions = f"""Eres Dakota, operadora de voz de Ausarta. Estás hablando por teléfono con un cliente real.

DATOS TÉCNICOS (INVISIBLES PARA EL CLIENTE):
- ID DE LA ENCUESTA: {self.survey_id}

REGLAS DE ORO (¡MUY IMPORTANTE!):
1. PROHIBIDO NARRAR ACCIONES: NUNCA digas "*guardo datos*" ni menciones el "ID de encuesta". Habla SOLO como una persona normal.
2. PRONUNCIACIÓN: Di siempre "UNO" (ej: "del UNO al diez"), nunca "un".
3. PARA COLGAR: Siempre despídete diciendo "Gracias, que tenga buen día" y LUEGO usa finalizar_llamada.
4. Si el cliente dice NO al principio: Di "Entendido, disculpe. Que tenga buen día" y usa finalizar_llamada.

GUION ESTRICTO (SIGUE EL ORDEN EXACTO):
1. Confirma si tiene un momento.
2. Pregunta 1: "Del 1 al 10, ¿cómo valora la atención comercial recibida?"
3. Pregunta 2: "¿Y la profesionalidad del instalador, del 1 al 10?"
4. Pregunta 3: "¿Y la rapidez de la instalación, del 1 al 10?"
5. "¿Algún comentario o sugerencia para mejorar?" (acepta no/ninguno)
6. OBLIGATORIO ANTES DE COLGAR: Llama a la herramienta guardar_encuesta con id_encuesta={self.survey_id} y todas las notas y comentarios. NO omitas este paso.
7. Di "Muchas gracias por su tiempo. Que tenga muy buen día, adiós."
8. Usa finalizar_llamada para colgar.

IMPORTANTE: El paso 6 (guardar_encuesta) es OBLIGATORIO. Debes llamarla SIEMPRE antes de colgar."""

        super().__init__(
            instructions=final_instructions,
        )
        # Flag para detectar si el LLM ya llamó a guardar_encuesta
        self._data_saved = False



    async def on_enter(self):
        # Delay mínimo para que el pipeline de audio esté listo
        await asyncio.sleep(0.3)
        logger.info(f"📢 Intentando saludo inicial | survey_id={self.survey_id}...")
        # Pre-calentar Cartesia TTS: enviar un texto muy corto primero para inicializar
        # el WebSocket interno y evitar el error "no audio frames" en el saludo real
        try:
            await self.session.say(" ", allow_interruptions=False)
        except Exception:
            pass  # El pre-calentamiento puede fallar, es normal
        # Esperar a que Cartesia esté completamente listo
        await asyncio.sleep(0.5)
        try:
            await self.session.say("Buenas, llamo de Ausarta para una encuesta rápida de calidad. ¿Tiene un momento?", allow_interruptions=False)
            logger.info("✅ Saludo inicial enviado a TTS.")
        except Exception as e:
            logger.error(f"❌ Error al decir saludo inicial: {e}")

    async def on_exit(self):
        """Safety net: si el LLM nunca llamó a guardar_encuesta, guardamos al menos el estado."""
        if not self._data_saved:
            real_id = int(self.survey_id) if str(self.survey_id).isdigit() else 0
            if real_id > 0:
                logger.warning(f"⚠️ [SAFETY] guardar_encuesta NO fue llamada por el LLM. Guardando status=incomplete para ID={real_id}")
                fallback_data = {
                    "status": "incomplete",
                    "llm_model": self.llm_model_name or "unknown"
                }
                await self._save_to_supabase(real_id, fallback_data)
                self._data_saved = True  # ← CRÍTICO: evitar que FINAL SAVE sobreescriba con 'unreached'
            else:
                logger.warning("⚠️ [SAFETY] survey_id inválido, no se puede guardar fallback.")
        else:
            logger.info(f"✅ [EXIT] Datos ya guardados correctamente para survey_id={self.survey_id}.")

    async def _save_to_supabase(self, real_id: int, update_data: dict):
        """Guarda los datos directamente en Supabase (sin pasar por el bridge server)."""
        logger.info(f"🔌 [DB] Estado Supabase: {'conectado' if supabase else 'DESCONECTADO'}")
        if not supabase:
            logger.error("❌ [DB] No hay cliente Supabase disponible en el agente. Verifica SUPABASE_URL y SUPABASE_KEY.")
            return
        try:
            logger.info(f"📤 [DB] Ejecutando UPDATE encuestas SET {update_data} WHERE id={real_id}")
            result = supabase.table("encuestas").update(update_data).eq("id", real_id).execute()
            rows_updated = len(result.data) if result.data else 0
            if rows_updated > 0:
                logger.info(f"✅ [DB] UPDATE exitoso. Filas actualizadas: {rows_updated}. Datos: {result.data}")
            else:
                logger.warning(f"⚠️ [DB] UPDATE ejecutado pero 0 filas afectadas. ¿Existe la encuesta ID={real_id}?")
            # Si completed/incomplete, actualizar también campaign_leads
            status = update_data.get("status")
            if status in ("completed", "incomplete", "rejected_opt_out"):
                cl_result = supabase.table("campaign_leads").update({"status": status}).eq("call_id", real_id).execute()
                cl_rows = len(cl_result.data) if cl_result.data else 0
                logger.info(f"📋 [DB] campaign_leads actualizado: {cl_rows} filas con status='{status}'")
        except Exception as e:
            logger.error(f"❌ [DB] Error CRÍTICO al guardar en Supabase ID={real_id}: {type(e).__name__}: {e}")

    @function_tool(name="guardar_encuesta")
    async def _http_tool_guardar_encuesta(
        self, 
        context: RunContext, 
        id_encuesta: int, 
        nota_comercial: Optional[int] = None, 
        nota_instalador: Optional[int] = None, 
        nota_rapidez: Optional[int] = None, 
        comentarios: Optional[str] = None
    ) -> str | None:
        logger.info(f"🔧 [TOOL] guardar_encuesta LLAMADA POR EL LLM → id_encuesta={id_encuesta} | self.survey_id={self.survey_id} | real_id será={int(self.survey_id) if str(self.survey_id).isdigit() else id_encuesta}")
        logger.info(f"   notas: comercial={nota_comercial}, instalador={nota_instalador}, rapidez={nota_rapidez}, comentarios={comentarios}")
        
        # Siempre usamos el ID de la sala (más fiable que el que pasa el LLM)
        real_id = int(self.survey_id) if str(self.survey_id).isdigit() else id_encuesta

        # Si tenemos las 3 notas, la encuesta está completa
        has_all_scores = (nota_comercial is not None and 
                          nota_instalador is not None and 
                          nota_rapidez is not None)
        status = "completed" if has_all_scores else "incomplete"

        update_data = {"status": status}
        if nota_comercial is not None: update_data["puntuacion_comercial"] = nota_comercial
        if nota_instalador is not None: update_data["puntuacion_instalador"] = nota_instalador
        if nota_rapidez is not None: update_data["puntuacion_rapidez"] = nota_rapidez
        if comentarios is not None: update_data["comentarios"] = comentarios
        if self.llm_model_name: update_data["llm_model"] = self.llm_model_name
        if has_all_scores: update_data["completada"] = 1
        
        logger.info(f"💾 [TOOL] guardar_encuesta → ID={real_id} | status={status} | datos={update_data}")
        # Guardado directo en Supabase (sin bridge server)
        await self._save_to_supabase(real_id, update_data)
        self._data_saved = True  # Marcar como guardado para que on_exit no sobreescriba
        return "Dato guardado."

    @function_tool(name="finalizar_llamada")
    async def _http_tool_finalizar_llamada(
        self, context: RunContext, nombre_sala: str
    ) -> str | None:
        """
        Herramienta para colgar la llamada telefónica.
        Úsala siempre que la conversación deba terminar.
        """
        context.disallow_interruptions()
        
        logger.info("⏳ Esperando 4s para colgar (permitiendo audio despedida)...")
        await asyncio.sleep(4) 
        
        url = f"{self.server_url}/colgar"
        payload = {"nombre_sala": nombre_sala}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=5, json=payload) as resp:
                    logger.info(f"✂️ COLGANDO: {nombre_sala}")
                    return await resp.text()
        except Exception as e:
            raise ToolError(f"Error Colgar: {e}")

server = AgentServer()

@server.rtc_session(agent_name="Dakota-1ef9")
async def entrypoint(ctx: JobContext):
    
    vad_model = silero.VAD.load()
    
    def handle_error(error):
        msg = str(error)
        if "429" in msg: 
            logger.error("\n\n🚨🚨🚨 ALERTA RATE LIMIT: Se ha alcanzado el límite de tokens 🚨🚨🚨\n")
        else:
            logger.error(f"\n⚠️ ERROR DEL AGENTE: {error}\n")

    # --- CARGA DINÁMICA DE CONFIGURACIÓN ---
    llm_provider = "openai"
    llm_model = "gpt-4o-mini"
    tts_provider = "cartesia"
    tts_model = "sonic-multilingual"
    tts_voice = "6511153f-72f9-4314-a204-8d8d8afd646a" # Default
    
    # Prompt / Instrucciones
    instructions = "Eres Dakota, operadora de voz de Ausarta."
    greeting = "Buenas, llamo de Ausarta para una encuesta rápida de calidad."

    if supabase:
        try:
            # 1. Cargar LLM / TTS Config
            res_ai = supabase.table("ai_config").select("*").limit(1).execute()
            if res_ai.data:
                config = res_ai.data[0]
                llm_provider = config.get("llm_provider", "openai")
                llm_model = config.get("llm_model", "gpt-4o-mini")
                tts_provider = config.get("tts_provider", "cartesia")
                tts_model = config.get("tts_model", "sonic-multilingual")
                tts_voice = config.get("tts_voice", tts_voice)
            
            # 2. Cargar Instrucciones / Prompt
            res_agent = supabase.table("agent_config").select("*").limit(1).execute()
            if res_agent.data:
                agent = res_agent.data[0]
                instructions = agent.get("instructions", instructions)
                greeting = agent.get("greeting", greeting)

            logger.info(f"⚙️ Configuración Dinámica CARGADA de Supabase:")
            logger.info(f"   - LLM: {llm_provider} ({llm_model})")
            logger.info(f"   - TTS: {tts_provider} ({tts_model}) | Voz: {tts_voice}")
            logger.info(f"   - Prompt: {len(instructions)} caracteres")

        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar configuración dinámica, usando defaults: {e}")

    # --- SELECCIÓN DE LLM ---
    selected_llm = None
    if llm_provider == "groq":
        selected_llm = openai.LLM(
            model=llm_model, 
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.4
        )
    elif llm_provider == "google" or llm_provider == "gemini":
        selected_llm = google.LLM(
            model=llm_model if "models/" in llm_model else f"models/{llm_model}",
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.4
        )
    else: # Default: OpenAI
        selected_llm = openai.LLM(
            model=llm_model,
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.4
        )

    # --- SELECCIÓN DE TTS (BOCA) - SOLO CARTESIA ---
    selected_tts = cartesia.TTS(
        api_key=os.getenv("CARTESIA_API_KEY"),
        model=tts_model if tts_model else "sonic-multilingual",
        voice=tts_voice if tts_voice else "6511153f-72f9-4314-a204-8d8d8afd646a"
    )

    # Configurar instancia del agente con prompt de la DB
    agent_instance = DefaultAgent(
        room_name=ctx.room.name, 
        instructions=instructions,
        llm_model_name=llm_model
    )

    try:
        session = AgentSession(
            stt=deepgram.STT(model="nova-2", language="es"),
            llm=selected_llm,
            tts=selected_tts,
            vad=vad_model,
            preemptive_generation=False,
            # Las herramientas @function_tool se descubren automáticamente
            # cuando se llama a session.start(agent=agent_instance)
        )
        
        # --- MONITORIZACIÓN EN TIEMPO REAL ---
        
        @session.on("user_speech_committed")
        def on_user_speech(msg: stt.SpeechEvent):
            text = msg.alternatives[0].text
            logger.info(f"🎤 [OÍDOS - STT]: Usuario ha dicho: '{text}'")

        @session.on("agent_speech_started")
        def on_agent_speech_started():
            logger.info(f"🧠 [CEREBRO - LLM]: Respuesta generada, enviando a TTS...")

        @session.on("agent_started_speaking")
        def on_agent_started_speaking():
            logger.info(f"🗣️  [BOCA - TTS]: Hablando ahora mismo (Audio saliendo)...")
            
        @session.on("agent_speech_interrupted")
        def on_agent_interrupted():
            logger.info(f"🤫 [BOCA]: El usuario me ha interrumpido.")

        # --- INICIO DE SESIÓN ---

        await session.start(
            agent=agent_instance,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: noise_cancellation.BVCTelephony() if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP else noise_cancellation.BVC(),
                ),
                # No cerrar la sesión automáticamente al desconectarse:
                # controlamos el cierre manualmente para garantizar que on_exit se ejecuta
                close_on_disconnect=False,
            ),
        )
        
        logger.info(f"🚀 [SISTEMA]: Agente '{ctx.room.name}' ONLINE y listo.")

        background_audio = BackgroundAudioPlayer(
            ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.1),
        )
        await background_audio.start(room=ctx.room, agent_session=session)

        # --- ESPERAR DESCONEXION: usar participant_disconnected para detectar cuelgue del usuario ---
        disconnect_event = asyncio.Event()

        @ctx.room.on("participant_disconnected")
        def _on_participant_disconnected(participant):
            # Solo reaccionar al participante SIP/usuario (no al agente mismo)
            if participant.identity != ctx.room.local_participant.identity:
                logger.info(f"[SISTEMA] Participante desconectado: {participant.identity}")
                disconnect_event.set()

        @ctx.room.on("disconnected")
        def _on_room_disconnected():
            disconnect_event.set()

        logger.info("[SISTEMA] Esperando desconexion del participante...")
        await disconnect_event.wait()
        logger.info("[SISTEMA] Llamada terminada. Cerrando sesión limpiamente...")

        # Cerrar la sesión del agente manualmente (garantiza que on_exit se ejecute)
        await session.aclose()
        logger.info("[SISTEMA] Sesión cerrada. Verificando si los datos fueron guardados...")

        # --- SAFETY NET FINAL (solo si on_exit NO pudo guardar) ---
        if not agent_instance._data_saved:
            survey_id_str = str(agent_instance.survey_id)
            real_id = int(survey_id_str) if survey_id_str.isdigit() else 0
            if real_id > 0 and supabase:
                logger.warning(f"[FINAL SAVE] Ningún guardado previo detectado -> guardando 'unreached' para ID={real_id}")
                try:
                    result = supabase.table("encuestas").update({
                        "status": "unreached",
                        "llm_model": agent_instance.llm_model_name or "unknown"
                    }).eq("id", real_id).execute()
                    rows = len(result.data) if result.data else 0
                    logger.info(f"[FINAL SAVE] Guardado correctamente. Filas afectadas: {rows}")
                except Exception as db_err:
                    logger.error(f"[FINAL SAVE] Error al guardar: {db_err}")
            else:
                logger.warning(f"[FINAL SAVE] survey_id inválido o Supabase no disponible.")
        else:
            logger.info(f"[FINAL SAVE] ✅ Datos ya guardados correctamente. survey_id={agent_instance.survey_id}")

    except Exception as e:
        handle_error(e)

if __name__ == "__main__":
    cli.run_app(server)