@echo off
title DialCraft Launcher
echo.
echo  ============================================
echo       DialCraft - AI Voice Agent Launcher
echo  ============================================
echo.

:: ── Step 1: Start the AI Server ──────────────────────
echo [1/3] Starting AI Server...
start "DialCraft Server" cmd /k "conda activate shrishtiai && cd /d %~dp0 && python main.py"

:: Wait for the server to boot (Whisper + Kokoro loading)
echo       Waiting 15 seconds for models to load...
timeout /t 15 /nobreak > nul

:: ── Step 2: Start ngrok tunnel ───────────────────────
echo [2/3] Starting ngrok tunnel...
start "ngrok" cmd /k "cd /d %~dp0 && ngrok http 8000"

:: Wait for ngrok to establish the tunnel
echo       Waiting 5 seconds for ngrok...
timeout /t 5 /nobreak > nul

:: ── Step 3: Place the call ───────────────────────────
echo [3/3] Placing call to your phone...
echo.
start "DialCraft Call" cmd /k "conda activate shrishtiai && cd /d %~dp0 && python call_me.py && echo. && echo Your phone should be ringing! Pick up to talk to the AI. && pause"

echo.
echo  ============================================
echo   All systems launched! Check the 3 windows.
echo   - Server  : AI models + WebSocket
echo   - ngrok   : Public tunnel
echo   - Call    : Dialing your phone
echo  ============================================
echo.
pause
