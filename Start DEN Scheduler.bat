@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo DEN Scheduler is not installed on this computer yet.
  echo.
  echo Run these commands in this folder first:
  echo   python -m venv .venv
  echo   .venv\Scripts\python -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run app.py --server.headless false

