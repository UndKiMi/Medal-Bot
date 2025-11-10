@echo off
chcp 65001 >nul
title Medal Bot - Interface Graphique

echo.
echo ========================================
echo    MEDAL BOT - Interface Graphique
echo ========================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installé ou pas dans le PATH
    pause
    exit /b 1
)

REM Vérifier si les dépendances sont installées
python -c "import selenium" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installation des dépendances...
    pip install -r requirements_optimized.txt
    if errorlevel 1 (
        echo [ERREUR] Échec de l'installation des dépendances
        pause
        exit /b 1
    )
)

echo [INFO] Lancement de l'interface graphique...
echo.

REM Lancer l'interface GUI
python gui.py

pause
