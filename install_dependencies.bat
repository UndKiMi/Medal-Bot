@echo off
chcp 65001 >nul
title Medal Bot - Installation des dépendances

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║          MEDAL BOT - Installation des dépendances            ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo [INFO] Vérification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installé ou pas dans le PATH
    echo.
    echo Veuillez installer Python depuis: https://www.python.org/downloads/
    echo N'oubliez pas de cocher "Add Python to PATH" pendant l'installation !
    echo.
    pause
    exit /b 1
)

echo [OK] Python est installé
echo.

echo [INFO] Installation des dépendances...
echo.

pip install --upgrade pip
pip install -r requirements_optimized.txt

if errorlevel 1 (
    echo.
    echo [ERREUR] L'installation a échoué
    echo.
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                  INSTALLATION TERMINÉE !                     ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Vous pouvez maintenant lancer le bot avec:
echo   - Double-clic sur "start_gui.bat"
echo   - Ou double-clic sur "dist\MedalBot.exe"
echo.

pause
