@echo off
chcp 65001 >nul
echo Shutting down platform...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    echo Backend stopped (PID: %%a)
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    echo Frontend stopped (PID: %%a)
)

taskkill /f /im node.exe >nul 2>&1

echo Done.
ping -n 3 127.0.0.1 >nul
