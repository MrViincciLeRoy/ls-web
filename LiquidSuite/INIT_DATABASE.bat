@echo off
REM Initialize LiquidSuite Database for Offline Mode

echo ===============================================
echo LiquidSuite - Database Initialization
echo ===============================================
echo.
echo This will:
echo  1. Create all database tables
echo  2. Seed default categories
echo  3. Create an admin user (optional)
echo.
echo Database: data\lsuite.db (SQLite)
echo ===============================================
echo.

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.10 or higher
    echo.
    pause
    exit /b 1
)

echo Running initialization script...
echo.

python init_offline_db.py

echo.
echo ===============================================
echo.
pause
