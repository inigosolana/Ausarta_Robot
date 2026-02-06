# 🐳 Despliegue en Docker con Portainer

Guía completa para desplegar Ausarta Robot en Docker usando Portainer.

## 📦 Estructura Docker

```
ausarta-robot-voice-agent-platform/
├── docker-compose.yml          # Orquestación de servicios
├── .env.example                # Variables de entorno
├── Dockerfile                  # Frontend (React + Nginx)
├── nginx.conf                  # Configuración Nginx
├── init-db.sql                 # Inicialización MySQL
└── backend/
    ├── Dockerfile              # Backend (API + Agent)
    └── start.sh                # Script de inicio
```

## 🚀 Opción 1: Despliegue en Portainer (Recomendado)

### Paso 1: Preparar el archivo .env

1. Copia `.env.example` a `.env`:
```bash
cp .env.example .env
```

2. Edita `.env` con tus credenciales:
```env
LIVEKIT_URL=wss://tu-proyecto.livekit.cloud
LIVEKIT_API_KEY=tu_api_key
LIVEKIT_API_SECRET=tu_api_secret
SIP_OUTBOUND_TRUNK_ID=ST_tu_trunk_id
DEEPGRAM_API_KEY=tu_deepgram_key
CARTESIA_API_KEY=tu_cartesia_key
GROQ_API_KEY=tu_groq_key
DB_USER=ausarta_user
DB_PASSWORD=tu_password_seguro
DB_NAME=encuestas_ausarta
MYSQL_ROOT_PASSWORD=root_password_muy_seguro
```

### Paso 2: En Portainer

1. **Accede a Portainer** (ej: http://tu-servidor:9000)

2. **Navega a Stacks** en el menú lateral

3. **Haz clic en "Add Stack"**

4. **Configura el Stack:**
   - **Name**: `ausarta-robot`
   - **Build method**: Selecciona **"Repository"**
   
5. **Configuración del Repositorio:**
   - **Repository URL**: `https://github.com/inigosolana/Ausarta_Robot`
   - **Repository reference**: `refs/heads/master`
   - **Compose path**: `docker-compose.yml`

6. **Variables de Entorno:**
   
   Haz clic en "Add environment variable" y añade cada una:
   
   | Variable | Valor |
   |----------|-------|
   | `LIVEKIT_URL` | `wss://tu-proyecto.livekit.cloud` |
   | `LIVEKIT_API_KEY` | `tu_api_key` |
   | `LIVEKIT_API_SECRET` | `tu_api_secret` |
   | `SIP_OUTBOUND_TRUNK_ID` | `ST_tu_trunk_id` |
   | `DEEPGRAM_API_KEY` | `tu_deepgram_key` |
   | `CARTESIA_API_KEY` | `tu_cartesia_key` |
   | `GROQ_API_KEY` | `tu_groq_key` |
   | `OPENAI_API_KEY` | `tu_openai_key` |
   | `DB_HOST` | `mysql` |
   | `DB_USER` | `ausarta_user` |
   | `DB_PASSWORD` | `tu_password_seguro` |
   | `DB_NAME` | `encuestas_ausarta` |
   | `MYSQL_ROOT_PASSWORD` | `root_password_muy_seguro` |

7. **Haz clic en "Deploy the stack"**

8. **Espera a que se construyan los contenedores** (puede tardar 5-10 minutos la primera vez)

### Paso 3: Verificar el Despliegue

1. En Portainer, ve a "Containers"
2. Deberías ver 3 contenedores corriendo:
   - ✅ `ausarta-frontend` (puerto 80)
   - ✅ `ausarta-backend` (puerto 8001)
   - ✅ `ausarta-mysql` (puerto 3306)

3. **Accede a la aplicación:**
   - Frontend: http://tu-servidor:80
   - Backend API: http://tu-servidor:8001
   - API Docs: http://tu-servidor:8001/docs

## 🐳 Opción 2: Despliegue Local con Docker Compose

### Requisitos previos:
- Docker instalado
- Docker Compose instalado

### Pasos:

1. **Clonar el repositorio:**
```bash
git clone https://github.com/inigosolana/Ausarta_Robot.git
cd Ausarta_Robot
```

2. **Crear archivo .env:**
```bash
cp .env.example .env
# Edita .env con tus credenciales
nano .env
```

3. **Construir y ejecutar:**
```bash
docker-compose up -d --build
```

4. **Ver logs:**
```bash
# Todos los servicios
docker-compose logs -f

# Solo backend
docker-compose logs -f backend

# Solo frontend
docker-compose logs -f frontend
```

5. **Detener servicios:**
```bash
docker-compose down
```

6. **Detener y eliminar volúmenes (limpieza completa):**
```bash
docker-compose down -v
```

## 📊 Servicios y Puertos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **Frontend** | 80 | Interfaz web React |
| **Backend** | 8001 | API FastAPI + LiveKit Agent |
| **MySQL** | 3306 | Base de datos |

## 🔍 Verificación de Health Checks

Los contenedores tienen health checks configurados:

```bash
# Ver estado de salud
docker ps

# Detalles del health check
docker inspect ausarta-backend --format='{{json .State.Health}}' | jq
docker inspect ausarta-frontend --format='{{json .State.Health}}' | jq
docker inspect ausarta-mysql --format='{{json .State.Health}}' | jq
```

## 🛠️ Troubleshooting

### Backend no inicia

**Problema**: El backend muestra errores de conexión

**Solución**:
```bash
# Ver logs del backend
docker logs ausarta-backend -f

# Verificar variables de entorno
docker exec ausarta-backend env | grep LIVEKIT

# Reiniciar contenedor
docker restart ausarta-backend
```

### Frontend no carga

**Problema**: La página web no responde

**Solución**:
```bash
# Ver logs del frontend
docker logs ausarta-frontend -f

# Verificar nginx
docker exec ausarta-frontend nginx -t

# Reiniciar contenedor
docker restart ausarta-frontend
```

### MySQL no conecta

**Problema**: Error de conexión a base de datos

**Solución**:
```bash
# Ver logs de MySQL
docker logs ausarta-mysql -f

# Conectar manualmente
docker exec -it ausarta-mysql mysql -u root -p

# Verificar base de datos
docker exec ausarta-mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SHOW DATABASES;"
```

### Problemas de red

**Problema**: Los contenedores no se comunican

**Solución**:
```bash
# Listar redes
docker network ls

# Inspeccionar red
docker network inspect ausarta_ausarta-network

# Recrear la red
docker-compose down
docker-compose up -d
```

## 🔄 Actualizar el Stack

### Método 1: Desde Portainer

1. Ve a "Stacks" → "ausarta-robot"
2. Haz clic en "Pull and redeploy"
3. Espera a que se actualice

### Método 2: Desde línea de comandos

```bash
cd Ausarta_Robot
git pull origin master
docker-compose down
docker-compose up -d --build
```

## 📝 Logs y Monitoreo

### Ver logs en tiempo real

```bash
# Todos los servicios
docker-compose logs -f

# Solo errores
docker-compose logs -f | grep ERROR

# Últimas 100 líneas
docker-compose logs --tail=100
```

### Monitoreo de recursos

```bash
# Ver uso de recursos
docker stats

# Ver procesos dentro del contenedor
docker top ausarta-backend
docker top ausarta-frontend
```

## 🧹 Mantenimiento

### Limpiar imágenes antiguas

```bash
# Eliminar imágenes no utilizadas
docker image prune -a

# Eliminar volúmenes no utilizados
docker volume prune
```

### Backup de la base de datos

```bash
# Crear backup
docker exec ausarta-mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} encuestas_ausarta > backup.sql

# Restaurar backup
docker exec -i ausarta-mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} encuestas_ausarta < backup.sql
```

## 📈 Escalado

### Aumentar recursos

Edita `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Múltiples replicas (con Docker Swarm)

```bash
# Inicializar swarm
docker swarm init

# Desplegar stack
docker stack deploy -c docker-compose.yml ausarta

# Escalar servicio
docker service scale ausarta_backend=3
```

## 🔒 Seguridad

### Variables de entorno en Portainer

**IMPORTANTE**: No expongas las variables de entorno en el repositorio.

En Portainer:
1. Ve a "Secrets"
2. Crea secretos para cada credencial sensible
3. Referéncialos en el stack

### HTTPS con Let's Encrypt

Añade un reverse proxy (Traefik o Nginx Proxy Manager):

```yaml
services:
  traefik:
    image: traefik:v2.9
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./traefik.yml:/traefik.yml
      - ./acme.json:/acme.json
```

## ✅ Checklist de Despliegue

- [ ] Archivo `.env` configurado con todas las credenciales
- [ ] Puertos 80 y 8001 disponibles
- [ ] Docker y Docker Compose instalados
- [ ] Variables de entorno añadidas en Portainer
- [ ] Stack desplegado correctamente
- [ ] 3 contenedores corriendo (frontend, backend, mysql)
- [ ] Health checks en estado "healthy"
- [ ] Frontend accesible en http://tu-servidor
- [ ] Backend API accesible en http://tu-servidor:8001
- [ ] Base de datos inicializada correctamente

## 🎉 ¡Listo!

Tu aplicación Ausarta Robot está ahora corriendo en Docker y lista para usar.

**URLs de acceso:**
- 🌐 Frontend: http://tu-servidor
- 🔧 Backend API: http://tu-servidor:8001
- 📚 API Docs: http://tu-servidor:8001/docs
