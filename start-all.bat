@echo off
echo ========================================
echo  Ausarta Voice Agent - FULL STACK
echo ========================================
echo.
echo Iniciando todos los servicios...
echo.

REM Iniciar el agente LiveKit
echo [1/3] Iniciando agente LiveKit...
start "LiveKit Agent" cmd /k "cd backend && python agent.py dev"

timeout /t 3 /nobreak > nul

REM Iniciar el backend API
echo [2/3] Iniciando Backend API...
start "Backend API" cmd /k "cd backend && python -m uvicorn api:app --reload --host 0.0.0.0 --port 8001"

timeout /t 3 /nobreak > nul

REM Iniciar el frontend
echo [3/3] Iniciando Frontend...
start "Frontend" cmd /k "npm run dev"

echo.
echo ========================================
echo  ✅ Todos los servicios iniciados!
echo ========================================
echo.
echo - LiveKit Agent: Running
echo - Backend API: http://localhost:8001
echo - Frontend: http://localhost:5173
echo.
echo Presiona cualquier tecla para cerrar este mensaje...
pause > nul
