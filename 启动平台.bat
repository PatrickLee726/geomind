@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   AI Adjustment Teaching Platform
echo ========================================
echo.

:: Check if already running
netstat -ano 2>nul | findstr ":8000" >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARN] Port 8000 is in use.
    echo        Run Close.bat first if you need to restart.
    echo.
)

echo [1/3] Starting backend...
start "Backend" /MIN cmd /c "cd /d backend && py -m uvicorn app.main:app --port 8000 2>..\backend.log"
echo        Backend: http://localhost:8000

echo        Waiting for backend...
ping -n 6 127.0.0.1 >nul
echo        Backend should be ready
echo.

echo [2/3] Starting frontend...
start "Frontend" /MIN cmd /c "cd /d frontend && npm run dev"
echo        Frontend: http://localhost:5173
echo.

echo [3/3] Opening browser...
ping -n 4 127.0.0.1 >nul
start http://localhost:5173

echo.
echo ========================================
echo   Platform is running!
echo ========================================
echo.
echo   Backend API : http://localhost:8000/docs
echo   Frontend UI : http://localhost:5173
echo.
echo   Press any key to close this window
echo   (platform keeps running in background)
echo   Run Close.bat to fully stop
echo ========================================
pause >nul
