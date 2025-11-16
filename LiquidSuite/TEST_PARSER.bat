@echo off
echo ========================================
echo  LiquidSuite - Test PDF Parser
echo ========================================
echo.
echo This will test the improved Capitec parser
echo against your account_statement.pdf file
echo.
pause
echo.
echo Running parser test...
echo.

cd /d "%~dp0"
python test_parser.py

echo.
echo ========================================
echo Test completed!
echo ========================================
echo.
pause
