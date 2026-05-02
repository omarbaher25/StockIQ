@echo off
title StockIQ - AI Market Intelligence Launcher
color 0B

echo ========================================================
echo        StockIQ - AI Stock Market Intelligence
echo ========================================================
echo.
echo Initializing environment...

:: 1. Navigate to the project directory
cd /d "%~dp0"

:: 2. Check if the Python 3.14 virtual environment exists
if not exist "venv314\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Creating it and installing dependencies...
    python -m venv venv314
    call "venv314\Scripts\activate.bat"
    pip install -r requirements.txt
)

:: 3. Activate the virtual environment
call "venv314\Scripts\activate.bat"

:: 4. Run the Streamlit Application
echo [INFO] Starting the AI engine and dashboard...
echo [INFO] The application will open in your default web browser shortly.
echo.
python -m streamlit run app.py

:: Keep the window open if Streamlit crashes or is closed
pause
