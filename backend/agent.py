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
        
        super().__init__(
            instructions=instructions,
        )

    async def on_enter(self):
        # Forzamos al agente a saludar primero sin usar herramientas
        await self.session.generate_reply(
            instructions=f"{self.greeting} No uses herramientas todavía.",
            allow_interruptions=False
        )

    @function_tool(name="guardar_encuesta")
    async def _http_tool_guardar_encuesta(
        self, context: RunContext, id_encuesta: int, nota_comercial: int, nota_instalador: int, nota_rapidez: int, comentarios: Optional[str] = None
    ) -> str | None:
        """Guarda los datos de la encuesta recibidos del usuario."""
        print(f"🛠️ [Tool] Ejecutando guardar_encuesta: ID={id_encuesta}, Notas=[{nota_comercial}, {nota_instalador}, {nota_rapidez}]")
        context.disallow_interruptions()
        url = f"{self.server_url}/guardar-encuesta"
        payload = {
            "id_encuesta": id_encuesta,
            "nota_comercial": nota_comercial,
            "nota_instalador": nota_instalador,
            "nota_rapidez": nota_rapidez,
            "comentarios": comentarios,
        }
        try:
            session = utils.http_context.http_session()
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=10), json=payload) as resp:
                resultado = await resp.text()
                print(f"✅ [Tool] Resultado guardar_encuesta: {resultado}")
                return resultado
        except Exception as e:
            print(f"❌ [Tool] Error en guardar_encuesta: {e}")
            raise ToolError(f"Error DB: {e}")

    @function_tool(name="finalizar_llamada")
    async def _http_tool_finalizar_llamada(
        self, context: RunContext, nombre_sala: str
    ) -> str | None:
        """Corta la llamada inmediatamente."""
        print(f"🛠️ [Tool] Ejecutando finalizar_llamada: Sala={nombre_sala}")
        context.disallow_interruptions()
        url = f"{self.server_url}/colgar"
        payload = {"nombre_sala": nombre_sala}
        try:
            session = utils.http_context.http_session()
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=10), json=payload) as resp:
                resultado = await resp.text()
                print(f"✅ [Tool] Resultado finalizar_llamada: {resultado}")
                return resultado
        except Exception as e:
            print(f"❌ [Tool] Error en finalizar_llamada: {e}")
            raise ToolError(f"Error Colgar: {e}")

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server = AgentServer(setup_fnc=prewarm)

@server.rtc_session(agent_name="Dakota-1ef9")
async def entrypoint(ctx: JobContext):
    print(f"⚡ [Agent] ¡Job recibido! Sala: {ctx.room.name}")
    
    # Cargar configuración dinámica
    ai_config, agent_config = get_config()
    
    # Defaults
    llm_model = ai_config.get('llm_model', 'llama-3.3-70b-versatile')
    tts_model = ai_config.get('tts_model', 'sonic-3')
    tts_voice = ai_config.get('tts_voice', '6511153f-72f9-4314-a204-8d8d8afd646a')
    stt_model = ai_config.get('stt_model', 'nova-3')
    
    instructions = agent_config.get('instructions', "Eres un asistente de encuestas de calidad de Ausarta.")
    greeting = agent_config.get('greeting', "Hola, soy Dakota de Ausarta.")

    print(f"🎤 [Agent] Inicializando sesión con: LLM={llm_model}, TTS={tts_model}")

    try:
        session = AgentSession(
            stt=inference.STT(model=f"deepgram/{stt_model}", language="es"),
            # Configuración Groq (LLM)
            llm=openai.LLM(
                model=llm_model,
                base_url="https://api.groq.com/openai/v1",
                api_key=os.getenv("GROQ_API_KEY")
            ),
            tts=inference.TTS(
                model=f"cartesia/{tts_model}",
                voice=tts_voice,
                language="es"
            ),
            vad=ctx.proc.userdata["vad"],
            preemptive_generation=True,
        )

        print("🚀 [Agent] Conectando a la sala...")
        await session.start(
            agent=DefaultAgent(instructions=instructions, greeting=greeting),
            room=ctx.room,
        )
        print("✅ [Agent] Conectado y listo para hablar!")

        background_audio = BackgroundAudioPlayer(
            ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.1),
        )
        await background_audio.start(room=ctx.room, agent_session=session)
        print("🎵 [Agent] Audio de fondo iniciado")
        
    except Exception as e:
        print(f"❌ [Agent] ERROR FATAL en entrypoint: {e}")
        logger.error(f"Error starting session: {e}", exc_info=True)

if __name__ == "__main__":
    cli.run_app(server)