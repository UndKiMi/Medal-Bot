#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lanceur pour Medal Bot"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Obtenir le répertoire du script
    if getattr(sys, 'frozen', False):
        script_dir = Path(sys.executable).parent
    else:
        script_dir = Path(__file__).parent
    
    # Chercher le projet Medal-Bot
    project_dir = script_dir / "Medal-Bot"
    if not project_dir.exists():
        project_dir = script_dir
    
    # Chemin vers l'exécutable du bot principal
    # Le bot principal est compilé avec le nom MedalBot_Main.exe
    exe_path = project_dir / "dist" / "MedalBot_Main.exe"
    
    # Si MedalBot_Main.exe n'existe pas, chercher MedalBot.exe (fallback)
    if not exe_path.exists():
        exe_path = project_dir / "dist" / "MedalBot.exe"
    
    if not exe_path.exists():
        import tkinter.messagebox as msgbox
        msgbox.showerror(
            "Erreur",
            f"Le fichier MedalBot.exe n'existe pas.\n\nChemin attendu: {exe_path}\n\nVeuillez compiler le projet avec build.bat"
        )
        sys.exit(1)
    
    try:
        os.chdir(project_dir)
        subprocess.Popen([str(exe_path)], cwd=str(project_dir))
    except Exception as e:
        import tkinter.messagebox as msgbox
        msgbox.showerror("Erreur", f"Impossible de lancer le bot:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

