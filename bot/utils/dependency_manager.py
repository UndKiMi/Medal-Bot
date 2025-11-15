#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gestionnaire de mise à jour des dépendances (#70)."""

import logging
import subprocess
import sys
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    # Essayer d'abord avec importlib.metadata (Python 3.8+)
    from importlib.metadata import version, distributions
    HAS_PKG_RESOURCES = True
    USE_IMPORTLIB = True
except ImportError:
    try:
        # Fallback vers pkg_resources (déprécié mais fonctionne)
        import pkg_resources
        HAS_PKG_RESOURCES = True
        USE_IMPORTLIB = False
    except ImportError:
        HAS_PKG_RESOURCES = False
        USE_IMPORTLIB = False


class DependencyManager:
    """Gère les mises à jour des dépendances."""
    
    def __init__(self, requirements_file: Optional[Path] = None):
        """
        Initialise le gestionnaire de dépendances.
        
        Args:
            requirements_file: Chemin vers le fichier requirements.txt
        """
        if requirements_file is None:
            requirements_file = Path(__file__).parent.parent.parent / "requirements_optimized.txt"
        self.requirements_file = requirements_file
    
    def check_outdated_packages(self) -> List[Dict]:
        """
        Vérifie les packages obsolètes.
        
        Returns:
            Liste des packages avec leurs versions
        """
        if not HAS_PKG_RESOURCES:
            logger.warning("⚠️ pkg_resources non disponible")
            return []
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--outdated', '--format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                outdated = json.loads(result.stdout)
                return outdated
            else:
                logger.warning(f"⚠️ Erreur lors de la vérification: {result.stderr}")
                return []
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification des packages: {e}")
            return []
    
    def update_package(self, package_name: str, version: Optional[str] = None) -> bool:
        """
        Met à jour un package.
        
        Args:
            package_name: Nom du package
            version: Version spécifique (optionnel)
        
        Returns:
            True si succès
        """
        try:
            package_spec = f"{package_name}=={version}" if version else package_name
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '--upgrade', package_spec],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Package {package_name} mis à jour")
                return True
            else:
                logger.error(f"❌ Erreur lors de la mise à jour de {package_name}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"❌ Erreur lors de la mise à jour: {e}")
            return False
    
    def check_compatibility(self, package_name: str, version: str) -> bool:
        """
        Vérifie la compatibilité d'une version.
        
        Args:
            package_name: Nom du package
            version: Version à vérifier
        
        Returns:
            True si compatible
        """
        # Vérification basique - peut être améliorée
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '--dry-run', f"{package_name}=={version}"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except:
            return False
    
    def get_installed_versions(self) -> Dict[str, str]:
        """Retourne les versions installées des packages."""
        if not HAS_PKG_RESOURCES:
            return {}
        
        try:
            installed = {}
            with open(self.requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Gérer les formats: package>=version, package==version, package
                        parts = line.split('>=')[0].split('==')[0].split('<=')[0].split('~=')[0]
                        package_name = parts.strip()
                        try:
                            if USE_IMPORTLIB:
                                installed[package_name] = version(package_name)
                            else:
                                import pkg_resources
                                dist = pkg_resources.get_distribution(package_name)
                                installed[package_name] = dist.version
                        except:
                            installed[package_name] = 'unknown'
            return installed
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des versions: {e}")
            return {}


# Instance globale
dependency_manager = DependencyManager()

