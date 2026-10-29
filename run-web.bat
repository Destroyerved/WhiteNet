@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM UTF-8 console (banner / symbols in Python output)
chcp 65001 >nul 2>&1

echo.
echo === WhiteNet web dashboard ===
echo Project: %CD%
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found in PATH. Install Python and try again.
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js/npm not found in PATH. Install Node.js and try again.
  pause
  exit /b 1
)

echo [1/3] Installing Python dependencies ^(requirements-web.txt^)...
python -m pip install -r requirements-web.txt
if errorlevel 1 (
  echo ERROR: pip install failed.
  pause
  exit /b 1
)

echo.
echo [2/3] Building React client ^(web\client^)...
pushd "web\client"
call npm install
if errorlevel 1 (
  popd
  echo ERROR: npm install failed.
  pause
  exit /b 1
)
call npm run build
if errorlevel 1 (
  popd
  echo ERROR: npm run build failed.
  pause
  exit /b 1
)
popd

echo.
echo [3/3] Starting server...
echo   Dashboard:  http://127.0.0.1:5050/
echo   About:      http://127.0.0.1:5050/about
echo   Use cases:  http://127.0.0.1:5050/use-cases
echo.
echo Press Ctrl+C to stop the server.
echo.

python web\server.py
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" (
  echo Server exited with code %EXITCODE%.
)
pause
exit /b %EXITCODE%
