@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Sophon Realtime Voice AI PL (Port 7869) - Adventists AI
echo ===============================================================================
echo   Sophon Realtime Voice AI PL (Port 7869)
echo   Model: Sophon-Realtime & DuplexJev Turn-Taking
echo   Detekcja Emocji (13 nastrojów), Ironii, Tagi Ekspresji i Obsługa Barge-in
echo   Lokalizacja: D:\AI-Tools\sophon-realtime
echo   Adres WebUI: http://localhost:7869
echo ===============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [BLAD] Nie znaleziono srodowiska .venv w %~dp0!
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo Uruchamianie polskiego interfejsu WebUI Sophon na porcie 7869...
python webui_server.py --port 7869 %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [BLAD] Aplikacja Sophon zakonczyla dzialanie z kodem bledu %ERRORLEVEL%.
)
cmd /k
