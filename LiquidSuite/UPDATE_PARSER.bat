@echo off
echo =========================================
echo    LIQUIDSUITE PARSER UPDATE TOOL
echo =========================================
echo.
echo This will update your parser to extract ALL transactions
echo from your PDFs without missing any.
echo.
echo IMPORTANT: This will backup your current parser first!
echo.
pause
echo.
echo Step 1: Creating backup...
copy "lsuite\gmail\parsers.py" "lsuite\gmail\parsers_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.py"
if errorlevel 1 (
    echo ERROR: Could not create backup!
    pause
    exit /b 1
)
echo ✓ Backup created successfully!
echo.
echo Step 2: Updating parser...
copy /Y "lsuite\gmail\parsers_perfect.py" "lsuite\gmail\parsers.py"
if errorlevel 1 (
    echo ERROR: Could not update parser!
    echo Your original parser is still backed up.
    pause
    exit /b 1
)
echo ✓ Parser updated successfully!
echo.
echo =========================================
echo    UPDATE COMPLETE!
echo =========================================
echo.
echo Your parser has been updated to extract ALL transactions.
echo.
echo Next steps:
echo   1. Restart your LiquidSuite application
echo   2. Upload your PDF again to test
echo   3. Verify all transactions are captured
echo.
echo If you need to restore the old parser:
echo   Look for parsers_backup_*.py in lsuite\gmail\
echo.
pause
