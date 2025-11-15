#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gestion des avis clients."""

import os
import random
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class AvisManager:
    """Gestionnaire des fichiers d'avis."""
    
    def __init__(self, avis_mapping: Dict[str, str]):
        """Initialise le gestionnaire d'avis."""
        self.avis_mapping = avis_mapping
        self._cache = {}
        self._recent_avis = {}  # Pour rotation intelligente (#11)
        self._max_recent = 5  # Nombre d'avis récents à éviter
    
    def load_avis(self, category: str = None) -> str:
        """Charge un avis aléatoire depuis les fichiers."""
        try:
            # Déterminer le fichier à utiliser
            if not category or category not in self.avis_mapping:
                avis_file = self.avis_mapping.get('drive')
            else:
                avis_file = self.avis_mapping.get(category)
            
            # Vérifier si le fichier existe
            if not os.path.exists(avis_file):
                logger.error(f"❌ Fichier d'avis introuvable: {avis_file}")
                return "Excellent service, très satisfait de ma visite !"
            
            # Charger depuis le cache ou lire le fichier
            if avis_file not in self._cache:
                with open(avis_file, 'r', encoding='utf-8') as f:
                    avis_lines = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('AVIS'):
                            import re
                            cleaned_line = re.sub(r'^\d+\.\s*', '', line)
                            if cleaned_line:
                                avis_lines.append(cleaned_line)
                    self._cache[avis_file] = avis_lines
            
            avis_list = self._cache[avis_file]
            
            if not avis_list:
                logger.error(f"❌ Aucun avis trouvé dans le fichier: {avis_file}")
                return "Excellent service, très satisfait de ma visite !"
            
            # Rotation intelligente (#11) - Éviter de répéter les mêmes avis
            recent = self._recent_avis.get(avis_file, [])
            available_avis = [a for a in avis_list if a not in recent]
            
            # Si tous les avis ont été récemment utilisés, réinitialiser
            if not available_avis:
                available_avis = avis_list
                recent = []
            
            selected_avis = random.choice(available_avis)
            
            # Ajouter à la liste des récents
            recent.append(selected_avis)
            if len(recent) > self._max_recent:
                recent.pop(0)
            self._recent_avis[avis_file] = recent
            
            return selected_avis
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sélection de l'avis: {e}")
            return "Excellent service, très satisfait de ma visite !"
    
    def validate_avis_files(self) -> Dict[str, tuple]:
        """
        Valide tous les fichiers d'avis (#12).
        
        Returns:
            Dict[str, tuple]: {category: (is_valid, message)}
        """
        results = {}
        for category, avis_file in self.avis_mapping.items():
            is_valid = True
            message = "OK"
            
            if not os.path.exists(avis_file):
                is_valid = False
                message = f"Fichier introuvable: {avis_file}"
            else:
                try:
                    with open(avis_file, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('AVIS')]
                        if not lines:
                            is_valid = False
                            message = "Fichier vide"
                        elif len(lines) < 3:
                            is_valid = False
                            message = f"Trop peu d'avis ({len(lines)}), minimum 3 recommandé"
                except Exception as e:
                    is_valid = False
                    message = f"Erreur de lecture: {str(e)}"
            
            results[category] = (is_valid, message)
        
        return results
