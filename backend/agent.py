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
        
        super().__init__(
            instructions=instructions,
        )
    @function_tool(name="guardar_encuesta")
    async def _http_tool_guardar_encuesta(
        self, 
        context: RunContext, 
        id_encuesta: int, 
        nota_comercial: Optional[str | int] = None, 
        nota_instalador: Optional[str | int] = None, 
        nota_rapidez: Optional[str | int] = None, 
        comentarios: Optional[str] = None
    ) -> str | None:
        """
        Guarda los datos de la encuesta. LLAMAR SIEMPRE que se obtenga una nota o comentario.
        """
        print(f"🛠️ [Tool] Ejecutando guardar_encuesta: ID={id_encuesta}")
        context.disallow_interruptions()
        url = f"{self.server_url}/guardar-encuesta"
        
        # Enviar también la transcripción acumulada hasta ahora
        transcript = ""
        if hasattr(self, 'full_transcript'):
            transcript = self.full_transcript

        payload = {
            "id_encuesta": id_encuesta,
            "nota_comercial": nota_comercial,
            "nota_instalador": nota_instalador,
            "nota_rapidez": nota_rapidez,
            "comentarios": comentarios,
            "transcription": transcript
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
    proc.userdata["vad"] = silero.VAD.load(min_speech_duration=0.2, min_silence_duration=0.5)

server = AgentServer(setup_fnc=prewarm)

@server.rtc_session(agent_name="Dakota-1ef9")
async def entrypoint(ctx: JobContext):
    ai_config, agent_config = get_config()
    
    # Defaults ultra-estables (Hardcoded para evitar fallos de BD)
    llm_model = ai_config.get('llm_model') or 'llama-3.3-70b-versatile'
    tts_model = ai_config.get('tts_model') or 'sonic-multilingual'
    tts_voice = ai_config.get('tts_voice') or '6511153f-72f9-4314-a204-8d8d8afd646a'
    stt_model = ai_config.get('stt_model') or 'nova-2'
    
    instructions = """Tu nombre es Dakota. Le llamas de Ausarta para realizar una breve encuesta de satisfacción sobre un servicio reciente.
    
    MISION:
    1. Saluda cordialmente y pregunta si dispone de un minuto.
    2. Si acepta, haz estas 3 preguntas UNA A UNA:
       - Califique del 1 al 10 el trato comercial recibido.
       - Califique del 1 al 10 al técnico instalador.
       - Califique del 1 al 10 la rapidez del servicio.
    3. Al finalizar las 3 notas, pregunta si desea dejar algún comentario adicional.
    4. Usa la herramienta 'guardar_encuesta' tras cada respuesta para registrar los datos.
    
    REGLAS DE ORO:
    - NUNCA menciones IDs técnicos, números de encuesta ni nombres de bases de datos.
    - Si el cliente cuelga pronto o dice que no puede hablar, no insistas. Simplemente guarda lo que tengas.
    - Cuando digas el número 1, di SIEMPRE "uno".
    - Sé directo, educado y muy breve. Una encuesta de menos de 1 minuto.
    - Una vez recogido el comentario (o si dice que no tiene ninguno), di: "Muchas gracias por su tiempo. Que tenga un buen día. Adiós." y usa 'finalizar_llamada' inmediatamente.
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

    try:
        session = AgentSession(
            stt=inference.STT(model=f"deepgram/{stt_model}", language="es"),
            llm=openai.LLM(model=llm_model, base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY")),
            tts=inference.TTS(model=f"cartesia/{tts_model}", voice=tts_voice, language="es"),
            vad=ctx.proc.userdata["vad"],
            preemptive_generation=True,
        )

        agent_instance = DefaultAgent(instructions=instructions, greeting=greeting)
        agent_instance.full_transcript = ""
        agent_instance.interaction_count = 0

        # Capturar transcripción en tiempo real
        @session.on("transcription_received")
        def on_transcription(transcript: inference.Transcription):
            if transcript.is_final:
                role = "Agente" if transcript.participant == ctx.room.local_participant else "Cliente"
                if role == "Cliente":
                    agent_instance.interaction_count += 1
                msg = f"{role}: {transcript.text}\n"
                agent_instance.full_transcript += msg
                print(f"📝 {msg.strip()}")

        print(f"🚀 [Agent] Conectando sala {ctx.room.name}...")
        await session.start(agent=agent_instance, room=ctx.room)
        
        # Saludo inicial explícito
        await session.generate_reply(
            instructions=f"Eres Dakota. Acabas de entrar en la llamada y DEBES saludar exactamente así: '{greeting}'. No uses herramientas todavía.",
            allow_interruptions=True
        )

        # Al terminar la sesión (porque cuelguen), intentar guardar la transcripción final
        async def cleanup():
            if survey_id:
                # Si el cliente nunca dijo nada, marcamos como fallida (IVR, buzón, colgó rápido)
                final_status = 'completed' if agent_instance.interaction_count > 0 else 'failed'
                print(f"💾 Guardando final - ID {survey_id} | Status: {final_status}")
                
                url = f"http://127.0.0.1:8001/guardar-encuesta"
                payload = {
                    "id_encuesta": survey_id, 
                    "transcription": agent_instance.full_transcript,
                    "status": final_status
                }
                try:
                    async with aiohttp.ClientSession() as s:
                        await s.post(url, json=payload, timeout=5)
                except Exception as e:
                    print(f"⚠️ Error cleanup save: {e}")

        ctx.add_shutdown_callback(cleanup)

        # Restaurar audio de ambiente oficial
        background_audio = BackgroundAudioPlayer(
            ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.05),
        )
        await background_audio.start(room=ctx.room, agent_session=session)
        print("✅ [Agent] Sesión iniciada y saludo enviado.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    cli.run_app(server)