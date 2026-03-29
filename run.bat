@echo off
echo ========================================
echo Ultimate Video Downloader
echo ========================================
echo.

if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

echo Starting application...
call venv\Scripts\activate.bat
python main.py

pause
