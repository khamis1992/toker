@echo off
REM Start TikTok Bot with background process
REM Usage: start_bot.bat [session-id]

echo ========================================
echo   TikTok Bot Startup Script
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Get session ID from argument or generate one
if not "%1"=="" (
    set SESSION_ID=%1
) else (
    set SESSION_ID=%RANDOM%%RANDOM%
)

echo Starting bot session: %SESSION_ID%
echo.

REM Run the bot in the background
start "" python manage.py run_bot --session-id %SESSION_ID%

echo Bot started in background!
echo Session ID: %SESSION_ID%
echo.
echo To view logs, check the Django logs window
echo To stop the bot, use Ctrl+C in the bot window
echo ========================================
