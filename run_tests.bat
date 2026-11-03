@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m unittest discover -s tests -v
) else (
  python -m unittest discover -s tests -v
)
if errorlevel 1 exit /b 1
where node >nul 2>nul
if %errorlevel%==0 (
  node tests\test_secp256k1_math.js
  if errorlevel 1 exit /b 1
) else (
  echo Node.js not found; skipping the JavaScript math tests.
)
pause
