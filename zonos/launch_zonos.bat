@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Zonos Voice Studio PL (Port 7860) - Zyphra TTS & Voice Cloning
echo ===============================================================================
echo   Zonos Voice Studio PL (Port 7860)
echo   Model: Zyphra Zonos-v0.1 MoE Transformer (800M)
echo   8-Wymiarowa Kontrola Emocji, Suwaki Akustyczne i Klonowanie Glosu
echo   Lokalizacja: D:\AI-Tools\Zonos
echo   Adres WebUI: http://localhost:7860
echo ===============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [BLAD] Nie znaleziono srodowiska .venv w %~dp0!
    echo Tworzenie srodowiska uv sync...
    uv sync
)

call .venv\Scripts\activate.bat

echo Uruchamianie polskiego interfejsu WebUI Zonos na porcie 7860...
python webui_zonos_pl.py --port 7860 %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [BLAD] Aplikacja zakonczyla dzialanie z kodem bledu %ERRORLEVEL%.
)
cmd /k
