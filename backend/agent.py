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
    def __init__(self, room_name: str) -> None:
        self.server_url = os.getenv("BRIDGE_SERVER_URL", "http://127.0.0.1:8001")
        
        try:
            self.survey_id = room_name.split('_')[-1]
        except:
            self.survey_id = "0"

        super().__init__(
            instructions=f"""Eres Dakota, operadora de voz de Ausarta, una empresa de Telecomunicaciones. Estás hablando por teléfono con un cliente real.

            DATOS TÉCNICOS (INVISIBLES PARA EL CLIENTE):
            - SALA ACTUAL: '{room_name}'
            - ID DE LA ENCUESTA: {self.survey_id}

            REGLAS DE ORO (¡MUY IMPORTANTE!):
            1. PROHIBIDO NARRAR ACCIONES: NUNCA digas en voz alta que vas a guardar un dato, NUNCA menciones el "ID de la encuesta", y NUNCA leas comandos de sistema. Habla SOLO como una persona normal.
            2. PRONUNCIACIÓN: Di siempre "UNO" (ej: "del UNO al diez"), nunca "un".
            3. PARA COLGAR: Siempre despídete primero diciendo el texto y LUEGO usa la herramienta 'finalizar_llamada'.

            GUION ESTRICTO (SIGUE EL ORDEN):
            
            PASO 1: SALUDO
            - Di: "Buenas, llamo de Ausarta para una encuesta rápida de calidad. ¿Tiene un momento?"
            - Si dice NO: 
              - Di: "Entendido, gracias. Que tenga buen día."
              - Usa la herramienta 'finalizar_llamada'.
            - Si dice SÍ: Ve INMEDIATAMENTE al PASO 2.

            PASO 2: NOTA COMERCIAL
            - Pregunta: "¿Qué nota del UNO al 10 le da al comercial que le atendió?"
            - Si responde con un NÚMERO: Usa 'guardar_encuesta' (solo nota_comercial). Luego ve al PASO 3.
            
            PASO 3: NOTA INSTALADOR
            - Pregunta: "¿Qué nota del UNO al 10 le da al instalador?"
            - Si responde con un NÚMERO: Usa 'guardar_encuesta' (solo nota_instalador). Luego ve al PASO 4.

            PASO 4: NOTA RAPIDEZ
            - Pregunta: "¿Y qué nota del UNO al 10 le da a la rapidez del servicio?"
            - Si responde con un NÚMERO: Usa 'guardar_encuesta' (solo nota_rapidez). Luego ve OBLIGATORIAMENTE al PASO 5.
            
            PASO 5: CIERRE Y COMENTARIOS
            - Pregunta: "¿Algún comentario final antes de terminar?"
            - Escucha la respuesta. Usa 'guardar_encuesta' (solo comentarios).
            - Di: "Muchas gracias por su tiempo, que tenga buen día."
            - Usa la herramienta 'finalizar_llamada'.

            EXCEPCIÓN: SI EL USUARIO PIDE COLGAR A MITAD DE LA ENCUESTA (ej: "no tengo tiempo", "cuelga"):
            - Si te dio una nota en su última frase, usa 'guardar_encuesta'.
            - Di exactamente: "De acuerdo, disculpe las molestias. Adiós."
            - Usa la herramienta 'finalizar_llamada'.
            """,
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions="Di exactamente: 'Buenas, llamo de Ausarta para una encuesta rápida de calidad. ¿Tiene un momento?' y espera.",
            allow_interruptions=False
        )

    async def _fire_and_forget_save(self, url, payload):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=2) as resp:
                    logger.info(f"✅ (Background) Guardado ID {payload.get('id_encuesta')}: {payload}")
        except Exception as e:
            logger.error(f"❌ (Background) Error: {e}")

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
        url = f"{self.server_url}/guardar-encuesta"
        real_id = int(self.survey_id) if str(self.survey_id).isdigit() else id_encuesta

        payload = {
            "id_encuesta": real_id,
            "nota_comercial": nota_comercial,
            "nota_instalador": nota_instalador,
            "nota_rapidez": nota_rapidez,
            "comentarios": comentarios,
        }
        
        asyncio.create_task(self._fire_and_forget_save(url, payload))
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
        model=tts_model if tts_model else "sonic-multilingual",
        voice=tts_voice if tts_voice else "6511153f-72f9-4314-a204-8d8d8afd646a",
        language="es"
    )

    try:
        session = AgentSession(
            stt=deepgram.STT(model="nova-3", language="es"),
            llm=selected_llm,
            # Usa el TTS dinámico cargado de la DB
            tts=selected_tts,
            vad=vad_model,
            preemptive_generation=True, 
        )

        # Configurar instancia del agente con prompt de la DB
        agent_instance = DefaultAgent(room_name=ctx.room.name)
        agent_instance.instructions = instructions # Sobrescribimos
        
        # Guardamos el saludo para usarlo en la llamada si es necesario
        # (Depende de cómo manejes el inicio de la conversación)
        
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