@echo off
echo ========================================
echo   TikTok Bot - Start Viewer Session
echo ========================================
echo.
echo This will start a bot session with viewers.
echo Keep this window open while the bot is running!
echo.
echo Press Ctrl+C to stop the session.
echo.
pause
echo.
echo Starting bot...
python manage.py run_tiktok_bot --session-id %RANDOM%%RANDOM%
echo.
echo Session ended.
pause
