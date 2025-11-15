#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cache intelligent des éléments DOM (#32)."""

import logging
import hashlib
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


class DOMCache:
    """Cache intelligent pour les éléments DOM fréquemment utilisés."""
    
    def __init__(self, default_ttl: int = 30):
        """
        Initialise le cache DOM.
        
        Args:
            default_ttl: TTL par défaut en secondes
        """
        self.cache: Dict[str, Dict] = {}
        self.default_ttl = default_ttl
        self.max_cache_size = 100  # Nombre max d'éléments en cache
        self.access_times: Dict[str, datetime] = {}
    
    def get_element(self, driver: WebDriver, by: By, value: str, 
                   ttl: Optional[int] = None) -> Optional[WebElement]:
        """
        Récupère un élément depuis le cache ou le trouve.
        
        Args:
            driver: Instance du driver
            by: Méthode de localisation (By.XPATH, etc.)
            value: Valeur du sélecteur
            ttl: TTL personnalisé (optionnel)
        
        Returns:
            WebElement ou None
        """
        cache_key = self._generate_key(by, value)
        ttl = ttl or self.default_ttl
        
        # Vérifier le cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            
            # Vérifier si le cache est encore valide
            age = (datetime.now() - cached['timestamp']).total_seconds()
            if age < ttl:
                try:
                    # Vérifier que l'élément est toujours valide
                    element = cached['element']
                    _ = element.is_displayed()  # Test simple de validité
                    
                    # Mettre à jour le temps d'accès
                    self.access_times[cache_key] = datetime.now()
                    
                    logger.debug(f"✅ Élément récupéré du cache: {value[:50]}")
                    return element
                except:
                    # Élément invalide, le retirer du cache
                    logger.debug(f"⚠️ Élément du cache invalide, retrait: {value[:50]}")
                    del self.cache[cache_key]
                    if cache_key in self.access_times:
                        del self.access_times[cache_key]
            else:
                # Cache expiré
                logger.debug(f"⏱️ Cache expiré pour: {value[:50]}")
                del self.cache[cache_key]
                if cache_key in self.access_times:
                    del self.access_times[cache_key]
        
        # Élément non en cache ou invalide, le trouver
        try:
            element = driver.find_element(by, value)
            
            # Mettre en cache
            self._cache_element(cache_key, element, value)
            
            return element
        except Exception as e:
            logger.debug(f"❌ Élément non trouvé: {value[:50]} - {str(e)[:50]}")
            return None
    
    def get_elements(self, driver: WebDriver, by: By, value: str,
                    ttl: Optional[int] = None) -> List[WebElement]:
        """
        Récupère plusieurs éléments depuis le cache ou les trouve.
        
        Args:
            driver: Instance du driver
            by: Méthode de localisation
            value: Valeur du sélecteur
            ttl: TTL personnalisé
        
        Returns:
            Liste de WebElements
        """
        cache_key = self._generate_key(by, value, multiple=True)
        ttl = ttl or self.default_ttl
        
        # Vérifier le cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            age = (datetime.now() - cached['timestamp']).total_seconds()
            
            if age < ttl:
                try:
                    elements = cached['elements']
                    # Vérifier que les éléments sont toujours valides
                    valid_elements = [e for e in elements if self._is_element_valid(e)]
                    
                    if len(valid_elements) > 0:
                        self.access_times[cache_key] = datetime.now()
                        logger.debug(f"✅ {len(valid_elements)} éléments récupérés du cache: {value[:50]}")
                        return valid_elements
                except:
                    pass
            
            # Cache invalide ou expiré
            del self.cache[cache_key]
            if cache_key in self.access_times:
                del self.access_times[cache_key]
        
        # Trouver les éléments
        try:
            elements = driver.find_elements(by, value)
            self._cache_elements(cache_key, elements, value)
            return elements
        except Exception as e:
            logger.debug(f"❌ Éléments non trouvés: {value[:50]} - {str(e)[:50]}")
            return []
    
    def _generate_key(self, by: By, value: str, multiple: bool = False) -> str:
        """Génère une clé de cache."""
        key_data = f"{by}:{value}:{multiple}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _cache_element(self, key: str, element: WebElement, selector: str):
        """Met un élément en cache."""
        # Nettoyer le cache si nécessaire
        self._cleanup_cache()
        
        self.cache[key] = {
            'element': element,
            'timestamp': datetime.now(),
            'selector': selector
        }
        self.access_times[key] = datetime.now()
    
    def _cache_elements(self, key: str, elements: List[WebElement], selector: str):
        """Met plusieurs éléments en cache."""
        self._cleanup_cache()
        
        self.cache[key] = {
            'elements': elements,
            'timestamp': datetime.now(),
            'selector': selector
        }
        self.access_times[key] = datetime.now()
    
    def _is_element_valid(self, element: WebElement) -> bool:
        """Vérifie si un élément est toujours valide."""
        try:
            _ = element.is_displayed()
            return True
        except:
            return False
    
    def _cleanup_cache(self):
        """Nettoie le cache si nécessaire."""
        if len(self.cache) < self.max_cache_size:
            return
        
        # Supprimer les éléments les moins récemment utilisés
        sorted_keys = sorted(
            self.access_times.items(),
            key=lambda x: x[1]
        )
        
        # Supprimer les 20% les plus anciens
        to_remove = int(self.max_cache_size * 0.2)
        for key, _ in sorted_keys[:to_remove]:
            if key in self.cache:
                del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
    
    def clear_cache(self):
        """Vide complètement le cache."""
        self.cache.clear()
        self.access_times.clear()
        logger.info("✅ Cache DOM vidé")
    
    def get_cache_stats(self) -> Dict:
        """Retourne des statistiques sur le cache."""
        return {
            'size': len(self.cache),
            'max_size': self.max_cache_size,
            'usage_percent': (len(self.cache) / self.max_cache_size) * 100
        }


# Instance globale
dom_cache = DOMCache()

