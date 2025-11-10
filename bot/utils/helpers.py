#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fonctions utilitaires pour le bot."""

import random
import time
from typing import List
from selenium.webdriver.remote.webelement import WebElement


def wait_random(min_seconds: float, max_seconds: float) -> None:
    """Attend un nombre aléatoire de secondes avec distribution gaussienne (plus humain)."""
    mean = (min_seconds + max_seconds) / 2
    std = (max_seconds - min_seconds) / 6
    delay = random.gauss(mean, std)
    delay = max(min_seconds, min(max_seconds, delay))
    
    # 10% du temps, ajouter une micro-pause (humain hésite)
    if random.random() < 0.1:
        delay += random.uniform(0.3, 1.0)
    
    time.sleep(delay)


def human_typing(element: WebElement, text: str, min_delay: float = 0.08, max_delay: float = 0.15, error_rate: float = 0.02) -> None:
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
        
        # Vitesse variable selon le caractère
        if char == ' ':
            delay = random.uniform(0.15, 0.25)  # Plus lent pour espace
        elif char in '.,!?':
            delay = random.uniform(0.2, 0.4)    # Pause après ponctuation
        elif char.isupper():
            delay = random.uniform(0.12, 0.20)  # Majuscule = Shift
        else:
            delay = random.uniform(min_delay, max_delay)
        
        time.sleep(delay)
        
        # Pause aléatoire (humain réfléchit)
        if random.random() < 0.05:
            time.sleep(random.uniform(0.5, 1.5))
        
        i += 1
    
    # Pause après avoir fini de taper
    time.sleep(random.uniform(0.3, 0.8))


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
