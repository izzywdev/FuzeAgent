@echo off
REM FuzeAgent Mock Server + UI Runner Script for Windows
REM This script runs the mock server in Docker and the UI locally

echo 🚀 Starting FuzeAgent Mock Server + UI...

REM Start the mock server in Docker
echo 📦 Starting Mock Server in Docker...
docker-compose -f docker-compose.mock-ui.yml up -d

REM Wait for mock server to be ready
echo ⏳ Waiting for Mock Server to be ready...
:wait_loop
powershell -Command "try { Invoke-WebRequest -Uri http://localhost:8001/health -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 (
    echo    Waiting for mock server...
    timeout /t 2 /nobreak >nul
    goto wait_loop
)

echo ✅ Mock Server is ready at http://localhost:8001

REM Check if UI dependencies are installed
if not exist "services\ui-react\node_modules" (
    echo 📦 Installing UI dependencies...
    cd services\ui-react
    npm install --legacy-peer-deps
    cd ..\..
)

REM Set environment variable for UI
set REACT_APP_API_URL=http://localhost:8001

echo 🎨 Starting UI in development mode...
echo    UI will be available at http://localhost:3000
echo    Mock Server API docs at http://localhost:8001/docs
echo.
echo Press Ctrl+C to stop both services

REM Start the UI
cd services\ui-react
npm start
