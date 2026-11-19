@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Haru Full-Duplex Voice Studio PL (Port 8998) - Higurashi AI
echo ===============================================================================
echo   Haru Full-Duplex Voice Studio PL (Port 8998)
echo   Model: Higurashi AI Haru-4B VibeVoice
echo   End-to-End Speech-to-Speech (65ms opóźnienia, pełny dupleks, język polski)
echo   Lokalizacja: D:\AI-Tools\Haru
echo   Adres Panelu: http://localhost:8998
echo ===============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [BLAD] Srodowisko wirtualne .venv nie zostalo znalezione w %~dp0!
    echo Uruchom 'uv venv .venv --python 3.11' i zainstaluj zaleznosci.
    pause
    exit /b 1
)

echo Aktywacja srodowiska Haru (.venv)...
call .venv\Scripts\activate.bat

echo Uruchamianie Polskiego Panelu Kontrolnego Haru na porcie 8998...
python control_center_pl.py --port 8998 --language pl %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [INFO] Serwer Haru zakonczyl dzialanie z kodem %ERRORLEVEL%.
)
cmd /k
