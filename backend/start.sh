#!/bin/bash

# Script de inicio para backend (API + Agent)

echo "🚀 Iniciando Backend de Ausarta Robot..."
echo ""

# Iniciar el agente LiveKit en background
echo "🤖 Iniciando LiveKit Agent..."
python agent.py dev &
AGENT_PID=$!
echo "   ✅ Agent PID: $AGENT_PID"

# Esperar un poco para que el agente se inicie
sleep 3

# Iniciar la API
echo "🔧 Iniciando API FastAPI en puerto 8001..."
uvicorn api:app --host 0.0.0.0 --port 8001 &
API_PID=$!
echo "   ✅ API PID: $API_PID"

echo ""
echo "✅ Backend iniciado correctamente!"
echo "   - LiveKit Agent: PID $AGENT_PID"
echo "   - API: http://0.0.0.0:8001"
echo ""

# Mantener el contenedor vivo
wait -n

# Si cualquier proceso termina, terminar el otro también
kill $AGENT_PID $API_PID 2>/dev/null
