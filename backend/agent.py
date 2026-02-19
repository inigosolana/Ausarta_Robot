import logging
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



    async def on_enter(self):
        # Pequeño delay para asegurar que el socket de Cartesia esté listo
        await asyncio.sleep(1.0)
        logger.info(f"📢 Intentando saludo inicial en sala {self.session.room.name}...")
        try:
            # Usamos .say() para una frase fija
            await self.session.say("Buenas, llamo de Ausarta para una encuesta rápida de calidad. ¿Tiene un momento?", allow_interruptions=False)
            logger.info("✅ Saludo inicial enviado a TTS.")
        except Exception as e:
            logger.error(f"❌ Error al decir saludo inicial: {e}")

    async def _save_to_supabase(self, real_id: int, update_data: dict):
        """Guarda los datos directamente en Supabase (sin pasar por el bridge server)."""
        try:
            if not supabase:
                logger.error("❌ [SAVE] No hay conexión a Supabase en el agente.")
                return
            result = supabase.table("encuestas").update(update_data).eq("id", real_id).execute()
            logger.info(f"✅ [SAVE] Encuesta ID={real_id} guardada en Supabase: {update_data}")
            # Si completed/incomplete, actualizar también campaign_leads
            status = update_data.get("status")
            if status in ("completed", "incomplete", "rejected_opt_out"):
                supabase.table("campaign_leads").update({"status": status}).eq("call_id", real_id).execute()
        except Exception as e:
            logger.error(f"❌ [SAVE] Error al guardar en Supabase ID={real_id}: {e}")

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
        asyncio.create_task(self._save_to_supabase(real_id, update_data))
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
            fnc_ctx=agent_instance, # <--- Registra las herramientas del agente
            preemptive_generation=False, 
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
            ),
        )
        
        logger.info(f"🚀 [SISTEMA]: Agente '{ctx.room.name}' ONLINE y listo.")

        background_audio = BackgroundAudioPlayer(
            ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.1),
        )
        await background_audio.start(room=ctx.room, agent_session=session)
    
    except Exception as e:
        handle_error(e)

if __name__ == "__main__":
    cli.run_app(server)