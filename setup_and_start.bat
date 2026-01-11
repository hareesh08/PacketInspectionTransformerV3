@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM =====================================================
REM Universal Setup and Start Script
REM Packet Inspection Transformer V3
REM =====================================================

set "SCRIPT_DIR=%~dp0"
set "FRONTEND_DIR=%SCRIPT_DIR%Frontend"
set "BACKEND_DIR=%SCRIPT_DIR%"
set "DB_FILE=%SCRIPT_DIR%threats.db"
set "LOGS_DIR=%SCRIPT_DIR%logs"
set "CACHE_DIR=%SCRIPT_DIR%cache"

REM Colors for Windows
if defined ANSICON (
    set "RED=%ESC%[91m"
    set "GREEN=%ESC%[92m"
    set "YELLOW=%ESC%[93m"
    set "BLUE=%ESC%[94m"
    set "RESET=%ESC%[0m"
) else (
    for /f "delims=#" %%a in ('"prompt #$E# & for %%b in (1) do rem"') do set "ESC=%%a"
    set "RED=%ESC%[91m"
    set "GREEN=%ESC%[92m"
    set "YELLOW=%ESC%[93m"
    set "BLUE=%ESC%[94m"
    set "RESET=%ESC%[0m"
)

:FIND_PYTHON
REM Try to find Python executable (Anaconda preferred, then system Python)
set "PYTHON_EXE="

REM Check common Anaconda locations first
if exist "D:\Programs\anaconda3\python.exe" set "PYTHON_EXE=D:\Programs\anaconda3\python.exe"
if exist "C:\Programs\Anaconda3\python.exe" set "PYTHON_EXE=C:\Programs\Anaconda3\python.exe"
if exist "%USERPROFILE%\anaconda3\python.exe" set "PYTHON_EXE=%USERPROFILE%\anaconda3\python.exe"
if exist "D:\anaconda3\python.exe" set "PYTHON_EXE=D:\anaconda3\python.exe"

REM Check for Anaconda environment (fyp as mentioned in original script)
if exist "D:\Programs\anaconda3\envs\fyp\python.exe" set "PYTHON_EXE=D:\Programs\anaconda3\envs\fyp\python.exe"
if exist "C:\Programs\Anaconda3\envs\fyp\python.exe" set "PYTHON_EXE=C:\Programs\Anaconda3\envs\fyp\python.exe"
if exist "%USERPROFILE%\anaconda3\envs\fyp\python.exe" set "PYTHON_EXE=%USERPROFILE%\anaconda3\envs\fyp\python.exe"

REM If no Anaconda, try system Python
if not defined PYTHON_EXE (
    python --version >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=*" %%a in ('python -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%a"
    ) else (
        REM Try py command
        py --version >nul 2>&1
        if not errorlevel 1 (
            for /f "tokens=*" %%a in ('py -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%a"
        )
    )
)

if not defined PYTHON_EXE (
    echo [%RED!%RESET] Python not found! Please install Python 3.9+ or Anaconda first.
    echo    Downloads:
    echo      - Python: https://python.org/downloads/
    echo      - Anaconda: https://www.anaconda.com/products/distributed
    set "ERROR_FOUND=1"
    goto :eof
)

echo    Detected Python: %PYTHON_EXE"
%PYTHON_EXE% --version
goto :eof

:MAIN_MENU
cls
echo.
echo ====================================================
echo   PACKET INSPECTION TRANSFORMER V3 - SETUP UTILITY
echo ====================================================
echo.
echo   [1] Fresh Setup    - Install all dependencies
echo   [2] Start Server   - Run backend and frontend
echo   [3] Clean All      - Remove DB, cache, node_modules
echo   [4] Restart        - Stop all and start fresh
echo   [5] Exit
echo.
echo ====================================================
echo.

set /p "CHOICE=Select an option [1-5]: "

if "%CHOICE%"=="1" goto FRESH_SETUP
if "%CHOICE%"=="2" goto START_SERVER
if "%CHOICE%"=="3" goto CLEAN_ALL
if "%CHOICE%"=="4" goto RESTART_ALL
if "%CHOICE%"=="5" goto EXIT
goto MAIN_MENU

:FRESH_SETUP
cls
echo.
echo ====================================================
echo   FRESH SETUP - Installing Dependencies
echo ====================================================
echo.

REM Find Python executable
echo [%GREEN*%RESET] Detecting Python installation...
set "ERROR_FOUND="
call :FIND_PYTHON
if defined ERROR_FOUND (
    pause
    goto MAIN_MENU
)

REM Check Node.js
echo [%GREEN*%RESET] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo [%RED!%RESET] Node.js not found! Please install Node.js 18+ first.
    echo    Download from: https://nodejs.org/
    pause
    goto MAIN_MENU
)
for /f "tokens=*" %%a in ('node -v') do set "NODE_VERSION=%%a"
echo    Using Node.js: %NODE_VERSION%

REM Install Python dependencies
echo.
echo [%GREEN*%RESET] Installing Python dependencies...
echo    This may take a few minutes...
%PYTHON_EXE% -m pip install --upgrade pip --quiet
%PYTHON_EXE% -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet
if errorlevel 1 (
    echo [%RED!%RESET] Failed to install Python dependencies!
    pause
    goto MAIN_MENU
)
echo    [%GREEN✓%RESET] Python dependencies installed

REM Install Node.js dependencies
echo.
echo [%GREEN*%RESET] Installing Node.js dependencies...
echo    This may take a few minutes...
if not exist "%FRONTEND_DIR%\package.json" (
    echo [%RED!%RESET] Frontend package.json not found!
    pause
    goto MAIN_MENU
)
cd /d "%FRONTEND_DIR%"
call npm install --legacy-peer-deps
if errorlevel 1 (
    echo [%RED!%RESET] Failed to install Node.js dependencies!
    pause
    goto MAIN_MENU
)
echo    [%GREEN✓%RESET] Node.js dependencies installed

REM Create necessary directories
echo.
echo [%GREEN*%RESET] Creating necessary directories...
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"
echo    [%GREEN✓%RESET] Directories created

echo.
echo [%GREEN==================================================%RESET]
echo   Fresh Setup Complete!
echo [%GREEN==================================================%RESET]
echo.
echo Next steps:
echo   - Run option [2] Start Server to launch the application
echo.
pause
goto MAIN_MENU

:START_SERVER
cls
echo.
echo ====================================================
echo   STARTING SERVER
echo ====================================================
echo.

REM Find Python executable
echo [%GREEN*%RESET] Detecting Python installation...
set "ERROR_FOUND="
call :FIND_PYTHON
if defined ERROR_FOUND (
    echo [%RED!%RESET] Cannot start server without Python!
    pause
    goto MAIN_MENU
)

REM Kill existing processes on ports 8000 and 5173
echo [%YELLOW*%RESET] Checking for existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo    Stopping process on port 8000 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo    Stopping process on port 5173 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

REM Start Backend
echo.
echo [%GREEN*%RESET] Starting Backend (Python/FastAPI)...
cd /d "%BACKEND_DIR%"
start "Backend - Packet Inspection Transformer" cmd /c "%PYTHON_EXE% app.py"

REM Start Frontend
echo [%GREEN*%RESET] Starting Frontend (Vite/React)...
cd /d "%FRONTEND_DIR%"
start "Frontend - Packet Inspection Transformer" cmd /c "npm run dev"

echo.
echo [%GREEN==================================================%RESET]
echo   Server Started Successfully!
echo [%GREEN==================================================%RESET]
echo.
echo   - Backend API: http://localhost:8000
echo   - Frontend:    http://localhost:5173 (check window for URL)
echo   - API Docs:    http://localhost:8000/docs
echo.
echo   Press any key to return to menu...
pause >nul
goto MAIN_MENU

:CLEAN_ALL
cls
echo.
echo ====================================================
echo   CLEAN ALL DATA AND CACHE
echo ====================================================
echo.
echo [%YELLOW!%RESET] WARNING: This will remove:
echo    - Database file (threats.db)
echo    - All log files
echo    - Node_modules folder
echo    - Python cache (__pycache__)
echo    - Vite cache
echo.

set /p "CONFIRM=Are you sure? [y/N]: "
if /i not "%CONFIRM%"=="y" goto MAIN_MENU
if /i not "%CONFIRM%"=="yes" goto MAIN_MENU

echo.
echo [%GREEN*%RESET] Cleaning up...

REM Stop any running processes
echo    Stopping running services...
taskkill /IM "cmd.exe" /FI "WINDOWTITLE eq *Backend*" /F >nul 2>&1
taskkill /IM "cmd.exe" /FI "WINDOWTITLE eq *Frontend*" /F >nul 2>&1

REM Remove database
if exist "%DB_FILE%" (
    del /f /q "%DB_FILE%"
    echo    [%GREEN✓%RESET] Removed database
) else (
    echo    [%YELLOW-%RESET] No database file found
)

REM Remove logs
if exist "%LOGS_DIR%\*" (
    del /f /q "%LOGS_DIR%\*"
    echo    [%GREEN✓%RESET] Removed log files
) else (
    echo    [%YELLOW-%RESET] No log files found
)

REM Remove Python cache
for /d /r "%SCRIPT_DIR%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d"
)
echo    [%GREEN✓%RESET] Removed Python cache

REM Remove node_modules
if exist "%FRONTEND_DIR%\node_modules" (
    rmdir /s /q "%FRONTEND_DIR%\node_modules"
    echo    [%GREEN✓%RESET] Removed node_modules
) else (
    echo    [%YELLOW-%RESET] No node_modules found
)

REM Remove Vite cache
if exist "%FRONTEND_DIR%\node_modules\.vite" (
    rmdir /s /q "%FRONTEND_DIR%\node_modules\.vite"
)
if exist "%FRONTEND_DIR%\dist" (
    rmdir /s /q "%FRONTEND_DIR%\dist"
)
echo    [%GREEN✓%RESET] Removed Vite cache

REM Clean pip cache
%PYTHON_EXE% -m pip cache purge >nul 2>&1
echo    [%GREEN✓%RESET] Cleaned pip cache

echo.
echo [%GREEN==================================================%RESET]
echo   Cleanup Complete!
echo [%GREEN==================================================%RESET]
echo.
pause
goto MAIN_MENU

:RESTART_ALL
cls
echo.
echo ====================================================
echo   RESTARTING ALL SERVICES
echo ====================================================
echo.

echo [%YELLOW*%RESET] Stopping all running services...

REM Kill all related processes
taskkill /IM "cmd.exe" /FI "WINDOWTITLE eq *Backend*" /F >nul 2>&1
taskkill /IM "cmd.exe" /FI "WINDOWTITLE eq *Frontend*" /F >nul 2>&1

REM Wait a moment
timeout /t 2 /nobreak >nul

echo [%GREEN✓%RESET] All services stopped

echo.
goto START_SERVER

:EXIT
exit /b 0
endlocal