#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Système de logs amélioré avec recherche et filtres (#48)."""

import logging
import re
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path


class AdvancedLogHandler(logging.Handler):
    """Handler de logs avec fonctionnalités avancées."""
    
    def __init__(self, log_file: Path, max_lines: int = 10000):
        """
        Initialise le handler avancé.
        
        Args:
            log_file: Fichier de log
            max_lines: Nombre maximum de lignes à garder en mémoire
        """
        super().__init__()
        self.log_file = log_file
        self.max_lines = max_lines
        self.log_buffer: List[Dict] = []
        self.filters = {
            'level': None,  # Filtrer par niveau
            'keyword': None,  # Filtrer par mot-clé
            'date_from': None,  # Date de début
            'date_to': None  # Date de fin
        }
    
    def emit(self, record):
        """Émet un log."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Ajouter au buffer
        self.log_buffer.append(log_entry)
        
        # Limiter la taille du buffer
        if len(self.log_buffer) > self.max_lines:
            self.log_buffer = self.log_buffer[-self.max_lines:]
    
    def search_logs(self, query: str, case_sensitive: bool = False) -> List[Dict]:
        """
        Recherche dans les logs.
        
        Args:
            query: Requête de recherche
            case_sensitive: Recherche sensible à la casse
        
        Returns:
            Liste des logs correspondants
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(query, flags)
        
        results = []
        for entry in self.log_buffer:
            if pattern.search(entry['message']) or pattern.search(entry['module']):
                results.append(entry)
        
        return results
    
    def filter_logs(self, level: Optional[str] = None, keyword: Optional[str] = None,
                   date_from: Optional[datetime] = None, 
                   date_to: Optional[datetime] = None) -> List[Dict]:
        """
        Filtre les logs selon différents critères.
        
        Args:
            level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
            keyword: Mot-clé à rechercher
            date_from: Date de début
            date_to: Date de fin
        
        Returns:
            Liste des logs filtrés
        """
        filtered = self.log_buffer
        
        if level:
            filtered = [e for e in filtered if e['level'] == level.upper()]
        
        if keyword:
            keyword_lower = keyword.lower()
            filtered = [e for e in filtered if keyword_lower in e['message'].lower()]
        
        if date_from:
            filtered = [e for e in filtered if e['timestamp'] >= date_from]
        
        if date_to:
            filtered = [e for e in filtered if e['timestamp'] <= date_to]
        
        return filtered
    
    def export_logs(self, output_file: Path, logs: Optional[List[Dict]] = None,
                   export_format: str = 'txt') -> bool:
        """
        Exporte les logs dans un fichier.
        
        Args:
            output_file: Fichier de sortie
            logs: Logs à exporter (None = tous)
            export_format: Format d'export (txt, json, csv)
        
        Returns:
            True si succès
        """
        logs_to_export = logs or self.log_buffer
        
        try:
            if export_format == 'json':
                import json
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(logs_to_export, f, indent=2, default=str)
            
            elif export_format == 'csv':
                import csv
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['timestamp', 'level', 'message', 'module', 'function', 'line'])
                    writer.writeheader()
                    for entry in logs_to_export:
                        writer.writerow(entry)
            
            else:  # txt
                with open(output_file, 'w', encoding='utf-8') as f:
                    for entry in logs_to_export:
                        f.write(f"[{entry['timestamp']}] {entry['level']}: {entry['message']}\n")
            
            return True
        except Exception as e:
            logging.error(f"❌ Erreur lors de l'export des logs: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Retourne des statistiques sur les logs."""
        if not self.log_buffer:
            return {}
        
        levels = {}
        for entry in self.log_buffer:
            level = entry['level']
            levels[level] = levels.get(level, 0) + 1
        
        return {
            'total_logs': len(self.log_buffer),
            'by_level': levels,
            'oldest': self.log_buffer[0]['timestamp'] if self.log_buffer else None,
            'newest': self.log_buffer[-1]['timestamp'] if self.log_buffer else None
        }
    
    def clear_buffer(self):
        """Vide le buffer de logs."""
        self.log_buffer.clear()

