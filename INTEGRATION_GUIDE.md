# 🎯 Guía de Integración Frontend-Backend

## Resumen de la Integración

Este documento explica cómo se ha integrado el backend del **AgenteLocal** en el **frontend React** para crear un sistema completo de agentes de voz con llamadas outbound.

## 🔄 Flujo Completo de una Llamada Outbound

### 1. Usuario crea un agente en el Frontend

**Frontend: VoiceAgentsView.tsx**
```typescript
// Usuario completa el formulario
const newAgent = {
  name: "Encuesta Calidad Ausarta",
  callType: "Outbound",
  useCase: "Encuestas de Satisfacción",
  description: "Realiza encuestas de calidad..."
};

// Se envía al backend
fetch('http://localhost:8001/api/agents', {
  method: 'POST',
  body: JSON.stringify(newAgent)
})
```

**Backend: api.py**
```python
@app.post("/api/agents")
async def create_agent(agent: VoiceAgentCreate):
    # Guarda el agente (mock por ahora)
    return {"id": "generated-id", ...}
```

### 2. Usuario inicia una llamada Outbound

**Frontend: VoiceAgentsView.tsx**
```typescript
// Usuario hace clic en el botón de teléfono
handleStartCall(agent) → abre diálogo
// Usuario ingresa número: +34621151394
handleMakeCall() → {
  fetch('http://localhost:8001/api/calls/outbound', {
    method: 'POST',
    body: JSON.stringify({
      agentId: "1",
      phoneNumber: "+34621151394"
    })
  })
}
```

**Backend: api.py**
```python
@app.post("/api/calls/outbound")
async def make_outbound_call(call_request: OutboundCallRequest):
    # 1. Crear ficha en BD
    ficha = await iniciar_encuesta(telefono)  # ID: 495
    
    # 2. Crear sala LiveKit
    sala = f"encuesta_{ficha['id']}"  # "encuesta_495"
    
    # 3. Despertar agente
    subprocess.run(["lk", "dispatch", "create", 
                   "--room", sala, 
                   "--agent-name", "Dakota-1ef9"])
    
    # 4. Crear participante SIP
    lkapi.sip.create_sip_participant(
        room_name=sala,
        sip_trunk_id="ST_UBZcusTkNdtH",
        sip_call_to="+34621151394",
        participant_identity="Cliente"
    )
    
    return {"status": "success", "callId": 495, "roomName": "encuesta_495"}
```

### 3. Agente LiveKit se conecta y realiza la llamada

**Backend: agent.py**
```python
@server.rtc_session(agent_name="Dakota-1ef9")
async def entrypoint(ctx: JobContext):
    # El agente se conecta a la sala "encuesta_495"
    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3"),
        llm=openai.LLM(model="llama-3.3-70b-versatile"),
        tts=inference.TTS(model="cartesia/sonic-3")
    )
    
    await session.start(agent=DefaultAgent(), room=ctx.room)
```

**DefaultAgent**
```python
class DefaultAgent(Agent):
    async def on_enter(self):
        # Saluda al usuario
        await self.session.generate_reply(
            instructions="Saluda y pregunta si tiene un minuto..."
        )
    
    @function_tool(name="guardar_encuesta")
    async def _http_tool_guardar_encuesta(self, ...):
        # Guarda datos en BD vía HTTP
        session.post(f"{BRIDGE_URL}/guardar-encuesta", json=datos)
    
    @function_tool(name="finalizar_llamada")
    async def _http_tool_finalizar_llamada(self, ...):
        # Cuelga la llamada vía HTTP
        session.post(f"{BRIDGE_URL}/colgar", json={"nombre_sala": sala})
```

### 4. Agente guarda datos y finaliza

**Backend: api.py**
```python
@app.post("/guardar-encuesta")
async def guardar_encuesta(datos: FinEncuesta):
    # Guarda en MySQL
    cursor.execute(
        "UPDATE encuestas SET puntuacion_comercial=%s, ... WHERE id=%s",
        (datos.nota_comercial, ..., id_ficha)
    )
    return {"status": "success"}

@app.post("/colgar")
async def colgar(datos: ColgarLlamada):
    await asyncio.sleep(2)  # Espera a que termine de hablar
    
    # Elimina la sala LiveKit
    await lkapi.room.delete_room(room=datos.nombre_sala)
    return {"status": "success"}
```

### 5. Frontend recibe confirmación

**Frontend: VoiceAgentsView.tsx**
```typescript
const data = await response.json();

if (response.ok) {
  alert(`✅ Llamada iniciada correctamente!
Sala: ${data.roomName}
ID: ${data.callId}`);
  
  onStartCall(); // Abre la vista LiveCall si es necesario
}
```

## 🏗️ Arquitectura de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Voice Agents │  │  Telephony   │  │  Campaigns   │      │
│  │     View     │  │     View     │  │     View     │      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
│         │                                                     │
│         │ HTTP Requests                                      │
│         ▼                                                     │
└─────────┼─────────────────────────────────────────────────┘
          │
          │ http://localhost:8001/api/*
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND API (FastAPI)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  api.py                                              │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │ GET /agents│  │POST /agents│  │POST /calls │    │   │
│  │  └────────────┘  └────────────┘  └─────┬──────┘    │   │
│  │                                         │            │   │
│  │  ┌────────────────────────────────────┼─────────┐  │   │
│  │  │ Bridge Endpoints                   │         │  │   │
│  │  │ POST /iniciar-encuesta    ◄────────┼─────────┼──┼─┐ │
│  │  │ POST /guardar-encuesta    ◄────────┼─────────┼──┼─┤ │
│  │  │ POST /colgar               ◄────────┼─────────┼──┼─┤ │
│  │  └────────────────────────────────────┼─────────┘  │ │ │
│  └───────────────────────────────────────┼────────────┘ │ │
│                                           │              │ │
│         ┌─────────────────────────────────┘              │ │
│         │                                                │ │
│         │ 1. Create DB Record                            │ │
│         │ 2. Create LiveKit Room                         │ │
│         │ 3. Dispatch Agent                              │ │
│         │ 4. Create SIP Participant                      │ │
│         ▼                                                │ │
└─────────┼────────────────────────────────────────────────┘ │
          │                                                  │ │
          ▼                                                  │ │
┌─────────────────────────────────────────────────────────┐ │ │
│              LiveKit Server (Cloud)                      │ │ │
│  ┌──────────┐         ┌──────────┐                      │ │ │
│  │   Room   │ ◄─────► │   SIP    │                      │ │ │
│  │ encuesta │         │ Participant                     │ │ │
│  │   _495   │         │  (Client) │                      │ │ │
│  └────┬─────┘         └──────────┘                      │ │ │
│       │                                                   │ │ │
└───────┼───────────────────────────────────────────────────┘ │ │
        │                                                     │ │
        │ WebSocket Connection                                │ │
        ▼                                                     │ │
┌─────────────────────────────────────────────────────────┐ │ │
│             LIVEKIT AGENT (Python)                       │ │ │
│  ┌──────────────────────────────────────────────────┐   │ │ │
│  │  agent.py                                        │   │ │ │
│  │  ┌────────────┐    ┌────────────┐              │   │ │ │
│  │  │ DefaultAgent   │   │ STT/LLM/TTS           │   │ │ │
│  │  │              │    │ Pipeline    │           │   │ │ │
│  │  │ on_enter()   │    └────────────┘              │   │ │ │
│  │  │              │                                 │   │ │ │
│  │  │ @function_tool                               │   │ │ │
│  │  │ guardar_encuesta() ──────────────────────────┼───┘ │ │
│  │  │ finalizar_llamada() ─────────────────────────┼─────┘ │
│  │  └────────────┘                                 │   │   │
│  └──────────────────────────────────────────────────┘   │   │
└─────────────────────────────────────────────────────────┘   │
                                                               │
                                                               │
┌─────────────────────────────────────────────────────────┐   │
│                   MySQL Database                         │   │
│  ┌──────────────────────────────────────────────────┐   │   │
│  │  encuestas                                       │   │   │
│  │  ┌────┬──────────┬──────┬─────────────┬────┐   │   │   │
│  │  │ id │ telefono │ fecha│ completada  │ ...│   │   │   │
│  │  ├────┼──────────┼──────┼─────────────┼────┤   │   │   │
│  │  │495 │+34621... │2026..│      1      │ ...│   │   │   │
│  │  └────┴──────────┴──────┴─────────────┴────┘   │   │   │
│  └──────────────────────────────────────────────────┘   │   │
└─────────────────────────────────────────────────────────┘   │
                         ▲                                      │
                         │                                      │
                         └──────────────────────────────────────┘
```

## 📋 Endpoints de la API

### Frontend Endpoints

| Método | Endpoint | Descripción | Parámetros |
|--------|----------|-------------|------------|
| GET | `/api/agents` | Lista todos los agentes | - |
| POST | `/api/agents` | Crea un nuevo agente | `{name, callType, useCase, description}` |
| POST | `/api/calls/outbound` | Lanza llamada outbound | `{agentId, phoneNumber}` |
| POST | `/api/telephony/config` | Guarda config telefonía | `{provider, fromNumbers}` |

### Bridge Endpoints (para el Agente)

| Método | Endpoint | Descripción | Parámetros |
|--------|----------|-------------|------------|
| POST | `/iniciar-encuesta` | Crea ficha en BD | `{telefono}` |
| POST | `/guardar-encuesta` | Guarda datos encuesta | `{id_encuesta, notas, comentarios}` |
| POST | `/colgar` | Termina la llamada | `{nombre_sala}` |

## 🔑 Puntos Clave de la Integración

### 1. **Configuración de Telephony en el Frontend**
   - Los usuarios configuran el proveedor SIP en la vista "Telephony"
   - Los números "From" se almacenan para usarse en llamadas

### 2. **Creación de Agentes**
   - Los agentes se crean desde el frontend con tipo "Outbound"
   - El backend usa esta configuración para lanzar llamadas

### 3. **Lanzamiento de Llamadas**
   - El frontend envía el número de teléfono al backend
   - El backend orquesta todo: BD → LiveKit → SIP
   - El agente se conecta automáticamente y comienza la conversación

### 4. **Comunicación Agente-Backend**
   - El agente usa HTTP para comunicarse con el backend
   - Endpoints bridge permiten guardar datos y colgar

### 5. **Persistencia de Datos**
   - Toda la información se guarda en MySQL
   - ID de encuesta se usa para identificar la sala y los datos

## 🎨 Componentes del Frontend

### VoiceAgentsView.tsx

```typescript
// Estados principales
const [agents, setAgents] = useState<Agent[]>([]);
const [showCallDialog, setShowCallDialog] = useState(false);
const [phoneNumber, setPhoneNumber] = useState('+34');

// Handlers
const handleCreateAgent = async () => { /* POST /api/agents */ }
const handleStartCall = (agent) => { /* Abre diálogo */ }
const handleMakeCall = async () => { /* POST /api/calls/outbound */ }
```

### TelephonyView.tsx

```typescript
// Configuración de telefonía
const [config, setConfig] = useState({
  provider: 'LCR',
  fromNumbers: '+34944771453'
});

const saveConfig = async () => { /* POST /api/telephony/config */ }
```

## ✨ Mejoras Futuras

1. **Persistencia de Agentes**: Guardar agentes en BD en lugar de mock
2. **Configuración de Telephony Real**: Usar los números configurados en llamadas
3. **Historial de Llamadas**: Mostrar llamadas realizadas
4. **Panel de Monitoreo**: Ver llamadas en curso en tiempo real
5. **Webhooks**: Notificaciones cuando finaliza una llamada
6. **Templates de Agentes**: Plantillas predefinidas para casos comunes

## 🚀 Cómo Extender

### Añadir un nuevo tipo de agente

1. **Frontend**: Añadir opción en el select de `callType`
2. **Backend**: Modificar `VoiceAgentCreate` para incluir el nuevo tipo
3. **Agent**: Crear una nueva clase de agente con las instrucciones específicas

### Añadir nuevos endpoints

1. **Backend**: Definir el endpoint en `api.py`
2. **Frontend**: Crear la función fetch correspondiente
3. **UI**: Añadir botón/formulario en el componente correspondiente

## 📚 Referencias

- [LiveKit Documentation](https://docs.livekit.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [LiveKit Agents](https://docs.livekit.io/agents/)
