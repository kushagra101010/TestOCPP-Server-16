@echo off
echo ========================================
echo    OCPP Server v1.6 - Starting...
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "ocpp_env" (
    echo ❌ ERROR: Virtual environment not found!
    echo Please run setup.bat first to install dependencies.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call ocpp_env\Scripts\activate.bat

REM Get local IP address
echo Detecting network configuration...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set "ip=%%a"
    goto :found
)
:found
set ip=%ip: =%

echo.
echo ========================================
echo    🚀 OCPP Server Starting! 🚀
echo ========================================
echo.
echo Server will be available at:
echo • Web Dashboard: http://localhost:8000
echo • Network Access: http://%ip%:8000
echo.
echo Chargers should connect to:
echo • WebSocket URL: ws://%ip%:8000/ws/CHARGER_ID
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Start the server
python -m backend.main

echo.
echo Server stopped.
pause 