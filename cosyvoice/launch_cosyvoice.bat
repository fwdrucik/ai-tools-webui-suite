@echo off
chcp 65001 >nul
cd /d "%~dp0"
title CosyVoice 2 Studio PL (Port 7862) - FunAudioLLM & QwenAudio
echo ===============================================================================
echo   CosyVoice 2 Studio PL (Port 7862)
echo   Model: FunAudioLLM CosyVoice 2 (Multi-Lingual & Expressive TTS)
echo   Błyskawiczne Klonowanie 3-5s Zero-Shot, Whisper ASR, Cross-Lingual & Instruct
echo   Lokalizacja: D:\AI-Tools\CosyVoice
echo   Adres WebUI: http://localhost:7862
echo ===============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [BLAD] Srodowisko wirtualne .venv nie zostalo znalezione w %~dp0!
    pause
    exit /b 1
)

echo Aktywacja srodowiska CosyVoice (.venv)...
call .venv\Scripts\activate.bat

echo Uruchamianie polskiego interfejsu WebUI CosyVoice na porcie 7862...
python webui_cosyvoice_pl.py --port 7862 %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [BLAD] Aplikacja CosyVoice zakonczyla dzialanie z kodem bledu %ERRORLEVEL%.
)
cmd /k
