@echo off
setlocal

set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if not exist "%PYTHON_EXE%" (
  echo Python not found at "%PYTHON_EXE%".
  exit /b 1
)

"%PYTHON_EXE%" "%~dp0main.py" %*
