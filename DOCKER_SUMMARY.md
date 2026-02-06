# 🐳 Configuración Docker - Resumen Final

## ✅ Archivos Docker Creados

### 📂 Estructura Completa

```
ausarta-robot-voice-agent-platform/
│
├── 🐳 docker-compose.yml           # Orquestación principal
├── 🐳 Dockerfile                   # Frontend (React + Nginx)
├── 🔧 nginx.conf                   # Configuración Nginx
├── 📝 .env.example                 # Variables de entorno ejemplo
├── 🗄️ init-db.sql                  # Inicialización MySQL
├── 📦 .dockerignore                # Frontend dockerignore
├── 📖 DOCKER_DEPLOYMENT.md         # Guía completa
├── 🚀 PORTAINER_QUICKSTART.md      # Guía rápida
│
└── backend/
    ├── 🐳 Dockerfile               # Backend (API + Agent)
    ├── 🔧 start.sh                 # Script inicio backend
    └── 📦 .dockerignore            # Backend dockerignore
```

## 🎯 Servicios Docker

### 1. **Frontend** (React + Nginx)
- **Puerto**: 80
- **Imagen**: Multi-stage build (Node.js → Nginx)
- **Características**:
  - Build optimizado de producción
  - Nginx como servidor web
  - Proxy reverso al backend
  - Compresión gzip
  - Cache de archivos estáticos

### 2. **Backend** (FastAPI + LiveKit Agent)
- **Puerto**: 8001
- **Imagen**: Python 3.11-slim
- **Características**:
  - API FastAPI
  - LiveKit Agent en el mismo contenedor
  - Script start.sh para lanzar ambos
  - Health checks configurados

### 3. **MySQL Database**
- **Puerto**: 3306
- **Imagen**: MySQL 8.0
- **Características**:
  - Inicialización automática con init-db.sql
  - Volumen persistente
  - Health checks

## 🔗 Red y Comunicación

```
┌─────────────────────────────────────────┐
│         ausarta-network (bridge)        │
│                                          │
│  ┌────────────┐  ┌────────────┐         │
│  │  Frontend  │  │  Backend   │         │
│  │  (nginx)   │◄─┤  (FastAPI) │         │
│  │  Port: 80  │  │  Port:8001 │         │
│  └─────┬──────┘  └──────┬─────┘         │
│        │                 │               │
│        │        ┌────────▼─────┐         │
│        └────────►    MySQL     │         │
│                 │  Port: 3306  │         │
│                 └──────────────┘         │
│                                          │
└─────────────────────────────────────────┘
```

## 📋 Variables de Entorno Requeridas

### LiveKit
- `LIVEKIT_URL` - URL del servidor LiveKit
- `LIVEKIT_API_KEY` - API Key de LiveKit
- `LIVEKIT_API_SECRET` - Secret de LiveKit
- `SIP_OUTBOUND_TRUNK_ID` - ID del SIP trunk

### Servicios AI
- `DEEPGRAM_API_KEY` - Para Speech-to-Text
- `CARTESIA_API_KEY` - Para Text-to-Speech
- `GROQ_API_KEY` - Para LLM (Llama)
- `OPENAI_API_KEY` - Opcional

### Base de Datos
- `DB_HOST=mysql` - Hostname del servicio MySQL
- `DB_USER` - Usuario de la BD
- `DB_PASSWORD` - Contraseña de la BD
- `DB_NAME` - Nombre de la BD
- `MYSQL_ROOT_PASSWORD` - Password root de MySQL

## 🚀 Comandos Útiles

### Desarrollo Local
```bash
# Build y arrancar
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Parar
docker-compose down

# Limpiar todo (incluido volúmenes)
docker-compose down -v
```

### En Portainer

1. **Crear Stack**:
   - Repository: `https://github.com/inigosolana/Ausarta_Robot`
   - Compose path: `docker-compose.yml`
   
2. **Añadir Variables de Entorno** (ver .env.example)

3. **Deploy**

4. **Verificar**:
   - Containers → 3 corriendo
   - Logs → Sin errores

## 🔍 Health Checks

Cada servicio tiene health checks:

```yaml
# Backend
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8001/"]
  interval: 30s
  timeout: 10s
  retries: 3

# Frontend
healthcheck:
  test: ["CMD", "wget", "--quiet", "--tries=1", "http://localhost/"]
  interval: 30s
  timeout: 10s
  retries: 3

# MySQL
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root"]
  interval: 10s
  timeout: 5s
  retries: 5
```

## 📊 Volúmenes

### Persistencia de Datos

```yaml
volumes:
  mysql-data:  # Datos permanentes de MySQL
```

### Desarrollo (opcional)
```yaml
# Descomentar en docker-compose.yml para desarrollo:
# - ./backend:/app  # Hot reload del backend
```

## 🔧 Configuración Nginx

El nginx actúa como:
1. **Servidor web** para el frontend React
2. **Proxy reverso** para el backend API
3. **Optimizador** (compresión, cache)

### Rutas configuradas:
- `/` → Frontend React (SPA)
- `/api/*` → Backend FastAPI
- `/iniciar-encuesta` → Bridge endpoint
- `/guardar-encuesta` → Bridge endpoint
- `/colgar` → Bridge endpoint

## 🛠️ Troubleshooting Docker

### Backend no arranca
```bash
# Ver logs detallados
docker logs ausarta-backend -f

# Entrar al contenedor
docker exec -it ausarta-backend bash

# Verificar variables de entorno
docker exec ausarta-backend env | grep LIVEKIT
```

### Frontend no conecta al backend
```bash
# Verificar configuración nginx
docker exec ausarta-frontend cat /etc/nginx/conf.d/default.conf

# Testear nginx
docker exec ausarta-frontend nginx -t

# Recargar nginx
docker exec ausarta-frontend nginx -s reload
```

### MySQL no acepta conexiones
```bash
# Verificar estado
docker exec ausarta-mysql mysqladmin ping -uroot -p

# Conectar manualmente
docker exec -it ausarta-mysql mysql -uroot -p

# Ver logs
docker logs ausarta-mysql -f
```

## 📦 Optimizaciones Incluidas

### Multi-stage Build (Frontend)
- **Stage 1**: Build con Node.js (descartado después)
- **Stage 2**: Solo archivos estáticos + Nginx
- **Resultado**: Imagen ~30MB vs ~1GB

### .dockerignore
- Excluye `node_modules`, `dist`, `.git`, etc.
- Builds más rápidos y livianos

### Health Checks
- Detecta servicios no saludables
- Portainer puede auto-reiniciar
- Mejor observabilidad

## 🔒 Seguridad

### Variables de Entorno
- ✅ No incluidas en el repositorio
- ✅ Configuradas en Portainer
- ✅ .env.example como referencia

### Secretos (Opcional)
Para mayor seguridad en Portainer:
1. Create → Secrets
2. Añadir cada credential como secret
3. Referenciarlos en el stack

## 📈 Escalado (Futuro)

### Docker Swarm
```bash
# Convertir a Swarm
docker swarm init

# Deploy
docker stack deploy -c docker-compose.yml ausarta

# Escalar
docker service scale ausarta_backend=3
```

### Kubernetes (Avanzado)
Convertir docker-compose.yml con:
```bash
kompose convert
```

## ✅ Checklist Final

- [x] docker-compose.yml creado
- [x] Dockerfiles para frontend y backend
- [x] nginx.conf configurado
- [x] init-db.sql para MySQL
- [x] .env.example con todas las variables
- [x] .dockerignore en frontend y backend
- [x] Health checks configurados
- [x] Documentación completa
- [x] Subido a GitHub
- [x] Listo para Portainer

## 🎉 Estado

**TODO LISTO PARA PRODUCCIÓN**

Ahora puedes:
1. Ir a Portainer
2. Crear el stack desde GitHub
3. Configurar variables de entorno
4. Deploy
5. ¡Usar la aplicación!

---

**Creado**: 2026-02-06  
**Versión Docker**: Compose v3.8  
**Estado**: ✅ Completo y Funcional
