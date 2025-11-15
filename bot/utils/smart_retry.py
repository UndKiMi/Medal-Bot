#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Système de retry intelligent amélioré (#29)."""

import logging
import time
from typing import Callable, Optional, Dict, List
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SmartRetry:
    """Système de retry intelligent avec détection d'erreurs récurrentes."""
    
    def __init__(self):
        """Initialise le système de retry intelligent."""
        self.error_history = defaultdict(list)  # Historique des erreurs par fonction
        self.error_patterns = {}  # Patterns d'erreurs détectés
        self.max_error_count = 5  # Nombre max d'erreurs avant pause
        self.pause_duration = 300  # Durée de pause en secondes (5 minutes)
        self.paused_functions = {}  # Fonctions en pause
    
    def smart_retry(self, max_retries: int = 3, delay: float = 2.0, backoff: float = 1.5, 
                   min_backoff: float = 1.0, max_backoff: float = 60.0):
        """
        Décorateur de retry intelligent avec backoff exponentiel amélioré.
        
        Args:
            max_retries: Nombre maximum de tentatives
            delay: Délai initial entre les tentatives (secondes)
            backoff: Multiplicateur pour augmenter le délai
            min_backoff: Délai minimum
            max_backoff: Délai maximum
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                func_name = func.__name__
                
                # Vérifier si la fonction est en pause
                if func_name in self.paused_functions:
                    pause_until = self.paused_functions[func_name]
                    if datetime.now() < pause_until:
                        remaining = (pause_until - datetime.now()).total_seconds()
                        logger.warning(f"⏸️ Fonction {func_name} en pause pour {remaining:.0f} secondes (trop d'erreurs)")
                        raise Exception(f"Function paused due to repeated failures. Resumes in {remaining:.0f}s")
                    else:
                        # Pause terminée, réinitialiser
                        del self.paused_functions[func_name]
                        self.error_history[func_name].clear()
                
                current_delay = delay
                last_exception = None
                errors_in_attempt = []
                
                for attempt in range(1, max_retries + 1):
                    try:
                        result = func(*args, **kwargs)
                        
                        # Succès - enregistrer et retourner
                        if attempt > 1:
                            logger.info(f"✅ {func_name} réussi après {attempt} tentatives")
                        
                        # Réinitialiser l'historique d'erreurs en cas de succès
                        if len(self.error_history[func_name]) > 0:
                            self.error_history[func_name].clear()
                        
                        return result
                        
                    except Exception as e:
                        last_exception = e
                        error_msg = str(e)
                        errors_in_attempt.append(error_msg)
                        
                        # Enregistrer l'erreur
                        self.error_history[func_name].append({
                            'timestamp': datetime.now(),
                            'error': error_msg,
                            'attempt': attempt
                        })
                        
                        # Nettoyer l'historique (garder seulement les 20 dernières erreurs)
                        if len(self.error_history[func_name]) > 20:
                            self.error_history[func_name] = self.error_history[func_name][-20:]
                        
                        # Vérifier les erreurs récurrentes
                        if self._detect_recurrent_errors(func_name):
                            pause_until = datetime.now() + timedelta(seconds=self.pause_duration)
                            self.paused_functions[func_name] = pause_until
                            logger.error(f"🚨 Trop d'erreurs récurrentes pour {func_name}. Pause de {self.pause_duration}s")
                            raise Exception(f"Too many recurrent errors. Function paused for {self.pause_duration}s")
                        
                        if attempt < max_retries:
                            # Backoff exponentiel avec limites
                            logger.warning(f"⚠️ Tentative {attempt}/{max_retries} échouée pour {func_name}: {error_msg[:100]}")
                            
                            # Calculer le délai avec backoff
                            current_delay = min(max(current_delay * backoff, min_backoff), max_backoff)
                            
                            # Ajouter un peu de jitter pour éviter les thundering herds
                            jitter = current_delay * 0.1 * (0.5 - time.time() % 1)
                            sleep_time = current_delay + jitter
                            
                            time.sleep(sleep_time)
                        else:
                            logger.error(f"❌ {func_name} a échoué après {max_retries} tentatives")
                
                raise last_exception
            return wrapper
        return decorator
    
    def _detect_recurrent_errors(self, func_name: str) -> bool:
        """Détecte si une fonction a trop d'erreurs récurrentes."""
        errors = self.error_history.get(func_name, [])
        if len(errors) < self.max_error_count:
            return False
        
        # Vérifier les erreurs récentes (dernières 10 minutes)
        recent_errors = [
            e for e in errors 
            if (datetime.now() - e['timestamp']).total_seconds() < 600
        ]
        
        if len(recent_errors) >= self.max_error_count:
            # Vérifier si ce sont les mêmes erreurs
            error_messages = [e['error'] for e in recent_errors]
            unique_errors = set(error_messages)
            
            # Si moins de 3 types d'erreurs différents, c'est récurrent
            if len(unique_errors) <= 2:
                return True
        
        return False
    
    def reset_function(self, func_name: str):
        """Réinitialise l'historique d'erreurs d'une fonction."""
        if func_name in self.error_history:
            self.error_history[func_name].clear()
        if func_name in self.paused_functions:
            del self.paused_functions[func_name]
        logger.info(f"✅ Historique d'erreurs réinitialisé pour {func_name}")


# Instance globale
smart_retry = SmartRetry()

