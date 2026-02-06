import logging
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
    noise_cancellation,
    silero,
    openai, 
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent-Dakota-1ef9")

# Carga el archivo .env de la carpeta actual
load_dotenv()

class DefaultAgent(Agent):
    def __init__(self) -> None:
        # Puerto 8001 para el Bridge local
        self.server_url = os.getenv("BRIDGE_SERVER_URL", "http://127.0.0.1:8001")
        
        super().__init__(
            instructions="""Eres un asistente de encuestas de calidad de Ausarta. Tu tono es profesional, amable y eficiente.

            TU MISIÓN:
            1. Saluda y pregunta si tienen un momento. ESPERA SIEMPRE A QUE EL USUARIO RESPONDA.
            2. Si aceptan, haz las 3 preguntas numéricas (del 1 al 10) una a una.
            3. Pide un comentario final breve.

            REGLAS CRÍTICAS DE HERRAMIENTAS:
            - NO TE INVENTES LOS DATOS. Solo usa 'guardar_encuesta' cuando el usuario te haya dado las 3 notas y el comentario.
            - NO ejecutes 'finalizar_llamada' hasta que te hayas despedido después de guardar los datos.
            - Si el usuario dice que NO quiere participar, di 'Entendido, gracias' y ejecuta 'finalizar_llamada'.
            - El ID de la encuesta búscalo en el nombre de la sala (ej: encuesta_495 -> ID 495). Si no lo ves, usa 0.""",
        )

    async def on_enter(self):
        # Forzamos al agente a saludar primero sin usar herramientas
        await self.session.generate_reply(
            instructions="Saluda cordialmente al usuario y pregunta si tiene un minuto para una encuesta rápida. No uses herramientas todavía.",
            allow_interruptions=False
        )

    @function_tool(name="guardar_encuesta")
    async def _http_tool_guardar_encuesta(
        self, context: RunContext, id_encuesta: int, nota_comercial: int, nota_instalador: int, nota_rapidez: int, comentarios: Optional[str] = None
    ) -> str | None:
        """Guarda los datos de la encuesta recibidos del usuario."""
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
                return await resp.text()
        except Exception as e:
            raise ToolError(f"Error DB: {e}")

    @function_tool(name="finalizar_llamada")
    async def _http_tool_finalizar_llamada(
        self, context: RunContext, nombre_sala: str
    ) -> str | None:
        """Corta la llamada inmediatamente."""
        context.disallow_interruptions()
        url = f"{self.server_url}/colgar"
        payload = {"nombre_sala": nombre_sala}
        try:
            session = utils.http_context.http_session()
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=10), json=payload) as resp:
                return await resp.text()
        except Exception as e:
            raise ToolError(f"Error Colgar: {e}")

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server = AgentServer(setup_fnc=prewarm)

@server.rtc_session(agent_name="Dakota-1ef9")
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="es"),
        # Configuración Groq
        llm=openai.LLM(
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        ),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="6511153f-72f9-4314-a204-8d8d8afd646a",
            language="es"
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    await session.start(
        agent=DefaultAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony() if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP else noise_cancellation.BVC(),
            ),
        ),
    )

    background_audio = BackgroundAudioPlayer(
        ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.1),
    )
    await background_audio.start(room=ctx.room, agent_session=session)

if __name__ == "__main__":
    cli.run_app(server)