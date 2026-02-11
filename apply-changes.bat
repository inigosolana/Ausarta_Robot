@echo off
echo ========================================
echo  Aplicando cambios RAPIDO (sin rebuild)
echo ========================================
echo.

REM Cambiar a Groq en la base de datos
echo [1/2] Cambiando a modelo GRATIS (Groq)...
docker exec ausarta-backend python /app/switch_to_groq.py

REM Reiniciar contenedor para aplicar cambios
echo.
echo [2/2] Reiniciando backend...
docker restart ausarta-backend

echo.
echo ========================================
echo  ✅ Cambios aplicados!
echo ========================================
echo.
echo - Modelo: Groq Llama 3.3 (GRATIS)
echo - Hot Reload: ACTIVADO
echo.
echo Los proximos cambios en codigo se aplicaran INSTANTANEAMENTE.
pause
