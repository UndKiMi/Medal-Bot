#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Récepteur de webhooks pour commandes externes (#36)."""

import logging
import json
import hmac
import hashlib
import threading
from typing import Optional, Callable, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class WebhookHandler(BaseHTTPRequestHandler):
    """Handler pour les webhooks entrants."""
    
    webhook_receiver = None  # Sera défini par le serveur
    
    def do_POST(self):
        """Gère les requêtes POST (webhooks)."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
            
            # Vérifier la signature si configurée
            signature = self.headers.get('X-Webhook-Signature', '')
            if not self._verify_signature(body, signature):
                self._send_error(401, "Invalid signature")
                return
            
            # Traiter le webhook
            result = self._process_webhook(data)
            self._send_json({'success': True, 'result': result})
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement du webhook: {e}")
            self._send_error(500, str(e))
    
    def _verify_signature(self, body: str, signature: str) -> bool:
        """Vérifie la signature du webhook."""
        if not self.webhook_receiver or not self.webhook_receiver.secret:
            return True  # Pas de vérification si pas de secret configuré
        
        try:
            expected_signature = hmac.new(
                self.webhook_receiver.secret.encode(),
                body.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except:
            return False
    
    def _process_webhook(self, data: Dict) -> Any:
        """Traite le webhook."""
        if not self.webhook_receiver:
            return {'error': 'Webhook receiver not available'}
        
        action = data.get('action')
        params = data.get('params', {})
        
        return self.webhook_receiver.handle_action(action, params)
    
    def _send_json(self, data: Dict):
        """Envoie une réponse JSON."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _send_error(self, code: int, message: str):
        """Envoie une erreur."""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Désactive les logs par défaut."""
        pass


class WebhookReceiver:
    """Récepteur de webhooks pour commandes externes."""
    
    def __init__(self, port: int = 8081, secret: Optional[str] = None, bot_controller: Optional[Any] = None):
        """
        Initialise le récepteur de webhooks.
        
        Args:
            port: Port d'écoute
            secret: Secret pour vérifier les signatures (optionnel)
            bot_controller: Contrôleur du bot
        """
        self.port = port
        self.secret = secret
        self.bot_controller = bot_controller
        self.server = None
        self.server_thread = None
        self.running = False
        self.action_handlers = {
            'start': self._handle_start,
            'stop': self._handle_stop,
            'status': self._handle_status,
            'stats': self._handle_stats
        }
    
    def start(self):
        """Démarre le récepteur de webhooks."""
        if self.running:
            logger.warning("⚠️ Récepteur de webhooks déjà en cours d'exécution")
            return
        
        try:
            WebhookHandler.webhook_receiver = self
            self.server = HTTPServer(('localhost', self.port), WebhookHandler)
            self.running = True
            
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            logger.info(f"✅ Récepteur de webhooks démarré sur http://localhost:{self.port}")
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du récepteur de webhooks: {e}")
            self.running = False
    
    def _run_server(self):
        """Exécute le serveur dans un thread."""
        try:
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"❌ Erreur dans le récepteur de webhooks: {e}")
        finally:
            self.running = False
    
    def stop(self):
        """Arrête le récepteur de webhooks."""
        if not self.running:
            return
        
        try:
            self.running = False
            if self.server:
                self.server.shutdown()
            logger.info("✅ Récepteur de webhooks arrêté")
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'arrêt du récepteur de webhooks: {e}")
    
    def handle_action(self, action: str, params: Dict) -> Any:
        """Traite une action de webhook."""
        handler = self.action_handlers.get(action)
        if handler:
            return handler(params)
        else:
            return {'error': f'Unknown action: {action}'}
    
    def register_handler(self, action: str, handler: Callable):
        """Enregistre un handler personnalisé."""
        self.action_handlers[action] = handler
    
    def _handle_start(self, params: Dict) -> Dict:
        """Gère l'action start."""
        if not self.bot_controller:
            return {'error': 'Bot controller not available'}
        success = self.bot_controller.start_bot()
        return {'success': success}
    
    def _handle_stop(self, params: Dict) -> Dict:
        """Gère l'action stop."""
        if not self.bot_controller:
            return {'error': 'Bot controller not available'}
        success = self.bot_controller.stop_bot()
        return {'success': success}
    
    def _handle_status(self, params: Dict) -> Dict:
        """Gère l'action status."""
        if not self.bot_controller:
            return {'error': 'Bot controller not available'}
        return self.bot_controller.get_status()
    
    def _handle_stats(self, params: Dict) -> Dict:
        """Gère l'action stats."""
        if not self.bot_controller:
            return {'error': 'Bot controller not available'}
        return self.bot_controller.get_stats()
    
    def is_running(self) -> bool:
        """Vérifie si le récepteur est en cours d'exécution."""
        return self.running

