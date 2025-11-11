#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface graphique pour Medal Bot
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import json
import os
import logging
from datetime import datetime
from pathlib import Path
import sys

# Ajouter le répertoire du projet au chemin Python
sys.path.append(str(Path(__file__).parent))

from bot.config_loader import config
from bot.utils.driver_manager import setup_driver, cleanup_driver
from bot.survey_runner import run_survey_bot
from bot.scheduler import scheduler


class StdoutRedirector:
    """Redirige stdout/stderr vers la console GUI."""
    
    def __init__(self, log_queue, tag='info'):
        self.log_queue = log_queue
        self.tag = tag
        self.buffer = ''
    
    def write(self, message):
        """Écrit dans la queue."""
        if message and message.strip():
            self.log_queue.put((message, self.tag))
    
    def flush(self):
        """Flush le buffer."""
        pass


class QueueHandler(logging.Handler):
    """Handler personnalisé pour envoyer les logs vers la queue GUI."""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        """Émet un log vers la queue."""
        try:
            msg = self.format(record)
            
            # Déterminer le tag selon le niveau de log ET le contenu
            if record.levelno >= logging.ERROR or '❌' in msg or 'ERREUR' in msg.upper():
                tag = 'error'
            elif record.levelno >= logging.WARNING or '⚠️' in msg or 'WARNING' in msg.upper():
                tag = 'warning'
            elif '✅' in msg or '🎉' in msg or 'SUCCÈS' in msg.upper() or 'SUCCESS' in msg.upper():
                tag = 'success'
            elif record.levelno >= logging.INFO:
                tag = 'info'
            else:
                tag = 'debug'
            
            # Ajouter à la queue
            self.log_queue.put((f"{msg}\n", tag))
        except Exception:
            self.handleError(record)


class MedalBotGUI:
    # Palette de couleurs Dark Mode moderne
    COLORS = {
        'bg_dark': '#1e1e1e',           # Fond principal très sombre
        'bg_medium': '#252526',         # Fond moyen
        'bg_light': '#2d2d30',          # Fond clair
        'bg_hover': '#3e3e42',          # Fond au survol
        'border': '#3e3e42',            # Bordures
        'text': '#cccccc',              # Texte principal
        'text_dim': '#858585',          # Texte atténué
        'accent_blue': '#0e639c',       # Bleu accent
        'accent_blue_hover': '#1177bb', # Bleu accent hover
        'success': '#4ec9b0',           # Vert succès
        'error': '#f48771',             # Rouge erreur
        'warning': '#dcdcaa',           # Jaune warning
        'info': '#569cd6',              # Bleu info
    }
    
    def __init__(self, root):
        self.root = root
        self.root.title("Medal Bot - Interface de Contrôle")
        self.root.geometry("1000x750")
        self.root.resizable(True, True)
        
        # Appliquer le thème dark mode
        self.apply_dark_theme()
        
        # Variables
        self.bot_running = False
        self.driver = None
        self.bot_thread = None
        self.stats_file = Path(__file__).parent / "bot_stats.json"
        
        # Statistiques
        self.stats = self.load_stats()
        
        # Queue pour les messages entre threads
        self.log_queue = queue.Queue()
        
        # Configurer le logging pour capturer les logs du bot
        self.setup_logging()
        
        # Créer l'interface
        self.create_widgets()
        
        # Démarrer la mise à jour de l'interface
        self.update_gui()
    
    def apply_dark_theme(self):
        """Applique le thème dark mode à l'interface."""
        # Configurer le fond de la fenêtre principale
        self.root.configure(bg=self.COLORS['bg_dark'])
        
        # Configurer le style ttk pour dark mode
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configuration globale
        style.configure('.',
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['text'],
            bordercolor=self.COLORS['border'],
            darkcolor=self.COLORS['bg_medium'],
            lightcolor=self.COLORS['bg_light'],
            troughcolor=self.COLORS['bg_medium'],
            focuscolor=self.COLORS['accent_blue'],
            selectbackground=self.COLORS['accent_blue'],
            selectforeground='white',
            fieldbackground=self.COLORS['bg_medium'],
            font=('Segoe UI', 9)
        )
        
        # Frame
        style.configure('TFrame',
            background=self.COLORS['bg_dark']
        )
        
        # LabelFrame
        style.configure('TLabelframe',
            background=self.COLORS['bg_dark'],
            bordercolor=self.COLORS['border'],
            relief='flat'
        )
        style.configure('TLabelframe.Label',
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['text'],
            font=('Segoe UI', 10, 'bold')
        )
        
        # Label
        style.configure('TLabel',
            background=self.COLORS['bg_dark'],
            foreground=self.COLORS['text']
        )
        
        # Button moderne
        style.configure('TButton',
            background=self.COLORS['accent_blue'],
            foreground='white',
            bordercolor=self.COLORS['accent_blue'],
            focuscolor='none',
            font=('Segoe UI', 9, 'bold'),
            padding=(10, 5)
        )
        style.map('TButton',
            background=[('active', self.COLORS['accent_blue_hover']),
                       ('pressed', self.COLORS['bg_hover'])],
            foreground=[('active', 'white')]
        )
        
        # Treeview
        style.configure('Treeview',
            background=self.COLORS['bg_medium'],
            foreground=self.COLORS['text'],
            fieldbackground=self.COLORS['bg_medium'],
            bordercolor=self.COLORS['border'],
            relief='flat'
        )
        style.configure('Treeview.Heading',
            background=self.COLORS['bg_light'],
            foreground=self.COLORS['text'],
            relief='flat',
            font=('Segoe UI', 9, 'bold')
        )
        style.map('Treeview',
            background=[('selected', self.COLORS['accent_blue'])],
            foreground=[('selected', 'white')]
        )
        
        # Scrollbar
        style.configure('Vertical.TScrollbar',
            background=self.COLORS['bg_medium'],
            troughcolor=self.COLORS['bg_dark'],
            bordercolor=self.COLORS['bg_dark'],
            arrowcolor=self.COLORS['text']
        )
        
        # Notebook (onglets)
        style.configure('TNotebook',
            background=self.COLORS['bg_dark'],
            borderwidth=0
        )
        style.configure('TNotebook.Tab',
            background=self.COLORS['bg_medium'],
            foreground=self.COLORS['text'],
            padding=[20, 10],
            font=('Segoe UI', 10, 'bold')
        )
        style.map('TNotebook.Tab',
            background=[('selected', self.COLORS['accent_blue']),
                       ('active', self.COLORS['bg_hover'])],
            foreground=[('selected', 'white')]
        )
    
    def setup_logging(self):
        """Configure le système de logging pour capturer les logs du bot."""
        queue_handler = QueueHandler(self.log_queue)
        queue_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('[%(asctime)s] %(message)s',
                                     datefmt='%H:%M:%S')
        queue_handler.setFormatter(formatter)
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        if not root_logger.handlers:
            root_logger.addHandler(queue_handler)
        else:
            root_logger.handlers.clear()
            root_logger.addHandler(queue_handler)
        
        # Rediriger stdout et stderr vers la console GUI (important pour .exe)
        sys.stdout = StdoutRedirector(self.log_queue, 'info')
        sys.stderr = StdoutRedirector(self.log_queue, 'error')
        
    def load_stats(self):
        """Charge les statistiques depuis le fichier JSON."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'by_category': {
                'Borne': 0,
                'Comptoir': 0,
                'Click & Collect App': 0,
                'Click & Collect Site': 0,
                'Drive': 0,
                'Livraison': 0
            },
            'recent_surveys': [],
            'next_survey': None
        }
    
    def save_stats(self):
        """Sauvegarde les statistiques dans le fichier JSON."""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"❌ Erreur lors de la sauvegarde des stats: {e}")
    
    def create_widgets(self):
        """Crée tous les widgets de l'interface."""
        
        # Frame principal avec padding
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration du grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # ===== HEADER MODERNE =====
        header_frame = ttk.LabelFrame(main_frame, text="🎯 MEDAL BOT - CONTRÔLE", padding="15")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        
        # Boutons de contrôle avec style moderne
        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = ttk.Button(btn_frame, text="▶️  LANCER LE BOT", command=self.start_bot, width=22)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹️  STOPPER LE BOT", command=self.stop_bot, width=22, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(btn_frame, text="🗑️  EFFACER LES LOGS", command=self.clear_logs, width=22)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Status avec style moderne
        status_frame = tk.Frame(header_frame, bg=self.COLORS['bg_medium'], relief='flat', bd=0)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = tk.Label(
            status_frame, 
            text="⚪ BOT ARRÊTÉ", 
            font=('Segoe UI', 11, 'bold'),
            bg=self.COLORS['bg_medium'],
            fg=self.COLORS['text'],
            pady=8
        )
        self.status_label.pack()
        
        # ===== STATISTIQUES MODERNES =====
        stats_frame = ttk.LabelFrame(main_frame, text="📊 STATISTIQUES", padding="15")
        stats_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        
        # Grille de stats
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        # Stats globales avec fond
        global_frame = tk.Frame(stats_grid, bg=self.COLORS['bg_medium'], relief='flat', bd=0)
        global_frame.pack(side=tk.LEFT, padx=10, pady=5, ipadx=10, ipady=8)
        
        tk.Label(global_frame, text="Total:", font=('Segoe UI', 10, 'bold'), 
                bg=self.COLORS['bg_medium'], fg=self.COLORS['text']).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.total_label = tk.Label(global_frame, text="0", font=('Segoe UI', 12, 'bold'),
                                    bg=self.COLORS['bg_medium'], fg=self.COLORS['info'])
        self.total_label.grid(row=0, column=1, padx=10, pady=2)
        
        tk.Label(global_frame, text="✅ Succès:", font=('Segoe UI', 10, 'bold'),
                bg=self.COLORS['bg_medium'], fg=self.COLORS['text']).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.success_label = tk.Label(global_frame, text="0", font=('Segoe UI', 12, 'bold'),
                                      bg=self.COLORS['bg_medium'], fg=self.COLORS['success'])
        self.success_label.grid(row=1, column=1, padx=10, pady=2)
        
        tk.Label(global_frame, text="❌ Échecs:", font=('Segoe UI', 10, 'bold'),
                bg=self.COLORS['bg_medium'], fg=self.COLORS['text']).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.failed_label = tk.Label(global_frame, text="0", font=('Segoe UI', 12, 'bold'),
                                     bg=self.COLORS['bg_medium'], fg=self.COLORS['error'])
        self.failed_label.grid(row=2, column=1, padx=10, pady=2)
        
        # Séparateur vertical
        sep_frame = tk.Frame(stats_grid, bg=self.COLORS['border'], width=2)
        sep_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15)
        
        # Stats par catégorie
        category_frame = ttk.Frame(stats_grid)
        category_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(category_frame, text="Par catégorie:", font=('Segoe UI', 10, 'bold'),
                bg=self.COLORS['bg_dark'], fg=self.COLORS['text']).pack(anchor=tk.W, pady=(0, 5))
        
        self.category_labels = {}
        categories = ['Borne', 'Comptoir', 'Click & Collect App', 'Click & Collect Site', 'Drive', 'Livraison']
        
        cat_grid = tk.Frame(category_frame, bg=self.COLORS['bg_dark'])
        cat_grid.pack(fill=tk.X, pady=5)
        
        for i, cat in enumerate(categories):
            row = i // 3
            col = i % 3
            
            frame = tk.Frame(cat_grid, bg=self.COLORS['bg_dark'])
            frame.grid(row=row, column=col, padx=12, pady=3, sticky=tk.W)
            
            tk.Label(frame, text=f"{cat}:", font=('Segoe UI', 9),
                    bg=self.COLORS['bg_dark'], fg=self.COLORS['text_dim']).pack(side=tk.LEFT)
            label = tk.Label(frame, text="0", font=('Segoe UI', 10, 'bold'),
                           bg=self.COLORS['bg_dark'], fg=self.COLORS['info'])
            label.pack(side=tk.LEFT, padx=5)
            self.category_labels[cat] = label
        
        # ===== PROCHAIN QUESTIONNAIRE =====
        next_frame = ttk.LabelFrame(main_frame, text="⏭️ PROCHAIN QUESTIONNAIRE", padding="12")
        next_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        
        next_inner = tk.Frame(next_frame, bg=self.COLORS['bg_medium'], relief='flat', bd=0)
        next_inner.pack(fill=tk.X, pady=5, padx=5, ipadx=10, ipady=8)
        
        self.next_survey_label = tk.Label(
            next_inner, 
            text="Aucun questionnaire prévu", 
            font=('Segoe UI', 10),
            bg=self.COLORS['bg_medium'],
            fg=self.COLORS['text']
        )
        self.next_survey_label.pack()
        
        # ===== NOTEBOOK POUR CONSOLE ET RÉCENTS =====
        notebook_frame = ttk.LabelFrame(main_frame, text="📊 DONNÉES", padding="10")
        notebook_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        
        # Configuration du grid pour le notebook
        notebook_frame.columnconfigure(0, weight=1)
        notebook_frame.rowconfigure(0, weight=1)
        
        # Créer le Notebook
        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Onglet 1: Console
        self.create_logs_tab()
        
        # Onglet 2: Questionnaires récents
        self.create_recent_tab()
    
    def create_logs_tab(self):
        """Onglet 1: Console - Logs en temps réel."""
        tab = ttk.Frame(self.notebook, padding="12")
        self.notebook.add(tab, text="📝 CONSOLE")
        
        # Configuration du grid
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        
        # Frame des logs
        logs_frame = ttk.Frame(tab)
        logs_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Zone de texte avec scrollbar et fond sombre
        self.log_text = scrolledtext.ScrolledText(
            logs_frame, 
            wrap=tk.WORD, 
            height=20, 
            font=('Consolas', 9),
            bg='#1e1e1e',  # Fond sombre (VS Code style)
            fg='#d4d4d4',  # Texte gris clair par défaut
            insertbackground='white',  # Curseur blanc
            selectbackground='#264f78',  # Sélection bleue
            state='disabled'  # Lecture seule
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Tags pour colorer les logs avec des couleurs vives sur fond sombre
        self.log_text.tag_config('success', foreground='#4ec9b0')  # Vert cyan vif
        self.log_text.tag_config('error', foreground='#f48771')    # Rouge vif
        self.log_text.tag_config('warning', foreground='#dcdcaa')  # Jaune/Orange vif
        self.log_text.tag_config('info', foreground='#569cd6')     # Bleu vif
        self.log_text.tag_config('debug', foreground='#9cdcfe')    # Bleu clair
        self.log_text.tag_config('timestamp', foreground='#808080') # Gris pour timestamp
        
    def create_recent_tab(self):
        """Onglet 2: Questionnaires récents."""
        tab = ttk.Frame(self.notebook, padding="12")
        self.notebook.add(tab, text="📋 RÉCENTS")
        
        # Configuration du grid
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        
        # Frame du tableau
        recent_frame = ttk.Frame(tab)
        recent_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Treeview pour afficher les questionnaires récents
        columns = ('Heure', 'Catégorie', 'Statut')
        self.recent_tree = ttk.Treeview(recent_frame, columns=columns, show='headings', height=5)
        
        self.recent_tree.heading('Heure', text='Heure')
        self.recent_tree.heading('Catégorie', text='Catégorie')
        self.recent_tree.heading('Statut', text='Statut')
        
        self.recent_tree.column('Heure', width=150)
        self.recent_tree.column('Catégorie', width=200)
        self.recent_tree.column('Statut', width=100)
        
        self.recent_tree.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar pour le treeview
        scrollbar = ttk.Scrollbar(recent_frame, orient=tk.VERTICAL, command=self.recent_tree.yview)
        self.recent_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Charger les stats initiales
        self.update_stats_display()
        self.update_recent_surveys()
        
        # Message de bienvenue dans la console
        self.log_welcome_message()
    
    def log(self, message, tag='info'):
        """Ajoute un message dans les logs."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((f"[{timestamp}] {message}\n", tag))
    
    def log_welcome_message(self):
        """Affiche un message de bienvenue dans la console."""
        welcome = """
╔══════════════════════════════════════════════════════════════╗
║          SURVEY BOT - Interface de Contrôle v1.0             ║
║                  Bot de questionnaires automatique           ║
╚══════════════════════════════════════════════════════════════╝

📊 Console de logs en temps réel
   🔵 INFO    - Messages d'information
   🟢 SUCCESS - Opérations réussies  
   🟡 WARNING - Avertissements
   🔴 ERROR   - Erreurs critiques

Prêt à démarrer ! Cliquez sur "▶️ Lancer le Bot" pour commencer.
"""
        self.log_queue.put((welcome, 'info'))
    
    def update_gui(self):
        """Met à jour l'interface graphique (appelé périodiquement)."""
        # Traiter les messages de log
        try:
            while True:
                message, tag = self.log_queue.get_nowait()
                self.log_text.config(state='normal')
                self.log_text.insert(tk.END, message, tag)
                self.log_text.see(tk.END)
                self.log_text.config(state='disabled')
        except queue.Empty:
            pass
        
        # Planifier la prochaine mise à jour
        self.root.after(100, self.update_gui)
    
    def update_stats_display(self):
        """Met à jour l'affichage des statistiques."""
        self.total_label.config(text=str(self.stats['total']))
        self.success_label.config(text=str(self.stats['success']))
        self.failed_label.config(text=str(self.stats['failed']))
        
        for cat, label in self.category_labels.items():
            count = self.stats['by_category'].get(cat, 0)
            label.config(text=str(count))
        
        # Prochain questionnaire
        if self.stats.get('next_survey'):
            next_info = self.stats['next_survey']
            self.next_survey_label.config(
                text=f"Catégorie: {next_info['category']} | Prévu à: {next_info['time']}"
            )
        else:
            self.next_survey_label.config(text="Aucun questionnaire prévu")
    
    def update_recent_surveys(self):
        """Met à jour la liste des questionnaires récents."""
        # Effacer le treeview
        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
        
        # Ajouter les questionnaires récents
        for survey in reversed(self.stats.get('recent_surveys', [])[-10:]):
            status_emoji = "✅" if survey['status'] == 'success' else "❌"
            self.recent_tree.insert('', 0, values=(
                survey['time'],
                survey['category'],
                f"{status_emoji} {survey['status'].title()}"
            ))
    
    def start_bot(self):
        """Démarre le bot dans un thread séparé."""
        if self.bot_running:
            self.log("⚠️ Le bot est déjà en cours d'exécution", 'warning')
            return
        
        self.bot_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="🟢 BOT EN COURS D'EXÉCUTION", fg=self.COLORS['success'])
        
        self.log("🚀 Démarrage du bot...", 'info')
        
        # Lancer le bot dans un thread
        self.bot_thread = threading.Thread(target=self.run_bot_loop, daemon=True)
        self.bot_thread.start()
    
    def stop_bot(self):
        """Arrête le bot."""
        if not self.bot_running:
            return
        
        self.bot_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="🔴 BOT ARRÊTÉ", fg=self.COLORS['error'])
        
        self.log("🛑 Arrêt du bot demandé...", 'warning')
        
        # Fermer le driver si ouvert
        if self.driver:
            try:
                cleanup_driver(self.driver)
                self.driver = None
            except:
                pass
    
    def run_bot_loop(self):
        """Boucle principale du bot (exécutée dans un thread)."""
        try:
            # Afficher les règles du scheduler
            self.log("═" * 60, 'info')
            self.log("📋 RÈGLES D'EXÉCUTION", 'info')
            self.log("═" * 60, 'info')
            status = scheduler.get_status()
            self.log(f"⏰ Horaires du bot: {status['bot_hours']}", 'info')
            self.log(f"📊 Quota journalier: {status['daily_limit']} questionnaires", 'info')
            self.log(f"✅ Complétés aujourd'hui: {status['today_count']}/{status['daily_limit']}", 'info')
            self.log(f"📍 Restants: {status['remaining']}", 'info')
            self.log("═" * 60, 'info')
            self.log("", 'info')
            
            # Initialiser le navigateur
            self.log("🌐 Initialisation du navigateur...", 'info')
            chrome_options = config.get_chrome_options()
            self.driver = setup_driver(chrome_options)
            
            if not self.driver:
                self.log("❌ Impossible d'initialiser le navigateur", 'error')
                self.stop_bot()
                return
            
            self.log("✅ Navigateur initialisé avec succès", 'success')
            
            survey_url = config.get('survey_url')
            
            while self.bot_running:
                try:
                    # Déterminer la catégorie (aléatoire) AVANT de vérifier si on peut exécuter
                    import random
                    categories = ['Borne', 'Comptoir', 'Click & Collect App', 'Click & Collect Site', 'Drive', 'Livraison']
                    category = random.choice(categories)
                    
                    # Vérifier si on peut exécuter un questionnaire
                    can_run, reason = scheduler.can_run_questionnaire()
                    
                    if not can_run:
                        self.log(f"⏸️ Impossible d'exécuter maintenant: {reason}", 'warning')
                        next_run = scheduler.calculate_next_run_time()
                        scheduler.set_next_scheduled_time(next_run)
                        if next_run:
                            import time as time_module
                            wait_seconds = int((next_run - datetime.now()).total_seconds())
                            
                            if wait_seconds > 0:
                                self.log(f"⏰ Prochain run: {next_run.strftime('%d/%m/%Y à %H:%M')}", 'info')
                                self.log(f"⏱️ Attente de {wait_seconds} secondes ({wait_seconds // 60} minutes)...", 'info')
                                self.stats['next_survey'] = {
                                    'category': category,
                                    'time': next_run.strftime('%d/%m/%Y à %H:%M')
                                }
                                self.save_stats()
                                self.root.after(0, self.update_stats_display)
                                
                                for i in range(wait_seconds):
                                    if not self.bot_running:
                                        break
                                    time_module.sleep(1)
                                
                                continue
                        
                        self.log("🛑 Impossible de planifier le prochain questionnaire", 'warning')
                        self.stop_bot()
                        break
                    
                    # Préparer le prochain questionnaire
                    next_time = datetime.now().strftime("%H:%M:%S")
                    self.stats['next_survey'] = {
                        'category': category,
                        'time': next_time
                    }
                    self.save_stats()
                    self.root.after(0, self.update_stats_display)
                    
                    self.log(f"📍 Questionnaire #{self.stats['total'] + 1} - Catégorie: {category}", 'info')
                    
                    # Charger la page
                    self.log("🌍 Chargement de la page...", 'info')
                    self.driver.get(survey_url)
                    
                    import time
                    time.sleep(random.uniform(2, 4))
                    
                    # Exécuter le bot
                    self.log("🤖 Exécution du questionnaire...", 'info')
                    self.log("─" * 60, 'info')
                    
                    success = run_survey_bot(self.driver)
                    
                    self.log("─" * 60, 'info')
                    
                    # Mettre à jour les stats
                    self.stats['total'] += 1
                    
                    if success:
                        self.stats['success'] += 1
                        self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + 1
                        self.log(f"✅ Questionnaire #{self.stats['total']} terminé avec succès! (+1 {category})", 'success')
                        status = 'success'
                        
                        # Incrémenter le compteur du scheduler
                        scheduler.increment_count()
                        
                        # Afficher le statut mis à jour
                        sched_status = scheduler.get_status()
                        self.log(f"📊 Progression: {sched_status['today_count']}/{sched_status['daily_limit']} questionnaires aujourd'hui", 'info')
                    else:
                        self.stats['failed'] += 1
                        self.log(f"❌ Échec du questionnaire #{self.stats['total']}", 'error')
                        status = 'failed'
                    
                    # Ajouter aux questionnaires récents
                    self.stats['recent_surveys'].append({
                        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'category': category,
                        'status': status
                    })
                    
                    # Garder seulement les 50 derniers
                    self.stats['recent_surveys'] = self.stats['recent_surveys'][-50:]
                    
                    # Sauvegarder et mettre à jour l'affichage
                    self.save_stats()
                    self.root.after(0, self.update_stats_display)
                    self.root.after(0, self.update_recent_surveys)
                    
                    if not self.bot_running:
                        break
                    
                    # Vérifier si on a atteint le quota
                    sched_status = scheduler.get_status()
                    if sched_status['remaining'] <= 0:
                        self.log("🎯 Quota journalier atteint!", 'success')
                        next_run = scheduler.calculate_next_run_time()
                        scheduler.set_next_scheduled_time(next_run)
                        if next_run:
                            import time as time_module
                            wait_seconds = int((next_run - datetime.now()).total_seconds())
                            
                            if wait_seconds > 0:
                                next_category = random.choice(categories)
                                self.log(f"⏰ Prochain run: {next_run.strftime('%d/%m/%Y à %H:%M')}", 'info')
                                self.log(f"⏱️ Attente jusqu'à demain ({wait_seconds // 3600} heures)...", 'info')
                                self.stats['next_survey'] = {
                                    'category': next_category,
                                    'time': next_run.strftime('%d/%m/%Y à %H:%M')
                                }
                                self.save_stats()
                                self.root.after(0, self.update_stats_display)
                                
                                for i in range(wait_seconds):
                                    if not self.bot_running:
                                        break
                                    time_module.sleep(1)
                                
                                continue
                        
                        self.log("🛑 Impossible de planifier le prochain questionnaire", 'warning')
                        self.stop_bot()
                        break
                    
                    # Calculer le délai avant le prochain questionnaire
                    next_run = scheduler.calculate_next_run_time()
                    scheduler.set_next_scheduled_time(next_run)
                    if next_run:
                        import time as time_module
                        wait_seconds = int((next_run - datetime.now()).total_seconds())
                        
                        if wait_seconds > 0:
                            next_category = random.choice(categories)
                            self.log(f"⏱️ Attente de {wait_seconds} secondes avant le prochain questionnaire...", 'info')
                            self.log(f"⏰ Prochain questionnaire prévu à {next_run.strftime('%H:%M')}", 'info')
                            self.stats['next_survey'] = {
                                'category': next_category,
                                'time': next_run.strftime('%d/%m/%Y à %H:%M')
                            }
                            self.save_stats()
                            self.root.after(0, self.update_stats_display)
                            
                            for i in range(wait_seconds):
                                if not self.bot_running:
                                    break
                                time_module.sleep(1)
                        else:
                            self.log("⏸️ Attente terminée, vérification des conditions...", 'info')
                    else:
                        self.log("⏸️ Impossible de planifier maintenant, nouvelle tentative dans 60 secondes...", 'warning')
                        for i in range(60):
                            if not self.bot_running:
                                break
                            time_module.sleep(1)
                
                except Exception as e:
                    self.stats['failed'] += 1
                    self.log(f"❌ Erreur: {e}", 'error')
                    
                    if not self.bot_running:
                        break
                    
                    # Attendre avant de réessayer
                    time.sleep(10)
        
        except Exception as e:
            self.log(f"❌ Erreur critique: {e}", 'error')
        
        finally:
            # Nettoyer
            if self.driver:
                cleanup_driver(self.driver)
                self.driver = None
            
            self.bot_running = False
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.status_label.config(text="⚪ BOT ARRÊTÉ", fg=self.COLORS['text']))
            self.log("👋 Bot arrêté", 'info')
    
    def clear_logs(self):
        """Efface les logs."""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log("🗑️ Logs effacés", 'info')


def main():
    """Point d'entrée de l'application."""
    root = tk.Tk()
    app = MedalBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
