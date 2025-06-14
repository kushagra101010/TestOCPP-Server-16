@echo off
echo ========================================
echo    OCPP Demo Charger - Starting...
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

echo.
echo ========================================
echo    🔌 Demo Charger Starting! 🔌
echo ========================================
echo.
echo This demo charger will:
echo • Connect to the OCPP server
echo • Simulate charging sessions
echo • Send heartbeats and status updates
echo • Respond to remote commands
echo.
echo Make sure the OCPP server is running first!
echo Press Ctrl+C to stop the demo charger
echo ========================================
echo.

REM Start the demo charger
python demo_charger.py

echo.
echo Demo charger stopped.
pause 