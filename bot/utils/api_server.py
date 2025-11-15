#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serveur API REST pour contrôler le bot à distance (#35)."""

import logging
import json
import threading
from typing import Optional, Callable, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class BotAPIHandler(BaseHTTPRequestHandler):
    """Handler pour les requêtes API."""
    
    bot_controller = None  # Sera défini par le serveur
    
    def do_GET(self):
        """Gère les requêtes GET."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        if path == '/api/status':
            self._handle_status()
        elif path == '/api/stats':
            self._handle_stats()
        elif path == '/api/health':
            self._handle_health()
        else:
            self._send_error(404, "Endpoint not found")
    
    def do_POST(self):
        """Gère les requêtes POST."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path == '/api/start':
            self._handle_start()
        elif path == '/api/stop':
            self._handle_stop()
        elif path == '/api/command':
            self._handle_command(data)
        else:
            self._send_error(404, "Endpoint not found")
    
    def _handle_status(self):
        """Retourne le statut du bot."""
        if not self.bot_controller:
            self._send_error(500, "Bot controller not available")
            return
        
        status = self.bot_controller.get_status()
        self._send_json(status)
    
    def _handle_stats(self):
        """Retourne les statistiques."""
        if not self.bot_controller:
            self._send_error(500, "Bot controller not available")
            return
        
        stats = self.bot_controller.get_stats()
        self._send_json(stats)
    
    def _handle_health(self):
        """Health check endpoint."""
        self._send_json({'status': 'ok', 'service': 'medal-bot-api'})
    
    def _handle_start(self):
        """Démarre le bot."""
        if not self.bot_controller:
            self._send_error(500, "Bot controller not available")
            return
        
        success = self.bot_controller.start_bot()
        self._send_json({'success': success, 'message': 'Bot started' if success else 'Failed to start'})
    
    def _handle_stop(self):
        """Arrête le bot."""
        if not self.bot_controller:
            self._send_error(500, "Bot controller not available")
            return
        
        success = self.bot_controller.stop_bot()
        self._send_json({'success': success, 'message': 'Bot stopped' if success else 'Failed to stop'})
    
    def _handle_command(self, data: Dict):
        """Exécute une commande personnalisée."""
        if not self.bot_controller:
            self._send_error(500, "Bot controller not available")
            return
        
        command = data.get('command')
        if not command:
            self._send_error(400, "Command not specified")
            return
        
        result = self.bot_controller.execute_command(command, data.get('params', {}))
        self._send_json({'success': True, 'result': result})
    
    def _send_json(self, data: Dict):
        """Envoie une réponse JSON."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
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


class BotAPIServer:
    """Serveur API REST pour le bot."""
    
    def __init__(self, port: int = 8080, bot_controller: Optional[Any] = None):
        """
        Initialise le serveur API.
        
        Args:
            port: Port d'écoute
            bot_controller: Contrôleur du bot (doit avoir get_status, get_stats, start_bot, stop_bot)
        """
        self.port = port
        self.bot_controller = bot_controller
        self.server = None
        self.server_thread = None
        self.running = False
    
    def start(self):
        """Démarre le serveur API."""
        if self.running:
            logger.warning("⚠️ Serveur API déjà en cours d'exécution")
            return
        
        try:
            BotAPIHandler.bot_controller = self.bot_controller
            self.server = HTTPServer(('localhost', self.port), BotAPIHandler)
            self.running = True
            
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            logger.info(f"✅ Serveur API démarré sur http://localhost:{self.port}")
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du serveur API: {e}")
            self.running = False
    
    def _run_server(self):
        """Exécute le serveur dans un thread."""
        try:
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"❌ Erreur dans le serveur API: {e}")
        finally:
            self.running = False
    
    def stop(self):
        """Arrête le serveur API."""
        if not self.running:
            return
        
        try:
            self.running = False
            if self.server:
                self.server.shutdown()
            logger.info("✅ Serveur API arrêté")
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'arrêt du serveur API: {e}")
    
    def is_running(self) -> bool:
        """Vérifie si le serveur est en cours d'exécution."""
        return self.running

