#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Statistiques avancées pour Medal Bot (#3)."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class AdvancedStats:
    """Gestionnaire de statistiques avancées."""
    
    def __init__(self, stats_data: Dict):
        """Initialise avec les données de stats existantes."""
        self.stats = stats_data
    
    def get_step_times(self) -> Dict[str, float]:
        """Calcule le temps moyen par étape (#3)."""
        step_times = self.stats.get('step_times', {})
        if not step_times:
            return {}
        
        averages = {}
        for step_name, times in step_times.items():
            if times:
                averages[step_name] = sum(times) / len(times)
        
        return averages
    
    def get_success_rate_by_hour(self) -> Dict[int, Dict[str, int]]:
        """Calcule le taux de réussite par heure de la journée (#3)."""
        daily_stats = self.stats.get('daily_stats', {})
        hour_stats = defaultdict(lambda: {'success': 0, 'failed': 0, 'total': 0})
        
        for day, hours in daily_stats.items():
            if isinstance(hours, dict):
                for hour_str, hour_data in hours.items():
                    if isinstance(hour_data, dict):
                        try:
                            hour = int(hour_str)
                            hour_stats[hour]['success'] += hour_data.get('success', 0)
                            hour_stats[hour]['failed'] += hour_data.get('failed', 0)
                            hour_stats[hour]['total'] += hour_stats[hour]['success'] + hour_stats[hour]['failed']
                        except (ValueError, TypeError):
                            continue
        
        return dict(hour_stats)
    
    def get_failure_causes(self) -> List[Tuple[str, int]]:
        """Analyse les causes d'échec les plus fréquentes (#3)."""
        failure_causes = self.stats.get('failure_causes', {})
        if not failure_causes:
            return []
        
        # Trier par fréquence décroissante
        sorted_causes = sorted(failure_causes.items(), key=lambda x: x[1], reverse=True)
        return sorted_causes[:10]  # Top 10
    
    def estimate_time_to_quota(self, quota: int, current_count: int) -> Optional[float]:
        """Prédit le temps restant pour atteindre le quota (#3)."""
        if current_count >= quota:
            return 0.0
        
        # Calculer la vitesse moyenne (questionnaires/heure)
        durations = self.stats.get('durations', [])
        if not durations or len(durations) < 3:
            return None
        
        # Utiliser les 10 derniers questionnaires pour la prédiction
        recent_durations = durations[-10:]
        avg_duration = sum(recent_durations) / len(recent_durations)
        
        # Temps entre questionnaires (en secondes)
        between_questionnaires = self.stats.get('avg_between_time', 60)
        
        # Temps total estimé pour un questionnaire
        total_time_per_survey = avg_duration + between_questionnaires
        
        # Questionnaires restants
        remaining = quota - current_count
        
        # Temps estimé en heures
        estimated_seconds = remaining * total_time_per_survey
        estimated_hours = estimated_seconds / 3600
        
        return estimated_hours
    
    def get_comparative_stats(self, period: str = 'week') -> Dict:
        """Statistiques comparatives (jour/semaine/mois) (#3)."""
        now = datetime.now()
        stats = {
            'period': period,
            'total': 0,
            'success': 0,
            'failed': 0,
            'success_rate': 0.0,
            'avg_duration': 0.0
        }
        
        if period == 'day':
            start_date = now.date()
        elif period == 'week':
            start_date = (now - timedelta(days=7)).date()
        elif period == 'month':
            start_date = (now - timedelta(days=30)).date()
        else:
            return stats
        
        daily_stats = self.stats.get('daily_stats', {})
        durations = []
        
        for day_str, hours in daily_stats.items():
            try:
                day_date = datetime.strptime(day_str, "%Y-%m-%d").date()
                if day_date >= start_date:
                    if isinstance(hours, dict):
                        for hour_data in hours.values():
                            if isinstance(hour_data, dict):
                                stats['success'] += hour_data.get('success', 0)
                                stats['failed'] += hour_data.get('failed', 0)
            except (ValueError, TypeError):
                continue
        
        stats['total'] = stats['success'] + stats['failed']
        if stats['total'] > 0:
            stats['success_rate'] = (stats['success'] / stats['total']) * 100
        
        # Durée moyenne
        all_durations = self.stats.get('durations', [])
        if all_durations:
            stats['avg_duration'] = sum(all_durations) / len(all_durations)
        
        return stats
    
    def record_step_time(self, step_name: str, duration: float):
        """Enregistre le temps d'exécution d'une étape."""
        if 'step_times' not in self.stats:
            self.stats['step_times'] = {}
        
        if step_name not in self.stats['step_times']:
            self.stats['step_times'][step_name] = []
        
        self.stats['step_times'][step_name].append(duration)
        
        # Garder seulement les 100 derniers
        if len(self.stats['step_times'][step_name]) > 100:
            self.stats['step_times'][step_name] = self.stats['step_times'][step_name][-100:]
    
    def record_failure_cause(self, cause: str):
        """Enregistre une cause d'échec."""
        if 'failure_causes' not in self.stats:
            self.stats['failure_causes'] = {}
        
        self.stats['failure_causes'][cause] = self.stats['failure_causes'].get(cause, 0) + 1

