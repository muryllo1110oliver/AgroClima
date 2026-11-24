@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Ambiente nao configurado. Execute instalar.bat primeiro.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -c "import PySide6.QtWidgets, pyqtgraph, serial, requests, certifi"
if errorlevel 1 (
 echo Dependencias incompletas. Execute instalar.bat novamente.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" main.py %*
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
 echo O aplicativo encontrou um erro. Consulte logs\agroclima.log.
 pause
)
exit /b %APP_EXIT%
