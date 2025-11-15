#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Détecteur de changements de structure de page (#28)."""

import logging
import hashlib
from typing import Dict, Optional, List
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


class PageChangeDetector:
    """Détecte les changements dans la structure du questionnaire."""
    
    def __init__(self):
        """Initialise le détecteur."""
        self.page_signatures = {}  # Stocke les signatures des pages
        self.expected_elements = {
            'start_button': ["//button[contains(text(), 'Commencer')]"],
            'age_radios': ["//input[@type='radio']"],
            'date_field': ["//input[@placeholder='JJ/MM/AAAA']"],
            'restaurant_field': ["//input[@maxlength='4' and @type='text']"],
            'satisfaction_smileys': ["//input[@type='radio']"],
            'comment_textarea': ["//textarea"],
            'next_button': ["//button[contains(., 'Suivant')]"]
        }
    
    def get_page_signature(self, driver: WebDriver, step_name: str) -> Optional[str]:
        """
        Génère une signature de la page actuelle.
        
        Args:
            driver: Instance du driver Selenium
            step_name: Nom de l'étape
        
        Returns:
            Signature hash de la page
        """
        try:
            # Récupérer les éléments clés de la page
            elements_data = []
            
            for element_type, selectors in self.expected_elements.items():
                found = False
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            # Prendre quelques attributs pour la signature
                            for elem in elements[:3]:  # Max 3 éléments
                                try:
                                    elem_id = elem.get_attribute('id') or ''
                                    elem_class = elem.get_attribute('class') or ''
                                    elem_text = elem.text[:50] if elem.text else ''
                                    elements_data.append(f"{element_type}:{elem_id}:{elem_class}:{elem_text}")
                                except:
                                    pass
                            found = True
                            break
                    except:
                        continue
                
                if not found:
                    elements_data.append(f"{element_type}:NOT_FOUND")
            
            # Créer une signature hash
            signature_data = "|".join(elements_data)
            signature = hashlib.md5(signature_data.encode()).hexdigest()
            
            return signature
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de la génération de la signature: {e}")
            return None
    
    def detect_changes(self, driver: WebDriver, step_name: str) -> Dict:
        """
        Détecte les changements dans la structure de la page.
        
        Args:
            driver: Instance du driver Selenium
            step_name: Nom de l'étape
        
        Returns:
            Dict avec les informations de détection
        """
        current_signature = self.get_page_signature(driver, step_name)
        
        if not current_signature:
            return {
                'changed': False,
                'error': 'Impossible de générer la signature'
            }
        
        # Vérifier si on a déjà vu cette signature
        if step_name in self.page_signatures:
            previous_signature = self.page_signatures[step_name]
            
            if current_signature != previous_signature:
                logger.warning(f"⚠️ Changement détecté dans la structure de l'étape: {step_name}")
                return {
                    'changed': True,
                    'step': step_name,
                    'previous_signature': previous_signature,
                    'current_signature': current_signature
                }
        
        # Sauvegarder la nouvelle signature
        self.page_signatures[step_name] = current_signature
        
        return {
            'changed': False,
            'signature': current_signature
        }
    
    def verify_expected_elements(self, driver: WebDriver, step_name: str) -> List[str]:
        """
        Vérifie la présence des éléments attendus.
        
        Args:
            driver: Instance du driver Selenium
            step_name: Nom de l'étape
        
        Returns:
            Liste des éléments manquants
        """
        missing = []
        
        # Déterminer quels éléments sont attendus pour cette étape
        expected_for_step = self._get_expected_for_step(step_name)
        
        for element_type, selectors in expected_for_step.items():
            found = False
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        found = True
                        break
                except:
                    continue
            
            if not found:
                missing.append(element_type)
                logger.warning(f"⚠️ Élément attendu non trouvé: {element_type} (étape: {step_name})")
        
        return missing
    
    def _get_expected_for_step(self, step_name: str) -> Dict:
        """Retourne les éléments attendus pour une étape donnée."""
        step_mapping = {
            'step_1': ['start_button'],
            'step_2': ['age_radios', 'next_button'],
            'step_3': ['date_field', 'restaurant_field', 'next_button'],
            'step_4': ['age_radios', 'next_button'],
            'step_5': ['satisfaction_smileys', 'comment_textarea', 'next_button'],
            'step_6': ['age_radios', 'next_button'],
            'step_7': ['age_radios', 'next_button'],
            'step_8': ['age_radios', 'next_button']
        }
        
        expected_keys = step_mapping.get(step_name, [])
        return {k: v for k, v in self.expected_elements.items() if k in expected_keys}


# Instance globale
page_change_detector = PageChangeDetector()

