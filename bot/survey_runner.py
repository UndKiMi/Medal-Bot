#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exécuteur principal du questionnaire."""

import logging
import traceback
from datetime import datetime
from typing import Dict, Union

import undetected_chromedriver as uc

from bot.config_loader import config
from bot.automation import (
    step_1_start_survey,
    step_2_age_selection,
    step_3_ticket_info,
    step_4_order_location,
    step_4b_consumption_type,
    step_4c_pickup_location,
    step_4d_click_collect_pickup,
    step_5_satisfaction_comment,
    step_6_dimension_ratings,
    step_7_order_accuracy,
    step_8_problem_encountered,
    session_data
)

logger = logging.getLogger(__name__)


def run_survey_bot(driver: uc.Chrome) -> bool:
    """Exécute le bot de questionnaire."""
    try:
        session_data['start_time'] = datetime.now()
        session_data['requires_extra_steps'] = False
        logger.info("🚀 Démarrage du bot de questionnaire")
        
        # Étapes de base (1-4)
        base_steps = [
            (step_1_start_survey, "Page d'accueil - Commencer l'enquête", 1),
            (step_2_age_selection, "Sélection tranche d'âge", 2),
            (step_3_ticket_info, "Informations du ticket", 3),
            (step_4_order_location, "Lieu de commande", 4),
        ]
        
        # Exécuter les étapes de base
        for step_func, step_name, step_num in base_steps:
            if not _execute_step(driver, step_func, step_name, step_num):
                return False
        
        # Étapes conditionnelles selon le type de commande
        extra_steps_type = session_data.get('requires_extra_steps')
        
        if extra_steps_type == 'borne_comptoir':
            logger.info("🔀 Étapes supplémentaires: Borne/Comptoir")
            
            conditional_steps = [
                (step_4b_consumption_type, "Type de consommation", "4b"),
                (step_4c_pickup_location, "Lieu de récupération", "4c"),
            ]
            
            for step_func, step_name, step_num in conditional_steps:
                if not _execute_step(driver, step_func, step_name, step_num):
                    return False
        
        elif extra_steps_type == 'click_collect':
            logger.info("🔀 Étapes supplémentaires: Click & Collect")
            
            if not _execute_step(driver, step_4d_click_collect_pickup, "Lieu de récupération Click & Collect", "4d"):
                return False
        
        # Étapes finales (5-8)
        final_steps = [
            (step_5_satisfaction_comment, "Satisfaction générale + commentaire", 5),
            (step_6_dimension_ratings, "Notes sur chaque dimension", 6),
            (step_7_order_accuracy, "Commande exacte", 7),
            (step_8_problem_encountered, "Problème rencontré", 8)
        ]
        
        for step_func, step_name, step_num in final_steps:
            if not _execute_step(driver, step_func, step_name, step_num):
                return False
        
        # Succès
        duration = (datetime.now() - session_data['start_time']).total_seconds()
        logger.info(f"⏱️  Durée totale: {duration:.2f} secondes")
        logger.info("🎉 Questionnaire complété avec succès!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur critique: {e}")
        logger.debug(f"Détails: {traceback.format_exc()}")
        return False


def _execute_step(driver, step_func, step_name: str, step_num: Union[int, str]) -> bool:
    """Exécute une étape du questionnaire."""
    try:
        result = step_func(driver)
        
        if not result:
            logger.error(f"❌ Échec de l'étape {step_num}: {step_name}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur à l'étape {step_num} ({step_name}): {e}")
        logger.debug(f"Détails: {traceback.format_exc()}")
        return False


def get_session_data() -> Dict:
    """Retourne les données de session."""
    return session_data
