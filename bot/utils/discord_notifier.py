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
    
    # ===== AMÉLIORATION 24: NOTIFICATIONS DISCORD AVANCÉES =====
    
    def notify_daily_summary(self, stats: dict):
        """Envoie un résumé quotidien (#24)."""
        if not self.enabled:
            return False
        
        try:
            from datetime import datetime
            total = stats.get('total', 0)
            success = stats.get('success', 0)
            failed = stats.get('failed', 0)
            success_rate = (success / total * 100) if total > 0 else 0
            
            embed = {
                "title": "📊 Résumé Quotidien",
                "description": f"Statistiques du {datetime.now().strftime('%d/%m/%Y')}",
                "color": 0x4ec9b0 if success_rate >= 80 else 0xdcdcaa if success_rate >= 50 else 0xf48771,
                "fields": [
                    {"name": "Total", "value": str(total), "inline": True},
                    {"name": "✅ Succès", "value": str(success), "inline": True},
                    {"name": "❌ Échecs", "value": str(failed), "inline": True},
                    {"name": "Taux de réussite", "value": f"{success_rate:.1f}%", "inline": True},
                ],
                "timestamp": datetime.now().isoformat(),
                "footer": {"text": "Medal Bot - Résumé automatique"}
            }
            
            # Ajouter les statistiques par catégorie
            by_category = stats.get('by_category', {})
            if by_category:
                category_text = "\n".join([f"{cat}: {count}" for cat, count in by_category.items() if count > 0])
                if category_text:
                    embed["fields"].append({"name": "Par catégorie", "value": category_text[:1024], "inline": False})
            
            return self.send_message("📊 **Résumé quotidien**", embed)
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'envoi du résumé quotidien: {e}")
            return False
    
    def notify_weekly_summary(self, stats: dict):
        """Envoie un résumé hebdomadaire (#24)."""
        if not self.enabled:
            return False
        
        try:
            from datetime import datetime, timedelta
            week_start = datetime.now() - timedelta(days=7)
            
            total = stats.get('total', 0)
            success = stats.get('success', 0)
            failed = stats.get('failed', 0)
            success_rate = (success / total * 100) if total > 0 else 0
            
            embed = {
                "title": "📈 Résumé Hebdomadaire",
                "description": f"Statistiques de la semaine du {week_start.strftime('%d/%m/%Y')} au {datetime.now().strftime('%d/%m/%Y')}",
                "color": 0x569cd6,  # Bleu
                "fields": [
                    {"name": "Total", "value": str(total), "inline": True},
                    {"name": "✅ Succès", "value": str(success), "inline": True},
                    {"name": "❌ Échecs", "value": str(failed), "inline": True},
                    {"name": "Taux de réussite", "value": f"{success_rate:.1f}%", "inline": True},
                ],
                "timestamp": datetime.now().isoformat(),
                "footer": {"text": "Medal Bot - Résumé hebdomadaire"}
            }
            
            return self.send_message("📈 **Résumé hebdomadaire**", embed)
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'envoi du résumé hebdomadaire: {e}")
            return False
    
    def send_rich_embed(self, title: str, description: str, color: int = 0x4ec9b0, 
                       fields: list = None, footer: str = None):
        """Envoie un embed riche avec tous les détails (#24)."""
        if not self.enabled:
            return False
        
        try:
            from datetime import datetime
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.now().isoformat()
            }
            
            if fields:
                embed["fields"] = fields
            
            if footer:
                embed["footer"] = {"text": footer}
            
            return self.send_message(title, embed)
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'envoi de l'embed riche: {e}")
            return False


# Instance globale
discord_notifier = DiscordNotifier()

