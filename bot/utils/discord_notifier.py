#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module de notifications Discord pour Medal Bot."""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("⚠️ Module 'requests' non installé. Les notifications Discord ne fonctionneront pas.")


class DiscordNotifier:
    """Gestionnaire de notifications Discord."""
    
    def __init__(self, bot_token: Optional[str] = None, channel_id: Optional[str] = None):
        """
        Initialise le notificateur Discord.
        
        Args:
            bot_token: Token du bot Discord (ou depuis variable d'environnement DISCORD_BOT_TOKEN)
            channel_id: ID du canal Discord (ou depuis variable d'environnement DISCORD_CHANNEL_ID)
        """
        self.bot_token = bot_token or os.getenv('DISCORD_BOT_TOKEN')
        self.channel_id = channel_id or os.getenv('DISCORD_CHANNEL_ID')
        self.enabled = bool(self.bot_token and self.channel_id and HAS_REQUESTS)
        
        if not HAS_REQUESTS:
            logger.warning("⚠️ Module 'requests' non disponible. Installez-le avec: pip install requests")
        elif not self.enabled:
            logger.info("ℹ️ Notifications Discord désactivées (token ou channel_id manquant)")
        else:
            logger.info("✅ Notifications Discord activées")
    
    def send_message(self, message: str, embed: Optional[dict] = None) -> bool:
        """
        Envoie un message sur Discord.
        
        Args:
            message: Message texte à envoyer
            embed: Dictionnaire pour créer un embed (optionnel)
        
        Returns:
            True si envoyé avec succès, False sinon
        """
        if not self.enabled:
            return False
        
        try:
            url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"
            headers = {
                "Authorization": f"Bot {self.bot_token}",
                "Content-Type": "application/json"
            }
            
            payload = {"content": message}
            if embed:
                payload["embeds"] = [embed]
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'envoi de notification Discord: {e}")
            return False
    
    def notify_success(self, questionnaire_num: int, category: str, duration: float):
        """Envoie une notification de succès."""
        embed = {
            "title": "✅ Questionnaire terminé avec succès",
            "description": f"Questionnaire #{questionnaire_num} - {category}",
            "color": 0x4ec9b0,  # Vert
            "fields": [
                {"name": "Catégorie", "value": category, "inline": True},
                {"name": "Durée", "value": f"{duration:.1f}s", "inline": True}
            ],
            "timestamp": None
        }
        self.send_message(f"✅ Questionnaire #{questionnaire_num} terminé avec succès!", embed)
    
    def notify_failure(self, questionnaire_num: int, category: str, reason: str = ""):
        """Envoie une notification d'échec."""
        embed = {
            "title": "❌ Échec du questionnaire",
            "description": f"Questionnaire #{questionnaire_num} - {category}",
            "color": 0xf48771,  # Rouge
            "fields": [
                {"name": "Catégorie", "value": category, "inline": True},
            ],
            "timestamp": None
        }
        if reason:
            embed["fields"].append({"name": "Raison", "value": reason, "inline": False})
        
        self.send_message(f"❌ Échec du questionnaire #{questionnaire_num}", embed)
    
    def notify_captcha(self):
        """Envoie une notification de détection CAPTCHA."""
        embed = {
            "title": "🚨 CAPTCHA détecté",
            "description": "Un CAPTCHA a été détecté. Le bot a été arrêté.",
            "color": 0xff0000,  # Rouge vif
            "timestamp": None
        }
        self.send_message("🚨 **CAPTCHA DÉTECTÉ** - Le bot a été arrêté automatiquement!", embed)
    
    def notify_quota_reached(self, count: int, limit: int):
        """Envoie une notification de quota atteint."""
        embed = {
            "title": "📊 Quota journalier atteint",
            "description": f"{count}/{limit} questionnaires effectués aujourd'hui",
            "color": 0xdcdcaa,  # Jaune
            "timestamp": None
        }
        self.send_message(f"📊 Quota journalier atteint: {count}/{limit}", embed)
    
    def notify_error(self, error_message: str):
        """Envoie une notification d'erreur."""
        embed = {
            "title": "⚠️ Erreur",
            "description": error_message[:2000],  # Limite Discord
            "color": 0xf48771,  # Rouge
            "timestamp": None
        }
        self.send_message(f"⚠️ Erreur: {error_message[:500]}", embed)


# Instance globale
discord_notifier = DiscordNotifier()

