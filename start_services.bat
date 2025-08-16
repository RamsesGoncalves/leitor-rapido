@echo off
echo Iniciando servicos do Leitor Rapido...
echo.
echo IP da rede local: 192.168.1.13
echo Frontend: http://192.168.1.13:5173
echo Backend: http://192.168.1.13:8000
echo.

REM Inicia o backend
echo Iniciando backend...
start "Backend" cmd /k "cd /d %~dp0 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Aguarda um pouco antes de iniciar o frontend
timeout /t 3 /nobreak

REM Inicia o frontend
echo Iniciando frontend...
start "Frontend" cmd /k "cd /d %~dp0\web && npm run dev"

echo.
echo Servicos iniciados!
echo Acesse pelo celular: http://192.168.1.13:5173
pause

