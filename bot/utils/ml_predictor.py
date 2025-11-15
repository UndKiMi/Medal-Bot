#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prédictions ML pour optimiser l'exécution (#50)."""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class MLPredictor:
    """Prédictions simples basées sur l'historique (ML simplifié)."""
    
    def __init__(self):
        """Initialise le prédicteur ML."""
        self.success_history = []  # Historique des succès/échecs
        self.timing_history = []  # Historique des temps d'exécution
        self.hourly_success = defaultdict(list)  # Succès par heure
    
    def predict_best_time(self, hours_ahead: int = 24) -> Optional[Dict]:
        """
        Prédit le meilleur moment pour exécuter un questionnaire.
        
        Args:
            hours_ahead: Nombre d'heures à prédire
        
        Returns:
            Dict avec les prédictions
        """
        if not self.hourly_success:
            return None
        
        # Calculer le taux de succès par heure
        hourly_rates = {}
        for hour, successes in self.hourly_success.items():
            if successes:
                success_rate = sum(1 for s in successes if s) / len(successes)
                hourly_rates[hour] = success_rate
        
        if not hourly_rates:
            return None
        
        # Trouver les meilleures heures
        sorted_hours = sorted(hourly_rates.items(), key=lambda x: x[1], reverse=True)
        best_hours = sorted_hours[:3]  # Top 3
        
        # Prédire pour les prochaines heures
        now = datetime.now()
        predictions = []
        
        for hour_offset in range(hours_ahead):
            target_time = now + timedelta(hours=hour_offset)
            target_hour = target_time.hour
            
            if target_hour in hourly_rates:
                predictions.append({
                    'time': target_time,
                    'hour': target_hour,
                    'predicted_success_rate': hourly_rates[target_hour],
                    'confidence': min(len(self.hourly_success[target_hour]), 10) / 10  # Basé sur le nombre de données
                })
        
        if predictions:
            best_prediction = max(predictions, key=lambda x: x['predicted_success_rate'])
            return {
                'best_time': best_prediction['time'],
                'best_hour': best_prediction['hour'],
                'predicted_rate': best_prediction['predicted_success_rate'],
                'confidence': best_prediction['confidence'],
                'all_predictions': predictions
            }
        
        return None
    
    def detect_error_patterns(self) -> List[Dict]:
        """
        Détecte les patterns d'erreur récurrents.
        
        Returns:
            Liste des patterns détectés
        """
        if len(self.success_history) < 10:
            return []
        
        # Analyser les échecs récents
        recent_failures = [
            h for h in self.success_history[-50:] 
            if not h.get('success', False)
        ]
        
        if len(recent_failures) < 3:
            return []
        
        # Grouper par heure
        failures_by_hour = defaultdict(int)
        for failure in recent_failures:
            hour = failure.get('hour', 0)
            failures_by_hour[hour] += 1
        
        # Détecter les heures problématiques
        patterns = []
        total_failures = len(recent_failures)
        
        for hour, count in failures_by_hour.items():
            if count / total_failures > 0.3:  # Plus de 30% des échecs à cette heure
                patterns.append({
                    'type': 'hourly_failure_pattern',
                    'hour': hour,
                    'failure_count': count,
                    'failure_rate': count / total_failures,
                    'recommendation': f'Éviter les exécutions à {hour}h'
                })
        
        return patterns
    
    def record_execution(self, success: bool, duration: float, hour: Optional[int] = None):
        """Enregistre une exécution pour l'apprentissage."""
        if hour is None:
            hour = datetime.now().hour
        
        self.success_history.append({
            'success': success,
            'duration': duration,
            'hour': hour,
            'timestamp': datetime.now()
        })
        
        self.timing_history.append(duration)
        self.hourly_success[hour].append(success)
        
        # Garder seulement les 1000 derniers
        if len(self.success_history) > 1000:
            self.success_history = self.success_history[-1000:]
        if len(self.timing_history) > 1000:
            self.timing_history = self.timing_history[-1000:]
    
    def predict_duration(self) -> Optional[float]:
        """Prédit la durée d'exécution d'un questionnaire."""
        if not self.timing_history:
            return None
        
        # Utiliser la moyenne des 10 derniers
        recent_timings = self.timing_history[-10:]
        return sum(recent_timings) / len(recent_timings)


# Instance globale
ml_predictor = MLPredictor()

