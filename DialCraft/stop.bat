@echo off
title DialCraft Shutdown
echo.
echo  ============================================
echo       DialCraft - Shutting Down
echo  ============================================
echo.

echo [1/3] Stopping ngrok...
taskkill /f /im ngrok.exe >nul 2>&1

echo [2/3] Stopping anything on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo [3/3] Closing launcher windows...
taskkill /f /fi "WINDOWTITLE eq DialCraft Server" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq DialCraft Call" >nul 2>&1

echo.
echo  ============================================
echo   All DialCraft processes stopped.
echo  ============================================
echo.
pause
