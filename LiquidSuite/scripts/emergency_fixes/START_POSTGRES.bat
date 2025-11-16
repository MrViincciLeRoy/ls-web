@echo off
REM Start PostgreSQL Service on Windows
REM Run this as Administrator

echo ===============================================
echo PostgreSQL Service Starter
echo ===============================================
echo.

echo Attempting to start PostgreSQL...
echo.

REM Try different PostgreSQL version names
net start postgresql-x64-16 2>nul
if %errorlevel% == 0 goto success

net start postgresql-x64-15 2>nul
if %errorlevel% == 0 goto success

net start postgresql-x64-14 2>nul
if %errorlevel% == 0 goto success

net start postgresql-x64-13 2>nul
if %errorlevel% == 0 goto success

net start postgresql-x64-12 2>nul
if %errorlevel% == 0 goto success

echo.
echo ===============================================
echo Could not start PostgreSQL automatically.
echo ===============================================
echo.
echo Please try one of these methods:
echo.
echo METHOD 1: Windows Services
echo   1. Press Windows+R
echo   2. Type: services.msc
echo   3. Find PostgreSQL service
echo   4. Right-click and select Start
echo.
echo METHOD 2: Check if already running
echo   - PostgreSQL might already be running
echo   - Check Task Manager - Services tab
echo.
echo METHOD 3: Install PostgreSQL
echo   - If not installed, download from:
echo   - https://www.postgresql.org/download/windows/
echo.
echo ===============================================
goto end

:success
echo.
echo ===============================================
echo SUCCESS! PostgreSQL is now running
echo ===============================================
echo.
echo You can now:
echo 1. Run LiquidSuite: python app.py
echo 2. Run the fix: python scripts\emergency_fixes\fix_bank_account_constraint.py
echo.
echo ===============================================

:end
pause
