@echo off
REM Quick Offline Mode Starter for LiquidSuite

echo ===============================================
echo LiquidSuite - OFFLINE MODE (SQLite)
echo ===============================================
echo.

cd /d "%~dp0"

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo.
    echo Please ensure the .env file exists with:
    echo OFFLINE_MODE=true
    echo.
    pause
    exit /b 1
)

REM Verify python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.10 or higher
    echo.
    pause
    exit /b 1
)

echo ✅ Configuration found
echo 🔵 Starting in OFFLINE MODE...
echo 📁 Database: data\lsuite.db
echo 🌐 URL: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ===============================================
echo.

python app.py

pause
