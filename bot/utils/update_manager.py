#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gestionnaire de mises à jour (#8)."""

import logging
import json
import os
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class UpdateManager:
    """Gère les mises à jour automatiques."""
    
    VERSION = "1.0.0"  # Version actuelle
    UPDATE_CHECK_URL = "https://api.github.com/repos/yourusername/medal-bot/releases/latest"  # À configurer
    CHECK_INTERVAL_HOURS = 24  # Vérifier toutes les 24h
    
    def __init__(self):
        """Initialise le gestionnaire de mises à jour."""
        self.data_file = Path(__file__).parent.parent.parent / "update_data.json"
        self.last_check = None
        self._load_data()
    
    def _load_data(self):
        """Charge les données de mise à jour."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    last_check_str = data.get('last_check')
                    if last_check_str:
                        self.last_check = datetime.fromisoformat(last_check_str)
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du chargement des données de mise à jour: {e}")
    
    def _save_data(self):
        """Sauvegarde les données de mise à jour."""
        try:
            data = {
                'last_check': self.last_check.isoformat() if self.last_check else None
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de la sauvegarde des données de mise à jour: {e}")
    
    def should_check_update(self) -> bool:
        """Vérifie si une vérification de mise à jour est nécessaire."""
        if not self.last_check:
            return True
        
        from datetime import timedelta
        time_since_check = datetime.now() - self.last_check
        return time_since_check.total_seconds() >= (self.CHECK_INTERVAL_HOURS * 3600)
    
    def check_for_updates(self) -> Optional[Dict]:
        """
        Vérifie les mises à jour disponibles.
        
        Returns:
            Dict avec les infos de mise à jour ou None
        """
        if not HAS_REQUESTS:
            logger.warning("⚠️ Module 'requests' non disponible pour vérifier les mises à jour")
            return None
        
        try:
            response = requests.get(self.UPDATE_CHECK_URL, timeout=10)
            response.raise_for_status()
            release_data = response.json()
            
            latest_version = release_data.get('tag_name', '').lstrip('v')
            if self._is_newer_version(latest_version, self.VERSION):
                self.last_check = datetime.now()
                self._save_data()
                
                return {
                    'available': True,
                    'current_version': self.VERSION,
                    'latest_version': latest_version,
                    'release_notes': release_data.get('body', ''),
                    'download_url': release_data.get('html_url', ''),
                    'published_at': release_data.get('published_at', '')
                }
            else:
                self.last_check = datetime.now()
                self._save_data()
                return {'available': False, 'current_version': self.VERSION}
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de la vérification des mises à jour: {e}")
            return None
    
    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """Compare deux versions (format semver)."""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # Normaliser à 3 parties
            while len(v1_parts) < 3:
                v1_parts.append(0)
            while len(v2_parts) < 3:
                v2_parts.append(0)
            
            for i in range(3):
                if v1_parts[i] > v2_parts[i]:
                    return True
                elif v1_parts[i] < v2_parts[i]:
                    return False
            
            return False
        except:
            return False
    
    def get_changelog(self) -> str:
        """Récupère le changelog."""
        # Pour l'instant, retourne un changelog statique
        # Peut être amélioré pour récupérer depuis GitHub
        return f"""
Version {self.VERSION} - Changelog

Nouvelles fonctionnalités:
- Statistiques avancées
- Détection CAPTCHA améliorée
- Thèmes personnalisables
- Interface responsive
- Notifications Discord avancées
- Et bien plus...
        """.strip()


# Instance globale
update_manager = UpdateManager()

