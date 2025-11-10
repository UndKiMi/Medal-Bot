#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gestion du driver Chrome."""

import logging
import random
import traceback
from typing import Optional

import undetected_chromedriver as uc
from selenium.webdriver import ActionChains
from selenium_stealth import stealth

logger = logging.getLogger(__name__)


def setup_driver(chrome_options: dict) -> Optional[uc.Chrome]:
    """Configure et retourne une instance du navigateur Chrome avec anti-détection avancée."""
    driver = None
    try:
        options = uc.ChromeOptions()
        
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-notifications')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-popup-blocking')
        
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        logger.info("🔧 Création du driver Chrome...")
        driver = uc.Chrome(
            options=options,
            use_subprocess=True,
            version_main=None,
            suppress_welcome=True,
            driver_executable_path=None
        )
        
        logger.info("🎨 Application des paramètres de furtivité...")
        stealth(
            driver,
            languages=chrome_options['languages'],
            vendor=chrome_options['vendor'],
            platform=chrome_options['platform'],
            webgl_vendor=chrome_options['webgl_vendor'],
            renderer=chrome_options['renderer'],
            fix_hairline=True,
            user_agent=chrome_options["user_agent"]
        )
        
        logger.info("📜 Injection des scripts anti-détection...")
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                window.chrome = {
                    runtime: {}
                };
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['fr-FR', 'fr', 'en-US', 'en']
                });
            '''
        })
        
        logger.info("📐 Configuration de la fenêtre...")
        width, height = map(int, chrome_options['window_size'].split(','))
        width += random.randint(-20, 20)
        height += random.randint(-20, 20)
        driver.set_window_size(width, height)
        
        logger.info("🖱️ Simulation de mouvement de souris...")
        action = ActionChains(driver)
        action.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()
        
        logger.info("✅ Navigateur initialisé avec anti-détection avancée")
        return driver
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation du navigateur: {e}")
        logger.debug(f"Détails: {traceback.format_exc()}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return None


def cleanup_driver(driver) -> None:
    """Ferme le navigateur de manière propre."""
    if driver:
        try:
            driver.quit()
            logger.info("✅ Navigateur fermé avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la fermeture du navigateur: {e}")
