@echo off
echo Installing Node.js dependencies for QTrigdoppler Remote Server
echo ============================================================

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Node.js is not installed or not in your PATH.
    echo Please install Node.js from https://nodejs.org/
    echo Then run this script again.
    pause
    exit /b 1
)

REM Display Node.js version
echo Using Node.js:
node --version

REM Install dependencies
echo.
echo Installing required packages...
call npm install express socket.io ini

echo.
echo ============================================================
echo Installation complete!
echo.
echo To start the remote server:
echo    node remote_server.js
echo.
echo After starting, you can configure QTrigdoppler to connect to it by
echo editing config.ini:
echo.
echo [remote_server]
echo enable = True
echo url = http://localhost:5001
echo port = 5001
echo debug = False
echo.
echo ============================================================

pause
