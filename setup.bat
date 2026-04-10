@echo off
echo ==========================================
echo Notes App - Local Setup (Windows)
echo ==========================================

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python.
    pause
    exit /b 1
)

:: 2. Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
) else (
    echo [INFO] Virtual environment already exists.
)

:: 3. Install dependencies
echo [INFO] Installing dependencies from requirements.txt...
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

:: 4. Initialize Database
echo [INFO] Initializing Database (ensure XAMPP MySQL is running!)...
python init_db.py

echo ==========================================
echo Setup Complete!
echo To run the app, use:
echo .\venv\Scripts\activate
echo python app.py
echo ==========================================
pause
