#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gestion du driver Chrome."""

import logging
import random
import time
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
        
        # Création du driver (logs détaillés supprimés pour la console)
        driver = uc.Chrome(
            options=options,
            use_subprocess=True,
            version_main=None,
            suppress_welcome=True,
            driver_executable_path=None
        )
        
        # Attendre que le driver soit stable et charger une page blanche pour maintenir la fenêtre ouverte
        time.sleep(1)  # Délai pour stabiliser le driver
        
        # Vérifier que la fenêtre est toujours ouverte
        try:
            _ = driver.current_url
        except Exception:
            logger.error("❌ La fenêtre Chrome s'est fermée immédiatement après l'ouverture")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            return None
        
        # Charger une page blanche pour maintenir la fenêtre ouverte pendant l'injection des scripts
        try:
            driver.get("about:blank")
            time.sleep(0.5)  # Attendre que la page se charge
        except Exception as e:
            logger.warning(f"⚠️ Impossible de charger about:blank: {e}")
        
        # Application des paramètres de furtivité avec gestion d'erreur
        try:
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
        except Exception as stealth_error:
            # Si stealth échoue, on continue quand même (les scripts manuels seront injectés)
            logger.warning(f"⚠️ Erreur lors de l'application de stealth (continuation): {stealth_error}")
            # Vérifier que la fenêtre est toujours ouverte
            try:
                _ = driver.current_url
            except Exception:
                logger.error("❌ La fenêtre Chrome s'est fermée pendant l'injection stealth")
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                return None
        
        # Injection des scripts anti-détection avec gestion d'erreur
        try:
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
        except Exception as cdp_error:
            # Si l'injection CDP échoue, on continue quand même
            logger.warning(f"⚠️ Erreur lors de l'injection CDP (continuation): {cdp_error}")
            # Vérifier que la fenêtre est toujours ouverte
            try:
                _ = driver.current_url
            except Exception:
                logger.error("❌ La fenêtre Chrome s'est fermée pendant l'injection CDP")
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                return None
        
        # Configuration de la fenêtre avec vérification
        try:
            width, height = map(int, chrome_options['window_size'].split(','))
            width += random.randint(-20, 20)
            height += random.randint(-20, 20)
            driver.set_window_size(width, height)
        except Exception as size_error:
            logger.warning(f"⚠️ Erreur lors du redimensionnement (continuation): {size_error}")
            # Vérifier que la fenêtre est toujours ouverte
            try:
                _ = driver.current_url
            except Exception:
                logger.error("❌ La fenêtre Chrome s'est fermée pendant le redimensionnement")
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                return None
        
        # Simulation de mouvement de souris avec vérification
        try:
            action = ActionChains(driver)
            action.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()
        except Exception as mouse_error:
            logger.warning(f"⚠️ Erreur lors du mouvement de souris (continuation): {mouse_error}")
        
        # Vérification finale que le driver est fonctionnel
        try:
            _ = driver.current_url
            logger.info("✅ Navigateur initialisé")
            return driver
        except Exception:
            logger.error("❌ Le driver n'est pas fonctionnel après l'initialisation")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            return None
        
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
