@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Apple FastFrames Video AI Studio (Port 7866)
echo ========================================================
echo   Apple FastFrames: Autoregressive Video Diffusion Studio
echo   Text-to-Video, LingBot 3D World, Checkpoints & VRAM
echo   Adres: http://localhost:7866
echo ========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [BLAD] Srodowisko wirtualne .venv nie zostalo znalezione w %~dp0!
    pause
    exit /b 1
)

echo Aktywacja srodowiska FastFrames (.venv)...
call .venv\Scripts\activate.bat

echo Otwieranie przegladarki na http://localhost:7866...
start "" http://localhost:7866

echo Uruchamianie serwera WebUI FastFrames Video AI (port 7866)...
python webui_fastframes_pl.py --port 7866 %*
pause
