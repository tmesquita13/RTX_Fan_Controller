@echo off
setlocal EnableDelayedExpansion
title Iniciar RTX Fan Controller
cd /d "%~dp0"

:: 1. Busca executavel do Python 3.12 64-bit
set "PYTHON_EXE="

if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
) else if exist "C:\Program Files\Python312\pythonw.exe" (
    set "PYTHON_EXE=C:\Program Files\Python312\pythonw.exe"
) else (
    where pythonw.exe >nul 2>&1
    if !errorlevel! == 0 (
        for /f "delims=" %%i in ('where pythonw.exe') do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
        )
    )
)

if not defined PYTHON_EXE (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else (
        echo [ERRO] Python 3.12 nao foi encontrado no caminho padrao!
        echo Caminho verificado: %LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe
        echo.
        pause
        exit /b 1
    )
)

:: 2. Inicia o programa com solicitacao de Administrador (necessario para controle de ventoinhas)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList '\"%~dp0app_webview.py\"' -WorkingDirectory '%~dp0.' -Verb RunAs"

if %errorlevel% neq 0 (
    :: Fallback: se o UAC for cancelado, abre em modo normal
    start "" "%PYTHON_EXE%" "%~dp0app_webview.py"
)

exit /b 0

