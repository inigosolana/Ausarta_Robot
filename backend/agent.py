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
    inference,
    room_io,
    utils,
    stt
)
from livekit.plugins import (
    noise_cancellation,
    silero,
    openai, 
)

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

class DefaultAgent(Agent):
    def __init__(self, room_name: str) -> None:
        self.server_url = os.getenv("BRIDGE_SERVER_URL", "http://127.0.0.1:8001")
        
        try:
            self.survey_id = room_name.split('_')[-1]
        except:
            self.survey_id = "0"

        super().__init__(
            instructions=f"""Eres Dakota, operadora de encuestas de Ausarta.
            
            DATOS TÉCNICOS:
            - SALA ACTUAL: '{room_name}'
            - ID DE LA ENCUESTA: {self.survey_id}

            REGLAS DE HABLA:
            - PRONUNCIACIÓN: Di siempre "UNO" (ej: "del UNO al diez"), nunca "un".
            - REGLA DE ORO PARA COLGAR: NUNCA ejecutes 'finalizar_llamada' sin haber dicho una frase de despedida ANTES.

            GUION ESTRICTO (SIGUE EL ORDEN):
            
            PASO 1: SALUDO
            - Di: "Buenas, llamo de Ausarta para una encuesta rápida de calidad. ¿Tiene un momento?"
            - Si dice NO: 
              1. Di: "Entendido, gracias. Que tenga buen día." 
              2. ESPERA A TERMINAR DE HABLAR.
              3. EJECUTA 'guardar_encuesta' con status='rejected_opt_out'.
              4. EJECUTA 'finalizar_llamada'.
            - Si dice SÍ: Ve INMEDIATAMENTE al PASO 2.

            PASO 2: NOTA COMERCIAL
            - Pregunta: "¿Qué nota del UNO al 10 le da al comercial que le atendió?"
            - Si responde NÚMERO: EJECUTA 'guardar_encuesta' (nota_comercial=X, status='incomplete'). LUEGO ve al PASO 3.
            
            PASO 3: NOTA INSTALADOR
            - Pregunta: "¿Qué nota del UNO al 10 le da al instalador?"
            - Si responde NÚMERO: EJECUTA 'guardar_encuesta' (nota_instalador=X, status='incomplete'). LUEGO ve al PASO 4.

            PASO 4: NOTA RAPIDEZ
            - Pregunta: "¿Y qué nota del UNO al 10 le da a la rapidez del servicio?"
            - Si responde NÚMERO: EJECUTA 'guardar_encuesta' (nota_rapidez=X, status='incomplete'). LUEGO ve OBLIGATORIAMENTE al PASO 5.
            
            PASO 5: CIERRE Y COMENTARIOS
            - Pregunta: "¿Algún comentario final antes de terminar?"
            - Escucha.
            - EJECUTA 'guardar_encuesta' (comentarios=X, status='completed').
            - Di: "Muchas gracias por su tiempo, que tenga buen día."
            - EJECUTA 'finalizar_llamada'.

            SI EL USUARIO PIDE COLGAR A MITAD:
            1. GUARDA lo que tengas con status='incomplete'.
            2. Di: "Entendido, gracias. Adiós."
            3. EJECUTA 'finalizar_llamada'.
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
        comentarios: Optional[str] = None,
        status: Optional[str] = None
    ) -> str | None:
        url = f"{self.server_url}/guardar-encuesta"
        real_id = int(self.survey_id) if str(self.survey_id).isdigit() else id_encuesta

        payload = {
            "id_encuesta": real_id,
            "nota_comercial": nota_comercial,
            "nota_instalador": nota_instalador,
            "nota_rapidez": nota_rapidez,
            "comentarios": comentarios,
            "status": status
        }
        
        asyncio.create_task(self._fire_and_forget_save(url, payload))
        return f"Dato guardado con estado {status}."

    @function_tool(name="finalizar_llamada")
    async def _http_tool_finalizar_llamada(
        self, context: RunContext, nombre_sala: str
    ) -> str | None:
        """
        Corta la llamada telefónica.
        IMPORTANTE: Antes de ejecutar esta herramienta, DEBES haberte despedido verbalmente del usuario (ej: 'Adiós').
        """
        # ^^^^ ESTE TEXTO DE ARRIBA (DOCSTRING) ES LEÍDO POR LA IA. ES CLAVE. ^^^^
        
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
            logger.error("\n\n🚨🚨🚨 ALERTA GROQ: Límite Alcanzado 🚨🚨🚨\n")
        else:
            logger.error(f"\n⚠️ ERROR DEL AGENTE: {error}\n")

    try:
        session = AgentSession(
            stt=inference.STT(model="deepgram/nova-3", language="es"),
            llm=openai.LLM(
                model="llama-3.3-70b-versatile", 
                base_url="https://api.groq.com/openai/v1",
                api_key=os.getenv("GROQ_API_KEY"),
                temperature=0.1
            ),
            tts=inference.TTS(
                model="cartesia/sonic-3",
                voice="6511153f-72f9-4314-a204-8d8d8afd646a",
                language="es"
            ),
            vad=vad_model,
            preemptive_generation=True, 
        )

        @session.on("user_speech_committed")
        def on_user_speech(msg: stt.SpeechEvent):
            print(f"\n🗣️  USUARIO DICE: {msg.alternatives[0].text}\n")
            logger.info(f"TRANSCRIPCIÓN: {msg.alternatives[0].text}")

        await session.start(
            agent=DefaultAgent(room_name=ctx.room.name),
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
    
    except Exception as e:
        handle_error(e)

if __name__ == "__main__":
    cli.run_app(server)