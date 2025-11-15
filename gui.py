#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface graphique pour Medal Bot
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys
import random
try:
    from win10toast import ToastNotifier  # Pour notifications Windows (#21)
    HAS_TOAST = True
except ImportError:
    HAS_TOAST = False
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

# Ajouter le répertoire du projet au chemin Python
sys.path.append(str(Path(__file__).parent))

from bot.config_loader import config
from bot.utils.driver_manager import setup_driver, cleanup_driver
from bot.utils.helpers import wait_with_check
from bot.survey_runner import run_survey_bot, get_session_data
from bot.scheduler import scheduler
from bot.utils.discord_notifier import discord_notifier


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
    
    # Messages à filtrer (trop verbeux ou inutiles)
    FILTERED_MESSAGES = [
        '📋 Catégorie reçue:',
        '📋 session_data complet:',
        '📁 Fichier d\'avis sélectionné:',
        '🔧 Création du driver Chrome...',
        '🎨 Application des paramètres de furtivité...',
        '📜 Injection des scripts anti-détection...',
        '📐 Configuration de la fenêtre...',
        '🖱️ Simulation de mouvement de souris...',
        'Détails:',
        'getting release number',
        'downloading from',
        'unzipping',
        'patching driver',
        'found block:',
        'replacing with:',
        'patching took',
        'Skipping Selenium Manager',
        'Started executable:',
        'POST http://localhost',
        'GET http://localhost',
        'Remote response:',
        'Finished Request',
        'Starting new HTTP connection',
        'http://localhost',
    ]
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def _should_filter(self, msg):
        """Vérifie si un message doit être filtré."""
        # Filtrer les messages DEBUG sauf les erreurs
        if 'Détails:' in msg and 'traceback' in msg.lower():
            return True
        
        # Filtrer les messages trop verbeux
        for filtered in self.FILTERED_MESSAGES:
            if filtered.lower() in msg.lower():
                return True
        
        # Filtrer les messages techniques de Selenium/Chrome
        if any(keyword in msg.lower() for keyword in [
            'session info: chrome=',
            'symbols not available',
            'dumping unresolved backtrace',
            'capabilities',
            'browsername',
            'chromedriverversion',
            'pageaddscripttoevaluatenewdocument',
            'executecdpcommand',
        ]):
            return True
        
        return False
    
    def _format_error(self, msg):
        """Formate les erreurs pour une meilleure lisibilité."""
        # Extraire le message d'erreur principal
        lines = msg.split('\n')
        error_lines = []
        
        for line in lines:
            # Ignorer les lignes de traceback complètes
            if 'File "' in line and '.py' in line:
                # Extraire juste le nom du fichier et la ligne
                if '", line' in line:
                    parts = line.split('", line')
                    if len(parts) > 1:
                        file_part = parts[0].split('\\')[-1].split('/')[-1]
                        line_part = parts[1].split(',')[0]
                        error_lines.append(f"   → {file_part}:{line_part}")
                continue
            
            # Ignorer les lignes de traceback standard
            if line.strip().startswith('Traceback') or line.strip().startswith('at 0x'):
                continue
            
            # Garder les messages d'erreur importants
            if line.strip() and not line.strip().startswith('File'):
                error_lines.append(line)
        
        return '\n'.join(error_lines) if error_lines else msg
    
    def emit(self, record):
        """Émet un log vers la queue."""
        try:
            msg = self.format(record)
            
            # Filtrer les messages inutiles
            if self._should_filter(msg):
                return
            
            # Déterminer le tag selon le niveau de log ET le contenu
            if record.levelno >= logging.ERROR or '❌' in msg or 'ERREUR' in msg.upper():
                tag = 'error'
                # Formater les erreurs pour une meilleure lisibilité
                msg = self._format_error(msg)
            elif record.levelno >= logging.WARNING or '⚠️' in msg or 'WARNING' in msg.upper():
                tag = 'warning'
            elif '✅' in msg or '🎉' in msg or 'SUCCÈS' in msg.upper() or 'SUCCESS' in msg.upper():
                tag = 'success'
            elif record.levelno >= logging.INFO:
                tag = 'info'
            else:
                # Filtrer les messages DEBUG sauf si c'est important
                if 'erreur' not in msg.lower() and 'error' not in msg.lower():
                    return
                tag = 'debug'
            
            # Nettoyer le message (retirer les timestamps en double si présents)
            if msg.startswith('[') and ']' in msg:
                # Le formatter a déjà ajouté un timestamp, on le garde
                pass
            else:
                # Ajouter un timestamp simple
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                msg = f"[{timestamp}] {msg}"
            
            # Ajouter à la queue
            self.log_queue.put((f"{msg}\n", tag))
        except Exception:
            self.handleError(record)


class MedalBotGUI:
    # Mapping des catégories techniques vers les catégories d'affichage
    CATEGORY_MAPPING = {
        # Catégories de base
        'Borne': 'Borne',
        'Comptoir': 'Comptoir',
        'Drive': 'Drive',
        'C&C App': 'C&C App',
        'C&C Site Web': 'C&C Site Web',
        # Catégories techniques (mappées vers les catégories d'affichage)
        'borne_sur_place': 'Borne',
        'borne_emporter': 'Borne',
        'comptoir_sur_place': 'Comptoir',
        'comptoir_emporter': 'Comptoir',
        'cc_appli_comptoir': 'C&C App',
        'cc_appli_drive': 'C&C App',
        'cc_appli_guichet': 'C&C App',
        'cc_appli_exterieur': 'C&C App',
        'cc_site_comptoir': 'C&C Site Web',
        'cc_site_drive': 'C&C Site Web',
        'cc_site_guichet': 'C&C Site Web',
        'cc_site_exterieur': 'C&C Site Web',
        'cc_site_guichet_vente': 'C&C Site Web',
    }
    
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
        self.root.geometry("1200x800")  # Fenêtre plus large pour meilleure organisation
        self.root.resizable(True, True)
        self.root.minsize(1000, 700)  # Taille minimale
        
        # Appliquer le thème dark mode
        self.apply_dark_theme()
        
        # Variables
        self.bot_running = False
        self.driver = None
        self.bot_thread = None
        self.stats_file = Path(__file__).parent / "bot_stats.json"
        self.current_step = 0
        self.total_steps = 8
        self.user_scrolled_up = False  # Pour auto-scroll intelligent
        self.survey_start_time = None  # Pour calculer la durée
        self.toast = None  # Pour notifications (#21)
        if HAS_TOAST:
            self.toast = ToastNotifier()
        self.last_health_check = datetime.now()  # Pour détection crash Chrome (#30)
        
        # Variables pour améliorations visuelles
        self.status_animation_id = None  # Pour animation statut
        self.pulse_alpha = 1.0  # Alpha pour pulsation
        self.pulse_direction = -1  # Direction pulsation
        self.bot_start_time = None  # Temps de démarrage du bot
        self.previous_success_rate = 0  # Pour tendance
        self.log_filter = 'all'  # Filtre logs (all/success/error/warning)
        self.log_search_text = ''  # Texte de recherche
        self.theme_mode = 'dark'  # Mode thème (dark/light)
        self.performance_data = []  # Données de performance
        self.streak_days = 0  # Jours consécutifs
        
        # Variables pour améliorations 10, 18, 25
        self.hourly_data = {}  # Données horaires pour timeline (#10)
        self.timeline_canvas = None  # Canvas pour timeline (#10)
        self.animation_queue = []  # Queue d'animations (#18)
        self.transition_active = False  # État des transitions (#18)
        self.data_cache = {}  # Cache pour optimisations (#25)
        self.cache_timestamps = {}  # Timestamps du cache (#25)
        self.energy_saving_mode = False  # Mode économie d'énergie (#25)
        self.loading_indicator = None  # Indicateur de charge (#25)
        
        # Variables pour Tray Icon (#3)
        self.tray_icon = None
        self.tray_thread = None
        self.minimize_to_tray = True  # Minimiser vers le tray au lieu de fermer
        self.is_minimized = False
        
        # Statistiques
        self.stats = self.load_stats()
        
        # Sauvegarde automatique des stats (#4)
        self.auto_save_interval = 300  # 5 minutes en secondes
        self.auto_save_timer = None
        self.start_auto_save()
        
        # Queue pour les messages entre threads
        self.log_queue = queue.Queue()
        
        # Configurer le logging pour capturer les logs du bot
        self.setup_logging()
        
        # Créer l'interface
        self.create_widgets()
        
        # Valider les fichiers d'avis au démarrage (#12)
        self.root.after(500, self._validate_avis_files_startup)
        
        # Configurer la gestion de la fermeture de fenêtre (#3)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Créer l'icône tray (#3)
        if HAS_PYSTRAY:
            self.setup_tray_icon()
        
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
        
        # Style pour bouton actif (vert)
        style.configure('Active.TButton',
            background=self.COLORS['success'],
            foreground='white',
            bordercolor=self.COLORS['success'],
            font=('Segoe UI', 9, 'bold'),
            padding=(10, 5)
        )
        style.map('Active.TButton',
            background=[('active', '#5dd9c4'),
                       ('pressed', '#3db8a0')],
            foreground=[('active', 'white')]
        )
        
        # Style pour bouton désactivé (gris)
        style.configure('Disabled.TButton',
            background=self.COLORS['bg_light'],
            foreground=self.COLORS['text_dim'],
            bordercolor=self.COLORS['border'],
            font=('Segoe UI', 9, 'bold'),
            padding=(10, 5)
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
        # Filtrer les logs DEBUG sauf les erreurs
        queue_handler.setLevel(logging.INFO)
        
        # Formatter simplifié (sans timestamp car ajouté dans emit)
        formatter = logging.Formatter('%(message)s')
        queue_handler.setFormatter(formatter)
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)  # INFO au lieu de DEBUG pour réduire le bruit
        
        # Réduire le niveau de logging de Selenium et urllib3 pour éviter les messages verbeux
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('undetected_chromedriver').setLevel(logging.WARNING)
        
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
                'C&C App': 0,
                'C&C Site Web': 0,
                'Drive': 0
            },
            'recent_surveys': [],
            'next_survey': None,
            'daily_stats': {},  # Pour #26 - meilleur jour/heure
            'durations': []  # Pour calculer la durée moyenne
        }
    
    def save_stats(self):
        """Sauvegarde les statistiques dans le fichier JSON."""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"❌ Erreur lors de la sauvegarde des stats: {e}")
    
    def create_widgets(self):
        """Crée tous les widgets de l'interface - Réorganisation user-friendly."""
        
        # Frame principal avec padding optimisé
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration du grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)  # Zone principale (notebook)
        
        # ===== ZONE 1: HEADER - CONTRÔLES PRINCIPAUX =====
        header_frame = ttk.LabelFrame(main_frame, text="🎯 CONTRÔLE", padding="15")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Ligne 1: Boutons principaux (groupés logiquement)
        primary_btn_frame = ttk.Frame(header_frame)
        primary_btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Groupe 1: Contrôles du bot
        control_group = tk.Frame(primary_btn_frame, bg=self.COLORS['bg_dark'])
        control_group.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(control_group, text="Contrôle:", font=('Segoe UI', 9, 'bold'),
                bg=self.COLORS['bg_dark'], fg=self.COLORS['text_dim']).pack(anchor=tk.W, pady=(0, 5))
        
        btn_control_frame = tk.Frame(control_group, bg=self.COLORS['bg_dark'])
        btn_control_frame.pack()
        
        self.start_btn = ttk.Button(btn_control_frame, text="▶️  LANCER", command=self.start_bot, width=18)
        self.start_btn.pack(side=tk.LEFT, padx=3)
        
        self.stop_btn = ttk.Button(btn_control_frame, text="⏹️  STOPPER", command=self.stop_bot, width=18, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=3)
        
        # Groupe 2: Actions
        action_group = tk.Frame(primary_btn_frame, bg=self.COLORS['bg_dark'])
        action_group.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(action_group, text="Actions:", font=('Segoe UI', 9, 'bold'),
                bg=self.COLORS['bg_dark'], fg=self.COLORS['text_dim']).pack(anchor=tk.W, pady=(0, 5))
        
        btn_action_frame = tk.Frame(action_group, bg=self.COLORS['bg_dark'])
        btn_action_frame.pack()
        
        self.clear_btn = ttk.Button(btn_action_frame, text="🗑️  EFFACER LOGS", command=self.clear_logs, width=18)
        self.clear_btn.pack(side=tk.LEFT, padx=3)
        
        self.reset_btn = ttk.Button(btn_action_frame, text="🔄  RÉINITIALISER", command=self.reset_stats, width=18)
        self.reset_btn.pack(side=tk.LEFT, padx=3)
        
        # Groupe 3: Options
        option_group = tk.Frame(primary_btn_frame, bg=self.COLORS['bg_dark'])
        option_group.pack(side=tk.LEFT)
        
        tk.Label(option_group, text="Options:", font=('Segoe UI', 9, 'bold'),
                bg=self.COLORS['bg_dark'], fg=self.COLORS['text_dim']).pack(anchor=tk.W, pady=(0, 5))
        
        btn_option_frame = tk.Frame(option_group, bg=self.COLORS['bg_dark'])
        btn_option_frame.pack()
        
        # Frame pour le bouton économie avec indicateur
        energy_frame = tk.Frame(btn_option_frame, bg=self.COLORS['bg_dark'])
        energy_frame.pack(side=tk.LEFT, padx=3)
        
        # Indicateur visuel (badge)
        self.energy_indicator = tk.Label(energy_frame, text="●", font=('Segoe UI', 8),
                                         bg=self.COLORS['bg_dark'], fg=self.COLORS['text_dim'])
        self.energy_indicator.pack(side=tk.LEFT, padx=(0, 3))
        
        self.energy_btn = ttk.Button(energy_frame, text="💡 ÉCONOMIE", command=self.toggle_energy_saving, width=18)
        self.energy_btn.pack(side=tk.LEFT)
        
        # Ligne 2: Statut et métriques (barre horizontale)
        status_frame = tk.Frame(header_frame, bg=self.COLORS['bg_medium'], relief='flat', bd=1)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        status_inner = tk.Frame(status_frame, bg=self.COLORS['bg_medium'])
        status_inner.pack(fill=tk.X, padx=15, pady=10)
        
        # Statut à gauche
        status_left = tk.Frame(status_inner, bg=self.COLORS['bg_medium'])
        status_left.pack(side=tk.LEFT)
        
        self.status_spinner = tk.Label(
            status_left,
            text="",
            font=('Segoe UI', 14),
            bg=self.COLORS['bg_medium'],
            fg=self.COLORS['accent_blue']
        )
        self.status_spinner.pack(side=tk.LEFT, padx=(0, 8))
        
        self.status_label = tk.Label(
            status_left, 
            text="⚪ BOT ARRÊTÉ", 
            font=('Segoe UI', 12, 'bold'),
            bg=self.COLORS['bg_medium'],
            fg=self.COLORS['text']
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Métriques à droite
        metrics_frame = tk.Frame(status_inner, bg=self.COLORS['bg_medium'])
        metrics_frame.pack(side=tk.RIGHT)
        
        self.speed_label = tk.Label(metrics_frame, text="⚡ Vitesse: 0/h", font=('Segoe UI', 10),
                                    bg=self.COLORS['bg_medium'], fg=self.COLORS['info'])
        self.speed_label.pack(side=tk.LEFT, padx=10)
        
        # ===== ZONE 2: STATISTIQUES - ORGANISATION EN CARTES =====
        stats_frame = ttk.LabelFrame(main_frame, text="📊 STATISTIQUES", padding="15")
        stats_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Grille de stats en 2 colonnes
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.BOTH, expand=True)
        stats_grid.columnconfigure(0, weight=1)
        stats_grid.columnconfigure(1, weight=1)
        
        # Colonne gauche: Stats principales
        left_col = tk.Frame(stats_grid, bg=self.COLORS['bg_dark'])
        left_col.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Carte 1: Stats globales
        global_frame = tk.LabelFrame(left_col, text="Vue d'ensemble", font=('Segoe UI', 10, 'bold'),
                                     bg=self.COLORS['bg_medium'], fg=self.COLORS['text'],
                                     relief='flat', bd=1, padx=15, pady=12)
        global_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Stats en grille 2x3
        stats_inner = tk.Frame(global_frame, bg=self.COLORS['bg_medium'])
        stats_inner.pack(fill=tk.BOTH, expand=True)
        
        # Ligne 1: Total et Succès (cartes améliorées avec bordures)
        row1 = tk.Frame(stats_inner, bg=self.COLORS['bg_medium'])
        row1.pack(fill=tk.X, pady=5)
        
        total_card = tk.Frame(row1, bg=self.COLORS['bg_light'], relief='flat', bd=1,
                             padx=12, pady=10)
        total_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        tk.Label(total_card, text="📊 Total", font=('Segoe UI', 9, 'bold'), 
                bg=self.COLORS['bg_light'], fg=self.COLORS['text_dim']).pack()
        self.total_label = tk.Label(total_card, text="0", font=('Segoe UI', 20, 'bold'),
                                    bg=self.COLORS['bg_light'], fg=self.COLORS['info'])
        self.total_label.pack()
        
        success_card = tk.Frame(row1, bg=self.COLORS['bg_light'], relief='flat', bd=1,
                               padx=12, pady=10)
        success_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        tk.Label(success_card, text="✅ Succès", font=('Segoe UI', 9, 'bold'), 
                bg=self.COLORS['bg_light'], fg=self.COLORS['text_dim']).pack()
        self.success_label = tk.Label(success_card, text="0", font=('Segoe UI', 20, 'bold'),
                                      bg=self.COLORS['bg_light'], fg=self.COLORS['success'])
        self.success_label.pack()
        
        # Ligne 2: Échecs et Taux
        row2 = tk.Frame(stats_inner, bg=self.COLORS['bg_medium'])
        row2.pack(fill=tk.X, pady=5)
        
        failed_card = tk.Frame(row2, bg=self.COLORS['bg_light'], relief='flat', bd=1,
                              padx=12, pady=10)
        failed_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        tk.Label(failed_card, text="❌ Échecs", font=('Segoe UI', 9, 'bold'), 
                bg=self.COLORS['bg_light'], fg=self.COLORS['text_dim']).pack()
        self.failed_label = tk.Label(failed_card, text="0", font=('Segoe UI', 20, 'bold'),
                                     bg=self.COLORS['bg_light'], fg=self.COLORS['error'])
        self.failed_label.pack()
        
        rate_card = tk.Frame(row2, bg=self.COLORS['bg_light'], relief='flat', bd=1,
                            padx=12, pady=10)
        rate_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        tk.Label(rate_card, text="📈 Taux", font=('Segoe UI', 9, 'bold'), 
                bg=self.COLORS['bg_light'], fg=self.COLORS['text_dim']).pack()
        rate_inner = tk.Frame(rate_card, bg=self.COLORS['bg_light'])
        rate_inner.pack()
        self.success_rate_label = tk.Label(rate_inner, text="0%", font=('Segoe UI', 20, 'bold'),
                                           bg=self.COLORS['bg_light'], fg=self.COLORS['success'])
        self.success_rate_label.pack(side=tk.LEFT)
        self.trend_label = tk.Label(rate_inner, text="", font=('Segoe UI', 16),
                                    bg=self.COLORS['bg_light'], fg=self.COLORS['text_dim'])
        self.trend_label.pack(side=tk.LEFT, padx=3)
        
        # Ligne 3: Record et Temps
        row3 = tk.Frame(stats_inner, bg=self.COLORS['bg_medium'])
        row3.pack(fill=tk.X, pady=5)
        
        record_card = tk.Frame(row3, bg=self.COLORS['bg_light'], relief='flat', bd=1,
                              padx=12, pady=10)
        record_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        tk.Label(record_card, text="🏆 Record du jour", font=('Segoe UI', 9, 'bold'), 
                bg=self.COLORS['bg_light'], fg=self.COLORS['text_dim']).pack()
        self.record_label = tk.Label(record_card, text="0", font=('Segoe UI', 20, 'bold'),
                                     bg=self.COLORS['bg_light'], fg=self.COLORS['warning'])
        self.record_label.pack()
        
        time_card = tk.Frame(row3, bg=self.COLORS['bg_light'], relief='flat', bd=1,
                            padx=12, pady=10)
        time_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        tk.Label(time_card, text="⏱️ Temps total", font=('Segoe UI', 9, 'bold'), 
                bg=self.COLORS['bg_light'], fg=self.COLORS['text_dim']).pack()
        self.total_time_label = tk.Label(time_card, text="0h 0m", font=('Segoe UI', 20, 'bold'),
                                         bg=self.COLORS['bg_light'], fg=self.COLORS['info'])
        self.total_time_label.pack()
        
        # Colonne droite: Stats par catégorie
        right_col = tk.Frame(stats_grid, bg=self.COLORS['bg_dark'])
        right_col.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        category_frame = tk.LabelFrame(right_col, text="Par catégorie", font=('Segoe UI', 10, 'bold'),
                                       bg=self.COLORS['bg_medium'], fg=self.COLORS['text'],
                                       relief='flat', bd=1, padx=15, pady=12)
        category_frame.pack(fill=tk.BOTH, expand=True)
        
        self.category_labels = {}
        categories = ['Borne', 'Comptoir', 'C&C App', 'C&C Site Web', 'Drive']
        
        cat_inner = tk.Frame(category_frame, bg=self.COLORS['bg_medium'])
        cat_inner.pack(fill=tk.BOTH, expand=True)
        
        # Stocker les barres de progression pour mise à jour
        self.category_progress_bars = {}
        
        for i, cat in enumerate(categories):
            cat_row = tk.Frame(cat_inner, bg=self.COLORS['bg_medium'])
            cat_row.pack(fill=tk.X, pady=8)
            
            # Label catégorie
            tk.Label(cat_row, text=cat, font=('Segoe UI', 10),
                    bg=self.COLORS['bg_medium'], fg=self.COLORS['text'], width=15, anchor='w').pack(side=tk.LEFT)
            
            # Frame pour barre de progression
            progress_container = tk.Frame(cat_row, bg=self.COLORS['bg_medium'])
            progress_container.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
            
            # Barre de progression visuelle améliorée
            progress_bg = tk.Frame(progress_container, bg=self.COLORS['bg_light'], height=22, 
                                  relief='flat', bd=1, highlightbackground=self.COLORS['border'],
                                  highlightthickness=1)
            progress_bg.pack(side=tk.LEFT, fill=tk.X, expand=True)
            progress_bg.pack_propagate(False)
            
            # Barre de remplissage (initialement vide)
            progress_fill = tk.Frame(progress_bg, bg=self.COLORS['info'], height=20)
            progress_fill.pack(side=tk.LEFT, fill=tk.Y)
            self.category_progress_bars[cat] = progress_fill
            
            # Valeur numérique avec taux de réussite (#9)
            label_frame = tk.Frame(progress_container, bg=self.COLORS['bg_medium'])
            label_frame.pack(side=tk.LEFT, padx=(8, 0))
            
            count_label = tk.Label(label_frame, text="0", font=('Segoe UI', 11, 'bold'),
                                 bg=self.COLORS['bg_medium'], fg=self.COLORS['info'], width=5)
            count_label.pack()
            self.category_labels[cat] = count_label
            
            # Label pour taux de réussite (#9)
            rate_label = tk.Label(label_frame, text="", font=('Segoe UI', 8),
                                bg=self.COLORS['bg_medium'], fg=self.COLORS['text_dim'])
            rate_label.pack()
            if not hasattr(self, 'category_rate_labels'):
                self.category_rate_labels = {}
            self.category_rate_labels[cat] = rate_label
        
        # ===== ZONE 3: PROGRESSION ET PROCHAIN QUESTIONNAIRE (côte à côte) =====
        progress_row = ttk.Frame(main_frame)
        progress_row.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        progress_row.columnconfigure(0, weight=2)
        progress_row.columnconfigure(1, weight=1)
        
        # Progression (plus large)
        progress_frame = ttk.LabelFrame(progress_row, text="📊 PROGRESSION", padding="12")
        progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        progress_inner = tk.Frame(progress_frame, bg=self.COLORS['bg_medium'], relief='flat', bd=0)
        progress_inner.pack(fill=tk.X, pady=5, padx=5, ipadx=10, ipady=8)
        
        self.progress_label = tk.Label(
            progress_inner,
            text="Aucun questionnaire en cours",
            font=('Segoe UI', 10),
            bg=self.COLORS['bg_medium'],
            fg=self.COLORS['text']
        )
        self.progress_label.pack()
        
        # Barre de progression avec animation (#3) - améliorée
        progress_bar_container = tk.Frame(progress_inner, bg=self.COLORS['bg_medium'])
        progress_bar_container.pack(fill=tk.X, pady=(5, 0))
        
        self.progress_bar = ttk.Progressbar(
            progress_bar_container,
            mode='determinate',
            length=400,
            maximum=8
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Pourcentage de progression
        self.progress_percent_label = tk.Label(progress_bar_container, text="0%", 
                                               font=('Segoe UI', 10, 'bold'),
                                               bg=self.COLORS['bg_medium'], fg=self.COLORS['info'],
                                               width=5)
        self.progress_percent_label.pack(side=tk.RIGHT)
        
        # Liste des étapes avec checkmarks (#3) - en 2 lignes
        steps_frame = tk.Frame(progress_inner, bg=self.COLORS['bg_medium'])
        steps_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.step_labels = {}
        steps = ['1. Démarrage', '2. Âge', '3. Ticket', '4. Lieu', '5. Satisfaction', '6. Dimensions', '7. Exactitude', '8. Problème']
        
        steps_row1 = tk.Frame(steps_frame, bg=self.COLORS['bg_medium'])
        steps_row1.pack(fill=tk.X, pady=2)
        steps_row2 = tk.Frame(steps_frame, bg=self.COLORS['bg_medium'])
        steps_row2.pack(fill=tk.X, pady=2)
        
        for i, step in enumerate(steps):
            row_frame = steps_row1 if i < 4 else steps_row2
            step_frame = tk.Frame(row_frame, bg=self.COLORS['bg_medium'])
            step_frame.pack(side=tk.LEFT, padx=8, expand=True)
            step_label = tk.Label(step_frame, text=f"○ {step}", font=('Segoe UI', 9),
                                 bg=self.COLORS['bg_medium'], fg=self.COLORS['text_dim'])
            step_label.pack()
            self.step_labels[i+1] = step_label
        
        # Prochain questionnaire (plus étroit)
        next_frame = ttk.LabelFrame(progress_row, text="⏭️ PROCHAIN", padding="12")
        next_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        next_inner = tk.Frame(next_frame, bg=self.COLORS['bg_medium'], relief='flat', bd=0)
        next_inner.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        self.next_survey_label = tk.Label(
            next_inner, 
            text="Aucun questionnaire prévu", 
            font=('Segoe UI', 10),
            bg=self.COLORS['bg_medium'],
            fg=self.COLORS['text'],
            wraplength=200,
            justify=tk.CENTER
        )
        self.next_survey_label.pack(expand=True)
        
        # ===== ZONE 4: NOTEBOOK POUR DONNÉES =====
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
        
        # Onglet 3: Graphiques (#22)
        if HAS_MATPLOTLIB:
            self.create_graphs_tab()
        
        # Onglet 4: Timeline/Historique (#10)
        self.create_timeline_tab()
        
        # Onglet 5: Éditeur d'avis (#1)
        self.create_avis_editor_tab()
    
    def create_logs_tab(self):
        """Onglet 1: Console - Logs en temps réel."""
        tab = ttk.Frame(self.notebook, padding="12")
        self.notebook.add(tab, text="📝 CONSOLE")
        
        # Configuration du grid
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        
        # Barre d'outils pour filtres et recherche (#7)
        toolbar = tk.Frame(tab, bg=self.COLORS['bg_medium'])
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Filtres (#7)
        tk.Label(toolbar, text="Filtre:", font=('Segoe UI', 9),
                bg=self.COLORS['bg_medium'], fg=self.COLORS['text']).pack(side=tk.LEFT, padx=5)
        
        filter_frame = tk.Frame(toolbar, bg=self.COLORS['bg_medium'])
        filter_frame.pack(side=tk.LEFT, padx=5)
        
        self.filter_var = tk.StringVar(value='all')
        filters = [('Tous', 'all'), ('Succès', 'success'), ('Erreurs', 'error'), ('Avertissements', 'warning')]
        for text, value in filters:
            rb = tk.Radiobutton(filter_frame, text=text, variable=self.filter_var, value=value,
                              command=lambda v=value: setattr(self, 'log_filter', v),
                              bg=self.COLORS['bg_medium'], fg=self.COLORS['text'],
                              selectcolor=self.COLORS['bg_dark'], activebackground=self.COLORS['bg_medium'],
                              activeforeground=self.COLORS['text'])
            rb.pack(side=tk.LEFT, padx=2)
        
        # Recherche (#7)
        tk.Label(toolbar, text="Recherche:", font=('Segoe UI', 9),
                bg=self.COLORS['bg_medium'], fg=self.COLORS['text']).pack(side=tk.LEFT, padx=(10, 5))
        self.search_entry = tk.Entry(toolbar, width=20, font=('Segoe UI', 9),
                                     bg=self.COLORS['bg_light'], fg=self.COLORS['text'],
                                     insertbackground=self.COLORS['text'])
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', lambda e: setattr(self, 'log_search_text', self.search_entry.get()))
        
        # Bouton export (#7)
        export_btn = tk.Button(toolbar, text="💾 Exporter", command=self._export_logs,
                              bg=self.COLORS['accent_blue'], fg='white',
                              font=('Segoe UI', 9), relief='flat', padx=10, pady=2)
        export_btn.pack(side=tk.RIGHT, padx=5)
        
        # Frame des logs
        logs_frame = ttk.Frame(tab)
        logs_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
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
        
        # Détecter le scroll manuel pour auto-scroll intelligent (#27)
        self.log_text.bind('<Button-1>', self._on_log_click)
        self.log_text.bind('<Key>', self._on_log_key)
        self.log_text.bind('<MouseWheel>', self._on_log_scroll)
        
        # Tags pour colorer les logs avec des couleurs vives sur fond sombre
        self.log_text.tag_config('success', foreground='#4ec9b0')  # Vert cyan vif
        self.log_text.tag_config('error', foreground='#f48771', font=('Consolas', 9, 'bold'))  # Rouge vif, gras pour erreurs
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
    
    def _on_log_click(self, event):
        """Détecte un clic dans les logs (auto-scroll intelligent #27)."""
        # Vérifier si l'utilisateur a cliqué en haut de la zone de texte
        self._check_scroll_position()
    
    def _on_log_key(self, event):
        """Détecte une touche dans les logs (auto-scroll intelligent #27)."""
        self._check_scroll_position()
    
    def _on_log_scroll(self, event):
        """Détecte un scroll manuel (auto-scroll intelligent #27)."""
        self._check_scroll_position()
    
    def _check_scroll_position(self):
        """Vérifie si l'utilisateur a scrollé vers le haut."""
        try:
            # Vérifier si on est en bas du texte
            self.log_text.update_idletasks()
            end_line = float(self.log_text.index('end-1c').split('.')[0])
            visible_start = float(self.log_text.index('@0,0').split('.')[0])
            visible_end = float(self.log_text.index(f'@0,{self.log_text.winfo_height()}').split('.')[0])
            
            # Si on n'est pas tout en bas, l'utilisateur a scrollé
            if visible_end < end_line - 2:
                self.user_scrolled_up = True
            else:
                self.user_scrolled_up = False
        except:
            pass
    
    def update_gui(self):
        """Met à jour l'interface graphique (appelé périodiquement)."""
        # Traiter les messages de log
        try:
            while True:
                message, tag = self.log_queue.get_nowait()
                self.log_text.config(state='normal')
                
                # Détecter les étapes dans les logs pour mettre à jour la progression (#3)
                if self.survey_start_time:
                    import re
                    step_match = re.search(r'Étape\s+(\d+)', message, re.IGNORECASE)
                    if step_match:
                        step_num = int(step_match.group(1))
                        self.current_step = min(step_num, 8)
                        self.root.after(0, lambda s=step_num: self.progress_bar.config(value=s))
                        self.root.after(0, lambda s=step_num: self._update_step_progress(s))
                        # Mettre à jour le pourcentage
                        if hasattr(self, 'progress_percent_label'):
                            percent = int((step_num / 8) * 100)
                            self.root.after(0, lambda p=percent: self.progress_percent_label.config(text=f"{p}%"))
                
                # Filtrer les logs selon le filtre actif (#7)
                if self.log_filter != 'all':
                    if self.log_filter == 'success' and tag != 'success':
                        continue
                    elif self.log_filter == 'error' and tag != 'error':
                        continue
                    elif self.log_filter == 'warning' and tag != 'warning':
                        continue
                
                # Recherche dans les logs (#7)
                if self.log_search_text and self.log_search_text.lower() not in message.lower():
                    continue
                
                # Pour les erreurs, ajouter un formatage spécial
                if tag == 'error':
                    # Insérer avec un style spécial pour les erreurs
                    self.log_text.insert(tk.END, message, 'error')
                else:
                    self.log_text.insert(tk.END, message, tag)
                
                # Auto-scroll intelligent (#27) : seulement si l'utilisateur n'a pas scrollé
                if not self.user_scrolled_up:
                    self.log_text.see(tk.END)
                else:
                    # Vérifier périodiquement si l'utilisateur est revenu en bas
                    self._check_scroll_position()
                
                self.log_text.config(state='disabled')
        except queue.Empty:
            pass
        
        # Mettre à jour les métriques en temps réel (#6, #8)
        self._update_realtime_metrics()
        
        # Traiter les animations en queue (#18)
        self._process_animation_queue()
        
        # Mettre à jour l'indicateur de charge (#25)
        self._update_loading_indicator()
        
        # Planifier la prochaine mise à jour
        update_interval = 500 if self.energy_saving_mode else 100  # Plus lent en mode économie (#25)
        self.root.after(update_interval, self.update_gui)
    
    def update_stats_display(self):
        """Met à jour l'affichage des statistiques."""
        self.total_label.config(text=str(self.stats['total']))
        self.success_label.config(text=str(self.stats['success']))
        self.failed_label.config(text=str(self.stats['failed']))
        
        # Calculer et afficher le taux de succès en % avec tendance (#2)
        total = self.stats['total']
        if total > 0:
            success_rate = (self.stats['success'] / total) * 100
            self.success_rate_label.config(text=f"{success_rate:.1f}%")
            
            # Afficher la tendance (#2)
            if hasattr(self, 'previous_success_rate') and self.previous_success_rate > 0:
                diff = success_rate - self.previous_success_rate
                if diff > 0.1:
                    self.trend_label.config(text="↑", fg=self.COLORS['success'])
                elif diff < -0.1:
                    self.trend_label.config(text="↓", fg=self.COLORS['error'])
                else:
                    self.trend_label.config(text="→", fg=self.COLORS['text_dim'])
            else:
                self.trend_label.config(text="")
            
            self.previous_success_rate = success_rate
        else:
            self.success_rate_label.config(text="0%")
            self.trend_label.config(text="")
            self.previous_success_rate = 0
        
        # Record du jour (#2)
        today = datetime.now().strftime("%Y-%m-%d")
        today_count = self.stats.get('daily_stats', {}).get(today, {})
        if isinstance(today_count, dict):
            today_total = sum(hour_data.get('success', 0) + hour_data.get('failed', 0) 
                            for hour_data in today_count.values() if isinstance(hour_data, dict))
        else:
            today_total = 0
        self.record_label.config(text=str(today_total))
        
        # Temps total d'exécution (#2, #6)
        if self.bot_start_time:
            elapsed = (datetime.now() - self.bot_start_time).total_seconds()
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            self.total_time_label.config(text=f"{hours}h {minutes}m")
        else:
            self.total_time_label.config(text="0h 0m")
        
        # Mettre à jour les labels et barres de progression avec taux de réussite (#9)
        max_count = max(self.stats['by_category'].values()) if self.stats['by_category'].values() else 1
        
        # Calculer les taux de réussite par catégorie (#9)
        category_success = self.stats.get('category_success', {})
        category_failed = self.stats.get('category_failed', {})
        
        for cat, label in self.category_labels.items():
            count = self.stats['by_category'].get(cat, 0)
            label.config(text=str(count))
            
            # Afficher le taux de réussite (#9)
            if hasattr(self, 'category_rate_labels') and cat in self.category_rate_labels:
                success_count = category_success.get(cat, 0)
                failed_count = category_failed.get(cat, 0)
                total_cat = success_count + failed_count
                
                if total_cat > 0:
                    rate = (success_count / total_cat) * 100
                    rate_label = self.category_rate_labels[cat]
                    rate_label.config(text=f"{rate:.0f}%", 
                                    fg=self.COLORS['success'] if rate >= 80 else 
                                       self.COLORS['warning'] if rate >= 50 else 
                                       self.COLORS['error'])
                else:
                    self.category_rate_labels[cat].config(text="", fg=self.COLORS['text_dim'])
            
            # Mettre à jour la barre de progression visuelle
            if hasattr(self, 'category_progress_bars') and cat in self.category_progress_bars:
                progress_bar = self.category_progress_bars[cat]
                if max_count > 0:
                    # Calculer la largeur en pourcentage
                    width_percent = (count / max_count) * 100
                    # Mettre à jour la largeur de la barre
                    progress_bar.config(width=int(width_percent * 1.5))  # Multiplier pour visibilité
                    
                    # Changer la couleur selon la valeur
                    if count > 0:
                        if count == max_count:
                            progress_bar.config(bg=self.COLORS['success'])
                        else:
                            progress_bar.config(bg=self.COLORS['info'])
                    else:
                        progress_bar.config(bg=self.COLORS['bg_light'])
                else:
                    progress_bar.config(width=0, bg=self.COLORS['bg_light'])
        
        # Prochain questionnaire ou meilleur jour/heure (#26)
        if self.stats.get('next_survey'):
            next_info = self.stats['next_survey']
            self.next_survey_label.config(
                text=f"Catégorie: {next_info['category']} | Prévu à: {next_info['time']}"
            )
        else:
            best_info = self._get_best_day_hour()
            if best_info:
                self.next_survey_label.config(
                    text=f"Meilleur moment: {best_info['day']} à {best_info['hour']}h ({best_info['count']} succès)"
                )
            else:
                self.next_survey_label.config(text="Aucun questionnaire prévu")
    
    def _get_best_day_hour(self):
        """Trouve le meilleur jour/heure pour les questionnaires (#26)."""
        daily_stats = self.stats.get('daily_stats', {})
        if not daily_stats:
            return None
        
        best_count = 0
        best_day = None
        best_hour = None
        
        for day, hours in daily_stats.items():
            for hour, stats in hours.items():
                success_count = stats.get('success', 0)
                if success_count > best_count:
                    best_count = success_count
                    best_day = day
                    best_hour = hour
        
        if best_day and best_hour:
            # Formater la date
            try:
                date_obj = datetime.strptime(best_day, "%Y-%m-%d")
                formatted_day = date_obj.strftime("%d/%m/%Y")
            except:
                formatted_day = best_day
            
            return {
                'day': formatted_day,
                'hour': best_hour,
                'count': best_count
            }
        return None
    
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
    
    def create_graphs_tab(self):
        """Onglet 3: Graphiques (#22)."""
        tab = ttk.Frame(self.notebook, padding="12")
        self.notebook.add(tab, text="📈 GRAPHIQUES")
        
        # Configuration du grid
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        
        # Frame pour les graphiques
        graphs_frame = ttk.Frame(tab)
        graphs_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Graphique 1: Répartition par catégorie (amélioré)
        fig1, ax1 = plt.subplots(figsize=(7, 5), facecolor='#1e1e1e', edgecolor='#3e3e42', linewidth=2)
        ax1.set_facecolor('#252526')
        
        categories = list(self.stats['by_category'].keys())
        counts = [self.stats['by_category'].get(cat, 0) for cat in categories]
        
        # Couleurs améliorées avec dégradé
        colors = ['#4ec9b0', '#569cd6', '#dcdcaa', '#f48771', '#9cdcfe']
        
        # Barres avec ombre et valeurs affichées
        bars = ax1.bar(categories, counts, color=colors[:len(categories)], 
                      edgecolor='white', linewidth=1.5, alpha=0.9)
        
        # Afficher les valeurs sur les barres
        for i, (bar, count) in enumerate(zip(bars, counts)):
            if count > 0:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(count)}',
                        ha='center', va='bottom', color='white', fontweight='bold', fontsize=10)
        
        ax1.set_title('📊 Répartition par catégorie', color='white', fontsize=14, fontweight='bold', pad=15)
        ax1.set_xlabel('Catégories', color='white', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Nombre de questionnaires', color='white', fontsize=11, fontweight='bold')
        ax1.tick_params(colors='white', labelsize=9)
        
        # Grille améliorée
        ax1.grid(True, alpha=0.3, color='white', linestyle='--', linewidth=0.5)
        ax1.set_axisbelow(True)
        
        # Bordures améliorées
        for spine in ax1.spines.values():
            spine.set_color('#3e3e42')
            spine.set_linewidth(1.5)
        
        # Rotation des labels si nécessaire
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=15, ha='right')
        
        canvas1 = FigureCanvasTkAgg(fig1, graphs_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(side=tk.LEFT, padx=10, pady=10)
        self.graph_canvas1 = canvas1  # Garder référence pour mise à jour
        
        # Graphique 2: Succès vs Échecs (amélioré)
        fig2, ax2 = plt.subplots(figsize=(7, 5), facecolor='#1e1e1e', edgecolor='#3e3e42', linewidth=2)
        ax2.set_facecolor('#252526')
        
        labels = ['✅ Succès', '❌ Échecs']
        sizes = [self.stats['success'], self.stats['failed']]
        colors_pie = ['#4ec9b0', '#f48771']
        
        if sum(sizes) > 0:
            # Graphique en camembert amélioré avec ombre
            wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors_pie, 
                                               autopct='%1.1f%%', 
                                               textprops={'color': 'white', 'fontsize': 11, 'fontweight': 'bold'},
                                               startangle=90, 
                                               explode=(0.05, 0.05),  # Séparation des parts
                                               shadow=True)
            
            # Améliorer l'apparence des pourcentages
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(12)
        else:
            # Afficher un message si pas de données
            ax2.text(0.5, 0.5, 'Aucune donnée\npour le moment', 
                    ha='center', va='center', color='#858585', fontsize=12)
        
        ax2.set_title('📈 Taux de succès global', color='white', fontsize=14, fontweight='bold', pad=15)
        
        canvas2 = FigureCanvasTkAgg(fig2, graphs_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(side=tk.LEFT, padx=10, pady=10)
        self.graph_canvas2 = canvas2  # Garder référence pour mise à jour
        self.graph_fig1 = fig1  # Garder référence aux figures
        self.graph_fig2 = fig2
        self.graph_ax1 = ax1
        self.graph_ax2 = ax2
    
    def _update_graphs(self):
        """Met à jour les graphiques avec les nouvelles données."""
        if not HAS_MATPLOTLIB or not hasattr(self, 'graph_ax1'):
            return
        
        try:
            # Mettre à jour le graphique 1 (barres)
            self.graph_ax1.clear()
            categories = list(self.stats['by_category'].keys())
            counts = [self.stats['by_category'].get(cat, 0) for cat in categories]
            
            colors = ['#4ec9b0', '#569cd6', '#dcdcaa', '#f48771', '#9cdcfe']
            bars = self.graph_ax1.bar(categories, counts, color=colors[:len(categories)], 
                                     edgecolor='white', linewidth=1.5, alpha=0.9)
            
            # Afficher les valeurs sur les barres
            for bar, count in zip(bars, counts):
                if count > 0:
                    height = bar.get_height()
                    self.graph_ax1.text(bar.get_x() + bar.get_width()/2., height,
                            f'{int(count)}',
                            ha='center', va='bottom', color='white', fontweight='bold', fontsize=10)
            
            self.graph_ax1.set_title('📊 Répartition par catégorie', color='white', fontsize=14, fontweight='bold', pad=15)
            self.graph_ax1.set_xlabel('Catégories', color='white', fontsize=11, fontweight='bold')
            self.graph_ax1.set_ylabel('Nombre de questionnaires', color='white', fontsize=11, fontweight='bold')
            self.graph_ax1.tick_params(colors='white', labelsize=9)
            self.graph_ax1.grid(True, alpha=0.3, color='white', linestyle='--', linewidth=0.5)
            self.graph_ax1.set_axisbelow(True)
            for spine in self.graph_ax1.spines.values():
                spine.set_color('#3e3e42')
                spine.set_linewidth(1.5)
            plt.setp(self.graph_ax1.xaxis.get_majorticklabels(), rotation=15, ha='right')
            
            # Mettre à jour le graphique 2 (camembert)
            self.graph_ax2.clear()
            labels = ['✅ Succès', '❌ Échecs']
            sizes = [self.stats['success'], self.stats['failed']]
            colors_pie = ['#4ec9b0', '#f48771']
            
            if sum(sizes) > 0:
                wedges, texts, autotexts = self.graph_ax2.pie(sizes, labels=labels, colors=colors_pie, 
                                                             autopct='%1.1f%%', 
                                                             textprops={'color': 'white', 'fontsize': 11, 'fontweight': 'bold'},
                                                             startangle=90, 
                                                             explode=(0.05, 0.05),
                                                             shadow=True)
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
                    autotext.set_fontsize(12)
            else:
                self.graph_ax2.text(0.5, 0.5, 'Aucune donnée\npour le moment', 
                        ha='center', va='center', color='#858585', fontsize=12)
            
            self.graph_ax2.set_title('📈 Taux de succès global', color='white', fontsize=14, fontweight='bold', pad=15)
            
            # Redessiner les canvas
            self.graph_canvas1.draw()
            self.graph_canvas2.draw()
        except Exception as e:
            # En cas d'erreur, ne pas bloquer l'interface
            pass
    
    def create_timeline_tab(self):
        """Onglet 4: Timeline et Historique (#10)."""
        tab = ttk.Frame(self.notebook, padding="12")
        self.notebook.add(tab, text="📅 TIMELINE")
        
        # Configuration du grid
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        
        # Barre d'outils
        toolbar = tk.Frame(tab, bg=self.COLORS['bg_medium'])
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        tk.Label(toolbar, text="Période:", font=('Segoe UI', 9),
                bg=self.COLORS['bg_medium'], fg=self.COLORS['text']).pack(side=tk.LEFT, padx=5)
        
        self.timeline_period = tk.StringVar(value='24h')
        periods = [('24h', '24h'), ('7j', '7d'), ('30j', '30d')]
        for text, value in periods:
            rb = tk.Radiobutton(toolbar, text=text, variable=self.timeline_period, value=value,
                              command=self._update_timeline,
                              bg=self.COLORS['bg_medium'], fg=self.COLORS['text'],
                              selectcolor=self.COLORS['bg_dark'], activebackground=self.COLORS['bg_medium'],
                              activeforeground=self.COLORS['text'])
            rb.pack(side=tk.LEFT, padx=2)
        
        # Canvas pour timeline avec scrollbar
        timeline_frame = ttk.Frame(tab)
        timeline_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        timeline_frame.columnconfigure(0, weight=1)
        timeline_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(timeline_frame, orient=tk.VERTICAL)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.timeline_canvas = tk.Canvas(timeline_frame, bg=self.COLORS['bg_dark'],
                                         yscrollcommand=scrollbar.set,
                                         highlightthickness=0)
        self.timeline_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.timeline_canvas.yview)
        
        # Frame interne pour le contenu
        self.timeline_content = tk.Frame(self.timeline_canvas, bg=self.COLORS['bg_dark'])
        self.timeline_window = self.timeline_canvas.create_window(0, 0, anchor=tk.NW, window=self.timeline_content)
        
        # Lier le redimensionnement
        self.timeline_canvas.bind('<Configure>', self._on_timeline_configure)
        self.timeline_content.bind('<Configure>', self._on_timeline_content_configure)
        
        # Initialiser la timeline
        self._update_timeline()
    
    def start_bot(self):
        """Démarre le bot dans un thread séparé."""
        if self.bot_running:
            self.log("⚠️ Le bot est déjà en cours d'exécution", 'warning')
            return
        
        self.bot_running = True
        self.bot_start_time = datetime.now()
        
        # Mise à jour visuelle des boutons
        self.start_btn.config(state=tk.DISABLED, style='Disabled.TButton')
        self.stop_btn.config(state=tk.NORMAL, style='TButton')
        
        self.status_label.config(text="🟢 BOT EN COURS D'EXÉCUTION", fg=self.COLORS['success'])
        
        # Mettre à jour l'icône tray (#3)
        if HAS_PYSTRAY:
            self.root.after(100, self.update_tray_icon_status)
        
        # Changer la couleur du header (#1)
        self._update_header_color('running')
        
        # Démarrer l'animation du spinner (#1)
        self._animate_spinner()
        
        # Démarrer l'animation de pulsation (#1)
        self._animate_status_pulse()
        
        self.log("🚀 Démarrage du bot...", 'info')
        
        # Lancer le bot dans un thread
        self.bot_thread = threading.Thread(target=self.run_bot_loop, daemon=True)
        self.bot_thread.start()
    
    def stop_bot(self):
        """Arrête le bot."""
        if not self.bot_running:
            return
        
        self.bot_running = False
        
        # Mise à jour visuelle des boutons
        self.start_btn.config(state=tk.NORMAL, style='TButton')
        self.stop_btn.config(state=tk.DISABLED, style='Disabled.TButton')
        
        self.status_label.config(text="⚪ BOT ARRÊTÉ", fg=self.COLORS['text'])
        
        # Mettre à jour l'icône tray (#3)
        if HAS_PYSTRAY:
            self.root.after(100, self.update_tray_icon_status)
        
        # Arrêter les animations (#1)
        if self.status_animation_id:
            self.root.after_cancel(self.status_animation_id)
            self.status_animation_id = None
        
        # Cacher le spinner (#1)
        self.status_spinner.config(text="")
        
        # Réinitialiser la couleur du header (#1)
        self._update_header_color('stopped')
        
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
            if not survey_url:
                self.log("❌ URL du questionnaire non trouvée dans la configuration", 'error')
                self.stop_bot()
                return
            
            self.log(f"📋 URL du questionnaire: {survey_url}", 'info')
            
            while self.bot_running:
                try:
                    # Déterminer la catégorie (aléatoire) AVANT de vérifier si on peut exécuter
                    import random
                    categories = ['Borne', 'Comptoir', 'C&C App', 'C&C Site Web', 'Drive']
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
                                
                                # Optimisation: attente avec vérification périodique
                                if not wait_with_check(wait_seconds, check_interval=1.0, stop_condition=lambda: not self.bot_running):
                                    break  # Bot arrêté pendant l'attente
                                
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
                    try:
                        if not self.driver:
                            self.log("❌ Le driver n'est pas initialisé", 'error')
                            break
                        
                        self.driver.get(survey_url)
                        import time
                        time.sleep(random.uniform(1, 2))  # Optimisé pour vitesse
                        
                        # Vérifier que la page a bien été chargée
                        current_url = self.driver.current_url
                        if 'about:blank' in current_url or current_url == 'about:blank':
                            self.log("⚠️ La page n'a pas été chargée, nouvelle tentative...", 'warning')
                            time.sleep(1)  # Optimisé pour vitesse
                            self.driver.get(survey_url)
                            time.sleep(random.uniform(1, 2))  # Optimisé pour vitesse
                            current_url = self.driver.current_url
                        
                        if 'about:blank' in current_url or current_url == 'about:blank':
                            self.log(f"❌ Impossible de charger l'URL du questionnaire. URL actuelle: {current_url}", 'error')
                            self.stats['failed'] += 1
                            self.save_stats()
                            continue
                        
                        self.log(f"✅ Page chargée: {current_url[:80]}...", 'success')
                    except Exception as e:
                        self.log(f"❌ Erreur lors du chargement de la page: {e}", 'error')
                        self.stats['failed'] += 1
                        self.save_stats()
                        continue
                    
                    # Exécuter le bot
                    self.log("🤖 Exécution du questionnaire...", 'info')
                    self.log("─" * 60, 'info')
                    
                    # Mettre à jour la barre de progression (#20, #3)
                    self.root.after(0, lambda: self.progress_bar.config(value=0))
                    self.root.after(0, lambda: self.progress_label.config(text="Questionnaire en cours..."))
                    self.root.after(0, lambda: self._update_step_progress(0))
                    if hasattr(self, 'progress_percent_label'):
                        self.root.after(0, lambda: self.progress_percent_label.config(text="0%"))
                    self.survey_start_time = datetime.now()
                    self.current_step = 0
                    
                    # Détection crash Chrome (#30) - vérifier périodiquement
                    self.last_health_check = datetime.now()
                    
                    # Sauvegarder les stats avant d'exécuter (en cas de crash)
                    self.save_stats()
                    
                    # Vérifier la santé du driver avant d'exécuter
                    if not self._check_driver_health():
                        self.log("⚠️ Le navigateur semble avoir crashé, réinitialisation...", 'warning')
                        try:
                            cleanup_driver(self.driver)
                        except:
                            pass
                        chrome_options = config.get_chrome_options()
                        self.driver = setup_driver(chrome_options)
                        if not self.driver:
                            self.log("❌ Impossible de réinitialiser le navigateur", 'error')
                            break
                        self.log("✅ Navigateur réinitialisé avec succès", 'success')
                    
                    # Vérifier la santé du driver pendant l'exécution (détection proactive de crash)
                    success = False
                    captcha_detected = False
                    try:
                        success = run_survey_bot(self.driver)
                        
                        # Vérifier si un CAPTCHA a été détecté (#17)
                        session_data = get_session_data()
                        if session_data.get('captcha_detected'):
                            captcha_detected = True
                            success = False
                    except Exception as e:
                        # Vérifier si c'est un crash Chrome
                        if not self._check_driver_health():
                            self.log("⚠️ Chrome a crashé pendant l'exécution, réinitialisation...", 'warning')
                            try:
                                cleanup_driver(self.driver)
                            except:
                                pass
                            chrome_options = config.get_chrome_options()
                            self.driver = setup_driver(chrome_options)
                            if not self.driver:
                                self.log("❌ Impossible de réinitialiser le navigateur après crash", 'error')
                                self.stats['failed'] += 1
                                self.save_stats()
                                break
                            self.log("✅ Navigateur réinitialisé après crash", 'success')
                            # Marquer comme échec car le questionnaire n'a pas pu se terminer
                            success = False
                        else:
                            # Autre erreur - la propager
                            self.log(f"❌ Erreur lors de l'exécution: {e}", 'error')
                            raise
                    
                    self.log("─" * 60, 'info')
                    
                    # Gérer la détection de CAPTCHA (#17)
                    if captcha_detected:
                        self.log("🚨 CAPTCHA détecté - Arrêt du bot", 'error')
                        discord_notifier.notify_captcha()  # (#5)
                        messagebox.showerror("CAPTCHA détecté", 
                                           "Un CAPTCHA a été détecté sur la page.\nLe bot a été arrêté automatiquement.")
                        self.stop_bot()
                        break
                    
                    # Mettre à jour les stats
                    self.stats['total'] += 1
                    
                    # Récupérer la catégorie technique réelle depuis session_data
                    session_data = get_session_data()
                    technical_category = session_data.get('current_category', category)
                    
                    # Mapper la catégorie technique vers la catégorie d'affichage
                    display_category = self.CATEGORY_MAPPING.get(technical_category, category)
                    if display_category not in self.stats['by_category']:
                        display_category = category  # Fallback sur la catégorie choisie aléatoirement
                    
                    # Calculer la durée (#24)
                    if self.survey_start_time:
                        duration = (datetime.now() - self.survey_start_time).total_seconds()
                        self.stats['durations'].append(duration)
                        # Garder seulement les 100 dernières durées
                        self.stats['durations'] = self.stats['durations'][-100:]
                    
                    # Statistiques par jour/heure (#26)
                    now = datetime.now()
                    day_key = now.strftime("%Y-%m-%d")
                    hour_key = now.strftime("%H")
                    if day_key not in self.stats['daily_stats']:
                        self.stats['daily_stats'][day_key] = {}
                    if hour_key not in self.stats['daily_stats'][day_key]:
                        self.stats['daily_stats'][day_key][hour_key] = {'success': 0, 'failed': 0}
                    
                    if success:
                        self.stats['success'] += 1
                        self.stats['by_category'][display_category] = self.stats['by_category'].get(display_category, 0) + 1
                        self.stats['daily_stats'][day_key][hour_key]['success'] += 1
                        self._track_category_result(display_category, True)  # (#9)
                        self.log(f"✅ Questionnaire #{self.stats['total']} terminé avec succès! (+1 {display_category})", 'success')
                        
                        # Notification Discord (#5)
                        duration = (datetime.now() - self.survey_start_time).total_seconds() if self.survey_start_time else 0
                        discord_notifier.notify_success(self.stats['total'], display_category, duration)
                        
                        # Animation de célébration (#18)
                        self.root.after(0, self._celebrate_success)
                        status = 'success'
                        
                        # Notification système (#21)
                        if self.toast:
                            self.toast.show_toast(
                                "Questionnaire terminé",
                                f"Questionnaire #{self.stats['total']} complété avec succès!",
                                duration=3
                            )
                        
                        # Incrémenter le compteur du scheduler
                        scheduler.increment_count()
                        
                        # Afficher le statut mis à jour
                        sched_status = scheduler.get_status()
                        self.log(f"📊 Progression: {sched_status['today_count']}/{sched_status['daily_limit']} questionnaires aujourd'hui", 'info')
                    else:
                        self.stats['failed'] += 1
                        self.stats['daily_stats'][day_key][hour_key]['failed'] += 1
                        self._track_category_result(display_category, False)  # (#9)
                        self.log(f"❌ Échec du questionnaire #{self.stats['total']}", 'error')
                        
                        # Notification Discord (#5)
                        discord_notifier.notify_failure(self.stats['total'], display_category)
                        
                        status = 'failed'
                        
                        # Notification système (#21)
                        if self.toast:
                            self.toast.show_toast(
                                "Questionnaire échoué",
                                f"Le questionnaire #{self.stats['total']} a échoué.",
                                duration=3
                            )
                    
                    # Réinitialiser la barre de progression (#20)
                    self.root.after(0, lambda: self.progress_bar.config(value=0))
                    self.root.after(0, lambda: self.progress_label.config(text="Aucun questionnaire en cours"))
                    if hasattr(self, 'progress_percent_label'):
                        self.root.after(0, lambda: self.progress_percent_label.config(text="0%"))
                    
                    # Ajouter aux questionnaires récents
                    self.stats['recent_surveys'].append({
                        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'category': display_category,
                        'status': status
                    })
                    
                    # Garder seulement les 50 derniers
                    self.stats['recent_surveys'] = self.stats['recent_surveys'][-50:]
                    
                    # Sauvegarder et mettre à jour l'affichage
                    self.save_stats()
                    self.root.after(0, self.update_stats_display)
                    self.root.after(0, self.update_recent_surveys)
                    
                    # Mettre à jour les graphiques (#22)
                    if hasattr(self, 'graph_canvas1'):
                        self.root.after(0, self._update_graphs)
                    
                    # Mettre à jour la timeline (#10)
                    if hasattr(self, 'timeline_period'):
                        self.root.after(0, self._update_timeline)
                    
                    # Mettre à jour l'icône tray (#3)
                    if HAS_PYSTRAY:
                        self.root.after(0, self.update_tray_icon_status)
                    
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
                                
                                # Optimisation: attente avec vérification périodique
                                if not wait_with_check(wait_seconds, check_interval=1.0, stop_condition=lambda: not self.bot_running):
                                    break  # Bot arrêté pendant l'attente
                                
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
                            
                            # Optimisation: attente avec vérification périodique
                            if not wait_with_check(wait_seconds, check_interval=1.0, stop_condition=lambda: not self.bot_running):
                                break  # Bot arrêté pendant l'attente
                        else:
                            self.log("⏸️ Attente terminée, vérification des conditions...", 'info')
                    else:
                        self.log("⏸️ Impossible de planifier maintenant, nouvelle tentative dans 30 secondes...", 'warning')
                        # Optimisation: attente avec vérification périodique
                        if not wait_with_check(30, check_interval=1.0, stop_condition=lambda: not self.bot_running):  # Optimisé pour vitesse
                            break  # Bot arrêté pendant l'attente
                
                except Exception as e:
                    self.stats['failed'] += 1
                    self.log(f"❌ Erreur: {e}", 'error')
                    
                    if not self.bot_running:
                        break
                    
                    # Attendre avant de réessayer (optimisé pour vitesse)
                    time.sleep(5)  # Réduit de 10 à 5 secondes
        
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
        # Animation visuelle : flash du bouton
        original_style = self.clear_btn.cget('style')
        self.clear_btn.config(style='Active.TButton')
        self.root.after(200, lambda: self.clear_btn.config(style=original_style))
        
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log("🗑️ Logs effacés", 'info')
    
    def _check_driver_health(self):
        """Vérifie si le driver Chrome est toujours actif (#30)."""
        if not self.driver:
            return False
        try:
            # Essayer d'accéder à une propriété simple du driver
            _ = self.driver.current_url
            # Vérifier aussi que la fenêtre est toujours ouverte
            handles = self.driver.window_handles
            if not handles or len(handles) == 0:
                return False
            # Vérifier que le driver répond toujours
            _ = self.driver.title
            return True
        except Exception:
            # Driver crashé ou non accessible
            return False
    
    # ===== MÉTHODES POUR AMÉLIORATIONS VISUELLES =====
    
    def _animate_spinner(self):
        """Animation du spinner (#1)."""
        if not self.bot_running:
            return
        
        spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        if not hasattr(self, '_spinner_index'):
            self._spinner_index = 0
        
        self.status_spinner.config(text=spinner_chars[self._spinner_index % len(spinner_chars)])
        self._spinner_index += 1
        self.root.after(100, self._animate_spinner)
    
    def _animate_status_pulse(self):
        """Animation de pulsation pour le statut (#1)."""
        if not self.bot_running:
            return
        
        # Simuler une pulsation en changeant l'opacité visuelle (via couleur)
        self.pulse_alpha += self.pulse_direction * 0.1
        if self.pulse_alpha <= 0.5:
            self.pulse_direction = 1
        elif self.pulse_alpha >= 1.0:
            self.pulse_direction = -1
        
        # Changer la couleur en fonction de l'alpha
        r = int(78 + (255 - 78) * (1 - self.pulse_alpha))
        g = int(201 + (255 - 201) * (1 - self.pulse_alpha))
        b = int(176 + (255 - 176) * (1 - self.pulse_alpha))
        color = f"#{r:02x}{g:02x}{b:02x}"
        self.status_label.config(fg=color)
        
        self.status_animation_id = self.root.after(50, self._animate_status_pulse)
    
    def _update_header_color(self, state):
        """Change la couleur du header selon l'état (#1)."""
        header_frame = None
        # Trouver le header_frame
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame) and 'CONTRÔLE' in str(child.cget('text')):
                        header_frame = child
                        break
        
        if header_frame:
            if state == 'running':
                header_frame.configure(style='HeaderRunning.TLabelframe')
            elif state == 'stopped':
                header_frame.configure(style='HeaderStopped.TLabelframe')
    
    def _update_realtime_metrics(self):
        """Met à jour les métriques en temps réel (#6, #8)."""
        if not self.bot_running or not self.bot_start_time:
            return
        
        # Calculer le temps d'exécution
        elapsed = (datetime.now() - self.bot_start_time).total_seconds()
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        
        # Calculer la vitesse moyenne (questionnaires/heure) (#8)
        if elapsed > 0:
            speed = (self.stats['total'] / elapsed) * 3600
            # Stocker pour affichage
            if not hasattr(self, '_current_speed'):
                self._current_speed = 0
            self._current_speed = speed
            
            # Mettre à jour l'affichage de la vitesse (#8)
            if hasattr(self, 'speed_label'):
                self.speed_label.config(text=f"⚡ Vitesse: {speed:.1f}/h")
    
    def _export_logs(self):
        """Exporte les logs dans un fichier (#7)."""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")]
            )
            if filename:
                content = self.log_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log(f"✅ Logs exportés vers {filename}", 'success')
        except Exception as e:
            self.log(f"❌ Erreur lors de l'export: {e}", 'error')
    
    def _update_step_progress(self, step_num):
        """Met à jour l'affichage des étapes avec checkmarks (#3)."""
        if not hasattr(self, 'step_labels') or step_num == 0:
            # Réinitialiser toutes les étapes
            if hasattr(self, 'step_labels'):
                steps = ['1. Démarrage', '2. Âge', '3. Ticket', '4. Lieu', '5. Satisfaction', '6. Dimensions', '7. Exactitude', '8. Problème']
                for i in range(1, 9):
                    if i in self.step_labels:
                        self.step_labels[i].config(text=f"○ {steps[i-1]}", fg=self.COLORS['text_dim'])
            return
        
        if hasattr(self, 'step_labels'):
            steps = ['1. Démarrage', '2. Âge', '3. Ticket', '4. Lieu', '5. Satisfaction', '6. Dimensions', '7. Exactitude', '8. Problème']
            for i in range(1, 9):
                if i in self.step_labels:
                    if i < step_num:
                        # Étape complétée
                        self.step_labels[i].config(text=f"✓ {steps[i-1]}", fg=self.COLORS['success'])
                    elif i == step_num:
                        # Étape en cours
                        self.step_labels[i].config(text=f"◉ {steps[i-1]}", fg=self.COLORS['accent_blue'])
                    else:
                        # Étape à venir
                        self.step_labels[i].config(text=f"○ {steps[i-1]}", fg=self.COLORS['text_dim'])
    
    def reset_stats(self):
        """Réinitialise les statistiques avec confirmation."""
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment réinitialiser toutes les statistiques ?"):
            # Animation visuelle : flash du bouton
            original_style = self.reset_btn.cget('style')
            self.reset_btn.config(style='Active.TButton')
            self.root.after(300, lambda: self.reset_btn.config(style=original_style))
            
            self.stats = {
                'total': 0,
                'success': 0,
                'failed': 0,
                'by_category': {
                    'Borne': 0,
                    'Comptoir': 0,
                    'C&C App': 0,
                    'C&C Site Web': 0,
                    'Drive': 0
                },
                'recent_surveys': [],
                'next_survey': None,
                'daily_stats': {},  # Pour #26
                'durations': []  # Pour #24
            }
            self.save_stats()
            self.update_stats_display()
            self.update_recent_surveys()
            self.log("🔄 Statistiques réinitialisées", 'success')
    
    # ===== MÉTHODES POUR AMÉLIORATION 10: TIMELINE/HISTORIQUE =====
    
    def _update_timeline(self):
        """Met à jour la timeline avec les données (#10)."""
        if not hasattr(self, 'timeline_content'):
            return
        
        # Nettoyer le contenu existant
        for widget in self.timeline_content.winfo_children():
            widget.destroy()
        
        # Récupérer la période
        period = self.timeline_period.get()
        now = datetime.now()
        
        if period == '24h':
            start_time = now - timedelta(hours=24)
            interval = timedelta(hours=1)
        elif period == '7d':
            start_time = now - timedelta(days=7)
            interval = timedelta(hours=6)
        else:  # 30d
            start_time = now - timedelta(days=30)
            interval = timedelta(days=1)
        
        # Collecter les données
        timeline_data = []
        current = start_time
        while current <= now:
            day_key = current.strftime("%Y-%m-%d")
            hour_key = current.strftime("%H")
            
            if day_key in self.stats.get('daily_stats', {}):
                day_data = self.stats['daily_stats'][day_key]
                if isinstance(day_data, dict) and hour_key in day_data:
                    hour_data = day_data[hour_key]
                    if isinstance(hour_data, dict):
                        success = hour_data.get('success', 0)
                        failed = hour_data.get('failed', 0)
                        if success + failed > 0:
                            timeline_data.append({
                                'time': current,
                                'success': success,
                                'failed': failed,
                                'total': success + failed
                            })
            
            current += interval
        
        # Afficher la timeline
        if not timeline_data:
            no_data_label = tk.Label(self.timeline_content, text="Aucune donnée pour cette période",
                                    font=('Segoe UI', 12), bg=self.COLORS['bg_dark'], fg=self.COLORS['text_dim'])
            no_data_label.pack(pady=20)
            return
        
        # Créer les éléments de timeline
        for i, data in enumerate(timeline_data):
            self._create_timeline_item(data, i)
    
    def _create_timeline_item(self, data, index):
        """Crée un élément de timeline (#10)."""
        item_frame = tk.Frame(self.timeline_content, bg=self.COLORS['bg_medium'], relief='flat', bd=1)
        item_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Ligne de temps
        time_line = tk.Frame(item_frame, bg=self.COLORS['accent_blue'], width=3)
        time_line.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 15))
        
        # Contenu
        content_frame = tk.Frame(item_frame, bg=self.COLORS['bg_medium'])
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        # Heure
        time_str = data['time'].strftime("%d/%m %H:%M")
        time_label = tk.Label(content_frame, text=time_str, font=('Segoe UI', 10, 'bold'),
                             bg=self.COLORS['bg_medium'], fg=self.COLORS['text'])
        time_label.pack(anchor=tk.W)
        
        # Statistiques
        stats_frame = tk.Frame(content_frame, bg=self.COLORS['bg_medium'])
        stats_frame.pack(anchor=tk.W, pady=(5, 0))
        
        tk.Label(stats_frame, text=f"✅ {data['success']}", font=('Segoe UI', 9),
                bg=self.COLORS['bg_medium'], fg=self.COLORS['success']).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(stats_frame, text=f"❌ {data['failed']}", font=('Segoe UI', 9),
                bg=self.COLORS['bg_medium'], fg=self.COLORS['error']).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(stats_frame, text=f"📊 Total: {data['total']}", font=('Segoe UI', 9),
                bg=self.COLORS['bg_medium'], fg=self.COLORS['info']).pack(side=tk.LEFT)
    
    def _on_timeline_configure(self, event):
        """Gère le redimensionnement du canvas timeline (#10)."""
        if hasattr(self, 'timeline_window'):
            canvas_width = event.width
            self.timeline_canvas.itemconfig(self.timeline_window, width=canvas_width)
    
    def _on_timeline_content_configure(self, event):
        """Gère la configuration du contenu timeline (#10)."""
        if hasattr(self, 'timeline_canvas'):
            self.timeline_canvas.configure(scrollregion=self.timeline_canvas.bbox("all"))
    
    # ===== MÉTHODES POUR AMÉLIORATION 18: ANIMATIONS ET TRANSITIONS =====
    
    def _process_animation_queue(self):
        """Traite la queue d'animations (#18)."""
        if not self.animation_queue or self.transition_active:
            return
        
        if self.energy_saving_mode:  # Ignorer les animations en mode économie (#25)
            self.animation_queue.clear()
            return
        
        # Traiter la première animation de la queue
        animation = self.animation_queue.pop(0)
        if callable(animation):
            try:
                animation()
            except Exception:
                pass
    
    def _animate_transition(self, widget, start_value, end_value, duration=300, callback=None):
        """Animation de transition fluide (#18)."""
        if self.energy_saving_mode:
            # Appliquer directement sans animation
            if callback:
                callback()
            return
        
        self.transition_active = True
        steps = 20
        step_delay = duration // steps
        delta = (end_value - start_value) / steps
        current = start_value
        step = 0
        
        def animate_step():
            nonlocal current, step
            if step < steps:
                current += delta
                # Ici on pourrait animer des propriétés comme opacity, position, etc.
                # Pour Tkinter, on peut animer la couleur ou la position
                step += 1
                self.root.after(step_delay, animate_step)
            else:
                self.transition_active = False
                if callback:
                    callback()
        
        animate_step()
    
    def _celebrate_success(self):
        """Animation de célébration pour succès (#18)."""
        if self.energy_saving_mode:
            return
        
        # Animation simple : flash de couleur verte
        original_bg = self.status_label.cget('bg')
        for i in range(3):
            def flash_on(delay=i * 200):
                self.root.after(delay, lambda: self.status_label.config(bg=self.COLORS['success']))
            def flash_off(delay=i * 200 + 100):
                self.root.after(delay, lambda: self.status_label.config(bg=original_bg))
            flash_on()
            flash_off()
    
    def _animate_value_change(self, label, old_value, new_value, duration=500):
        """Animation de changement de valeur (#18)."""
        if self.energy_saving_mode:
            label.config(text=str(new_value))
            return
        
        steps = 20
        step_delay = duration // steps
        delta = (new_value - old_value) / steps
        current = old_value
        step = 0
        
        def animate():
            nonlocal current, step
            if step < steps:
                current += delta
                label.config(text=f"{int(current)}")
                step += 1
                self.root.after(step_delay, animate)
            else:
                label.config(text=str(new_value))
        
        animate()
    
    # ===== MÉTHODES POUR AMÉLIORATION 25: OPTIMISATIONS VISUELLES =====
    
    def _get_cached_data(self, key, ttl=60):
        """Récupère des données du cache (#25)."""
        if key in self.data_cache:
            if key in self.cache_timestamps:
                age = (datetime.now() - self.cache_timestamps[key]).total_seconds()
                if age < ttl:
                    return self.data_cache[key]
                else:
                    # Cache expiré
                    del self.data_cache[key]
                    del self.cache_timestamps[key]
        return None
    
    def _set_cached_data(self, key, value):
        """Met en cache des données (#25)."""
        self.data_cache[key] = value
        self.cache_timestamps[key] = datetime.now()
    
    def _update_loading_indicator(self):
        """Met à jour l'indicateur de charge (#25)."""
        # Vérifier si des opérations sont en cours
        if hasattr(self, 'loading_indicator') and self.loading_indicator is not None:
            # Logique pour déterminer si on charge
            is_loading = False  # À implémenter selon les besoins
            
            try:
                if is_loading:
                    if not self.loading_indicator.winfo_viewable():
                        self.loading_indicator.pack()
                else:
                    if self.loading_indicator.winfo_viewable():
                        self.loading_indicator.pack_forget()
            except (AttributeError, tk.TclError):
                # Widget peut être détruit ou non initialisé
                pass
    
    def toggle_energy_saving(self):
        """Active/désactive le mode économie d'énergie (#25)."""
        self.energy_saving_mode = not self.energy_saving_mode
        if self.energy_saving_mode:
            # Arrêter toutes les animations
            self.animation_queue.clear()
            self.transition_active = False
            if self.status_animation_id:
                self.root.after_cancel(self.status_animation_id)
            
            # Mise à jour visuelle : bouton actif (vert)
            self.energy_btn.config(style='Active.TButton', text="💡 ÉCONOMIE ✓")
            self.energy_indicator.config(text="●", fg=self.COLORS['success'])
            
            self.log("💡 Mode économie d'énergie activé", 'info')
        else:
            # Redémarrer les animations si le bot tourne
            if self.bot_running:
                self._animate_spinner()
                self._animate_status_pulse()
            
            # Mise à jour visuelle : bouton inactif (normal)
            self.energy_btn.config(style='TButton', text="💡 ÉCONOMIE")
            self.energy_indicator.config(text="●", fg=self.COLORS['text_dim'])
            
            self.log("💡 Mode économie d'énergie désactivé", 'info')
    
    # ===== MÉTHODES POUR TRAY ICON (#3) =====
    
    def create_tray_icon_image(self):
        """Crée une icône simple pour le tray."""
        if not HAS_PYSTRAY:
            return None
        
        # Créer une image 64x64 avec un fond transparent
        image = Image.new('RGB', (64, 64), color='#1e1e1e')
        draw = ImageDraw.Draw(image)
        
        # Dessiner un cercle bleu (représentant le bot)
        draw.ellipse([10, 10, 54, 54], fill='#0e639c', outline='#4ec9b0', width=3)
        
        # Dessiner un "M" au centre (pour Medal Bot)
        draw.text((22, 18), "M", fill='white', font=None)
        
        return image
    
    def setup_tray_icon(self):
        """Configure l'icône dans la barre système (#3)."""
        if not HAS_PYSTRAY:
            return
        
        try:
            # Créer l'image de l'icône
            icon_image = self.create_tray_icon_image()
            if not icon_image:
                return
            
            # Créer le menu contextuel
            menu = pystray.Menu(
                pystray.MenuItem("📊 Afficher", self.show_window, default=True),
                pystray.MenuItem("▶️ Démarrer le bot", self.tray_start_bot, enabled=lambda item: not self.bot_running),
                pystray.MenuItem("⏹️ Arrêter le bot", self.tray_stop_bot, enabled=lambda item: self.bot_running),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("📈 Statistiques", self.tray_show_stats),
                pystray.MenuItem("📝 Ouvrir les logs", self.tray_show_logs),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("⚙️ Paramètres", self.tray_show_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ Quitter", self.tray_quit)
            )
            
            # Créer l'icône tray
            self.tray_icon = pystray.Icon(
                "Medal Bot",
                icon_image,
                "Medal Bot - Bot de questionnaires",
                menu
            )
            
            # Démarrer l'icône dans un thread séparé
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()
            
            self.log("✅ Icône système activée (barre des tâches)", 'success')
        except Exception as e:
            self.log(f"⚠️ Impossible de créer l'icône système: {e}", 'warning')
    
    def update_tray_icon_status(self):
        """Met à jour l'icône tray selon l'état du bot (#3)."""
        if not HAS_PYSTRAY or not self.tray_icon:
            return
        
        try:
            # Mettre à jour l'image selon l'état
            if self.bot_running:
                # Icône verte quand le bot tourne
                image = Image.new('RGB', (64, 64), color='#1e1e1e')
                draw = ImageDraw.Draw(image)
                draw.ellipse([10, 10, 54, 54], fill='#4ec9b0', outline='#0e639c', width=3)
                draw.text((22, 18), "M", fill='white', font=None)
            else:
                # Icône grise quand arrêté
                image = Image.new('RGB', (64, 64), color='#1e1e1e')
                draw = ImageDraw.Draw(image)
                draw.ellipse([10, 10, 54, 54], fill='#858585', outline='#3e3e42', width=3)
                draw.text((22, 18), "M", fill='white', font=None)
            
            # Mettre à jour l'icône
            self.tray_icon.icon = image
            
            # Mettre à jour le tooltip
            status_text = "🟢 Bot en cours" if self.bot_running else "⚪ Bot arrêté"
            total = self.stats.get('total', 0)
            success = self.stats.get('success', 0)
            self.tray_icon.title = f"Medal Bot - {status_text} | Total: {total} | Succès: {success}"
        except Exception as e:
            # Erreur silencieuse pour ne pas perturber l'interface
            pass
    
    def on_closing(self):
        """Gère la fermeture de la fenêtre (#3)."""
        if self.minimize_to_tray and HAS_PYSTRAY and self.tray_icon:
            # Minimiser vers le tray au lieu de fermer
            self.hide_window()
        else:
            # Fermer complètement
            self.quit_application()
    
    def hide_window(self):
        """Cache la fenêtre dans le tray (#3)."""
        if not self.is_minimized:
            self.root.withdraw()  # Cache la fenêtre
            self.is_minimized = True
            if HAS_TOAST and self.toast:
                self.toast.show_toast(
                    "Medal Bot",
                    "Application minimisée dans la barre système. Double-cliquez sur l'icône pour restaurer.",
                    duration=3
                )
    
    def show_window(self, icon=None, item=None):
        """Affiche la fenêtre depuis le tray (#3)."""
        if self.is_minimized:
            self.root.deiconify()  # Restaure la fenêtre
            self.root.lift()  # Met au premier plan
            self.root.focus_force()  # Force le focus
            self.is_minimized = False
    
    def tray_start_bot(self, icon=None, item=None):
        """Démarre le bot depuis le menu tray (#3)."""
        if not self.bot_running:
            self.root.after(0, self.start_bot)
            if HAS_TOAST and self.toast:
                self.toast.show_toast(
                    "Medal Bot",
                    "Bot démarré depuis la barre système",
                    duration=2
                )
    
    def tray_stop_bot(self, icon=None, item=None):
        """Arrête le bot depuis le menu tray (#3)."""
        if self.bot_running:
            self.root.after(0, self.stop_bot)
            if HAS_TOAST and self.toast:
                self.toast.show_toast(
                    "Medal Bot",
                    "Bot arrêté depuis la barre système",
                    duration=2
                )
    
    def tray_show_stats(self, icon=None, item=None):
        """Affiche la fenêtre sur l'onglet statistiques (#3)."""
        self.show_window()
        if hasattr(self, 'notebook'):
            self.root.after(100, lambda: self.notebook.select(1))  # Onglet Récents (stats)
    
    def tray_show_logs(self, icon=None, item=None):
        """Affiche la fenêtre sur l'onglet logs (#3)."""
        self.show_window()
        if hasattr(self, 'notebook'):
            self.root.after(100, lambda: self.notebook.select(0))  # Onglet Console
    
    def tray_show_settings(self, icon=None, item=None):
        """Affiche la fenêtre principale (#3)."""
        self.show_window()
    
    def tray_quit(self, icon=None, item=None):
        """Quitte l'application depuis le tray (#3)."""
        if self.bot_running:
            # Demander confirmation si le bot tourne
            self.show_window()
            if messagebox.askyesno(
                "Confirmation",
                "Le bot est en cours d'exécution. Voulez-vous vraiment quitter ?"
            ):
                self.quit_application()
        else:
            self.quit_application()
    
    def quit_application(self):
        """Ferme complètement l'application (#3)."""
        # Arrêter le bot si en cours
        if self.bot_running:
            self.stop_bot()
            # Attendre un peu que le bot s'arrête
            import time
            time.sleep(1)
        
        # Arrêter l'icône tray
        if HAS_PYSTRAY and self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
        
        # Arrêter la sauvegarde automatique
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)
        
        # Fermer la fenêtre
        self.root.quit()
        self.root.destroy()
    
    def start_auto_save(self):
        """Démarre la sauvegarde automatique des stats (#4)."""
        self.save_stats()
        self.auto_save_timer = self.root.after(self.auto_save_interval * 1000, self.start_auto_save)
    
    def create_avis_editor_tab(self):
        """Onglet 5: Éditeur d'avis par catégorie (#1)."""
        tab = ttk.Frame(self.notebook, padding="12")
        self.notebook.add(tab, text="✏️ ÉDITEUR D'AVIS")
        
        # Configuration du grid
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        
        # Barre d'outils
        toolbar = tk.Frame(tab, bg=self.COLORS['bg_medium'])
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Sélecteur de catégorie
        tk.Label(toolbar, text="Catégorie:", font=('Segoe UI', 9),
                bg=self.COLORS['bg_medium'], fg=self.COLORS['text']).pack(side=tk.LEFT, padx=5)
        
        from bot.config import AVIS_MAPPING
        categories = list(AVIS_MAPPING.keys())
        self.avis_category_var = tk.StringVar(value=categories[0] if categories else 'drive')
        category_menu = ttk.Combobox(toolbar, textvariable=self.avis_category_var, 
                                     values=categories, state='readonly', width=25)
        category_menu.pack(side=tk.LEFT, padx=5)
        category_menu.bind('<<ComboboxSelected>>', lambda e: self._load_avis_for_category())
        
        # Boutons
        save_btn = tk.Button(toolbar, text="💾 Sauvegarder", command=self._save_avis_category,
                            bg=self.COLORS['success'], fg='white',
                            font=('Segoe UI', 9), relief='flat', padx=10, pady=2)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        reload_btn = tk.Button(toolbar, text="🔄 Recharger", command=self._load_avis_for_category,
                              bg=self.COLORS['accent_blue'], fg='white',
                              font=('Segoe UI', 9), relief='flat', padx=10, pady=2)
        reload_btn.pack(side=tk.LEFT, padx=5)
        
        # Zone de texte pour éditer les avis
        text_frame = ttk.Frame(tab)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.avis_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text'],
            insertbackground=self.COLORS['text']
        )
        self.avis_text.pack(fill=tk.BOTH, expand=True)
        
        # Info
        info_label = tk.Label(tab, text="💡 Un avis par ligne. Les lignes vides sont ignorées.",
                             font=('Segoe UI', 8), bg=self.COLORS['bg_dark'],
                             fg=self.COLORS['text_dim'])
        info_label.grid(row=2, column=0, pady=(5, 0))
        
        # Charger la première catégorie
        self._load_avis_for_category()
    
    def _load_avis_for_category(self):
        """Charge les avis pour la catégorie sélectionnée."""
        try:
            from bot.config import AVIS_MAPPING
            category = self.avis_category_var.get()
            avis_file = AVIS_MAPPING.get(category)
            
            if not avis_file or not os.path.exists(avis_file):
                self.avis_text.delete('1.0', tk.END)
                self.avis_text.insert('1.0', f"⚠️ Fichier introuvable: {avis_file}")
                return
            
            with open(avis_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.avis_text.delete('1.0', tk.END)
            self.avis_text.insert('1.0', content)
            
        except Exception as e:
            self.log(f"❌ Erreur lors du chargement des avis: {e}", 'error')
    
    def _save_avis_category(self):
        """Sauvegarde les avis de la catégorie sélectionnée."""
        try:
            from bot.config import AVIS_MAPPING
            category = self.avis_category_var.get()
            avis_file = AVIS_MAPPING.get(category)
            
            if not avis_file:
                self.log(f"❌ Catégorie invalide: {category}", 'error')
                return
            
            content = self.avis_text.get('1.0', tk.END).strip()
            
            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(avis_file), exist_ok=True)
            
            with open(avis_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Invalider le cache
            from bot.utils.avis_manager import avis_manager
            if avis_file in avis_manager._cache:
                del avis_manager._cache[avis_file]
            
            self.log(f"✅ Avis sauvegardés pour {category}", 'success')
            
        except Exception as e:
            self.log(f"❌ Erreur lors de la sauvegarde: {e}", 'error')
    
    def _validate_avis_files_startup(self):
        """Valide les fichiers d'avis au démarrage (#12)."""
        try:
            from bot.utils.avis_manager import avis_manager
            results = avis_manager.validate_avis_files()
            
            invalid_files = []
            for category, (is_valid, message) in results.items():
                if not is_valid:
                    invalid_files.append(f"{category}: {message}")
            
            if invalid_files:
                warning_msg = "⚠️ Problèmes détectés dans les fichiers d'avis:\n" + "\n".join(invalid_files)
                self.log(warning_msg, 'warning')
                messagebox.showwarning("Validation des fichiers d'avis", 
                                     warning_msg + "\n\nVeuillez vérifier les fichiers dans l'onglet Éditeur d'avis.")
            else:
                self.log("✅ Tous les fichiers d'avis sont valides", 'success')
        except Exception as e:
            self.log(f"⚠️ Erreur lors de la validation: {e}", 'warning')
    
    def _track_category_result(self, category: str, success: bool):
        """Enregistre le résultat par catégorie pour calculer les taux (#9)."""
        if 'category_success' not in self.stats:
            self.stats['category_success'] = {}
        if 'category_failed' not in self.stats:
            self.stats['category_failed'] = {}
        
        if success:
            self.stats['category_success'][category] = self.stats['category_success'].get(category, 0) + 1
        else:
            self.stats['category_failed'][category] = self.stats['category_failed'].get(category, 0) + 1


def main():
    """Point d'entrée de l'application."""
    root = tk.Tk()
    app = MedalBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
