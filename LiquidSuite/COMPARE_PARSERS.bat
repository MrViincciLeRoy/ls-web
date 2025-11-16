@echo off
echo =========================================
echo    PARSER COMPARISON TOOL
echo =========================================
echo.
echo This will compare the OLD parser with the PERFECT parser
echo to show you exactly what improvements were made.
echo.
pause
echo.
python compare_parsers_detailed.py
echo.
echo =========================================
echo    Comparison Complete!
echo =========================================
echo.
echo If the PERFECT parser extracts more transactions,
echo we recommend updating by running: UPDATE_PARSER.bat
echo.
pause
