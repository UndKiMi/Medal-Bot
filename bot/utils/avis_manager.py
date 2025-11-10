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
                    self._cache[avis_file] = [line.strip() for line in f if line.strip()]
            
            avis_list = self._cache[avis_file]
            
            if not avis_list:
                logger.error(f"❌ Aucun avis trouvé dans le fichier: {avis_file}")
                return "Excellent service, très satisfait de ma visite !"
            
            selected_avis = random.choice(avis_list)
            logger.info(f"📝 Avis sélectionné: {selected_avis[:50]}...")
            
            return selected_avis
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sélection de l'avis: {e}")
            return "Excellent service, très satisfait de ma visite !"
