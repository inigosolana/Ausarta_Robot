import logging
import sqlite3
from typing import Optional
import os
import aiohttp
import asyncio
import traceback
import re
from dotenv import load_dotenv
from livekit import rtc, api
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
    llm,
)
import livekit.agents
import livekit.plugins
print(f"📦 [Versions] livekit-agents: {livekit.agents.__version__} | livekit: {rtc.__version__}")

async def discover_best_llm(google_key, groq_key, preferred_provider="google", preferred_model=None, openai_key=None):
    """Consulta en vivo qué modelos están disponibles y elige el orden de prioridad"""
    candidates = []
    
    # 1. Consultar Google (si hay clave)
    if google_key:
        try:
            # Intentar listar para ver si hay 429 inmediato
            async with aiohttp.ClientSession() as session:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={google_key}"
                async with session.get(url, timeout=3) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for m in data.get('models', []):
                            name = m.get('name', '')
                            # Solo modelos flash que sirven para chat
                            if 'flash' in name.lower() and 'generateContent' in m.get('supportedGenerationMethods', []):
                                # Evitar modelos experimentales (como 2.5-flash) si no son el preferido
                                is_preferred = preferred_model and preferred_model in name
                                if "2.5" in name and not is_preferred:
                                    priority = 100 # Muy baja prioridad
                                else:
                                    # Base Google: 30
                                    priority = 1 if is_preferred else 30
                                candidates.append((f"Google {name}", google.LLM(model=name, api_key=google_key), priority))
                    elif resp.status == 429:
                        print("⚠️ [Discovery] Google está en Rate Limit (429). Prioridad bajada.")
        except Exception as e:
            print(f"⚠️ [Discovery] Error consultando Google: {e}")

    # 2. Añadir Groq (si hay clave)
    if groq_key:
        is_groq_pref = preferred_provider == "groq"
        # Base Groq: 20
        groq_prio = 1 if is_groq_pref else 20
        candidates.append(("Groq Llama 3.3", openai.LLM(
            model="llama-3.3-70b-versatile", 
            base_url="https://api.groq.com/openai/v1", 
            api_key=groq_key
        ), groq_prio))
        candidates.append(("Groq Mixtral", openai.LLM(
            model="mixtral-8x7b-32768", 
            base_url="https://api.groq.com/openai/v1", 
            api_key=groq_key
        ), groq_prio + 1))

    # 3. Consultar OpenAI (si hay clave)
    if openai_key:
        try:
            is_openai_pref = preferred_provider == "openai"
            # Base OpenAI: 10
            openai_prio = 1 if is_openai_pref else 10
            
            headers = {"Authorization": f"Bearer {openai_key}"}
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.openai.com/v1/models", headers=headers, timeout=3) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        allowed_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
                        excluded_keywords = ["tts", "audio", "realtime", "transcribe", "search", "preview-202"]
                        found_models = []
                        for m in data.get('data', []):
                            m_id = m.get('id', '')
                            # Debe contener un modelo permitido y NO contener palabras prohibidas
                            if any(am in m_id for am in allowed_models):
                                if not any(ex in m_id.lower() for ex in excluded_keywords):
                                    is_preferred = preferred_model and preferred_model in m_id
                                    priority = 1 if (is_preferred or is_openai_pref) else 10
                                    candidates.append((f"OpenAI {m_id}", openai.LLM(model=m_id, api_key=openai_key), priority))
                                    found_models.append(m_id)
                        if found_models:
                            print(f"✅ [Discovery] OpenAI modelos encontrados: {found_models}")
                    else:
                        print(f"⚠️ [Discovery] OpenAI respondió con status {resp.status}")
        except Exception as e:
            print(f"⚠️ [Discovery] Error consultando OpenAI: {e}")

    # 4. DeepSeek (si hay clave)
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        try:
            is_deepseek_pref = preferred_provider == "deepseek"
            # Base DeepSeek: 15
            deepseek_prio = 1 if is_deepseek_pref else 15
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization": f"Bearer {deepseek_key}"},
                    json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                    timeout=3
                ) as resp:
                    if resp.status == 200 or resp.status == 429:
                        candidates.append(("DeepSeek Chat", openai.LLM(
                            model="deepseek-chat",
                            base_url="https://api.deepseek.com",
                            api_key=deepseek_key
                        ), deepseek_prio))
                        candidates.append(("DeepSeek Reasoner", openai.LLM(
                            model="deepseek-reasoner",
                            base_url="https://api.deepseek.com",
                            api_key=deepseek_key
                        ), deepseek_prio + 5))
                    else:
                        print(f"⚠️ [Discovery] DeepSeek respondió con status {resp.status}")
        except Exception as e:
            print(f"⚠️ [Discovery] Error consultando DeepSeek: {e}")

    # 5. Ordenar por prioridad calculada
    candidates.sort(key=lambda x: x[2])
    
    # Si el usuario quiere un proveedor específico, nos aseguramos de que lidere
    if preferred_provider == "groq":
        candidates.sort(key=lambda x: 0 if "Groq" in x[0] else x[2])
    elif preferred_provider == "openai":
        candidates.sort(key=lambda x: 0 if "OpenAI" in x[0] else x[2])
    elif preferred_provider == "google":
        candidates.sort(key=lambda x: 0 if "Google" in x[0] else x[2])
    elif preferred_provider == "deepseek":
        candidates.sort(key=lambda x: 0 if "DeepSeek" in x[0] else x[2])
    
    return [(c[0], c[1]) for c in candidates]

class RedundantLLMStream(llm.LLMStream):
    # Remove strict type hints for livekit classes that might have changed names/locations
    def __init__(self, candidates: list, llm_instance: llm.LLM, chat_ctx, fnc_ctx=None, parent_agent=None, **kwargs):
        # DEBUG: Log exact arguments to catch signature changes
        print(f"🛠️ [Stream Debug] Init RedundantLLMStream")
        print(f"   - Candidates count: {len(candidates)}")
        print(f"   - Extra kwargs keys: {list(kwargs.keys())}")
        
        # LLMStream.__init__ signature has come to include various keyword arguments like 'tools' and 'conn_options'
        # We pass appropriate defaults and allow kwargs to pass through any others
        conn_options = kwargs.pop('conn_options', None)
        tools = kwargs.pop('tools', None)
        
        # The base LLMStream.__init__ only takes specific arguments. 
        # Previous error: unexpected keyword argument 'fnc_ctx'
        # But it requires 'tools' and 'conn_options'.
        # We process fnc_ctx to ensure tools are passed if needed, but don't pass fnc_ctx itself to super.
        
        try:
            super().__init__(
                llm=llm_instance, 
                chat_ctx=chat_ctx, 
                conn_options=conn_options,
                tools=tools
            )
            print("   ✅ Base LLMStream init success")
        except TypeError as te:
            print(f"❌ [Stream Debug] FAILED to init Base LLMStream: {te}")
            # Si falla el init por argumentos, imprimimos TODO lo que tenemos para depurar
            import inspect
            try:
                sig = inspect.signature(llm.LLMStream.__init__)
                print(f"🔍 [Info] Firma esperada del constructor: {sig}")
            except: pass
            raise te
        
        self._candidates = candidates # Lista de (nombre, factory_fn)
        self._current_idx = 0
        self._current_stream = None
        self._parent_agent = parent_agent
        if self._parent_agent and self._candidates:
            self._parent_agent.active_llm_model = self._candidates[0][0]

    async def _run(self):
        """Implements the logic to iterate through candidates with fallback"""
        # Note: In recent LiveKit versions, _run must be a coroutine, not a generator.
        last_exception = None
        
        while self._current_idx < len(self._candidates):
            name, fn = self._candidates[self._current_idx]
            
            if self._parent_agent:
                self._parent_agent.active_llm_model = name
                
            try:
                print(f"📡 [Redundancy] Intentando con: {name}")
                stream = fn()
                
                async for chunk in stream:
                    if hasattr(self, '_event_ch'):
                        self._event_ch.send_nowait(chunk)
                
                print(f"✅ [Redundancy] Éxito con {name}")
                return

            except Exception as e:
                error_msg = str(e).lower()
                print(f"⚠️ [Redundancy] Fallo en {name}: {e}")
                last_exception = e
                
                # Si es un error de cuota (429), saltamos TODOS los demás modelos de este proveedor
                # porque lo más seguro es que compartan la misma API Key y cuota.
                is_rate_limit = "429" in error_msg or "quota" in error_msg or "resource_exhausted" in error_msg
                
                if is_rate_limit:
                    provider = name.split(' ')[0] if ' ' in name else name
                    print(f"🚀 [Redundancy] Cuota agotada para {provider}. Saltando candidatos similares...")
                    
                    # Registrar alerta en la BD para que el usuario la vea en el panel
                    try:
                        detailed_error = str(e)
                        log_system_alert("api_limit", f"Fallo 429 en {name}: {detailed_error[:150]}")
                    except:
                        pass
                    
                    # Avanzamos el índice hasta encontrar un proveedor distinto
                    self._current_idx += 1
                    while self._current_idx < len(self._candidates):
                        next_name, _ = self._candidates[self._current_idx]
                        if not next_name.startswith(provider):
                            break
                        print(f"⏭️ [Redundancy] Saltando {next_name} por fallo de cuota en {provider}")
                        self._current_idx += 1
                else:
                    self._current_idx += 1
                
        if last_exception:
            print(f"🚨 [Redundancy] Todos los candidatos fallaron. Último error: {last_exception}")
            raise last_exception
        else:
            raise Exception("No candidates available")

class RedundantLLM(llm.LLM):
    """Encadena múltiples candidatos (Google 2.0 -> Google 1.5 -> Groq Llama -> Groq Mixtral)"""
    def __init__(self, candidates: list, parent_agent=None):
        super().__init__()
        self._candidates = candidates
        self._parent_agent = parent_agent

    def chat(self, chat_ctx, fnc_ctx=None, **kwargs):
        print(f"🛠️ [LLM Debug] Chat started. Keys in kwargs: {list(kwargs.keys())}")
        
        # Extraction of tools for candidates
        # Many plugins expect 'tools' instead of 'fnc_ctx' in their chat() method
        tools = kwargs.pop('tools', None)
        if tools is None and fnc_ctx:
            # Try to extract tools from fnc_ctx
            if hasattr(fnc_ctx, 'ai_callable'): # Newer version
                tools = [v for k, v in fnc_ctx.ai_callable.items()]
            elif hasattr(fnc_ctx, 'tools'): # Older or different version
                tools = fnc_ctx.tools

        # Creamos factories para que cada reintento sea una petición fresca
        # We must pass arguments recognized by the underlying plugins
        chat_kwargs = {"chat_ctx": chat_ctx, "tools": tools}
        chat_kwargs.update(kwargs)

        factories = []
        for name, plugin in self._candidates:
            if plugin:
                # Create a closure that captures the plugin properly
                # Wrap in a helper to avoid late binding issues if needed (though p=plugin handles it)
                factories.append((name, lambda p=plugin, args=dict(chat_kwargs): p.chat(**args)))
                
        # We must pass 'self' (the LLM instance) to the stream
        return RedundantLLMStream(
            factories, 
            llm_instance=self, 
            chat_ctx=chat_ctx, 
            fnc_ctx=fnc_ctx,
            parent_agent=self._parent_agent,
            **kwargs
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
        self.active_llm_model = "Desconocido"
        
        # Metrics
        self.total_tokens = 0
        self.start_time = asyncio.get_event_loop().time()
        
        self.last_status = None
        
        super().__init__(instructions=instructions)

    async def helper_save_survey(self, id_encuesta, nota_comercial=None, nota_instalador=None, nota_rapidez=None, comentarios=None, transcript=None, status=None):
        """Helper para guardar encuesta con métricas de uso"""
        
        # Actualizar cache local
        # Actualizar cache local
        if nota_comercial is not None: self.current_scores["nota_comercial"] = nota_comercial
        if nota_instalador is not None: self.current_scores["nota_instalador"] = nota_instalador
        if nota_rapidez is not None: self.current_scores["nota_rapidez"] = nota_rapidez
        if comentarios is not None: self.current_scores["comentarios"] = comentarios
        if status: self.last_status = status
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
            "seconds_used": seconds_used,
            "llm_model": self.active_llm_model
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
        Guarda los datos de la encuesta obtenidos hasta el momento.
        LLAMAR INMEDIATAMENTE tras recibir cada respuesta (nota o comentario).
        - status='rejected_opt_out': Si el cliente rechaza participar explícitamente.
        - status='completed': Si el cliente termina la encuesta o dice que no quiere dejar comentarios finales.
        """
        print(f"🛠️ [Tool] Ejecutando guardar_encuesta: ID={id_encuesta}, status={status}")
        context.disallow_interruptions()
        url = f"{self.server_url}/guardar-encuesta"
        
        # Enviar también la transcripción acumulada hasta ahora
        transcript = ""
        if hasattr(self, 'full_transcript'):
            transcript = self.full_transcript

        # Si es un rechazo, marcarlo internamente
        if status == 'rejected_opt_out':
            self.last_status = 'rejected_opt_out'
            print(f"❌ [Tool] Marcando encuesta como rechazada (opt-out)")
        
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
        self, context: RunContext, status: Optional[str] = None
    ) -> str | None:
        """
        Corta la llamada inmediatamente. Usar tras despedirse.
        - status: 'completed' (si terminó bien) o 'rejected_opt_out' (si rechazó al inicio).
        """
        # Auto-detectar sala del contexto
        nombre_sala = None
        try:
            # Acceder al room name desde el agente session
            if hasattr(context, 'session') and hasattr(context.session, '_room'):
                nombre_sala = context.session._room.name
            elif hasattr(self, '_room_name'):
                nombre_sala = self._room_name
        except:
            pass
        
        # Fallback: buscar en la BD la última encuesta
        if not nombre_sala:
            try:
                conn_tmp = sqlite3.connect(DB_PATH)
                cur_tmp = conn_tmp.cursor()
                cur_tmp.execute("SELECT id FROM encuestas ORDER BY id DESC LIMIT 1")
                res_tmp = cur_tmp.fetchone()
                if res_tmp:
                    nombre_sala = f"encuesta_{res_tmp[0]}"
                conn_tmp.close()
            except:
                pass
        
        if not nombre_sala:
            print("⚠️ [Tool] No se pudo detectar nombre de sala para colgar")
            return "error: no room name"
        
        print(f"🛠️ [Tool] Finalizando llamada en sala: {nombre_sala}")
        
        # Marcar como completada para que el cleanup lo detecte
        self.is_completed = True
        print(f"✅ [Tool] Encuesta marcada como completada")
        
        context.disallow_interruptions()
        
        # Guardar una última vez antes de colgar
        try:
            import re
            match = re.search(r'encuesta_(\d+)', nombre_sala)
            if match:
                survey_id = int(match.group(1))
                # Use the passed status, defaulting to self.last_status or 'completed' if nothing else
                final_status = status or self.last_status or 'completed'
                await self.helper_save_survey(
                    id_encuesta=survey_id,
                    transcript=self.full_transcript,
                    status=final_status,
                    **self.current_scores
                )
                print(f"💾 [Tool] Guardado final antes de colgar (ID: {survey_id})")
        except Exception as e:
            print(f"⚠️ [Tool] Error al guardar antes de colgar: {e}")

        url = f"{self.server_url}/colgar"
        payload = {"nombre_sala": nombre_sala}
        try:
            # ESPERA CRÍTICA:
            # Damos 4 segundos para que el TTS (que va por otro stream) termine de decir "Adiós..."
            # Si cortamos aquí mismo, el usuario oye "Adió-" y se corta.
            print("⏳ [Tool] Esperando 4s para que termine el audio de despedida...")
            await asyncio.sleep(4)

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
    
    5. PREGUNTAS OBLIGATORIAS (en orden):
       a) "Del 0 al 10, ¿cómo calificaría al comercial?" → guardar_encuesta(nota_comercial=X)
       b) "Del 0 al 10, ¿cómo calificaría al instalador?" → guardar_encuesta(nota_instalador=X)
       c) "Del 0 al 10, ¿cómo calificaría la rapidez?" → guardar_encuesta(nota_rapidez=X)
    
    6. RECHAZO INICIAL (CUANDO EMPIEZAS LA LLAMADA):
       - Si al preguntarle si tiene un minuto dice NO, o que no le interesa:
       - PRIMERO Di: "Entendido, disculpe las molestias. Muchas gracias y adiós."
       - LUEGO llama a `guardar_encuesta(status='rejected_opt_out')`
       - POR ÚLTIMO llama a `finalizar_llamada(status='rejected_opt_out')`
       - IMPORTANTE: Di la frase de despedida ANTES de llamar a las herramientas.
    
    7. FINALIZACIÓN (CUANDO YA TIENES LAS 3 NOTAS):
       - Pregunta SIEMPRE: "¿Desea dejar algún comentario adicional?"
       
       CASO A: EL USUARIO QUIERE DEJAR UN COMENTARIO:
       1. Escucha atentamente su respuesta.
       2. RESPONDE brevemente: "Perfecto, tomo nota." (o algo acorde a lo que dijo).
       3. LLAMA a `guardar_encuesta(comentarios="...", status='completed')`.
       4. DI: "Muchas gracias por su tiempo. ¡Adiós!".
       5. ESPERA 1 SEGUNDO (en tu mente).
       6. POR ÚLTIMO llama a `finalizar_llamada()`.

       CASO B: EL USUARIO DICE QUE NO (a los comentarios):
       1. LLAMA a `guardar_encuesta(comentarios="Sin comentarios", status='completed')`.
       2. DI: "Perfecto. Muchas gracias por su tiempo. ¡Que tenga un buen día!".
       3. ESPERA 1 SEGUNDO (en tu mente).
       4. POR ÚLTIMO llama a `finalizar_llamada()`.

       ⚠️ REGLA CRÍTICA DE ORO:
       - JAMÁS llames a `finalizar_llamada` inmediatamente después de `guardar_encuesta`.
       - SIEMPRE debes decir la frase de despedida de forma audible.
       
       REGLA DE ORO DE DESPEDIDA:
       - SIEMPRE di la frase de despedida completa ("Gracias... adiós") ANTES de llamar a `finalizar_llamada()`.
       - Nunca cuelgues sin despedirte.
    """

    # Extraer ID de la sala
    # Extraer ID de la sala
    import re
    survey_id = 0
    match = re.search(r'encuesta_(\d+)', ctx.room.name)
    if match:
        survey_id = int(match.group(1))

    # --- DEFINICIÓN DE AGENTE Y ESTADO (Iniciamos vacío para alcance global en entrypoint) ---
    class AgentState:
        def __init__(self):
            self.instance = None
            self.survey_id = survey_id

    state = AgentState()

    # --- LÓGICA DE GUARDADO DE EMERGENCIA ---
    async def final_save():
        print(f"🛑 [Shutdown] Ejecutando guardado de emergencia para Sala {ctx.room.name}")
        
        if not state.instance:
            print("⚠️ [Shutdown] El agente no llegó a inicializarse. No se guarda nada.")
            return

        agent_inst = state.instance
        s_id = state.survey_id

        try:
             # Si ya estaba completada (por tool), ignoramos
            if agent_inst.is_completed:
                    print("✅ [Shutdown] Encuesta ya finalizada correctamente. No se sobrescribe.")
                    return

            # Si NO estaba completada, recuperamos status previo o 'incomplete'
            final_st = agent_inst.last_status 
            if not final_st:
                    # Si no ha dicho nada (interaction count bajo), quizás es un rejected implícito o unreached?
                    if agent_inst.interaction_count < 1:
                        final_st = 'incomplete' 
                    else:
                        final_st = 'incomplete'
            
            print(f"⚠️ [Shutdown] La encuesta NO estaba finalizada. Guardando forzosamente como '{final_st}'.")
            
            # Rescatar texto pendiente si hubo corte
            transcript_to_save = agent_inst.full_transcript
            if agent_inst.pending_client_text:
                transcript_to_save += f"\n[CORTE DE LLAMADA] Cliente: {agent_inst.pending_client_text}"

            await agent_inst.helper_save_survey(
                id_encuesta=s_id,
                transcript=transcript_to_save,
                status=final_st,
                **agent_inst.current_scores
            )
        except Exception as e:
            print(f"❌ [Shutdown] Error guardando: {e}")

    # Registramos los handlers de desconexión
    @ctx.room.on("disconnected")
    def on_room_disconnected():
        print("🔌 [Event] Room Disconnected")
        asyncio.create_task(final_save())

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        print(f"🔌 [Event] Participant Disconnected: {participant.identity}")
        # Si el usuario cuelga, forzamos el guardado inmediatamente
        asyncio.create_task(final_save())

    # Registramos también como callback de cierre de trabajo por si acaso
    ctx.add_shutdown_callback(final_save)

    try:
        # VAD ajustado: 0.1s para detectar rápido, 0.5s paradas cortas (más ágil)
        vad = silero.VAD.load(min_speech_duration=0.1, min_silence_duration=0.5)
        
        # Usar los plugins directamente (inference.STT/TTS
        stt = deepgram.STT(model=stt_model, language="es")
        # Forzar language='es' para evitar acento "chino/americano" en modelo multilingual
        tts = cartesia.TTS(model=tts_model, voice=tts_voice, language="es")
        
        # Validar API Keys
        groq_key = os.getenv("GROQ_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if groq_key:
             print(f"🔑 [Security] GROQ_API_KEY encontrada")
        if google_key:
             print(f"🔑 [Security] GOOGLE_API_KEY encontrada")
        if openai_key:
             print(f"🔑 [Security] OPENAI_API_KEY encontrada")

        print(f"🤖 [Init] Configurando LLM...")
        
        # 1. Leer configuración dinámica
        app_settings = get_app_settings()
        
        # Priorizar lo que venga en app_settings (ModelsView)
        provider = app_settings.get("llm_provider", "groq")
        model_name = app_settings.get("llm_model", "llama-3.3-70b-versatile")
        
        # Auto-corrección de seguridad para evitar 404s cruzados
        if provider == "google":
            if "gemini" not in model_name.lower():
                 print(f"⚠️ [Correction] Se pidió Google pero el modelo era '{model_name}'. Forzando 'models/gemini-2.0-flash'.")
                 model_name = "models/gemini-2.0-flash"
            elif not model_name.startswith("models/"):
                 print(f"⚠️ [Correction] Añadiendo prefijo 'models/' a {model_name}")
                 model_name = f"models/{model_name}"
        elif provider == "groq":
            if "gemini" in model_name.lower() or "gpt" in model_name.lower():
                 print(f"⚠️ [Correction] Se pidió Groq pero el modelo era '{model_name}'. Forzando 'llama-3.3-70b-versatile'.")
                 model_name = "llama-3.3-70b-versatile"
        elif provider == "openai":
            if "gpt" not in model_name.lower():
                 print(f"⚠️ [Correction] Se pidió OpenAI pero el modelo era '{model_name}'. Forzando 'gpt-4o-mini'.")
                 model_name = "gpt-4o-mini"
        elif provider == "deepseek":
            if "deepseek" not in model_name.lower():
                 print(f"⚠️ [Correction] Se pidió DeepSeek pero el modelo era '{model_name}'. Forzando 'deepseek-chat'.")
                 model_name = "deepseek-chat"

        print(f"⚙️ [LLM Config] Final -> Provider: {provider} | Model: {model_name}")

        # 2. DESCUBRIMIENTO DINÁMICO (Consulta ultra-rápida antes de elegir)
        # Esto evita silencios porque ya sabemos quién está "vivo" antes de empezar
        print(f"⚙️ [LLM Config] Preferencia -> Provider: {provider} | Model: {model_name}")
        candidates = await discover_best_llm(google_key, groq_key, preferred_provider=provider, preferred_model=model_name, openai_key=openai_key)
        
        if not candidates:
            print(f"❌ [Error] Ningún motor LLM respondió al pre-check de salud.")
            if groq_key:
                candidates = [("Groq Emergency", openai.LLM(
                    model="llama-3.3-70b-versatile", base_url="https://api.groq.com/openai/v1", api_key=groq_key
                ))]
            else:
                raise ValueError("No LLM services available after health check")

        print(f"⚙️ [Redundancy] HA Dinámica activada: {[c[0] for c in candidates]}")
        llm_plugin = RedundantLLM(candidates=candidates, parent_agent=agent_instance)
        
        # Asignar la instancia al estado global para los handlers de desconexión
        state.instance = agent_instance


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
                    print(f"⏱️ [Perf] Transcripción FINAL recibida: '{transcript.text}'")
                
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

        # DEBUG: Log de herramientas para ver latencia
        if hasattr(session, 'on'): # Verificar método para evitar crash si librería cambia
            try:
                @session.on("function_call_started")
                def on_tool_start(fn_call):
                    print(f"⏱️ [Perf] LLM decidió llamar a herramienta: {fn_call.tool_name} (args: {fn_call.arguments})")
                
                @session.on("function_call_finished")
                def on_tool_end(fn_call, result):
                    print(f"⏱️ [Perf] Herramienta {fn_call.tool_name} finalizó.")
            except:
                pass # Eventos pueden variar según versión del SDK
        
        print(f"🚀 [Agent] Conectando sala {ctx.room.name}...")
        await session.start(agent=agent_instance, room=ctx.room)
        
        # Saludo forzado inicial
        await session.generate_reply(
            instructions=f"Saluda ahora mismo diciendo exactamente: '{greeting}'. No uses herramientas.",
            allow_interruptions=True
        )

        # DETECCIÓN DE DESCONEXIÓN: Si el cliente nunca contesta o cuelga antes de responder,
        # el participante SIP se desconecta. Detectamos esto para cerrar la sala rápido.
        @ctx.room.on("participant_disconnected")
        def on_participant_left(participant):
             # Ya manejado por el handler global arriba
             pass

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