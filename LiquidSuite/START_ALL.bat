@echo off
cd /d "%~dp0"

set FLASK_ENV=development
set FLASK_APP=app.py
set OFFLINE_MODE=true

psql -U postgres -d postgres -c "SELECT 1;" >nul 2>&1
if %errorlevel% equ 0 (
    set OFFLINE_MODE=false
)

if not exist "logs" mkdir logs
if not exist "mock_data" mkdir mock_data

start /B python scripts\frappe_mock_api.py >logs\mock_api.log 2>&1

timeout /t 3 /nobreak >nul

python -c "from lsuite import create_app; from lsuite.extensions import db; app = create_app(); app.app_context().push(); db.create_all()" >nul 2>&1

python app.py

taskkill /F /FI "WINDOWTITLE eq frappe_mock_api" >nul 2>&1
