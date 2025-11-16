@echo off
REM Run LiquidSuite in ONLINE MODE (PostgreSQL)

echo ===============================================
echo LiquidSuite - ONLINE MODE (PostgreSQL)
echo ===============================================
echo.
echo This will run LiquidSuite using PostgreSQL database
echo PostgreSQL server must be running!
echo.
echo ===============================================
echo.

cd /d "%~dp0..\..\"

REM Set online mode (default)
set OFFLINE_MODE=false
set FLASK_ENV=development
set FLASK_APP=app.py

echo Checking PostgreSQL connection...
echo.

REM Try to connect to PostgreSQL
psql -U postgres -d postgres -c "SELECT 1;" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Cannot connect to PostgreSQL!
    echo.
    echo Please start PostgreSQL first:
    echo 1. Run START_POSTGRES.bat as Administrator
    echo 2. Or start it manually via services.msc
    echo.
    echo Alternatively, use OFFLINE MODE:
    echo - Double-click RUN_OFFLINE.bat
    echo.
    pause
    exit /b 1
)

echo ✅ PostgreSQL is running!
echo.
echo Starting LiquidSuite in ONLINE MODE...
echo.
echo 🟢 ONLINE MODE ACTIVATED
echo 💾 Using PostgreSQL database
echo 🌐 Server will start on http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.
echo ===============================================

python app.py

pause
