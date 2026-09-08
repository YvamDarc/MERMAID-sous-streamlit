@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
) else (
    set "PYTHON_CMD=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo Creation de l'environnement Python...
    %PYTHON_CMD% -m venv .venv
)

echo Installation ou verification des dependances...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo L'installation a echoue. Verifiez votre connexion internet et Python.
    pause
    exit /b 1
)

echo Lancement de Mermaid Studio...
".venv\Scripts\python.exe" -m streamlit run app.py
pause
