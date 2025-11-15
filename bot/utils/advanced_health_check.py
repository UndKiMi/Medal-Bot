#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Health check avancé du navigateur (#30)."""

import logging
import psutil
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


class AdvancedHealthCheck:
    """Monitoring avancé de la santé du navigateur."""
    
    def __init__(self):
        """Initialise le health check."""
        self.memory_threshold_mb = 2048  # 2GB
        self.cpu_threshold_percent = 90  # 90%
        self.check_interval = 30  # Vérifier toutes les 30 secondes
        self.last_check = None
        self.health_history = []
        self.max_history = 50
    
    def check_driver_health(self, driver: Optional[WebDriver]) -> Dict:
        """
        Vérifie la santé complète du driver.
        
        Args:
            driver: Instance du driver Selenium
        
        Returns:
            Dict avec les résultats du health check
        """
        result = {
            'healthy': False,
            'driver_accessible': False,
            'memory_ok': True,
            'cpu_ok': True,
            'window_open': False,
            'issues': []
        }
        
        if not driver:
            result['issues'].append('Driver is None')
            return result
        
        # Vérifier l'accessibilité du driver
        try:
            _ = driver.current_url
            result['driver_accessible'] = True
        except Exception as e:
            result['issues'].append(f'Driver not accessible: {str(e)[:50]}')
            return result
        
        # Vérifier que la fenêtre est ouverte
        try:
            handles = driver.window_handles
            result['window_open'] = len(handles) > 0
            if not result['window_open']:
                result['issues'].append('No window handles found')
        except Exception as e:
            result['issues'].append(f'Cannot check window handles: {str(e)[:50]}')
        
        # Vérifier l'utilisation mémoire
        try:
            memory_info = self._get_chrome_memory_usage()
            if memory_info:
                total_memory_mb = memory_info.get('total_mb', 0)
                if total_memory_mb > self.memory_threshold_mb:
                    result['memory_ok'] = False
                    result['issues'].append(f'High memory usage: {total_memory_mb:.0f}MB')
                result['memory_mb'] = total_memory_mb
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de la vérification mémoire: {e}")
        
        # Vérifier l'utilisation CPU
        try:
            cpu_percent = self._get_chrome_cpu_usage()
            if cpu_percent and cpu_percent > self.cpu_threshold_percent:
                result['cpu_ok'] = False
                result['issues'].append(f'High CPU usage: {cpu_percent:.1f}%')
            result['cpu_percent'] = cpu_percent
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de la vérification CPU: {e}")
        
        # Déterminer si tout est OK
        result['healthy'] = (
            result['driver_accessible'] and
            result['window_open'] and
            result['memory_ok'] and
            result['cpu_ok']
        )
        
        # Enregistrer dans l'historique
        self._record_health_check(result)
        
        self.last_check = datetime.now()
        return result
    
    def _get_chrome_memory_usage(self) -> Optional[Dict]:
        """Récupère l'utilisation mémoire de Chrome."""
        try:
            chrome_processes = []
            total_memory = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    if 'chrome' in proc.info['name'].lower():
                        memory_mb = proc.info['memory_info'].rss / (1024 * 1024)
                        total_memory += memory_mb
                        chrome_processes.append({
                            'pid': proc.info['pid'],
                            'memory_mb': memory_mb
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'total_mb': total_memory,
                'process_count': len(chrome_processes),
                'processes': chrome_processes[:10]  # Top 10
            }
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de la récupération mémoire: {e}")
            return None
    
    def _get_chrome_cpu_usage(self) -> Optional[float]:
        """Récupère l'utilisation CPU de Chrome."""
        try:
            total_cpu = 0.0
            chrome_count = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if 'chrome' in proc.info['name'].lower():
                        cpu = proc.cpu_percent(interval=0.1)
                        if cpu is not None:
                            total_cpu += cpu
                            chrome_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return total_cpu if chrome_count > 0 else None
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de la récupération CPU: {e}")
            return None
    
    def _record_health_check(self, result: Dict):
        """Enregistre un health check dans l'historique."""
        self.health_history.append({
            'timestamp': datetime.now(),
            'result': result
        })
        
        # Garder seulement les 50 derniers
        if len(self.health_history) > self.max_history:
            self.health_history = self.health_history[-self.max_history:]
    
    def get_health_summary(self) -> Dict:
        """Retourne un résumé de la santé."""
        if not self.health_history:
            return {'status': 'unknown', 'message': 'No health checks performed'}
        
        recent_checks = [
            h for h in self.health_history 
            if (datetime.now() - h['timestamp']).total_seconds() < 300  # 5 dernières minutes
        ]
        
        if not recent_checks:
            return {'status': 'unknown', 'message': 'No recent health checks'}
        
        healthy_count = sum(1 for h in recent_checks if h['result'].get('healthy', False))
        total_count = len(recent_checks)
        health_percentage = (healthy_count / total_count) * 100 if total_count > 0 else 0
        
        return {
            'status': 'healthy' if health_percentage >= 80 else 'degraded' if health_percentage >= 50 else 'unhealthy',
            'health_percentage': health_percentage,
            'recent_checks': total_count,
            'healthy_checks': healthy_count,
            'last_check': self.last_check.isoformat() if self.last_check else None
        }
    
    def should_restart(self) -> bool:
        """Détermine si un redémarrage est nécessaire."""
        if not self.health_history:
            return False
        
        recent_checks = [
            h for h in self.health_history 
            if (datetime.now() - h['timestamp']).total_seconds() < 300
        ]
        
        if len(recent_checks) < 3:
            return False
        
        # Si plus de 50% des checks récents sont malsains
        unhealthy_count = sum(1 for h in recent_checks if not h['result'].get('healthy', False))
        return (unhealthy_count / len(recent_checks)) > 0.5


# Instance globale
advanced_health_check = AdvancedHealthCheck()

