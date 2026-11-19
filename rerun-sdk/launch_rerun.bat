@echo off
cd /d "%~dp0"
title Rerun 3D Visualizer Studio (Port 7867)
echo ========================================================
echo   Rerun 3D Multimodal Visualizer Studio (v0.43.2)
echo   Lokalizacja: D:\AI-Tools\rerun-sdk
echo   Port WebUI:      http://localhost:7867
echo   Port Web Viewer: http://localhost:9097
echo   Port gRPC:       http://localhost:9877
echo ========================================================
echo.

set "PATH=%APPDATA%\Python\Python314\Scripts;%USERPROFILE%\.local\bin;%PATH%"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [BLAD] Nie znaleziono interpretera Python!
    pause
    exit /b 1
)

echo Uruchamianie Rerun 3D Visualizer WebUI na porcie 7867...
start "" http://localhost:7867
python webui_server.py
cmd /k
