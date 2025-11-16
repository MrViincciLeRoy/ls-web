@echo off
cd /d "%~dp0"

echo Viewing last 50 lines of each log...
echo.
echo === MAIN APP LOG ===
if exist "logs\lsuite_debug.log" (
    powershell -Command "Get-Content logs\lsuite_debug.log -Tail 50"
) else (
    echo No logs yet
)

echo.
echo === MOCK API LOG ===
if exist "logs\mock_api.log" (
    powershell -Command "Get-Content logs\mock_api.log -Tail 50"
) else (
    echo No logs yet
)

pause
