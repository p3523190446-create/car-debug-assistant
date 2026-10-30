@echo off
setlocal
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
py -3 -c "import sys; sys.exit(sys.version_info < (3,10))" >nul 2>&1
if not errorlevel 1 goto py_launcher
python -c "import sys; sys.exit(sys.version_info < (3,10))" >nul 2>&1
if not errorlevel 1 goto python_exe
python3 -c "import sys; sys.exit(sys.version_info < (3,10))" >nul 2>&1
if not errorlevel 1 goto python3_exe
echo Python 3.10 or newer is required.
echo Install Python from https://www.python.org/downloads/
goto finish
:py_launcher
py -3 app.py --open %*
goto finish
:python_exe
python app.py --open %*
goto finish
:python3_exe
python3 app.py --open %*
:finish
pause
