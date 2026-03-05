@echo off
echo ========================================
echo Starting TikTok Bot Dashboard
echo ========================================

REM Start the Django server in the background
start "TikTok Bot Server" python manage.py runserver

REM Wait a few seconds for the server to start
timeout /t 5 /nobreak >nul

REM Open the web browser to the dashboard
start http://localhost:8000

echo.
echo Server started! Opening http://localhost:8000 in your browser...
echo.
echo To stop the server, close the terminal window or press Ctrl+C
echo Username: admin
echo Password: password
echo.

pause