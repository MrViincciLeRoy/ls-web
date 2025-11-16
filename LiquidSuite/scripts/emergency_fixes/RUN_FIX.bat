@echo off
REM Emergency fix for LiquidSuite bank_account_id issue
REM This will automatically fix the NULL constraint problem

echo ===============================================
echo LiquidSuite - Bank Account ID Emergency Fix
echo ===============================================
echo.

cd /d "%~dp0"
cd ..\..\..

echo Running fix script...
echo.

python scripts\emergency_fixes\fix_bank_account_constraint.py

echo.
echo ===============================================
echo.
echo If the fix was successful, you can now:
echo 1. Go to your LiquidSuite application
echo 2. Navigate to Gmail - Statements
echo 3. Try parsing the statement again
echo.
echo ===============================================

pause
