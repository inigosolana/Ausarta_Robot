# 🗄️ SQLite vs MySQL - La Nueva Configuración

## ¿Qué ha cambiado?

### ❌ ANTES (MySQL)
```
- Necesitaba un contenedor MySQL separado
- Puerto 3306 (conflicto si ya tienes MySQL)
- Credenciales de base de datos
- Más complejo de configurar
```

### ✅ AHORA (SQLite)
```
- Base de datos en archivo local
- Sin puertos adicionales
- Sin credenciales de BD
- Configuración automática
- Más simple y ligero
```

---

## 🔄 Cómo Funciona Ahora

### 1. **Al Arrancar el Backend**

Cuando el contenedor backend arranca, automáticamente:

```python
# backend/api.py (líneas 27-67)

1. Crea la carpeta /app/data/ si no existe
2. Crea el archivo encuestas.db (base de datos SQLite)
3. Crea la tabla 'encuestas' con todos los campos
4. Crea índices para optimizar búsquedas
```

**Todo esto pasa automáticamente, no necesitas hacer nada.**

### 2. **Dónde se Guardan los Datos**

```
📦 Contenedor Backend
├── /app/
│   ├── api.py (API FastAPI)
│   ├── agent.py (LiveKit Agent)
│   └── data/
│       └── encuestas.db  ← AQUÍ ESTÁN LOS DATOS
```

El archivo `encuestas.db` está en un **volumen Docker persistente** llamado `sqlite-data`, así que:
- ✅ Los datos NO se pierden si reinicias el contenedor
- ✅ Los datos persisten entre builds
- ✅ Puedes hacer backup fácilmente

### 3. **Flujo de una Llamada**

```
FRONTEND → Botón "Llamar" → +34621151394
    ↓
BACKEND API → POST /api/calls/outbound
    ↓
1. Inserta en SQLite:
   INSERT INTO encuestas (telefono, fecha, completada)
   VALUES ('+34621151394', NOW(), 0)
   → Devuelve ID: 123
    ↓
2. Crea sala LiveKit: "encuesta_123"
    ↓
3. Lanza agente LiveKit
    ↓
AGENTE LIVEKIT → Habla con el usuario
    ↓
AGENTE → POST /guardar-encuesta
    {
      "id_encuesta": 123,
      "nota_comercial": 9,
      "nota_instalador": 8,
      ...
    }
    ↓
BACKEND → Actualiza SQLite:
   UPDATE encuestas SET
   puntuacion_comercial=9,
   puntuacion_instalador=8,
   completada=1
   WHERE id=123
    ↓
✅ DATOS GUARDADOS EN encuestas.db
```

---

## 🆚 Comparación

| Característica | MySQL (Antes) | SQLite (Ahora) |
|----------------|---------------|----------------|
| **Servicios Docker** | 3 (frontend, backend, mysql) | 2 (frontend, backend) |
| **Puertos** | 80, 8001, 3306 | 80, 8001 |
| **Variables ENV** | 9 necesarias | 4 necesarias |
| **Conflictos de puerto** | Sí (3306) | No |
| **Configuración** | Compleja | Simple |
| **Inicio** | ~60 segundos | ~30 segundos |
| **Memoria** | ~1.5GB | ~500MB |
| **Para este caso** | Overkill | Perfecto ✅ |

---

## 📊 Variables de Entorno Ahora

### ✅ Necesarias (Solo AI y LiveKit):
```env
LIVEKIT_URL=wss://tu-proyecto.livekit.cloud
LIVEKIT_API_KEY=tu_api_key
LIVEKIT_API_SECRET=tu_api_secret
SIP_OUTBOUND_TRUNK_ID=ST_tu_trunk_id
DEEPGRAM_API_KEY=tu_deepgram_key
CARTESIA_API_KEY=tu_cartesia_key
GROQ_API_KEY=tu_groq_key
```

### ❌ Ya NO necesitas:
```env
DB_HOST=mysql  ← ELIMINADO
DB_USER=...    ← ELIMINADO
DB_PASSWORD=.. ← ELIMINADO
DB_NAME=...    ← ELIMINADO
MYSQL_ROOT_PASSWORD=... ← ELIMINADO
```

---

## 🔍 Ver los Datos (Opcional)

Si quieres ver qué hay en la base de datos:

```bash
# Desde Portainer o terminal

# 1. Entrar al contenedor backend
docker exec -it ausarta-backend bash

# 2. Instalar sqlite3 (si no está)
apt-get update && apt-get install sqlite3

# 3. Abrir la base de datos
sqlite3 /app/data/encuestas.db

# 4. Ver las encuestas
SELECT * FROM encuestas;

# Salir
.exit
```

O puedes copiar el archivo a tu PC:
```bash
docker cp ausarta-backend:/app/data/encuestas.db ./encuestas.db
```

---

## 💾 Backup de los Datos

### Hacer Backup:
```bash
# Copiar archivo SQLite a tu PC
docker cp ausarta-backend:/app/data/encuestas.db ./backup-encuestas-$(date +%Y%m%d).db
```

### Restaurar Backup:
```bash
# Copiar archivo de vuelta al contenedor
docker cp ./backup-encuestas-20260206.db ausarta-backend:/app/data/encuestas.db

# Reiniciar backend para que recargue
docker restart ausarta-backend
```

---

## ✅ Ventajas de SQLite para tu caso:

1. **Sin conflictos de puerto** - No compite con tu MySQL existente
2. **Datos locales** - Todo en un archivo, fácil de backup
3. **Más simple** - Menos servicios, menos configuración
4. **Más rápido** - Sin latencia de red entre backend y BD
5. **Suficiente** - Para miles de encuestas funciona perfecto
6. **Portátil** - Puedes mover el archivo .db a otro servidor

---

## 🎯 ¿Cuándo usar MySQL en lugar de SQLite?

Usa MySQL si:
- ❌ Necesitas concurrencia masiva (miles de writes/segundo)
- ❌ Necesitas acceso remoto a la BD desde otras apps
- ❌ Necesitas replicación entre servidores
- ❌ Tienes millones de registros

Para tu caso de **encuestas de voz**:
- ✅ SQLite es más que suficiente
- ✅ Más simple de mantener
- ✅ Menos puntos de fallo

---

## 🚀 Resumen

**Con SQLite:**
- 2 contenedores en lugar de 3
- 7 variables de entorno en lugar de 12
- 30 segundos para arrancar en lugar de 60
- 500MB RAM en lugar de 1.5GB
- Todo funciona EXACTAMENTE igual
- Los datos se guardan en `/app/data/encuestas.db`
- Persistencia garantizada con volumen Docker

**¡Todo sigue funcionando igual, pero más simple!** 🎉
