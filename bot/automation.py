import logging
import os
import random
import time
import traceback
from datetime import datetime, timedelta
from typing import Optional
from bot.config_loader import config
from bot.utils.helpers import (
    wait_random, human_typing, random_scroll,
    click_next_button, validate_radio_selected, validate_text_input
)
from bot.utils.avis_manager import AvisManager
from bot.scheduler import scheduler
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import undetected_chromedriver as uc
from selenium_stealth import stealth

from bot.config import (
    XPATHS, TIMING, TIMEOUTS, CHROME_OPTIONS, 
    AVIS_MAPPING, SERVICE_TYPE_MAPPING,
    RESTAURANT_NUMBER, SURVEY_URL, BASE_DIR
)

# Logger (configuration centralisée dans main.py)
logger = logging.getLogger(__name__)

# Dictionnaire pour stocker les données de session
session_data = {
    'start_time': None,
    'current_category': None,
    'current_avis_file': None,
    'requires_extra_steps': False,
    'captcha_detected': False
}

# Instance globale du gestionnaire d'avis (cache)
avis_manager = AvisManager(AVIS_MAPPING)

# setup_driver et cleanup_driver sont définies dans bot.utils.driver_manager
# wait_random et human_typing sont importées depuis bot.utils.helpers

def pick_avis(category: str = None) -> str:
    """Sélectionne un avis aléatoire en fonction de la catégorie (utilise le cache)."""
    try:
        # Utiliser le gestionnaire d'avis avec cache
        selected_avis = avis_manager.load_avis(category)
        session_data['current_avis_file'] = avis_manager.avis_mapping.get(category or 'drive')
        
        return selected_avis
        
    except Exception as e:
        logger.error(f"❌ Erreur sélection avis ({category}): {e}")
        return "Excellent service, très satisfait de ma visite !"


def detect_captcha(driver) -> bool:
    """
    Détecte la présence d'un CAPTCHA sur la page (#17).
    
    Returns:
        True si un CAPTCHA est détecté, False sinon
    """
    try:
        # Rechercher des éléments typiques de CAPTCHA
        captcha_indicators = [
            "//iframe[contains(@src, 'recaptcha')]",
            "//iframe[contains(@src, 'captcha')]",
            "//div[contains(@class, 'recaptcha')]",
            "//div[contains(@class, 'captcha')]",
            "//div[contains(@id, 'recaptcha')]",
            "//div[contains(@id, 'captcha')]",
            "//img[contains(@alt, 'CAPTCHA')]",
            "//img[contains(@alt, 'captcha')]",
            "//*[contains(text(), 'CAPTCHA')]",
            "//*[contains(text(), 'captcha')]",
            "//*[contains(text(), 'Vérification')]",
            "//*[contains(text(), 'vérification')]",
        ]
        
        for selector in captcha_indicators:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    logger.error("🚨 CAPTCHA détecté sur la page!")
                    return True
            except:
                continue
        
        # Vérifier aussi dans le texte de la page
        try:
            page_text = driver.page_source.lower()
            captcha_keywords = ['captcha', 'recaptcha', 'hcaptcha', 'vérification humaine']
            if any(keyword in page_text for keyword in captcha_keywords):
                # Vérifier que ce n'est pas juste dans le code source
                body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(keyword in body_text for keyword in captcha_keywords):
                    logger.error("🚨 CAPTCHA détecté dans le contenu de la page!")
                    return True
        except:
            pass
        
        return False
        
    except Exception as e:
        logger.warning(f"⚠️ Erreur lors de la détection CAPTCHA: {e}")
        return False

# ============================================================================
# ÉTAPES DU QUESTIONNAIRE (ordre exact selon le code fourni)
# ============================================================================

def step_1_start_survey(driver) -> bool:
    """Étape 1: Page d'accueil - Cliquer sur 'Commencer l'enquête'"""
    logger.info("🏁 Étape 1: Page d'accueil - Commencer l'enquête")
    try:
        # Détecter CAPTCHA (#17)
        if detect_captcha(driver):
            logger.error("🚨 CAPTCHA détecté - Arrêt du bot")
            session_data['captcha_detected'] = True
            return False
        
        wait_random(1, 2)  # Optimisé pour vitesse
        
        # Chercher le bouton "Commencer l'enquête" ou "Commencer"
        start_button = None
        selectors = [
            "//button[contains(text(), 'Commencer')]",
            "//button[contains(., 'Commencer')]",
            "//button[contains(text(), 'Start')]",
            "//input[@type='submit']"
        ]
        
        for selector in selectors:
            try:
                start_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                if start_button:
                    break
            except:
                continue
        
        if not start_button:
            logger.error("❌ Bouton 'Commencer' non trouvé")
            return False
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", start_button)
        wait_random(0.3, 0.8)  # Optimisé pour vitesse
        driver.execute_script("arguments[0].click();", start_button)
        
        logger.info("✅ Bouton 'Commencer l'enquête' cliqué")
        wait_random(1, 1.5)  # Optimisé pour vitesse
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 1 échouée: {str(e)}")
        return False

def step_2_age_selection(driver) -> bool:
    """Étape 2: Sélection tranche d'âge (choix aléatoire, excluant 'moins de 15 ans')"""
    logger.info("👤 Étape 2: Sélection tranche d'âge")
    try:
        wait_random(0.5, 1)  # Optimisé pour vitesse
        
        # Trouver tous les boutons radio pour l'âge
        radios_age = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//input[@type='radio']"))
        )
        
        if radios_age and len(radios_age) > 1:
            # Exclure le premier bouton (moins de 15 ans) et choisir parmi les autres
            eligible_radios = radios_age[1:]  # Exclut le premier élément
            selected_radio = random.choice(eligible_radios)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_radio)
            wait_random(0.2, 0.4)  # Optimisé pour vitesse
            driver.execute_script("arguments[0].click();", selected_radio)
            logger.info("✅ Tranche d'âge sélectionnée (excluant 'moins de 15 ans')")
        
        # Cliquer sur Suivant (factorisé)
        wait_random(0.5, 1)  # Optimisé pour vitesse
        if not click_next_button(driver, timeout=TIMEOUTS['element_wait']):
            return False
        
        wait_random(1, 1.5)  # Optimisé pour vitesse
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 2 échouée: {str(e)}")
        return False

def step_3_ticket_info(driver) -> bool:
    """Étape 3: Informations du ticket (date/heure/minute/numéro resto)"""
    logger.info("🎫 Étape 3: Informations du ticket")
    try:
        wait_random(0.5, 1)  # Optimisé pour vitesse
        
        # Générer une heure de visite aléatoire réaliste via le scheduler
        visit_time = scheduler.get_random_visit_time()
        
        if visit_time is None:
            logger.error("❌ Impossible de générer une heure de visite valide")
            return False
        
        date_jour, heure, minute = visit_time
        
        # 1. Saisir la date avec validation
        try:
            date_field = driver.find_element(By.XPATH, "//input[@placeholder='JJ/MM/AAAA']")
            date_field.clear()
            wait_random(0.1, 0.3)  # Optimisé pour vitesse
            human_typing(date_field, date_jour)
            if not validate_text_input(driver, date_field, expected_text=date_jour, min_length=8):
                logger.warning("⚠️ Validation de la date échouée, mais on continue")
            logger.info(f"✅ Date saisie: {date_jour}")
        except:
            logger.warning("⚠️ Champ date non trouvé")
        
        wait_random(0.3, 0.6)  # Optimisé pour vitesse
        
        # 2. Saisir heure et minute avec validation
        try:
            heure_fields = driver.find_elements(By.XPATH, "//input[@maxlength='2' and @type='text']")
            if len(heure_fields) >= 2:
                heure_fields[0].clear()
                human_typing(heure_fields[0], heure)
                if not validate_text_input(driver, heure_fields[0], expected_text=heure, min_length=1):
                    logger.warning("⚠️ Validation de l'heure échouée")
                wait_random(0.2, 0.4)  # Optimisé pour vitesse
                heure_fields[1].clear()
                human_typing(heure_fields[1], minute)
                if not validate_text_input(driver, heure_fields[1], expected_text=minute, min_length=1):
                    logger.warning("⚠️ Validation des minutes échouée")
                logger.info(f"✅ Heure saisie: {heure}:{minute}")
        except:
            logger.warning("⚠️ Champs heure/minute non trouvés")
        
        wait_random(0.3, 0.6)  # Optimisé pour vitesse
        
        # 3. Saisir numéro restaurant (4 chiffres) avec validation
        try:
            restaurant_field = driver.find_element(By.XPATH, "//input[@maxlength='4' and @type='text']")
            restaurant_field.clear()
            wait_random(0.1, 0.3)  # Optimisé pour vitesse
            human_typing(restaurant_field, RESTAURANT_NUMBER)
            if not validate_text_input(driver, restaurant_field, expected_text=RESTAURANT_NUMBER, min_length=4):
                logger.warning("⚠️ Validation du numéro restaurant échouée")
            logger.info(f"✅ Numéro restaurant saisi: {RESTAURANT_NUMBER}")
        except:
            logger.warning("⚠️ Champ numéro restaurant non trouvé")
        
        # Cliquer sur Suivant (factorisé)
        wait_random(0.5, 1)  # Optimisé pour vitesse
        if not click_next_button(driver, timeout=TIMEOUTS['element_wait']):
            return False
        
        wait_random(1, 1.5)  # Optimisé pour vitesse
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 3 échouée: {str(e)}")
        return False

def step_4_order_location(driver) -> bool:
    """Étape 4: Lieu de commande (6 premières options seulement)"""
    logger.info("📍 Étape 4: Lieu de commande")
    try:
        wait_random(0.5, 1)  # Optimisé pour vitesse
        
        # Trouver tous les boutons radio
        lieu_radios = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//input[@type='radio']"))
        )
        
        # Stocker l'index sélectionné pour savoir si on a des étapes supplémentaires
        selected_index = None
        
        if lieu_radios and len(lieu_radios) >= 6:
            # Choisir parmi les 6 premières options uniquement
            selected_index = random.randint(0, 5)
            selected_radio = lieu_radios[selected_index]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_radio)
            wait_random(0.2, 0.4)  # Optimisé pour vitesse
            driver.execute_script("arguments[0].click();", selected_radio)
            # Validation
            if not validate_radio_selected(driver, selected_radio):
                logger.warning("⚠️ Validation du radio échouée, nouvelle tentative...")
                driver.execute_script("arguments[0].checked = true;", selected_radio)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", selected_radio)
            
            # Déterminer le type d'étapes supplémentaires selon l'option choisie
            # Index 0 = Borne → étapes 4b (consommation) + 4c (récupération)
            # Index 1 = Comptoir → étapes 4b (consommation) + 4c (récupération)
            # Index 2 = Drive → pas d'étapes supplémentaires
            # Index 3 = Guichet extérieur → pas d'étapes supplémentaires
            # Index 4 = Click & Collect app mobile → étape 4d (lieu récupération)
            # Index 5 = Click & Collect site web → étape 4d (lieu récupération)
            
            if selected_index in [0, 1]:
                # Borne ou Comptoir
                session_data['requires_extra_steps'] = 'borne_comptoir'
                session_data['order_location'] = 'borne' if selected_index == 0 else 'comptoir'
                logger.info(f"✅ Lieu de commande sélectionné (option {selected_index + 1}/6)")
                logger.info("ℹ️  Borne/Comptoir → Étapes supplémentaires: consommation + récupération")
            elif selected_index in [4, 5]:
                # Click & Collect
                session_data['requires_extra_steps'] = 'click_collect'
                session_data['order_location'] = 'cc_appli' if selected_index == 4 else 'cc_site'
                logger.info(f"✅ Lieu de commande sélectionné (option {selected_index + 1}/6)")
                logger.info("ℹ️  Click & Collect → Étape supplémentaire: lieu de récupération")
            else:
                # Drive ou Guichet extérieur → pas d'étapes supplémentaires
                session_data['requires_extra_steps'] = None
                session_data['current_category'] = 'drive'
                logger.info(f"✅ Lieu de commande sélectionné (option {selected_index + 1}/6)")
        
        # Cliquer sur Suivant (factorisé)
        wait_random(0.5, 1)  # Optimisé pour vitesse
        if not click_next_button(driver, timeout=TIMEOUTS['element_wait']):
            return False
        
        wait_random(1, 1.5)  # Optimisé pour vitesse
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 4 échouée: {str(e)}")
        return False

def step_4b_consumption_type(driver) -> bool:
    """Étape 4b (conditionnelle): Sur place ou à emporter"""
    logger.info("🍽️ Étape 4b: Type de consommation (sur place / à emporter)")
    try:
        wait_random(0.5, 1)  # Optimisé pour vitesse
        
        # Trouver les boutons radio pour le type de consommation
        consumption_radios = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//input[@type='radio']"))
        )
        
        if consumption_radios and len(consumption_radios) >= 2:
            # Choisir aléatoirement entre sur place (0) ou à emporter (1)
            selected_index = random.randint(0, 1)
            selected_radio = consumption_radios[selected_index]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_radio)
            wait_random(0.2, 0.4)  # Optimisé pour vitesse
            driver.execute_script("arguments[0].click();", selected_radio)
            
            # Stocker le type de consommation
            session_data['consumption_type'] = 'sur_place' if selected_index == 0 else 'emporter'
            logger.info(f"✅ Type de consommation sélectionné: {session_data['consumption_type']}")
        
        # Cliquer sur Suivant (factorisé)
        wait_random(0.5, 1)  # Optimisé pour vitesse
        if not click_next_button(driver, timeout=TIMEOUTS['element_wait']):
            return False
        
        wait_random(1, 1.5)  # Optimisé pour vitesse
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 4b échouée: {str(e)}")
        return False

def step_4c_pickup_location(driver) -> bool:
    """Étape 4c (conditionnelle Borne/Comptoir): Où avez-vous récupéré votre commande"""
    logger.info("📦 Étape 4c: Lieu de récupération de la commande (Borne/Comptoir)")
    try:
        wait_random(0.5, 1)  # Optimisé pour vitesse
        
        # Trouver les boutons radio pour le lieu de récupération
        pickup_radios = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//input[@type='radio']"))
        )
        
        if pickup_radios and len(pickup_radios) >= 2:
            # Choisir aléatoirement entre "Au comptoir" (0) ou "En service à table" (1)
            selected_radio = random.choice(pickup_radios[:2])
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_radio)
            wait_random(0.2, 0.4)  # Optimisé pour vitesse
            driver.execute_script("arguments[0].click();", selected_radio)
            
            # Définir la catégorie finale pour les avis
            order_loc = session_data.get('order_location', 'borne')
            consumption = session_data.get('consumption_type', 'sur_place')
            session_data['current_category'] = f"{order_loc}_{consumption}"
            logger.info(f"✅ Lieu de récupération sélectionné - Catégorie: {session_data['current_category']}")
        
        # Cliquer sur Suivant (factorisé)
        wait_random(0.5, 1)  # Optimisé pour vitesse
        if not click_next_button(driver, timeout=TIMEOUTS['element_wait']):
            return False
        
        wait_random(1, 1.5)  # Optimisé pour vitesse
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 4c échouée: {str(e)}")
        return False

def step_4d_click_collect_pickup(driver) -> bool:
    """Étape 4d (conditionnelle Click & Collect): Où avez-vous récupéré votre commande"""
    logger.info("📦 Étape 4d: Lieu de récupération Click & Collect")
    try:
        wait_random(0.5, 1)  # Optimisé pour vitesse
        
        # Trouver les boutons radio pour le lieu de récupération Click & Collect
        pickup_radios = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//input[@type='radio']"))
        )
        
        if pickup_radios and len(pickup_radios) >= 4:
            # Choisir aléatoirement parmi les 4 options:
            # 0 = Au comptoir
            # 1 = Au drive
            # 2 = Au guichet extérieur de vente à emporter
            # 3 = A l'extérieur du restaurant
            selected_index = random.randint(0, 3)
            selected_radio = pickup_radios[selected_index]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_radio)
            wait_random(0.2, 0.4)  # Optimisé pour vitesse
            driver.execute_script("arguments[0].click();", selected_radio)
            
            # Définir la catégorie finale pour les avis
            order_loc = session_data.get('order_location', 'cc_appli')
            pickup_locations = ['comptoir', 'drive', 'guichet', 'exterieur']
            session_data['current_category'] = f"{order_loc}_{pickup_locations[selected_index]}"
            logger.info(f"✅ Lieu de récupération Click & Collect sélectionné - Catégorie: {session_data['current_category']}")
        
        # Cliquer sur Suivant (factorisé)
        wait_random(0.5, 1)  # Optimisé pour vitesse
        if not click_next_button(driver, timeout=TIMEOUTS['element_wait']):
            return False
        
        wait_random(1, 1.5)  # Optimisé pour vitesse
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 4d échouée: {str(e)}")
        return False

def find_best_satisfaction_smiley(driver, all_radios):
    """Trouve le smiley de meilleure satisfaction en analysant les attributs."""
    try:
        logger.info(f"🔍 Analyse de {len(all_radios)} smileys pour trouver le vert foncé...")
        
        smiley_data = []
        for idx, radio in enumerate(all_radios):
            try:
                # Récupérer tous les attributs possibles
                value = driver.execute_script("return arguments[0].value;", radio)
                aria_label = driver.execute_script("return arguments[0].getAttribute('aria-label');", radio)
                aria_posinset = driver.execute_script("return arguments[0].getAttribute('aria-posinset');", radio)
                data_value = driver.execute_script("return arguments[0].getAttribute('data-value');", radio)
                data_mds_value = driver.execute_script("return arguments[0].getAttribute('data-mds-value');", radio)
                name = driver.execute_script("return arguments[0].name;", radio)
                id_attr = driver.execute_script("return arguments[0].id;", radio)
                
                # Récupérer les classes du label parent
                parent_classes = driver.execute_script("""
                    var label = arguments[0].closest('label');
                    return label ? label.className : '';
                """, radio)
                
                smiley_data.append({
                    'index': idx,
                    'element': radio,
                    'value': value,
                    'aria_label': aria_label,
                    'aria_posinset': aria_posinset,
                    'data_value': data_value,
                    'data_mds_value': data_mds_value,
                    'name': name,
                    'id': id_attr,
                    'parent_classes': parent_classes
                })
                
                logger.info(f"  Smiley {idx}: value={value}, aria-label=\"{aria_label}\", aria-posinset={aria_posinset}")
                
            except Exception as e:
                logger.warning(f"  ⚠️ Erreur analyse smiley {idx}: {e}")
        
        # Trouver le meilleur smiley
        # Structure Medallia: aria-posinset="1" + aria-label="Très satisfait" + value="1"
        best_smiley = None
        
        # Stratégie 1: Chercher aria-label="Très satisfait" (le plus fiable)
        for data in smiley_data:
            aria = str(data['aria_label']).lower() if data['aria_label'] else ''
            if 'très satisfait' in aria or 'very satisfied' in aria:
                logger.info(f"✅ Smiley trouvé par aria-label=\"{data['aria_label']}\" (index {data['index']})")
                best_smiley = data['element']
                break
        
        # Stratégie 2: Chercher value="1" (Medallia utilise 1=meilleur, 5=pire)
        if not best_smiley:
            for data in smiley_data:
                if data['value'] == '1':
                    logger.info(f"✅ Smiley trouvé par value=1 (index {data['index']})")
                    best_smiley = data['element']
                    break
        
        # Stratégie 3: Chercher aria-posinset="1"
        if not best_smiley:
            for data in smiley_data:
                if data['aria_posinset'] == '1':
                    logger.info(f"✅ Smiley trouvé par aria-posinset=1 (index {data['index']})")
                    best_smiley = data['element']
                    break
        
        # Stratégie 4: Prendre le premier (généralement le meilleur sur Medallia)
        if not best_smiley and smiley_data:
            best_smiley = smiley_data[0]['element']
            logger.info(f"✅ Smiley sélectionné: premier de la liste (index 0)")
        
        return best_smiley
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'analyse des smileys: {e}")
        return all_radios[0] if all_radios else None

def step_5_satisfaction_comment(driver) -> bool:
    """Étape 5: Satisfaction générale (premier smiley vert foncé) + commentaire"""
    logger.info("😊 Étape 5: Satisfaction générale + commentaire")
    try:
        wait_random(1, 1.5)  # Optimisé pour vitesse
        
        # 1. OBLIGATOIRE: Cliquer sur le smiley vert foncé (meilleure satisfaction)
        smiley_selected = False
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                all_radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
                
                if all_radios and len(all_radios) >= 4:
                    logger.info(f"📊 Tentative {attempt + 1}/{max_attempts}: {len(all_radios)} smileys trouvés")
                    
                    # Analyser et trouver le meilleur smiley
                    best_smiley = find_best_satisfaction_smiley(driver, all_radios)
                    
                    if not best_smiley:
                        logger.warning(f"⚠️ Aucun smiley trouvé à la tentative {attempt + 1}")
                        wait_random(0.3, 0.6)  # Optimisé pour vitesse
                        continue
                    
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", best_smiley)
                    wait_random(0.5, 1)  # Optimisé pour vitesse
                    
                    parent_label = driver.execute_script("return arguments[0].closest('label') || arguments[0].parentElement;", best_smiley)
                    if parent_label:
                        driver.execute_script("arguments[0].click();", parent_label)
                        wait_random(0.3, 0.6)  # Optimisé pour vitesse
                    
                    driver.execute_script("arguments[0].checked = true;", best_smiley)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", best_smiley)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('click', { bubbles: true }));", best_smiley)
                    wait_random(0.3, 0.6)  # Optimisé pour vitesse
                    
                    is_checked = driver.execute_script("return arguments[0].checked;", best_smiley)
                    if is_checked:
                        logger.info("✅ Smiley vert foncé (meilleure satisfaction) CONFIRMÉ coché")
                        smiley_selected = True
                        break
                    else:
                        logger.warning(f"⚠️ Tentative {attempt + 1} échouée, le smiley n'est pas coché")
                        wait_random(0.5, 1)
                else:
                    logger.warning(f"⚠️ Pas assez de smileys trouvés: {len(all_radios)}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Erreur tentative {attempt + 1}: {e}")
                wait_random(0.5, 1)
        
        if not smiley_selected:
            logger.error("❌ ÉCHEC: Impossible de sélectionner le smiley après 3 tentatives")
            return False
        
        wait_random(0.8, 1.2)  # Optimisé pour vitesse
        
        # 2. OBLIGATOIRE: Saisir le commentaire
        commentaire_saisi = False
        
        try:
            selectors = [
                "//textarea",
                "//textarea[@placeholder]",
                "//textarea[contains(@class, 'comment')]",
                "//textarea[contains(@id, 'comment')]"
            ]
            
            textarea = None
            for selector in selectors:
                try:
                    textarea = driver.find_element(By.XPATH, selector)
                    if textarea:
                        logger.info(f"✅ Textarea trouvé avec: {selector}")
                        break
                except:
                    continue
            
            if not textarea:
                logger.error("❌ ÉCHEC: Textarea non trouvé")
                return False
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", textarea)
            wait_random(0.5, 0.8)  # Optimisé pour vitesse
            
            commentaire = pick_avis(session_data.get('current_category'))
            if not commentaire:
                logger.error("❌ ÉCHEC: Aucun commentaire disponible")
                return False
            
            textarea.click()
            wait_random(0.3, 0.6)  # Optimisé pour vitesse
            textarea.clear()
            wait_random(0.2, 0.3)  # Optimisé pour vitesse
            
            logger.info(f"📝 Début de la saisie du commentaire: {commentaire[:50]}...")
            human_typing(textarea, commentaire)
            wait_random(0.6, 1)  # Optimisé pour vitesse
            
            valeur_saisie = driver.execute_script("return arguments[0].value || arguments[0].textContent || arguments[0].innerHTML;", textarea)
            logger.info(f"🔍 Vérification: valeur récupérée = '{valeur_saisie[:50] if valeur_saisie else 'VIDE'}...'")
            
            if valeur_saisie and len(valeur_saisie.strip()) > 10:
                logger.info(f"✅ Commentaire CONFIRMÉ saisi ({len(valeur_saisie)} caractères)")
                commentaire_saisi = True
            else:
                logger.error(f"❌ ÉCHEC: Commentaire non saisi correctement (longueur: {len(valeur_saisie) if valeur_saisie else 0})")
                logger.error(f"❌ Contenu récupéré: '{valeur_saisie}'")
                return False
                
        except Exception as e:
            logger.error(f"❌ ÉCHEC lors de la saisie du commentaire: {e}")
            return False
        
        if not commentaire_saisi:
            logger.error("❌ ÉCHEC: Le commentaire n'a pas été saisi")
            return False
        
        # 3. Cliquer sur Suivant SEULEMENT si smiley ET commentaire OK
        wait_random(1, 1.5)  # Optimisé pour vitesse
        
        try:
            next_button = driver.find_element(By.XPATH, "//button[contains(., 'Suivant')]")
            
            is_disabled = driver.execute_script("return arguments[0].disabled || arguments[0].hasAttribute('disabled');", next_button)
            if is_disabled:
                logger.warning("⚠️ Le bouton Suivant est désactivé, attente supplémentaire...")
                wait_random(1, 1.5)  # Optimisé pour vitesse
                is_disabled = driver.execute_script("return arguments[0].disabled || arguments[0].hasAttribute('disabled');", next_button)
                if is_disabled:
                    logger.error("❌ Le bouton Suivant reste désactivé")
                    return False
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            wait_random(0.5, 0.8)  # Optimisé pour vitesse
            driver.execute_script("arguments[0].click();", next_button)
            logger.info("✅ Clic sur Suivant effectué")
            
        except Exception as btn_err:
            logger.error(f"❌ Erreur lors du clic sur Suivant: {btn_err}")
            return False
        
        wait_random(1, 1.5)  # Optimisé pour vitesse
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 5 échouée: {str(e)}")
        return False

def step_6_dimension_ratings(driver) -> bool:
    """Étape 6: Notes sur chaque dimension (premier émoji vert foncé de chaque ligne)"""
    logger.info("⭐ Étape 6: Notes sur chaque dimension")
    try:
        wait_random(0.5, 1)  # Optimisé pour vitesse
        
        # Trouver tous les boutons radio (il y a 4 lignes avec 6 options chacune: 5 émojis + "Non concerné")
        radios_dim = driver.find_elements(By.XPATH, "//input[@type='radio']")
        
        if radios_dim:
            # Calculer le nombre d'options par ligne (normalement 6: 5 émojis + 1 "Non concerné")
            # Il y a 4 lignes de questions
            options_per_line = 6
            nb_lines = 4
            
            logger.info(f"📊 Total de boutons radio trouvés: {len(radios_dim)}")
            logger.info(f"📊 Nombre de lignes à traiter: {nb_lines}")
            
            # Pour chaque ligne, cliquer sur le premier émoji (index 0, 6, 12, 18)
            for line_num in range(nb_lines):
                index = line_num * options_per_line
                
                if index < len(radios_dim):
                    # Faire défiler jusqu'à l'élément
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", radios_dim[index])
                    wait_random(0.2, 0.4)  # Optimisé pour vitesse
                    
                    # Cliquer sur le premier émoji (vert foncé)
                    driver.execute_script("arguments[0].click();", radios_dim[index])
                    logger.info(f"✅ Ligne {line_num + 1}: Premier émoji vert foncé sélectionné (index {index})")
                    wait_random(0.1, 0.3)  # Optimisé pour vitesse
            
            logger.info("✅ Toutes les dimensions notées avec le meilleur score")
        else:
            logger.warning("⚠️ Aucun bouton radio trouvé")
        
        # Attendre que le bouton Suivant soit activé
        wait_random(0.5, 1)  # Optimisé pour vitesse
        
        # Chercher le bouton Suivant avec plusieurs sélecteurs possibles
        next_button = None
        selectors = [
            "//button[contains(., 'Suivant')]",
            "//button[contains(text(), 'Suivant')]",
            "//button[@type='submit']",
            "//input[@type='submit' and contains(@value, 'Suivant')]",
            "//button[contains(@class, 'next')]",
            "//button[contains(@class, 'submit')]"
        ]
        
        for selector in selectors:
            try:
                next_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                if next_button:
                    logger.info(f"✅ Bouton Suivant trouvé avec le sélecteur: {selector}")
                    break
            except:
                continue
        
        if not next_button:
            logger.error("❌ Bouton Suivant introuvable avec tous les sélecteurs")
            return False
        
        # Faire défiler et cliquer
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        wait_random(0.3, 0.6)  # Optimisé pour vitesse
        driver.execute_script("arguments[0].click();", next_button)
        logger.info("✅ Bouton Suivant cliqué")
        
        wait_random(1, 1.5)  # Optimisé pour vitesse
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 6 échouée: {str(e)}")
        return False

def step_7_order_accuracy(driver) -> bool:
    """Étape 7: Commande exacte (Oui = premier bouton)"""
    logger.info("✅ Étape 7: Commande exacte")
    try:
        wait_random(1, 2)
        
        # Cliquer sur le premier bouton (Oui)
        radios_exact = driver.find_elements(By.XPATH, "//input[@type='radio']")
        if radios_exact:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", radios_exact[0])
            wait_random(0.3, 0.7)
            driver.execute_script("arguments[0].click();", radios_exact[0])
            logger.info("✅ 'Oui' sélectionné (commande exacte)")
        
        # Cliquer sur Suivant (factorisé)
        wait_random(0.5, 1)  # Optimisé pour vitesse
        if not click_next_button(driver, timeout=TIMEOUTS['element_wait']):
            return False
        
        wait_random(1, 1.5)  # Optimisé pour vitesse
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 7 échouée: {str(e)}")
        return False

def step_8_problem_encountered(driver) -> bool:
    """Étape 8: Problème rencontré (Non = deuxième bouton)"""
    logger.info("❌ Étape 8: Problème rencontré")
    try:
        wait_random(0.5, 1)  # Optimisé pour vitesse
        
        # Cliquer sur le deuxième bouton (Non) avec WebDriverWait pour robustesse
        radios_prob = WebDriverWait(driver, TIMEOUTS['element_wait']).until(
            EC.presence_of_all_elements_located((By.XPATH, "//input[@type='radio']"))
        )
        if radios_prob and len(radios_prob) >= 2:
            selected_radio = radios_prob[1]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_radio)
            wait_random(0.2, 0.4)  # Optimisé pour vitesse
            driver.execute_script("arguments[0].click();", selected_radio)
            # Validation que le radio est bien sélectionné
            if not validate_radio_selected(driver, selected_radio):
                logger.warning("⚠️ Validation du radio échouée, nouvelle tentative...")
                driver.execute_script("arguments[0].checked = true;", selected_radio)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", selected_radio)
            logger.info("✅ 'Non' sélectionné (aucun problème)")
        else:
            logger.error("❌ Pas assez de boutons radio trouvés")
            return False
        
        # Cliquer sur Suivant (utiliser la fonction factorisée pour plus de robustesse)
        wait_random(0.5, 1)  # Optimisé pour vitesse
        if not click_next_button(driver, timeout=TIMEOUTS['element_wait']):
            logger.error("❌ Impossible de cliquer sur Suivant")
            return False
        
        wait_random(1.5, 2.5)  # Optimisé pour vitesse
        logger.info("🎉 Questionnaire terminé !")
        return True
        
    except Exception as e:
        logger.error(f"❌ Étape 8 échouée: {str(e)}")
        logger.debug(f"Détails: {traceback.format_exc()}")
        return False

# ============================================================================
# NOTE: La fonction run_survey_bot est définie dans bot/survey_runner.py
# Cette fonction est importée depuis survey_runner.py dans gui.py
# ============================================================================
