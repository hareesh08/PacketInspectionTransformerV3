@echo off
echo Starting Malware Detection Gateway...
echo.

REM Start backend in a new command window
echo [1/2] Starting backend on http://localhost:8000...
start "Backend - Python" cmd /c "cd /d %~dp0 && D:\Programs\anaconda3\envs\fyp\python.exe app.py"

REM Start frontend in a new command window
echo [2/2] Starting frontend...
start "Frontend - Vite" cmd /c "cd /d %~dp0\Frontend && npm run dev"

echo.
echo Both services are starting!
echo - Backend: http://localhost:8000
echo - Frontend: Check the Vite URL shown in the frontend window
echo.
pause