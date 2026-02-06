# Ausarta Robot - Voice Agent Platform 🤖📞

Plataforma completa de agentes de voz con integración frontend-backend para llamadas outbound usando LiveKit.

## 📦 Estructura del Proyecto

```
ausarta-robot-voice-agent-platform/
├── backend/                    # Backend integrado (AgenteLocal)
│   ├── api.py                 # API FastAPI principal
│   ├── agent.py               # Agente LiveKit de voz
│   ├── bridge_server.py       # Bridge server original
│   ├── lanzar_llamada.py      # Script de prueba
│   ├── .env                   # Variables de entorno
│   └── requirements.txt       # Dependencias Python
├── views/                     # Vistas React
│   ├── VoiceAgentsView.tsx   # Vista principal de agentes
│   ├── TelephonyView.tsx     # Configuración de telefonía
│   └── ...
├── App.tsx                    # Aplicación principal
├── start-backend.bat          # Iniciar solo backend
└── start-all.bat             # Iniciar todo (agente + backend + frontend)
```

## 🚀 Inicio Rápido

### Opción 1: Iniciar todo automáticamente

```bash
.\start-all.bat
```

Esto iniciará:
- ✅ Agente LiveKit (agent.py)
- ✅ Backend API (puerto 8001)
- ✅ Frontend React (puerto 5173)

### Opción 2: Iniciar servicios por separado

**1. Iniciar Backend:**
```bash
.\start-backend.bat
```

**2. Iniciar Agente LiveKit:**
```bash
cd backend
python agent.py dev
```

**3. Iniciar Frontend:**
```bash
npm run dev
```

## 🔧 Configuración

### Variables de Entorno (backend/.env)

Asegúrate de tener configuradas las siguientes variables en `backend/.env`:

```env
# LiveKit
LIVEKIT_URL=wss://tu-proyecto.livekit.cloud
LIVEKIT_API_KEY=tu_api_key
LIVEKIT_API_SECRET=tu_api_secret

# SIP Trunk
SIP_OUTBOUND_TRUNK_ID=ST_tu_trunk_id

# AI Providers
DEEPGRAM_API_KEY=tu_deepgram_key
CARTESIA_API_KEY=tu_cartesia_key
GROQ_API_KEY=tu_groq_key

# Database
DB_HOST=localhost
DB_USER=ausarta_user
DB_PASSWORD=tu_password
DB_NAME=encuestas_ausarta

# Bridge Server
BRIDGE_SERVER_URL=http://127.0.0.1:8001
```

## 📖 Cómo Usar

### 1. Crear un Agente de Voz

1. Abre el frontend (http://localhost:5173)
2. Ve a la sección "Voice Agents"
3. Haz clic en "New Agent"
4. Completa el formulario:
   - **Call Type**: Selecciona "Outbound"
   - **Agent Name**: Nombre descriptivo (ej. "Encuesta Calidad Ausarta")
   - **Use Case**: Propósito del agente (ej. "Encuestas de Satisfacción")
   - **Description**: Descripción detallada de qué hará el agente
5. Haz clic en "Create Agent"

### 2. Lanzar una Llamada Outbound

1. En la lista de agentes, busca el agente que quieres usar
2. Haz clic en el botón verde de teléfono (📞)
3. Ingresa el número de teléfono (con código de país, ej. +34621151394)
4. Haz clic en "Llamar Ahora"
5. ✅ ¡La llamada se iniciará automáticamente!

### 3. Configurar Telefonía

1. Ve a la sección "Telephony"
2. Selecciona el proveedor (por defecto: LCR/Asterisk)
3. Configura los números "From" (separados por comas)
4. Guarda la configuración

## 🏗️ Arquitectura

### Flujo de Llamada Outbound

```
Frontend (React)
    ↓ POST /api/calls/outbound
Backend API (FastAPI)
    ↓ 1. Crea ficha en BD
    ↓ 2. Crea sala LiveKit
    ↓ 3. Despacha agente
    ↓ 4. Crea participante SIP
LiveKit Agent (agent.py)
    ↓ Se conecta a la sala
    ↓ Interactúa con el usuario
    ↓ Llama a /guardar-encuesta
    ↓ Llama a /colgar
Backend API
    ↓ Guarda datos en BD
    ↓ Termina la sala
✅ Llamada completada
```

### Endpoints de la API

#### Frontend Endpoints

- `GET /api/agents` - Lista todos los agentes
- `POST /api/agents` - Crea un nuevo agente
- `POST /api/calls/outbound` - Lanza una llamada outbound
- `POST /api/telephony/config` - Guarda configuración de telefonía

#### Bridge Endpoints (usados por el agente)

- `POST /iniciar-encuesta` - Crea ficha en BD
- `POST /guardar-encuesta` - Guarda datos de la encuesta
- `POST /colgar` - Termina la llamada

## 🔍 Debugging

### Ver logs del backend:
```bash
# En la ventana del backend verás:
📞 Iniciando llamada outbound a +34...
✅ Ficha creada con ID: 123
🤖 Despertando agente en sala: encuesta_123
📞 Creando participante SIP...
🚀 ¡Llamada en curso!
```

### Ver logs del agente:
```bash
# En la ventana del agente verás:
✅ Ficha creada con ID: 123 (Esperando a la IA...)
📥 Recibiendo datos. La IA dice ID: 123
🚀 ¡EXITO! Datos guardados en ficha 123.
✂️  Petición de colgar recibida.
✅ Llamada cortada.
```

## 📝 Notas Importantes

1. **El agente debe estar corriendo** antes de lanzar llamadas
2. **El backend debe estar corriendo** en puerto 8001
3. **La base de datos MySQL debe estar accesible** con la tabla `encuestas` creada
4. **LiveKit debe estar configurado** con las credenciales correctas
5. **El SIP Trunk debe estar configurado** en LiveKit

## 🐛 Solución de Problemas

### "Error al iniciar la llamada"
- Verifica que el backend esté corriendo en puerto 8001
- Verifica las credenciales de LiveKit en `.env`
- Verifica que el SIP Trunk ID sea correcto

### "Error loading agents"
- Verifica que el backend API esté corriendo
- Verifica que no haya errores de CORS (el backend tiene CORS habilitado)

### "Error DB: ..."
- Verifica la conexión a MySQL
- Verifica que la tabla `encuestas` exista
- Verifica las credenciales DB en `.env`

## 🎨 Tecnologías Utilizadas

- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI + Python
- **Voice Agent**: LiveKit Agents Framework
- **AI**: Groq (LLM), Deepgram (STT), Cartesia (TTS)
- **Database**: MySQL
- **Telephony**: LiveKit SIP

## 📄 Licencia

Ausarta © 2026
