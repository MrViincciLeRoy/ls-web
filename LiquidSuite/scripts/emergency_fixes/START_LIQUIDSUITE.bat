@echo off
REM LiquidSuite Smart Launcher - Auto-detects and chooses best mode

echo ===============================================
echo LiquidSuite - SMART LAUNCHER
echo ===============================================
echo.
echo Detecting available database options...
echo.

cd /d "%~dp0..\..\"

REM Check if PostgreSQL is available
psql -U postgres -d postgres -c "SELECT 1;" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL is RUNNING
    echo.
    echo Starting in ONLINE MODE (PostgreSQL)...
    set OFFLINE_MODE=false
    set DB_MODE=ONLINE
) else (
    echo ⚠️  PostgreSQL is NOT running
    echo.
    echo Starting in OFFLINE MODE (SQLite)...
    echo No PostgreSQL needed - using local SQLite database
    set OFFLINE_MODE=true
    set DB_MODE=OFFLINE
)

echo.
echo ===============================================
echo MODE: %DB_MODE%
echo ===============================================
echo.

set FLASK_ENV=development
set FLASK_APP=app.py

if "%DB_MODE%"=="OFFLINE" (
    echo 🔵 OFFLINE MODE
    echo 📁 Database: data/lsuite.db
) else (
    echo 🟢 ONLINE MODE  
    echo 💾 Database: PostgreSQL
)

echo 🌐 Server: http://localhost:5000
echo.
echo Press Ctrl+C to stop
echo ===============================================
echo.

python app.py

if %errorlevel% neq 0 (
    echo.
    echo ===============================================
    echo ERROR: Failed to start LiquidSuite
    echo ===============================================
    echo.
    echo Possible solutions:
    echo 1. Check if Python is installed: python --version
    echo 2. Install requirements: pip install -r requirements.txt
    echo 3. Check if port 5000 is available
    echo.
    echo For OFFLINE mode specifically:
    echo - Run: RUN_OFFLINE.bat
    echo.
    echo For ONLINE mode specifically:
    echo - Start PostgreSQL first
    echo - Run: RUN_ONLINE.bat
    echo.
    pause
)

pause
