@echo off
echo Installation des dependances...
python -m pip install -r requirements_optimized.txt --quiet
python -m pip install undetected-chromedriver selenium selenium-stealth PyYAML python-dotenv psutil python-dateutil win10toast matplotlib --quiet

echo.
echo Compilation en cours...
python -m PyInstaller MedalBot.spec --clean --noconfirm

if errorlevel 1 (
    echo Erreur lors de la compilation
    pause
    exit /b 1
)

echo.
echo Copie sur le bureau...
copy /Y "dist\MedalBot_Main.exe" "%USERPROFILE%\Desktop\MedalBot.exe" >nul 2>&1

echo.
echo Compilation terminee!
pause

