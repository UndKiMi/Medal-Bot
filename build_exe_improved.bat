@echo off
title Medal Bot - Compilation EXE

echo.
echo ========================================
echo    MEDAL BOT - Compilation EXE
echo ========================================
echo.

REM Chercher Python dans plusieurs emplacements
set PYTHON_CMD=
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        if exist "C:\Python*\python.exe" (
            for /f "delims=" %%i in ('dir /b /ad "C:\Python*"') do (
                set PYTHON_CMD=C:\%%i\python.exe
                goto :found
            )
        )
        if exist "%LOCALAPPDATA%\Programs\Python\Python*\python.exe" (
            for /f "delims=" %%i in ('dir /b /ad "%LOCALAPPDATA%\Programs\Python\Python*"') do (
                set PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\%%i\python.exe
                goto :found
            )
        )
        if exist "%PROGRAMFILES%\Python*\python.exe" (
            for /f "delims=" %%i in ('dir /b /ad "%PROGRAMFILES%\Python*"') do (
                set PYTHON_CMD=%PROGRAMFILES%\%%i\python.exe
                goto :found
            )
        )
        echo [ERREUR] Python n'est pas trouve. Veuillez installer Python ou l'ajouter au PATH.
        pause
        exit /b 1
    )
)
:found

echo [INFO] Python trouve: %PYTHON_CMD%
echo [INFO] Version de Python:
%PYTHON_CMD% --version
if errorlevel 1 (
    echo [ERREUR] Impossible d'executer Python
    pause
    exit /b 1
)

echo.
echo [INFO] Installation de PyInstaller...
%PYTHON_CMD% -m pip install pyinstaller
if errorlevel 1 (
    echo [ERREUR] Echec de l installation de PyInstaller
    pause
    exit /b 1
)

echo.
echo [INFO] Installation des dependances optionnelles...
%PYTHON_CMD% -m pip install win10toast matplotlib --quiet
echo [INFO] (Les dependances optionnelles sont installees si disponibles)

echo.
echo [INFO] Compilation en cours...
echo [INFO] Cela peut prendre plusieurs minutes...
echo.

%PYTHON_CMD% -m PyInstaller MedalBot.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [ERREUR] La compilation a echoue
    pause
    exit /b 1
)

echo.
echo ========================================
echo [SUCCES] Compilation terminee !
echo ========================================
echo.
echo Le fichier MedalBot.exe se trouve dans le dossier dist
echo.

pause

