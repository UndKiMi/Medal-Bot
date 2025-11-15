#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Service de résolution de CAPTCHA avancé (#7)."""

import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class CaptchaSolver:
    """Gestionnaire de résolution de CAPTCHA via services externes."""
    
    def __init__(self):
        """Initialise le solveur de CAPTCHA."""
        self.enabled = False
        self.service = None
        self.api_key = None
        
        # Détection automatique du service configuré
        self._detect_service()
    
    def _detect_service(self):
        """Détecte et configure le service de résolution."""
        # 2Captcha
        api_key_2captcha = os.getenv('CAPTCHA_2CAPTCHA_API_KEY')
        if api_key_2captcha:
            self.service = '2captcha'
            self.api_key = api_key_2captcha
            self.enabled = True
            logger.info("✅ Service 2Captcha détecté")
            return
        
        # AntiCaptcha
        api_key_anticaptcha = os.getenv('CAPTCHA_ANTICAPTCHA_API_KEY')
        if api_key_anticaptcha:
            self.service = 'anticaptcha'
            self.api_key = api_key_anticaptcha
            self.enabled = True
            logger.info("✅ Service AntiCaptcha détecté")
            return
        
        logger.info("ℹ️ Aucun service de résolution CAPTCHA configuré")
    
    def solve_recaptcha_v2(self, site_key: str, page_url: str) -> Optional[str]:
        """
        Résout un reCAPTCHA v2.
        
        Args:
            site_key: Clé du site reCAPTCHA
            page_url: URL de la page contenant le CAPTCHA
        
        Returns:
            Token de résolution ou None en cas d'échec
        """
        if not self.enabled or not HAS_REQUESTS:
            return None
        
        try:
            if self.service == '2captcha':
                return self._solve_2captcha(site_key, page_url)
            elif self.service == 'anticaptcha':
                return self._solve_anticaptcha(site_key, page_url)
        except Exception as e:
            logger.error(f"❌ Erreur lors de la résolution CAPTCHA: {e}")
        
        return None
    
    def _solve_2captcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Résout via 2Captcha."""
        if not HAS_REQUESTS:
            return None
        
        # Soumettre la tâche
        submit_url = "http://2captcha.com/in.php"
        submit_data = {
            'key': self.api_key,
            'method': 'userrecaptcha',
            'googlekey': site_key,
            'pageurl': page_url,
            'json': 1
        }
        
        try:
            response = requests.post(submit_url, data=submit_data, timeout=30)
            result = response.json()
            
            if result.get('status') != 1:
                logger.error(f"❌ Erreur 2Captcha: {result.get('request', 'Unknown error')}")
                return None
            
            task_id = result.get('request')
            
            # Attendre la résolution (max 2 minutes)
            get_url = "http://2captcha.com/res.php"
            max_wait = 120
            waited = 0
            
            while waited < max_wait:
                time.sleep(5)
                waited += 5
                
                get_data = {
                    'key': self.api_key,
                    'action': 'get',
                    'id': task_id,
                    'json': 1
                }
                
                response = requests.get(get_url, params=get_data, timeout=30)
                result = response.json()
                
                if result.get('status') == 1:
                    return result.get('request')  # Token de résolution
                elif result.get('request') == 'CAPCHA_NOT_READY':
                    continue
                else:
                    logger.error(f"❌ Erreur 2Captcha: {result.get('request', 'Unknown error')}")
                    return None
            
            logger.warning("⏱️ Timeout lors de la résolution CAPTCHA")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la résolution 2Captcha: {e}")
            return None
    
    def _solve_anticaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Résout via AntiCaptcha."""
        if not HAS_REQUESTS:
            return None
        
        # AntiCaptcha utilise une API différente
        # Implémentation simplifiée - nécessite l'API complète pour production
        logger.warning("⚠️ AntiCaptcha non encore implémenté complètement")
        return None
    
    def is_enabled(self) -> bool:
        """Vérifie si le service est activé."""
        return self.enabled


# Instance globale
captcha_solver = CaptchaSolver()

