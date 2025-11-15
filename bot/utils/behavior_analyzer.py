#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyse comportementale pour simulation humaine améliorée (#51)."""

import logging
import random
import time
from typing import Dict, List, Tuple
from collections import deque

logger = logging.getLogger(__name__)


class BehaviorAnalyzer:
    """Analyse et améliore le comportement humain simulé."""
    
    def __init__(self):
        """Initialise l'analyseur comportemental."""
        self.typing_patterns = deque(maxlen=100)  # Patterns de frappe
        self.mouse_movements = deque(maxlen=100)  # Mouvements de souris
        self.action_timings = deque(maxlen=100)  # Temps entre actions
        self.human_variance = 0.15  # Variance pour rendre plus humain
    
    def get_typing_delay(self, char: str, base_delay: float = 0.08) -> float:
        """
        Calcule un délai de frappe plus humain.
        
        Args:
            char: Caractère à taper
            base_delay: Délai de base
        
        Returns:
            Délai ajusté
        """
        # Variations selon le type de caractère
        if char == ' ':
            delay = base_delay * random.uniform(1.5, 2.5)  # Espaces plus lents
        elif char.isupper():
            delay = base_delay * random.uniform(1.2, 1.8)  # Majuscules (Shift)
        elif char in '.,!?;:':
            delay = base_delay * random.uniform(1.3, 2.0)  # Ponctuation
        elif char.isdigit():
            delay = base_delay * random.uniform(0.9, 1.3)  # Chiffres
        else:
            delay = base_delay * random.uniform(0.8, 1.2)  # Lettres normales
        
        # Ajouter de la variance humaine
        variance = delay * self.human_variance * (random.random() - 0.5) * 2
        final_delay = max(0.05, delay + variance)
        
        # Enregistrer le pattern
        self.typing_patterns.append({
            'char': char,
            'delay': final_delay,
            'timestamp': time.time()
        })
        
        return final_delay
    
    def get_action_delay(self, action_type: str, base_delay: float = 1.0) -> float:
        """
        Calcule un délai entre actions plus humain.
        
        Args:
            action_type: Type d'action (click, scroll, etc.)
            base_delay: Délai de base
        
        Returns:
            Délai ajusté
        """
        # Délais différents selon le type d'action
        multipliers = {
            'click': random.uniform(0.8, 1.5),
            'scroll': random.uniform(0.5, 1.2),
            'type': random.uniform(1.0, 2.0),
            'read': random.uniform(1.5, 3.0),  # Lecture plus lente
            'think': random.uniform(0.5, 2.0)  # Réflexion variable
        }
        
        multiplier = multipliers.get(action_type, 1.0)
        delay = base_delay * multiplier
        
        # Ajouter de la variance
        variance = delay * self.human_variance * (random.random() - 0.5) * 2
        final_delay = max(0.3, delay + variance)
        
        # Enregistrer
        self.action_timings.append({
            'type': action_type,
            'delay': final_delay,
            'timestamp': time.time()
        })
        
        return final_delay
    
    def should_add_hesitation(self) -> bool:
        """Détermine si on doit ajouter une hésitation (comportement humain)."""
        # 5% de chance d'hésiter
        return random.random() < 0.05
    
    def get_hesitation_delay(self) -> float:
        """Retourne un délai d'hésitation."""
        return random.uniform(0.5, 2.0)
    
    def get_mouse_movement_path(self, start: Tuple[int, int], 
                                end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Génère un chemin de mouvement de souris plus humain (courbe de Bézier simplifiée).
        
        Args:
            start: Point de départ (x, y)
            end: Point d'arrivée (x, y)
        
        Returns:
            Liste de points pour le mouvement
        """
        # Mouvement linéaire avec légère courbure
        steps = random.randint(5, 15)
        path = []
        
        for i in range(steps + 1):
            t = i / steps
            
            # Courbe de Bézier quadratique simple
            # Point de contrôle aléatoire pour la courbure
            control_x = (start[0] + end[0]) / 2 + random.randint(-50, 50)
            control_y = (start[1] + end[1]) / 2 + random.randint(-50, 50)
            
            x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control_x + t ** 2 * end[0]
            y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control_y + t ** 2 * end[1]
            
            path.append((int(x), int(y)))
        
        return path
    
    def get_reading_time(self, text_length: int) -> float:
        """
        Calcule le temps de lecture d'un texte.
        
        Args:
            text_length: Longueur du texte en caractères
        
        Returns:
            Temps de lecture en secondes
        """
        # Vitesse de lecture moyenne: 200-300 mots/minute
        # Environ 5 caractères par mot
        words = text_length / 5
        reading_speed = random.uniform(200, 300)  # mots/minute
        reading_time = (words / reading_speed) * 60  # en secondes
        
        # Ajouter de la variance
        variance = reading_time * 0.2 * (random.random() - 0.5) * 2
        return max(1.0, reading_time + variance)


# Instance globale
behavior_analyzer = BehaviorAnalyzer()

