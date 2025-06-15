@echo off
echo ========================================
echo   OCPP 1.6 Server v2.2.0 - Setup Script
echo ========================================
echo.

REM Check if Python is installed
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

python --version
echo ✅ Python found!
echo.

REM Remove existing virtual environment to ensure clean install
echo [2/6] Removing existing virtual environment...
if exist "ocpp_env" (
    echo Removing existing virtual environment for clean installation...
    rmdir /s /q "ocpp_env"
    echo ✅ Old virtual environment removed!
) else (
    echo No existing virtual environment found.
)
echo.

REM Create virtual environment
echo [3/6] Creating virtual environment...
python -m venv ocpp_env
echo ✅ Virtual environment created!
echo.

REM Activate virtual environment
echo [4/6] Activating virtual environment...
call ocpp_env\Scripts\activate.bat

REM Upgrade pip
echo [5/6] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo [6/6] Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt

echo.
echo ========================================
echo    🎉 Installation Complete! 🎉
echo ========================================
echo.
echo Next steps:
echo 1. Run: start_server.bat
echo 2. Open browser to: http://localhost:8000
echo 3. Connect your chargers to: ws://YOUR_IP:8000/ws/CHARGER_ID
echo.
echo For demo purposes, you can also run: demo_charger.bat
echo.
pause 