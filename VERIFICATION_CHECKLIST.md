# 🔍 Checklist de Verificación - Integración Frontend-Backend

## ✅ Archivos Creados/Modificados

### Backend (carpeta `backend/`)
- [x] `backend/api.py` - API principal con endpoints para frontend y bridge
- [x] `backend/agent.py` - Agente LiveKit de voz (copiado)
- [x] `backend/bridge_server.py` - Bridge server original (copiado)
- [x] `backend/lanzar_llamada.py` - Script de prueba (copiado)
- [x] `backend/.env` - Variables de entorno (copiado)
- [x] `backend/requirements.txt` - Dependencias Python (copiado)

### Frontend (carpeta raíz)
- [x] `views/VoiceAgentsView.tsx` - Vista actualizada con integración al backend
- [x] `.gitignore` - Actualizado para Python y backend
- [x] `README.md` - Documentación principal
- [x] `INTEGRATION_GUIDE.md` - Guía técnica detallada
- [x] `start-backend.bat` - Script para iniciar solo backend
- [x] `start-all.bat` - Script para iniciar todo

## 🔧 Verificación de Configuración

### 1. Variables de Entorno (backend/.env)

Verifica que existan estas variables:

```bash
# LiveKit
LIVEKIT_URL=wss://...livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

# SIP
SIP_OUTBOUND_TRUNK_ID=ST_...

# AI Providers
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=...
GROQ_API_KEY=...

# Database
DB_HOST=localhost
DB_USER=ausarta_user
DB_PASSWORD=...
DB_NAME=encuestas_ausarta

# Bridge
BRIDGE_SERVER_URL=http://127.0.0.1:8001
```

### 2. Base de Datos MySQL

Verifica que exista la tabla `encuestas`:

```sql
USE encuestas_ausarta;

SHOW TABLES; -- Debe mostrar 'encuestas'

DESCRIBE encuestas;
-- Debe tener: id, telefono, fecha, completada, 
--             puntuacion_comercial, puntuacion_instalador, 
--             puntuacion_rapidez, comentarios
```

### 3. Dependencias Python

Verifica que estén instaladas:

```bash
cd backend
pip install -r requirements.txt

# Verificar instalación
python -c "import fastapi; print('FastAPI OK')"
python -c "import livekit; print('LiveKit OK')"
python -c "import mysql.connector; print('MySQL OK')"
```

### 4. Dependencias Node.js

Verifica que estén instaladas:

```bash
npm install

# Verificar instalación
npm list react
npm list lucide-react
```

## 🚀 Pasos para Probar

### Opción A: Todo de una vez

1. Ejecuta:
```bash
.\start-all.bat
```

2. Espera a que se abran 3 ventanas:
   - LiveKit Agent
   - Backend API
   - Frontend

3. Abre el navegador en: http://localhost:5173

### Opción B: Manual (recomendado para debugging)

1. **Ventana 1 - Backend API:**
```bash
cd backend
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8001
```

Deberías ver:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

2. **Ventana 2 - LiveKit Agent:**
```bash
cd backend
python agent.py dev
```

Deberías ver:
```
INFO:     Starting agent...
INFO:     Agent Dakota-1ef9 ready
```

3. **Ventana 3 - Frontend:**
```bash
npm run dev
```

Deberías ver:
```
VITE v6.2.0  ready in XXX ms

➜  Local:   http://localhost:5173/
```

## 🧪 Prueba Funcional

### Test 1: Crear Agente

1. Abre http://localhost:5173
2. Ve a "Voice Agents"
3. Haz clic en "New Agent"
4. Completa:
   - Call Type: Outbound
   - Agent Name: Test Encuesta
   - Use Case: Prueba
   - Description: Agente de prueba
5. Haz clic en "Create Agent"

**Resultado esperado:** El agente aparece en la lista

### Test 2: Verificar Backend

1. Abre http://localhost:8001
2. Deberías ver:
```json
{
  "message": "Ausarta Voice Agent API",
  "status": "running"
}
```

3. Abre http://localhost:8001/docs
4. Deberías ver la documentación interactiva de FastAPI

### Test 3: Lanzar Llamada

1. En "Voice Agents", selecciona un agente
2. Haz clic en el botón verde de teléfono (📞)
3. Ingresa un número de prueba: +34621151394
4. Haz clic en "Llamar Ahora"

**Resultado esperado en la consola del backend:**
```
📞 Iniciando llamada outbound a +34621151394
📝 1. Creando ficha para: +34621151394
✅ Ficha creada con ID: 123
🤖 Despertando agente en sala: encuesta_123
📞 Creando participante SIP...
🚀 ¡Llamada en curso!
```

**Resultado esperado en el frontend:**
```
✅ Llamada iniciada correctamente!
Sala: encuesta_123
ID: 123
```

## ❌ Problemas Comunes y Soluciones

### Error: "Cannot connect to backend"

**Problema:** El backend no está corriendo
**Solución:**
```bash
cd backend
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8001
```

### Error: "ModuleNotFoundError: No module named 'fastapi'"

**Problema:** Faltan dependencias Python
**Solución:**
```bash
cd backend
pip install -r requirements.txt
```

### Error: "Error loading agents"

**Problema:** CORS o backend no responde
**Solución:**
1. Verifica que el backend esté en puerto 8001
2. Verifica que no haya firewall bloqueando
3. Mira la consola del navegador (F12) para más detalles

### Error: "mysql.connector.errors.ProgrammingError"

**Problema:** Base de datos no configurada
**Solución:**
1. Crea la base de datos:
```sql
CREATE DATABASE encuestas_ausarta;
USE encuestas_ausarta;

CREATE TABLE encuestas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telefono VARCHAR(20),
    fecha DATETIME,
    completada TINYINT DEFAULT 0,
    puntuacion_comercial INT,
    puntuacion_instalador INT,
    puntuacion_rapidez INT,
    comentarios TEXT
);
```

### Error: "LiveKit API error"

**Problema:** Credenciales incorrectas
**Solución:**
1. Verifica las credenciales en `backend/.env`
2. Verifica que el LIVEKIT_URL sea correcto
3. Verifica que las API keys no hayan expirado

## 📊 Monitoreo

### Logs del Backend

Nivel de log: INFO

Logs importantes a vigilar:
- `📞 Iniciando llamada outbound` - Se inició una llamada
- `✅ Ficha creada con ID: X` - Se creó registro en BD
- `🚀 ¡Llamada en curso!` - Llamada SIP creada exitosamente
- `📥 Recibiendo datos` - Agente está guardando datos
- `✂️ Petición de colgar recibida` - Llamada finalizando

### Logs del Agente

Nivel de log: DEBUG

Logs importantes:
- `Agent connected to room` - Agente conectado
- `STT: [transcription]` - Qué está diciendo el usuario
- `LLM: [response]` - Qué está diciendo el agente
- `Tool call: guardar_encuesta` - Herramienta ejecutándose

### Frontend (Consola del Navegador)

Abre F12 → Console

Logs importantes:
- `Error loading agents:` - Error cargando agentes
- `Error making call:` - Error lanzando llamada

## ✅ Todo Funciona Cuando...

- [x] Backend responde en http://localhost:8001
- [x] Frontend carga en http://localhost:5173
- [x] Puedes crear agentes sin errores
- [x] Puedes lanzar llamadas y ves los logs en backend
- [x] El agente se conecta a la sala LiveKit
- [x] Los datos se guardan en la base de datos

## 🎉 ¡Integración Completa!

Si todos los tests pasan, la integración está funcionando correctamente.

---

**Fecha de integración:** 2026-02-06
**Versión:** 1.0.0
**Estado:** ✅ Completado
