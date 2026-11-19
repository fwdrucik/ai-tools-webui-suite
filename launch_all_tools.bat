@echo off
chcp 65001 >nul
cd /d "%~dp0"
title AI-Tools Master Launcher — 9 Desktopowych Narzedzi AI

echo ===============================================================================
echo                AI-TOOLS MASTER LAUNCHER - EKOSYSTEM NARZEDZI AI
echo           Zintegrowane srodowisko 9 aplikacji ze wsparciem jezyka polskiego
echo ===============================================================================
echo.

if "%1"=="--hub" goto launch_hub
if "%1"=="--all" goto launch_all
if "%1"=="--test" goto run_tests

:menu
echo Wybierz opcje uruchomienia:
echo.
echo   [1]  Uruchom Master Hub Portal (Port 7800)
echo   [2]  Uruchom Wszystkie 9 Narzedzi AI + Master Hub
echo   -----------------------------------------------------------------------------
echo   [3]  1. Zonos Voice Studio (Port 7860)
echo   [4]  2. Haru Full-Duplex Voice (Port 8998)
echo   [5]  3. CosyVoice Studio (Port 7862)
echo   [6]  4. Mini-Omni2 Multimodal Live (Port 7864)
echo   [7]  5. Gemini Omni Live Studio (Port 7865)
echo   [8]  6. Apple FastFrames Video AI (Port 7866)
echo   [9]  7. Rerun 3D Visualizer (Port 7867)
echo   [10] 8. AutoSwarm Multi-Agent (Port 7868)
echo   [11] 9. Sophon Realtime Voice AI (Port 7869)
echo   -----------------------------------------------------------------------------
echo   [12] Uruchom Pelny Pakiet Testow E2E (Tier 1-4)
echo   [13] Wyjscie
echo.
set /p opt="Wybierz numer [1-13]: "

if "%opt%"=="1" goto launch_hub
if "%opt%"=="2" goto launch_all
if "%opt%"=="3" goto tool_zonos
if "%opt%"=="4" goto tool_haru
if "%opt%"=="5" goto tool_cosyvoice
if "%opt%"=="6" goto tool_mini_omni2
if "%opt%"=="7" goto tool_gemini_live
if "%opt%"=="8" goto tool_fastframes
if "%opt%"=="9" goto tool_rerun
if "%opt%"=="10" goto tool_autoswarm
if "%opt%"=="11" goto tool_sophon
if "%opt%"=="12" goto run_tests
if "%opt%"=="13" goto end

echo [BLAD] Nieznana opcja. Wybierz ponownie.
goto menu

:launch_hub
echo.
echo ===============================================================================
echo   Uruchamianie AI-Tools Master Hub Portal na porcie 7800...
echo   Interfejs bedzie dostepny pod adresem: http://localhost:7800
echo ===============================================================================
start "AI-Tools Master Hub (Port 7800)" cmd /k "python hub\hub_server.py --port 7800"
timeout /t 2 >nul
start http://localhost:7800
echo Master Hub uruchomiony pomyslnie w osobnym oknie.
pause
goto end

:launch_all
echo.
echo ===============================================================================
echo   Uruchamianie calego ekosystemu AI-Tools (9 Narzedzi + Master Hub)...
echo ===============================================================================
echo [1/10] Uruchamianie Master Hub Portal (Port 7800)...
start "AI-Tools Master Hub (Port 7800)" cmd /k "python hub\hub_server.py --port 7800"

echo [2/10] Uruchamianie Zonos Voice Studio (Port 7860)...
start "Zonos Voice Studio (Port 7860)" /d "D:\AI-Tools\Zonos" cmd /c "launch_zonos.bat"

echo [3/10] Uruchamianie Haru Full-Duplex Voice (Port 8998)...
start "Haru Full-Duplex Voice (Port 8998)" /d "D:\AI-Tools\Haru" cmd /c "launch_haru.bat"

echo [4/10] Uruchamianie CosyVoice Studio (Port 7862)...
start "CosyVoice Studio (Port 7862)" /d "D:\AI-Tools\CosyVoice" cmd /c "launch_cosyvoice.bat"

echo [5/10] Uruchamianie Mini-Omni2 Multimodal Live (Port 7864)...
start "Mini-Omni2 Multimodal Live (Port 7864)" /d "D:\AI-Tools\mini-omni2" cmd /c "launch_mini_omni2.bat"

echo [6/10] Uruchamianie Gemini Omni Live Studio (Port 7865)...
start "Gemini Omni Live Studio (Port 7865)" /d "D:\AI-Tools\GeminiLiveStudio" cmd /c "launch_gemini_live.bat"

echo [7/10] Uruchamianie Apple FastFrames Video AI (Port 7866)...
start "Apple FastFrames Video AI (Port 7866)" /d "D:\AI-Tools\ml-fastframes" cmd /c "launch_fastframes.bat"

echo [8/10] Uruchamianie Rerun 3D Visualizer (Port 7867)...
start "Rerun 3D Visualizer (Port 7867)" /d "D:\AI-Tools\rerun-sdk" cmd /c "launch_rerun.bat"

echo [9/10] Uruchamianie AutoSwarm Multi-Agent (Port 7868)...
start "AutoSwarm Multi-Agent (Port 7868)" /d "D:\AI-Tools\AutoSwarm" cmd /c "launch_autoswarm.bat"

echo [10/10] Uruchamianie Sophon Realtime Voice AI (Port 7869)...
start "Sophon Realtime Voice AI (Port 7869)" /d "D:\AI-Tools\sophon-realtime" cmd /c "launch_sophon.bat"

echo.
echo Wszystkie 10 procesow zainicjalizowano. Otwieranie Master Hub...
timeout /t 3 >nul
start http://localhost:7800
pause
goto end

:tool_zonos
start "Zonos Voice Studio (Port 7860)" /d "D:\AI-Tools\Zonos" cmd /c "launch_zonos.bat"
goto menu

:tool_haru
start "Haru Full-Duplex Voice (Port 8998)" /d "D:\AI-Tools\Haru" cmd /c "launch_haru.bat"
goto menu

:tool_cosyvoice
start "CosyVoice Studio (Port 7862)" /d "D:\AI-Tools\CosyVoice" cmd /c "launch_cosyvoice.bat"
goto menu

:tool_mini_omni2
start "Mini-Omni2 Multimodal Live (Port 7864)" /d "D:\AI-Tools\mini-omni2" cmd /c "launch_mini_omni2.bat"
goto menu

:tool_gemini_live
start "Gemini Omni Live Studio (Port 7865)" /d "D:\AI-Tools\GeminiLiveStudio" cmd /c "launch_gemini_live.bat"
goto menu

:tool_fastframes
start "Apple FastFrames Video AI (Port 7866)" /d "D:\AI-Tools\ml-fastframes" cmd /c "launch_fastframes.bat"
goto menu

:tool_rerun
start "Rerun 3D Visualizer (Port 7867)" /d "D:\AI-Tools\rerun-sdk" cmd /c "launch_rerun.bat"
goto menu

:tool_autoswarm
start "AutoSwarm Multi-Agent (Port 7868)" /d "D:\AI-Tools\AutoSwarm" cmd /c "launch_autoswarm.bat"
goto menu

:tool_sophon
start "Sophon Realtime Voice AI (Port 7869)" /d "D:\AI-Tools\sophon-realtime" cmd /c "launch_sophon.bat"
goto menu

:run_tests
echo.
echo ===============================================================================
echo   Uruchamianie 4-poziomowego pakietu testow E2E (D:\AI-Tools\tests\e2e_suite.py)...
echo ===============================================================================
python tests\e2e_suite.py
echo.
pause
goto menu

:end
exit /b 0
