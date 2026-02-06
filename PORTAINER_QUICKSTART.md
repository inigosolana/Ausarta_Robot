# 🚀 GUÍA RÁPIDA: Desplegar en Portainer

## ⚡ Pasos Rápidos (5 minutos)

### 1️⃣ En Portainer

1. **Stacks** → **Add Stack**
2. **Name**: `ausarta-robot`
3. **Build method**: **Repository**
4. **Repository URL**: `https://github.com/inigosolana/Ausarta_Robot`
5. **Compose path**: `docker-compose.yml`

### 2️⃣ Variables de Entorno

Haz clic en **"Add environment variable"** y añade estas (IMPORTANTES):

**⚠️ IMPORTANTE: Usa tus propias credenciales, estos son solo ejemplos**

```
LIVEKIT_URL=wss://tu-proyecto.livekit.cloud
LIVEKIT_API_KEY=tu_livekit_api_key
LIVEKIT_API_SECRET=tu_livekit_api_secret
SIP_OUTBOUND_TRUNK_ID=ST_tu_trunk_id
DEEPGRAM_API_KEY=tu_deepgram_api_key
CARTESIA_API_KEY=tu_cartesia_api_key
GROQ_API_KEY=tu_groq_api_key
OPENAI_API_KEY=tu_openai_api_key
```

**💡 Tip**: Copia las credenciales desde tu archivo `backend/.env` local

**ℹ️ Nota**: Ya NO necesitas variables de MySQL. Ahora usamos SQLite (base de datos local en archivo)

### 3️⃣ Deploy

**Deploy the stack** → Espera 5-10 minutos

### 4️⃣ Verificar

**Containers** →  Deberías ver 2 contenedores:
- ✅ `ausarta-frontend` (puerto 80)
- ✅ `ausarta-backend` (puerto 8001)

**ℹ️ Nota**: Ya no hay contenedor MySQL. Los datos se guardan en SQLite dentro del backend.

### 5️⃣ Acceder

🌐 **Frontend**: http://tu-servidor
📡 **API**: http://tu-servidor:8001/docs

---

## 📋 Checklist Rápido

- [ ] Portainer instalado y corriendo
- [ ] Repositorio GitHub accesible
- [ ] Variables de entorno configuradas (solo AI y LiveKit)
- [ ] Stack desplegado sin errores
- [ ] 2 contenedores en estado "running"
- [ ] Frontend carga correctamente
- [ ] Backend API responde en /docs

---

## 🆘 Problemas Comunes

### ❌ "Build failed"
→ Revisa logs del contenedor que falló
→ Verifica que todas las variables estén configuradas

### ❌ "Backend unhealthy"
→ Ve a Logs del backend
→ Verifica credenciales de LiveKit y DB

### ❌ "Frontend no carga"
→ Ve a Logs del frontend
→ Verifica que el backend esté running

### ❌ "No conecta a MySQL"
→ Ve a Logs de MySQL
→ Verifica MYSQL_ROOT_PASSWORD

---

## 📞 URLs de Acceso

Reemplaza `tu-servidor` con tu IP o dominio:

- **Frontend**: http://tu-servidor
- **API Backend**: http://tu-servidor:8001
- **API Docs**: http://tu-servidor:8001/docs
- **Portainer**: http://tu-servidor:9000

---

## 🔄 Actualizar el Stack

1. **Stacks** → **ausarta-robot**
2. **Pull and redeploy**
3. Espera ~2 minutos

---

## 📊 Ver Logs en Tiempo Real

1. **Containers** → Clic en el contenedor
2. **Logs**
3. Habilita **Auto-refresh**

---

## 🎉 ¡Listo!

Tu plataforma está corriendo. Ahora puedes:
1. Ir a Voice Agents
2. Crear un agente "Outbound"
3. Lanzar una llamada con el número que quieras

**Documentación completa**: Ver `DOCKER_DEPLOYMENT.md`
