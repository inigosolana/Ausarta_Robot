@echo off
echo ========================================
echo  Ausarta Voice Agent Backend
echo ========================================
echo.
echo Iniciando servidor backend en puerto 8001...
echo.

cd backend
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8001
