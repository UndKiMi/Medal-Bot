#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Planificateur intelligent pour les questionnaires."""

import random
import logging
import json
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class QuestionnaireScheduler:
    """Gère la planification des questionnaires selon les horaires de l'établissement."""
    
    # Horaires d'ouverture de l'établissement
    OPENING_HOURS = {
        0: (time(9, 0), time(22, 30)),   # Lundi
        1: (time(9, 0), time(22, 30)),   # Mardi
        2: (time(9, 0), time(22, 30)),   # Mercredi
        3: (time(9, 0), time(22, 30)),   # Jeudi
        4: (time(9, 0), time(23, 0)),    # Vendredi
        5: (time(9, 0), time(23, 0)),    # Samedi
        6: (time(9, 0), time(22, 30)),   # Dimanche
    }
    
    # Règles du bot
    BOT_START_TIME = time(11, 30)       # Jamais avant 11h30
    BOT_END_TIME = time(21, 38)         # Jamais après 21h38
    DAILY_QUESTIONNAIRES = 6            # 6 questionnaires par jour
    MAX_PAST_MINUTES = 5                # Maximum 5 minutes dans le passé
    
    def __init__(self):
        self.data_file = Path(__file__).parent.parent / "scheduler_data.json"
        self._load_data()
    
    def _load_data(self):
        """Charge les données depuis le fichier JSON."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.today_count = data.get('today_count', 0)
                    last_date_str = data.get('last_reset_date')
                    if last_date_str:
                        self.last_reset_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
                    else:
                        self.last_reset_date = datetime.now().date()
                    
                    self.completed_times = data.get('completed_times', [])
                    self.next_scheduled_time = data.get('next_scheduled_time')
                    
                    logger.info(f"📂 Données chargées: {self.today_count} questionnaires aujourd'hui ({self.last_reset_date})")
                    if self.completed_times:
                        logger.info(f"📅 Horaires effectués: {', '.join(self.completed_times)}")
                    if self.next_scheduled_time:
                        logger.info(f"⏰ Prochain horaire planifié: {self.next_scheduled_time}")
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du chargement des données: {e}")
                self.today_count = 0
                self.last_reset_date = datetime.now().date()
                self.completed_times = []
                self.next_scheduled_time = None
        else:
            self.today_count = 0
            self.last_reset_date = datetime.now().date()
            self.completed_times = []
            self.next_scheduled_time = None
            logger.info("📂 Nouveau fichier de données créé")
    
    def _save_data(self):
        """Sauvegarde les données dans le fichier JSON."""
        try:
            data = {
                'today_count': self.today_count,
                'last_reset_date': self.last_reset_date.strftime('%Y-%m-%d'),
                'completed_times': self.completed_times,
                'next_scheduled_time': self.next_scheduled_time,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"💾 Données sauvegardées: {self.today_count} questionnaires")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde des données: {e}")
    
    def _reset_if_new_day(self):
        """Réinitialise le compteur si on est un nouveau jour."""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.today_count = 0
            self.last_reset_date = current_date
            self.completed_times = []
            self.next_scheduled_time = None
            self._save_data()
            logger.info(f"📅 Nouveau jour détecté - Compteur et horaires réinitialisés")
    
    def can_run_questionnaire(self) -> Tuple[bool, str]:
        """
        Vérifie si un questionnaire peut être exécuté maintenant.
        
        Returns:
            (bool, str): (peut_executer, raison)
        """
        self._reset_if_new_day()
        
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()
        
        # Vérifier si on a atteint le quota journalier
        if self.today_count >= self.DAILY_QUESTIONNAIRES:
            return False, f"Quota journalier atteint ({self.DAILY_QUESTIONNAIRES} questionnaires)"
        
        # Vérifier si on est dans la plage horaire du bot (11h30 - 21h38)
        if current_time < self.BOT_START_TIME:
            return False, f"Trop tôt - Le bot ne démarre qu'à {self.BOT_START_TIME.strftime('%H:%M')}"
        
        if current_time > self.BOT_END_TIME:
            return False, f"Trop tard - Le bot s'arrête à {self.BOT_END_TIME.strftime('%H:%M')}"
        
        # Vérifier si le restaurant est ouvert
        opening, closing = self.OPENING_HOURS[current_weekday]
        if current_time < opening or current_time > closing:
            return False, f"Restaurant fermé (ouvert de {opening.strftime('%H:%M')} à {closing.strftime('%H:%M')})"
        
        return True, "OK"
    
    def get_random_visit_time(self) -> Optional[Tuple[str, str, str]]:
        """
        Génère une heure de visite aléatoire réaliste.
        
        L'heure doit être:
        - Entre 11h30 et l'heure actuelle
        - Maximum 5 minutes dans le passé par rapport à maintenant
        - Jamais dans le futur
        
        Returns:
            Optional[Tuple[str, str, str]]: (date, heure, minute) ou None si impossible
        """
        now = datetime.now()
        current_time = now.time()
        
        # Définir la plage horaire disponible
        start_time = datetime.combine(now.date(), self.BOT_START_TIME)
        
        # L'heure maximale est soit maintenant, soit 5 minutes avant maintenant
        # On choisit aléatoirement pour varier
        if random.random() < 0.7:  # 70% du temps, on peut aller jusqu'à maintenant
            end_time = now
        else:  # 30% du temps, on recule de 1-5 minutes
            minutes_back = random.randint(1, self.MAX_PAST_MINUTES)
            end_time = now - timedelta(minutes=minutes_back)
        
        # Vérifier qu'on a une plage valide
        if end_time <= start_time:
            logger.warning("⚠️ Impossible de générer une heure de visite (trop tôt)")
            return None
        
        # Calculer la différence en minutes
        time_diff = (end_time - start_time).total_seconds() / 60
        
        if time_diff < 1:
            logger.warning("⚠️ Plage horaire trop courte")
            return None
        
        # Choisir un moment aléatoire dans cette plage
        random_minutes = random.randint(0, int(time_diff))
        visit_time = start_time + timedelta(minutes=random_minutes)
        
        # Formater pour le questionnaire
        date_str = visit_time.strftime("%d/%m/%Y")
        hour_str = visit_time.strftime("%H")
        minute_str = visit_time.strftime("%M")
        
        logger.info(f"🕐 Heure de visite générée: {visit_time.strftime('%d/%m/%Y à %H:%M')}")
        logger.info(f"   (Maintenant: {now.strftime('%H:%M')}, Plage: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')})")
        
        return date_str, hour_str, minute_str
    
    def calculate_next_run_time(self) -> Optional[datetime]:
        """
        Calcule le prochain moment où un questionnaire peut être exécuté.
        
        Returns:
            Optional[datetime]: Prochain moment d'exécution ou None si plus possible aujourd'hui
        """
        self._reset_if_new_day()
        
        now = datetime.now()
        current_time = now.time()
        
        # Si quota atteint, attendre demain
        if self.today_count >= self.DAILY_QUESTIONNAIRES:
            tomorrow = now + timedelta(days=1)
            next_run = datetime.combine(tomorrow.date(), self.BOT_START_TIME)
            logger.info(f"📅 Quota atteint - Prochain run: {next_run.strftime('%d/%m/%Y à %H:%M')}")
            return next_run
        
        # Si trop tôt, attendre 11h30
        if current_time < self.BOT_START_TIME:
            next_run = datetime.combine(now.date(), self.BOT_START_TIME)
            logger.info(f"⏰ Trop tôt - Prochain run: {next_run.strftime('%H:%M')}")
            return next_run
        
        # Si trop tard, attendre demain 11h30
        if current_time > self.BOT_END_TIME:
            tomorrow = now + timedelta(days=1)
            next_run = datetime.combine(tomorrow.date(), self.BOT_START_TIME)
            logger.info(f"🌙 Trop tard - Prochain run: {next_run.strftime('%d/%m/%Y à %H:%M')}")
            return next_run
        
        # Sinon, calculer un délai aléatoire entre les questionnaires
        # Répartir les 6 questionnaires sur la journée (11h30 - 21h38)
        total_minutes = (datetime.combine(now.date(), self.BOT_END_TIME) - 
                        datetime.combine(now.date(), self.BOT_START_TIME)).total_seconds() / 60
        
        remaining_questionnaires = self.DAILY_QUESTIONNAIRES - self.today_count
        
        if remaining_questionnaires > 0:
            # Calculer un intervalle moyen
            avg_interval = total_minutes / self.DAILY_QUESTIONNAIRES
            
            # Ajouter de la variation (±30%)
            min_interval = int(avg_interval * 0.7)
            max_interval = int(avg_interval * 1.3)
            
            # Délai aléatoire entre 5 minutes et l'intervalle calculé
            delay_minutes = random.randint(max(5, min_interval), max_interval)
            
            next_run = now + timedelta(minutes=delay_minutes)
            
            # Vérifier qu'on ne dépasse pas 21h38
            if next_run.time() > self.BOT_END_TIME:
                next_run = datetime.combine(now.date(), self.BOT_END_TIME)
            
            logger.info(f"⏱️ Prochain questionnaire dans {delay_minutes} minutes ({next_run.strftime('%H:%M')})")
            return next_run
        
        return None
    
    def increment_count(self):
        """Incrémente le compteur de questionnaires du jour."""
        self._reset_if_new_day()
        self.today_count += 1
        
        current_time = datetime.now().strftime('%H:%M:%S')
        self.completed_times.append(current_time)
        
        self._save_data()
        logger.info(f"📊 Questionnaires aujourd'hui: {self.today_count}/{self.DAILY_QUESTIONNAIRES}")
        logger.info(f"⏰ Questionnaire effectué à: {current_time}")
    
    def set_next_scheduled_time(self, next_time: Optional[datetime]):
        """Enregistre le prochain horaire planifié."""
        if next_time:
            self.next_scheduled_time = next_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.next_scheduled_time = None
        self._save_data()
        if self.next_scheduled_time:
            logger.info(f"📅 Prochain horaire enregistré: {self.next_scheduled_time}")
    
    def get_status(self) -> dict:
        """Retourne le statut actuel du planificateur."""
        self._reset_if_new_day()
        
        now = datetime.now()
        can_run, reason = self.can_run_questionnaire()
        next_run = self.calculate_next_run_time()
        
        return {
            'current_time': now.strftime('%H:%M:%S'),
            'today_count': self.today_count,
            'daily_limit': self.DAILY_QUESTIONNAIRES,
            'remaining': self.DAILY_QUESTIONNAIRES - self.today_count,
            'can_run': can_run,
            'reason': reason,
            'next_run': next_run.strftime('%d/%m/%Y à %H:%M') if next_run else 'N/A',
            'bot_hours': f"{self.BOT_START_TIME.strftime('%H:%M')} - {self.BOT_END_TIME.strftime('%H:%M')}"
        }


# Instance globale
scheduler = QuestionnaireScheduler()
