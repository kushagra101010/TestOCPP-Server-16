@echo off
echo ========================================
echo   OCPP 1.6 Server v2.2.0 - Starting...
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
echo 🔧 Activating virtual environment...
call ocpp_env\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ ERROR: Failed to activate virtual environment!
    echo Please check if ocpp_env is properly installed.
    echo.
    pause
    exit /b 1
)

REM Get local IP address
echo 🌐 Detecting network configuration...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set "ip=%%a"
    goto :found
)
:found
set ip=%ip: =%

echo.
echo ========================================
echo   🚀 OCPP 1.6 Server v2.2.0 Starting! 🚀
echo ========================================
echo.
echo ✅ Virtual environment: ACTIVATED
echo ✅ Server version: v2.2.0 (OCPP 1.6 Protocol)
echo ✅ Enhanced UI ^& multi-charger support
echo.
echo 🌐 Server will be available at:
echo • Web Dashboard: http://localhost:8000
echo • Network Access: http://%ip%:8000
echo.
echo 🔌 Chargers should connect to:
echo • WebSocket URL: ws://%ip%:8000/ws/CHARGER_ID
echo • Protocol: OCPP 1.6
echo.
echo 📋 Features Available:
echo • Remote Start/Stop Transactions
echo • Local List Management (Clear, Get Version, Generate Random)
echo • Configuration Management
echo • Data Transfer ^& Logging
echo • Real-time Connection Status
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Start the server
echo 🚀 Starting OCPP 1.6 Server v2.2.0...
python -m backend.main

echo.
echo 🛑 Server stopped.
echo Thank you for using OCPP 1.6 Server v2.2.0!
pause 