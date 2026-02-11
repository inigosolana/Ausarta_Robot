@echo off
echo ========================================
echo  REBUILD FORZADO - Aplicando cambios
echo ========================================
echo.

echo [1/3] Deteniendo contenedor...
docker stop ausarta-backend

echo.
echo [2/3] Reconstruyendo imagen SIN CACHE...
docker build --no-cache -t ausarta-backend-fixed ./backend

echo.
echo [3/3] Iniciando con nuevo codigo...
docker start ausarta-backend

echo.
echo ========================================
echo  ✅ LISTO! Cambios aplicados
echo ========================================
echo.
echo El filtro de modelos esta activo.
echo GPT-4o-mini-tts NO se usara mas.
echo.
pause
