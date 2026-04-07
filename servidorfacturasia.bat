@echo off
cd /d C:\CAMTOM

echo ====================================
echo Iniciando servidor FastAPI (Uvicorn)
echo ====================================
echo.

:: Lanza el servidor
python -m uvicorn consolidado:app --host 0.0.0.0 --port 8000

echo.
echo ------------------------------------
echo El servidor se ha detenido o falló.
echo ------------------------------------
pause
