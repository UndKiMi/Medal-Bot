#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optimisation des ressources Chrome (#34)."""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ResourceOptimizer:
    """Optimise l'utilisation des ressources Chrome."""
    
    def __init__(self):
        """Initialise l'optimiseur de ressources."""
        self.optimization_enabled = True
    
    def get_optimized_chrome_options(self) -> List[str]:
        """
        Retourne les options Chrome optimisées pour réduire l'utilisation des ressources.
        
        Returns:
            Liste des arguments Chrome
        """
        options = [
            # Désactiver les fonctionnalités inutiles
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-breakpad',
            '--disable-client-side-phishing-detection',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-features=TranslateUI',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-popup-blocking',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-sync',
            '--disable-translate',
            '--disable-web-resources',
            '--metrics-recording-only',
            '--no-first-run',
            '--safebrowsing-disable-auto-update',
            '--enable-automation',
            '--password-store=basic',
            '--use-mock-keychain',
            
            # Optimisations mémoire
            '--memory-pressure-off',
            '--max_old_space_size=4096',  # Limiter la mémoire JS
            
            # Désactiver GPU si possible (réduit la mémoire)
            '--disable-gpu',
            '--disable-software-rasterizer',
            
            # Autres optimisations
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
        ]
        
        return options
    
    def get_optimized_prefs(self) -> Dict:
        """
        Retourne les préférences Chrome optimisées.
        
        Returns:
            Dict des préférences
        """
        return {
            # Désactiver les fonctionnalités consommatrices
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.geolocation": 2,
            "profile.default_content_setting_values.media_stream": 2,
            "credentials_enable_service": False,
            "password_manager_enabled": False,
            
            # Optimisations de performance
            "profile.managed_default_content_settings.images": 1,  # Charger les images (nécessaire pour le bot)
            "profile.default_content_setting_values.plugins": 2,  # Désactiver les plugins
            "profile.content_settings.plugin_whitelist.adobe-flash-player": False,
            "profile.content_settings.exceptions.plugins.*,*.per_resource.adobe-flash-player": False,
            
            # Réduire la consommation mémoire
            "profile.default_content_setting_values.popups": 2,
            "profile.default_content_setting_values.mouselock": 2,
            "profile.default_content_setting_values.midi_sysex": 2,
            "profile.default_content_setting_values.push_messaging": 2,
        }
    
    def get_memory_optimization_tips(self) -> List[str]:
        """Retourne des conseils pour optimiser la mémoire."""
        return [
            "Fermer les onglets inutiles",
            "Réduire le nombre d'extensions",
            "Désactiver les animations",
            "Utiliser le mode headless si possible",
            "Redémarrer Chrome périodiquement",
            "Limiter le nombre de processus Chrome"
        ]


# Instance globale
resource_optimizer = ResourceOptimizer()

