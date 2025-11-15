#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chargeur de configuration YAML."""

import yaml
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """Charge et gère la configuration depuis le fichier YAML."""
    
    def __init__(self, config_file: str = "config.yaml"):
        """Initialise le chargeur de configuration."""
        self.base_dir = Path(__file__).parent.parent
        self.config_file = self.base_dir / config_file
        self._config = None
    
    def load(self) -> Dict[str, Any]:
        """Charge la configuration depuis le fichier YAML."""
        if self._config is None:
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f)
            except FileNotFoundError:
                raise FileNotFoundError(f"Fichier de configuration introuvable: {self.config_file}")
            except yaml.YAMLError as e:
                raise ValueError(f"Erreur lors du parsing du fichier YAML: {e}")
        
        return self._config
    
    def get(self, key: str, default=None) -> Any:
        """Récupère une valeur de configuration."""
        config = self.load()
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_chrome_options(self) -> Dict[str, Any]:
        """Récupère les options Chrome."""
        return self.get('chrome', {})
    
    def get_timing(self, key: str) -> tuple:
        """Récupère un timing (min, max)."""
        timing = self.get(f'timing.{key}', [1, 2])
        return tuple(timing)
    
    def get_avis_mapping(self) -> Dict[str, str]:
        """Récupère le mapping des fichiers d'avis."""
        avis_files = self.get('avis_files', {})
        return {k: str(self.base_dir / v) for k, v in avis_files.items()}


# Instance globale
config = ConfigLoader()
