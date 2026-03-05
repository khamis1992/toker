@echo off
TITLE TikTok Bot Dashboard Launcher
COLOR 0A

echo ========================================
echo   TikTok Bot Dashboard Launcher
echo ========================================
echo.
echo Starting TikTok Bot Dashboard...
echo.
echo Login credentials:
echo   Username: admin
echo   Password: password
echo.
echo The dashboard will be available at:
echo   http://localhost:8000
echo.
echo NOTE: Make sure to keep this window open
echo while using the dashboard!
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Start the dashboard
python start_dashboard.py

echo.
echo Press any key to exit...
pause >nul