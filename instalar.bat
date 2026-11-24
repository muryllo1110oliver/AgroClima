@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto instalar
where py >nul 2>nul
if not errorlevel 1 (
 py -3 -m venv .venv
 if errorlevel 1 goto erro
 goto instalar
)
where python >nul 2>nul
if errorlevel 1 goto erro
python -m venv .venv
if errorlevel 1 goto erro
:instalar
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -c "import PySide6.QtWidgets, PySide6.QtSvg, pyqtgraph, serial, requests, certifi; from pathlib import Path; assert Path(certifi.where()).is_file()"
if errorlevel 1 goto erro
echo Instalacao concluida. Abra executar.bat ou pressione F5 no VS Code.
if /i not "%~1"=="--no-pause" pause
exit /b 0
:erro
echo Falha na instalacao. Use Python 3.12 x64, confira a internet e a mensagem acima.
if /i not "%~1"=="--no-pause" pause
exit /b 1
