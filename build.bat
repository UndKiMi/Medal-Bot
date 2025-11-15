@echo off
title Medal Bot - Compilation

echo.
echo ========================================
echo    MEDAL BOT - Compilation Complete
echo ========================================
echo.

REM Chercher Python
set PYTHON_CMD=

REM Essayer python d'abord
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :found
)

REM Essayer py launcher
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :found
)

REM Chercher dans les emplacements standards
if exist "%LOCALAPPDATA%\Programs\Python\Python*\python.exe" (
    for /f "delims=" %%i in ('dir /b /ad "%LOCALAPPDATA%\Programs\Python\Python*"') do (
        if exist "%LOCALAPPDATA%\Programs\Python\%%i\python.exe" (
            set PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\%%i\python.exe
            goto :found
        )
    )
)

if exist "C:\Python*\python.exe" (
    for /f "delims=" %%i in ('dir /b /ad "C:\Python*"') do (
        if exist "C:\%%i\python.exe" (
            set PYTHON_CMD=C:\%%i\python.exe
            goto :found
        )
    )
)

echo [ERREUR] Python n'est pas trouve.
echo.
echo Veuillez installer Python depuis https://www.python.org/downloads/
echo.
pause
exit /b 1

:found
echo [INFO] Python trouve: %PYTHON_CMD%
echo [INFO] Version:
"%PYTHON_CMD%" --version
echo.

echo [INFO] Installation des dependances...
"%PYTHON_CMD%" -m pip install pyinstaller win10toast matplotlib PyYAML --quiet
echo.

echo [INFO] Compilation du bot en cours...
echo [INFO] Cela peut prendre plusieurs minutes...
echo.

"%PYTHON_CMD%" -m PyInstaller MedalBot.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [ERREUR] La compilation a echoue
    pause
    exit /b 1
)

echo.
echo [INFO] Nettoyage des fichiers inutiles...
if exist "build" rmdir /s /q "build"
if exist "*.pyc" del /q "*.pyc" 2>nul
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

echo.
echo [INFO] Creation du lanceur sur le bureau...

echo [INFO] Compilation du lanceur...
if exist "launcher.py" (
    "%PYTHON_CMD%" -m PyInstaller launcher.spec --clean --noconfirm >nul 2>&1
    
    REM Copier le lanceur sur le bureau
    if exist "dist\MedalBot.exe" (
        copy /Y "dist\MedalBot.exe" "%USERPROFILE%\Desktop\MedalBot.exe" >nul 2>&1
        if %errorlevel% equ 0 (
            echo [OK] Lanceur copie sur le bureau
        )
    )
) else (
    echo [INFO] Lanceur non trouve, copie directe du bot principal...
    if exist "dist\MedalBot_Main.exe" (
        copy /Y "dist\MedalBot_Main.exe" "%USERPROFILE%\Desktop\MedalBot.exe" >nul 2>&1
        if %errorlevel% equ 0 (
            echo [OK] MedalBot.exe copie sur le bureau
        )
    )
)

echo.
echo ========================================
echo [SUCCES] Compilation terminee !
echo ========================================
echo.
echo Fichiers crees:
echo   - Bot principal: dist\MedalBot_Main.exe
echo   - Lanceur sur le bureau: %USERPROFILE%\Desktop\MedalBot.exe
echo.
echo Double-cliquez sur MedalBot.exe sur votre bureau pour lancer le bot !
echo.

pause

