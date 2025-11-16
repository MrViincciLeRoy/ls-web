@echo off
REM Complete LiquidSuite Setup and Launcher

echo ╔═══════════════════════════════════════════════════════════════╗
echo ║         LiquidSuite - Complete Setup ^& Launcher              ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

REM Check if database exists
if exist "data\lsuite.db" (
    echo ✅ Database exists: data\lsuite.db
    echo.
    echo Skipping initialization...
    echo.
    goto :start_app
)

echo 📋 First-time setup detected!
echo.
echo This script will:
echo  1. Create database tables
echo  2. Seed default categories
echo  3. Create your admin user
echo  4. Start the application
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

REM Run initialization
echo Step 1: Initializing database...
echo.

python init_offline_db.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Database initialization failed!
    echo.
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo.

:start_app
echo 🚀 Starting LiquidSuite...
echo.
echo 🔵 Mode: OFFLINE (SQLite)
echo 📁 Database: data\lsuite.db
echo 🌐 URL: http://localhost:5000
echo.
echo The browser will open automatically...
echo Press Ctrl+C to stop the server
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

REM Start the app in background and open browser
start "" "http://localhost:5000"
python app.py

pause
