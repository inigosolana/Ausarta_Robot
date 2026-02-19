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
    deepgram, 
    cartesia  
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
            # Esperamos formatos: "encuesta_{ID}" O "encuesta_{ID}_{TIMESTAMP}"
            # Ejemplo: encuesta_26 OR encuesta_26_1771497318
            parts = room_name.split('_')
            if len(parts) >= 2 and parts[0] == "encuesta":
                self.survey_id = parts[1]
            else:
                self.survey_id = parts[-1] # Fallback para formatos antiguos
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
            4. SI EL CLIENTE NO TE ENTIENDE O DICE "¿CÓMO?", "¿QUÉ?": Repite la última pregunta que hiciste de forma amable y clara.
            5. SI ESCUCHAS RUIDO O UNA PALABRA SIN SENTIDO: Di "Disculpe, no le he escuchado bien, ¿me lo puede repetir?"
            6. VALIDACIÓN DE NOTAS: Si el usuario te da un número menor a 1 o mayor a 10 (ej: 0, 11), NO guardes el dato. Di "Disculpe, la nota debe ser entre 1 y 10. ¿Qué nota le daría?" y espera su respuesta.                                        
            
            

            GUION ESTRICTO (SIGUE EL ORDEN):
            
            PASO 1: SALUDO
            - Di: "Buenas, llamo de Ausarta para una encuesta rápida de calidad. ¿Tiene un momento?"
            - Si dice NO o NO PUEDO o NO ME INTERESA: 
              - Usa 'guardar_encuesta' (status='rejected').
              - Usa 'finalizar_llamada' (mensaje_despedida="Entendido, disculpe las molestias. Gracias y adiós.").
            - Si dice SÍ: Ve INMEDIATAMENTE al PASO 2.

            PASO 2: NOTA COMERCIAL
            - Pregunta: "¿Qué nota del UNO al 10 le da al comercial?"
            - Si responde NÚMERO: 'guardar_encuesta' -> PASO 3.
            
            PASO 3: NOTA INSTALADOR
            - Pregunta: "¿Qué nota del UNO al 10 le da al instalador?"
            - Si responde NÚMERO: 'guardar_encuesta' -> PASO 4.

            PASO 4: NOTA RAPIDEZ
            - Pregunta: "¿Y qué nota del UNO al 10 le da a la rapidez?"
            - Si responde NÚMERO: 'guardar_encuesta' -> PASO 5.
            
            PASO 5: CIERRE Y COMENTARIOS
            - Pregunta: "¿Algún comentario final?"
            - Si dice "NO", "NINGUNO":
              - Usa 'guardar_encuesta' (comentarios="Sin comentarios", status='completed').
              - Usa 'finalizar_llamada' (mensaje_despedida="Perfecto. Gracias por su tiempo y adiós.").
            - Si dice COMENTARIO:
              - Usa 'guardar_encuesta' (comentarios=COMENTARIO, status='completed').
              - Usa 'finalizar_llamada' (mensaje_despedida="Tomo nota. Gracias por su tiempo y adiós.").

            EXCEPCIÓN - BUZÓN DE VOZ / FUERA DE COBERTURA:
            - Si escuchas "fuera de cobertura", "móvil apagado", "buzón de voz", "contestador", "terminado el tiempo de grabación" o mensajes automáticos similares:
              - Usa 'guardar_encuesta' (status='failed').
              - Usa 'finalizar_llamada' (mensaje_despedida="").

            EXCEPCIÓN INTERRUPCIÓN/COLGAR:
            - Usa 'guardar_encuesta' (status='incomplete').
            - Usa 'finalizar_llamada' (mensaje_despedida="De acuerdo. Gracias, adiós.").
            """,
        )

    async def on_enter(self):
        # Pausa de cortesía: 1.5 segundos para que la red telefónica se estabilice antes de hablar
        await asyncio.sleep(1.5)
        
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

        if status == 'completed' and not comentarios:
            comentarios = "Sin comentarios"

        payload = {
            "id_encuesta": real_id,
            "nota_comercial": nota_comercial,
            "nota_instalador": nota_instalador,
            "nota_rapidez": nota_rapidez,
            "comentarios": comentarios,
            "status": status
        }
        
        asyncio.create_task(self._fire_and_forget_save(url, payload))
        return "Dato guardado."

    @function_tool(name="finalizar_llamada")
    async def _http_tool_finalizar_llamada(
        self, context: RunContext, nombre_sala: str, mensaje_despedida: Optional[str] = None
    ) -> str | None:
        """
        Herramienta para colgar la llamada telefónica.
        Úsala siempre que la conversación deba terminar.
        Args:
            mensaje_despedida: Texto exacto que el agente debe decir antes de colgar (ej: "Gracias y adiós").
        """
        context.disallow_interruptions()
        
        if mensaje_despedida:
            logger.info(f"🗣️ Generando despedida forzada: {mensaje_despedida}")
            # Lanzamos la generación de audio en background pero el sleep asegura que se escuche
            asyncio.create_task(self.session.generate_reply(
                instructions=f"Di exactamente con tono natural y amable: '{mensaje_despedida}'",
                allow_interruptions=False
            ))
        
        # Pausa para permitir que la frase se escuche
        logger.info("⏳ Esperando 4.0s para colgar...")
        await asyncio.sleep(4.0) 
        
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
    
    # --- MEJORA VAD ---
    # min_silence_duration=0.5 hace que el bot entienda que has terminado de hablar 
    # más rápido, evitando quedarse "sordo" escuchando el ruido de fondo de la llamada.
    vad_model = silero.VAD.load(min_silence_duration=0.5)
    
    def handle_error(error):
        msg = str(error)
        if "429" in msg: 
            logger.error("\n\n🚨🚨🚨 ALERTA GROQ: Límite Alcanzado 🚨🚨🚨\n")
        else:
            logger.error(f"\n⚠️ ERROR DEL AGENTE: {error}\n")

    try:
        session = AgentSession(
            stt=deepgram.STT(model="nova-3", language="es"),
            llm=openai.LLM(
                model="llama-3.3-70b-versatile", 
                base_url="https://api.groq.com/openai/v1",
                api_key=os.getenv("GROQ_API_KEY"),
                temperature=0.1
            ),
            tts=cartesia.TTS(
                model="sonic-multilingual",
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