@echo off
cd /d "%~dp0"
title AutoSwarm Multi-Agent WebUI (Port 7868)
echo ========================================================
echo   AutoSwarm 2.0.0 - Multi-Agent Swarm Orchestrator
echo   Lokalizacja: D:\AI-Tools\AutoSwarm
echo   Port WebUI:  http://localhost:7868
echo   Srodowisko:  .venv (Python 3.12)
echo ========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [BLAD] Nie znaleziono srodowiska .venv w %~dp0!
    pause
    exit /b 1
)

echo Aktywacja dedykowanego srodowiska wirtualnego .venv...
call .venv\Scripts\activate.bat

echo Uruchamianie AutoSwarm Multi-Agent WebUI na porcie 7868...
start "" http://localhost:7868
python webui_server.py
cmd /k
