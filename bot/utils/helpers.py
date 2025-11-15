#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fonctions utilitaires pour le bot."""

import random
import time
import logging
from typing import List, Callable, Optional, Any
from functools import wraps
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)


def wait_random(min_seconds: float, max_seconds: float) -> None:
    """Attend un nombre aléatoire de secondes avec distribution gaussienne (plus humain)."""
    mean = (min_seconds + max_seconds) / 2
    std = (max_seconds - min_seconds) / 6
    delay = random.gauss(mean, std)
    delay = max(min_seconds, min(max_seconds, delay))
    
    # 5% du temps, ajouter une micro-pause (humain hésite) - réduit pour vitesse
    if random.random() < 0.05:
        delay += random.uniform(0.2, 0.5)  # Optimisé pour vitesse
    
    time.sleep(delay)


def human_typing(element: WebElement, text: str, min_delay: float = 0.05, max_delay: float = 0.10, error_rate: float = 0.02) -> None:
    """Simule une frappe humaine avec erreurs et corrections occasionnelles."""
    from selenium.webdriver.common.keys import Keys
    
    i = 0
    while i < len(text):
        char = text[i]
        
        # Simuler erreur de frappe (2% du temps)
        if random.random() < error_rate and char.isalpha():
            wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
            element.send_keys(wrong_char)
            time.sleep(random.uniform(min_delay, max_delay))
            
            # Pause (réaliser l'erreur)
            time.sleep(random.uniform(0.2, 0.5))
            
            # Corriger avec backspace
            element.send_keys(Keys.BACKSPACE)
            time.sleep(random.uniform(0.1, 0.2))
        
        # Taper le bon caractère
        element.send_keys(char)
        
        # Vitesse variable selon le caractère (optimisé pour vitesse)
        if char == ' ':
            delay = random.uniform(0.08, 0.15)  # Plus lent pour espace
        elif char in '.,!?':
            delay = random.uniform(0.1, 0.2)    # Pause après ponctuation
        elif char.isupper():
            delay = random.uniform(0.08, 0.12)  # Majuscule = Shift
        else:
            delay = random.uniform(min_delay, max_delay)
        
        time.sleep(delay)
        
        # Pause aléatoire (humain réfléchit) - réduite
        if random.random() < 0.03:  # Réduit de 5% à 3%
            time.sleep(random.uniform(0.3, 0.8))  # Réduit de 0.5-1.5 à 0.3-0.8
        
        i += 1
    
        # Pause après avoir fini de taper (optimisé pour vitesse)
        time.sleep(random.uniform(0.2, 0.5))


def scroll_to_element(driver, element: WebElement, block: str = 'center') -> None:
    """Fait défiler la page jusqu'à l'élément avec scroll progressif (plus humain)."""
    # Scroll progressif au lieu de téléportation
    driver.execute_script(f"arguments[0].scrollIntoView({{behavior: 'smooth', block: '{block}'}});", element)
    
    # Attendre que le scroll se termine
    time.sleep(random.uniform(0.5, 1.0))
    
    # Parfois scroll un peu plus (humain ajuste)
    if random.random() < 0.2:
        driver.execute_script("window.scrollBy(0, arguments[0]);", random.randint(-50, 50))
        time.sleep(random.uniform(0.2, 0.4))


def click_element(driver, element: WebElement) -> None:
    """Clique sur un élément avec mouvement de souris simulé."""
    from selenium.webdriver import ActionChains
    
    # Scroll vers l'élément
    scroll_to_element(driver, element)
    
    # Simuler mouvement de souris vers l'élément
    action = ActionChains(driver)
    action.move_to_element(element)
    
    # Ajouter offset aléatoire (humain ne clique pas au centre exact)
    offset_x = random.randint(-5, 5)
    offset_y = random.randint(-5, 5)
    action.move_by_offset(offset_x, offset_y)
    
    # Pause avant de cliquer (humain hésite)
    time.sleep(random.uniform(0.1, 0.3))
    
    # Cliquer
    action.click()
    action.perform()
    
    # Pause après clic
    time.sleep(random.uniform(0.2, 0.5))


def safe_find_elements(driver, by, value, timeout: int = 10) -> List[WebElement]:
    """Trouve des éléments de manière sécurisée avec timeout."""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    try:
        elements = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((by, value))
        )
        return elements
    except:
        return []


def safe_find_element(driver, by, value, timeout: int = 10) -> WebElement:
    """Trouve un élément de manière sécurisée avec timeout."""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def random_scroll(driver) -> None:
    """Effectue un scroll aléatoire pour simuler la lecture (humain)."""
    scroll_amount = random.randint(100, 300)
    direction = random.choice([-1, 1])
    driver.execute_script(f"window.scrollBy(0, {scroll_amount * direction});")
    time.sleep(random.uniform(0.3, 0.8))


def random_mouse_movement(driver) -> None:
    """Effectue des mouvements de souris aléatoires."""
    from selenium.webdriver import ActionChains
    
    action = ActionChains(driver)
    
    # 2-4 mouvements aléatoires
    num_movements = random.randint(2, 4)
    for _ in range(num_movements):
        x = random.randint(-100, 100)
        y = random.randint(-100, 100)
        action.move_by_offset(x, y)
        time.sleep(random.uniform(0.1, 0.3))
    
    action.perform()


def simulate_reading_time(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    """Simule le temps de lecture d'une page (humain lit avant de cliquer)."""
    reading_time = random.uniform(min_seconds, max_seconds)
    
    # Parfois plus long (humain lit attentivement)
    if random.random() < 0.15:
        reading_time += random.uniform(1.0, 3.0)
    
    time.sleep(reading_time)


# ============================================================================
# OPTIMISATIONS : Retry, Attente optimisée, Factorisation
# ============================================================================

def retry_on_failure(max_retries: int = 3, delay: float = 2.0, backoff: float = 1.5):
    """
    Décorateur pour réessayer une fonction en cas d'échec.
    
    Args:
        max_retries: Nombre maximum de tentatives
        delay: Délai initial entre les tentatives (secondes)
        backoff: Multiplicateur pour augmenter le délai à chaque tentative
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logger.info(f"✅ {func.__name__} réussi après {attempt} tentatives")
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"⚠️ Tentative {attempt}/{max_retries} échouée pour {func.__name__}: {e}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"❌ {func.__name__} a échoué après {max_retries} tentatives")
            
            raise last_exception
        return wrapper
    return decorator


def wait_with_check(total_seconds: int, check_interval: float = 1.0, stop_condition: Optional[Callable[[], bool]] = None) -> bool:
    """
    Attend un nombre de secondes avec vérification périodique d'une condition d'arrêt.
    Plus efficace que time.sleep() en boucle.
    
    Args:
        total_seconds: Nombre total de secondes à attendre
        check_interval: Intervalle entre les vérifications (secondes)
        stop_condition: Fonction qui retourne True pour arrêter l'attente
    
    Returns:
        True si l'attente s'est terminée normalement, False si arrêtée par la condition
    """
    if total_seconds <= 0:
        return True
    
    elapsed = 0.0
    while elapsed < total_seconds:
        if stop_condition and stop_condition():
            return False
        
        sleep_time = min(check_interval, total_seconds - elapsed)
        time.sleep(sleep_time)
        elapsed += sleep_time
    
    return True


def click_next_button(driver, timeout: int = 10) -> bool:
    """
    Factorisation : Clique sur le bouton "Suivant" de manière sécurisée.
    
    Returns:
        True si le clic a réussi, False sinon
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    try:
        selectors = [
            "//button[contains(., 'Suivant')]",
            "//button[contains(text(), 'Suivant')]",
            "//button[contains(., 'Next')]",
            "//button[@type='submit']",
            "//input[@type='submit' and contains(@value, 'Suivant')]"
        ]
        
        next_button = None
        for selector in selectors:
            try:
                next_button = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                if next_button:
                    break
            except:
                continue
        
        if not next_button:
            logger.error("❌ Bouton Suivant introuvable")
            return False
        
        # Vérifier si le bouton est désactivé
        is_disabled = driver.execute_script(
            "return arguments[0].disabled || arguments[0].hasAttribute('disabled');", 
            next_button
        )
        if is_disabled:
            logger.warning("⚠️ Le bouton Suivant est désactivé, attente supplémentaire...")
            wait_random(2, 3)
            is_disabled = driver.execute_script(
                "return arguments[0].disabled || arguments[0].hasAttribute('disabled');", 
                next_button
            )
            if is_disabled:
                logger.error("❌ Le bouton Suivant reste désactivé")
                return False
        
        # Scroll et clic (optimisé pour vitesse)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        wait_random(0.3, 0.6)  # Optimisé pour vitesse
        driver.execute_script("arguments[0].click();", next_button)
        wait_random(0.5, 1)  # Optimisé pour vitesse
        
        logger.debug("✅ Bouton Suivant cliqué")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du clic sur Suivant: {e}")
        return False


def validate_radio_selected(driver, element: WebElement, timeout: int = 2) -> bool:
    """
    Valide qu'un bouton radio est bien sélectionné.
    
    Returns:
        True si sélectionné, False sinon
    """
    try:
        # Attendre un peu pour que la sélection se propage
        time.sleep(0.3)
        
        # Vérifier via JavaScript
        is_checked = driver.execute_script("return arguments[0].checked;", element)
        
        if not is_checked:
            # Réessayer en cliquant directement
            driver.execute_script("arguments[0].checked = true;", element)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", element)
            time.sleep(0.2)
            is_checked = driver.execute_script("return arguments[0].checked;", element)
        
        return is_checked
    except Exception as e:
        logger.warning(f"⚠️ Erreur lors de la validation du radio: {e}")
        return False


def validate_text_input(driver, element: WebElement, expected_text: Optional[str] = None, min_length: int = 1) -> bool:
    """
    Valide qu'un champ texte contient bien du texte.
    
    Args:
        driver: Instance du driver
        element: Élément input/textarea
        expected_text: Texte attendu (optionnel)
        min_length: Longueur minimale requise
    
    Returns:
        True si valide, False sinon
    """
    try:
        time.sleep(0.2)  # Attendre que la valeur se propage
        
        value = driver.execute_script(
            "return arguments[0].value || arguments[0].textContent || arguments[0].innerHTML;", 
            element
        )
        
        if not value or len(value.strip()) < min_length:
            return False
        
        if expected_text and value.strip() != expected_text.strip():
            return False
        
        return True
    except Exception as e:
        logger.warning(f"⚠️ Erreur lors de la validation du texte: {e}")
        return False
