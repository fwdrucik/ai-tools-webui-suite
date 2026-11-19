@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gemini Omni Multimodal Live Studio (Port 7865)
echo ========================================================
echo   Gemini Omni Multimodal Live Studio (Google GenAI)
echo   Rozmowa Multimodalna: Dzwiek, Obraz, Wizja na Zywo
echo   Adres: http://localhost:7865
echo ========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [BLAD] Nie znaleziono srodowiska .venv w %~dp0!
    echo Tworzenie srodowiska uv venv .venv --python 3.12...
    uv venv .venv --python 3.12
    call .venv\Scripts\activate.bat
    uv pip install google-genai pillow flask
) else (
    call .venv\Scripts\activate.bat
)

echo Otwieranie przegladarki na http://localhost:7865...
start "" http://localhost:7865

echo Uruchamianie serwera WebUI Gemini Live Studio (port 7865)...
python webui_gemini_pl.py --port 7865 %*
pause
