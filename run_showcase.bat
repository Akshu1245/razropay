@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if exist ".venv\Scripts\python.exe" (
  set "MG_PYTHON=.venv\Scripts\python.exe"
) else (
  set "MG_PYTHON=python"
)
echo Open http://127.0.0.1:8765 in your browser.
%MG_PYTHON% -m uvicorn api.index:app --host 127.0.0.1 --port 8765
