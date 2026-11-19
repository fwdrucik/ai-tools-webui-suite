@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Mini-Omni2 Multimodal Live Studio (Port 7864)
echo ========================================================
echo   Mini-Omni2 - Multimodal Live Studio
echo   Kamera, Mikrofon, Rozmowa w Czasie Rzeczywistym (SNAC)
echo   Adres: http://localhost:7864
echo ========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [BLAD] Srodowisko wirtualne .venv nie zostalo znalezione w %~dp0!
    pause
    exit /b 1
)

echo Aktywacja srodowiska Mini-Omni2 (.venv)...
call .venv\Scripts\activate.bat

echo Otwieranie przegladarki na http://localhost:7864...
start "" http://localhost:7864

echo Uruchamianie serwera WebUI Mini-Omni2 (port 7864)...
python webui_server.py --port 7864 %*
pause
