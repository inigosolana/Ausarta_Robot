#!/bin/bash

echo "========================================="
echo "  🔧 FORZANDO REBUILD COMPLETO"  
echo "========================================="
echo ""

# Detener contenedor
echo "[1/4] Deteniendo contenedor backend..."
docker stop ausarta-backend

# Eliminar contenedor
echo "[2/4] Eliminando contenedor viejo..."
docker rm ausarta-backend

# Rebuild sin caché
echo "[3/4] Reconstruyendo imagen SIN CACHÉ..."
cd /app
docker build --no-cache -t ausarta-backend:latest -f backend/Dockerfile backend/

# Recrear contenedor
echo "[4/4] Recreando contenedor..."
docker run -d \
  --name ausarta-backend \
  --restart unless-stopped \
  -p 8002:8001 \
  --network ausarta-network \
  -v sqlite-data:/app/data \
  -e LIVEKIT_URL="${LIVEKIT_URL}" \
  -e LIVEKIT_API_KEY="${LIVEKIT_API_KEY}" \
  -e LIVEKIT_API_SECRET="${LIVEKIT_API_SECRET}" \
  -e SIP_OUTBOUND_TRUNK_ID="${SIP_OUTBOUND_TRUNK_ID}" \
  -e DEEPGRAM_API_KEY="${DEEPGRAM_API_KEY}" \
  -e CARTESIA_API_KEY="${CARTESIA_API_KEY}" \
  -e GROQ_API_KEY="${GROQ_API_KEY}" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e GOOGLE_API_KEY="${GOOGLE_API_KEY}" \
  -e DB_PATH="/app/data/encuestas.db" \
  -e BRIDGE_SERVER_URL="http://127.0.0.1:8001" \
  ausarta-backend:latest

echo ""
echo "========================================="
echo "  ✅ REBUILD COMPLETO - Verificando logs..."
echo "========================================="

# Mostrar logs para verificar
docker logs -f ausarta-backend
