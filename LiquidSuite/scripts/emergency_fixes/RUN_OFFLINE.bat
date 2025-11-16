@echo off
REM Run LiquidSuite in OFFLINE MODE (SQLite - No PostgreSQL needed)

echo ===============================================
echo LiquidSuite - OFFLINE MODE (SQLite)
echo ===============================================
echo.
echo This will run LiquidSuite using SQLite database
echo No PostgreSQL server required!
echo.
echo Database location: data/lsuite.db
echo ===============================================
echo.

cd /d "%~dp0..\..\"

REM Set offline mode
set OFFLINE_MODE=true
set FLASK_ENV=development
set FLASK_APP=app.py

echo Starting LiquidSuite in OFFLINE MODE...
echo.
echo 🔵 OFFLINE MODE ACTIVATED
echo 📁 Using SQLite database
echo 🌐 Server will start on http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.
echo ===============================================

python app.py

pause
