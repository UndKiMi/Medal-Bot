#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chiffrement des données sensibles (#54)."""

import logging
import os
import base64
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    logger.warning("⚠️ Module 'cryptography' non disponible. Le chiffrement sera désactivé.")


class DataEncryption:
    """Gestionnaire de chiffrement des données sensibles."""
    
    def __init__(self):
        """Initialise le gestionnaire de chiffrement."""
        self.key_file = Path(__file__).parent.parent.parent / ".encryption_key"
        self.key = None
        self.cipher = None
        
        if HAS_CRYPTOGRAPHY:
            self._load_or_create_key()
        else:
            logger.warning("⚠️ Chiffrement désactivé - module cryptography non disponible")
    
    def _load_or_create_key(self):
        """Charge ou crée une clé de chiffrement."""
        if self.key_file.exists():
            try:
                with open(self.key_file, 'rb') as f:
                    self.key = f.read()
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement de la clé: {e}")
                self._create_new_key()
        else:
            self._create_new_key()
        
        if self.key:
            try:
                self.cipher = Fernet(self.key)
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'initialisation du chiffrement: {e}")
                self.cipher = None
    
    def _create_new_key(self):
        """Crée une nouvelle clé de chiffrement."""
        try:
            # Générer une clé depuis un mot de passe système ou aléatoire
            password = os.getenv('MEDAL_BOT_ENCRYPTION_PASSWORD', os.urandom(32))
            
            if isinstance(password, str):
                password = password.encode()
            
            # Utiliser PBKDF2 pour dériver une clé
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Sauvegarder la clé
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            # Définir les permissions (Unix seulement)
            try:
                os.chmod(self.key_file, 0o600)
            except:
                pass
            
            self.key = key
            logger.info("✅ Nouvelle clé de chiffrement créée")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la création de la clé: {e}")
            self.key = None
    
    def encrypt(self, data: str) -> Optional[str]:
        """
        Chiffre une chaîne de caractères.
        
        Args:
            data: Données à chiffrer
        
        Returns:
            Données chiffrées (base64) ou None en cas d'erreur
        """
        if not self.cipher or not HAS_CRYPTOGRAPHY:
            return data  # Retourner non chiffré si le chiffrement n'est pas disponible
        
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"❌ Erreur lors du chiffrement: {e}")
            return None
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """
        Déchiffre une chaîne de caractères.
        
        Args:
            encrypted_data: Données chiffrées (base64)
        
        Returns:
            Données déchiffrées ou None en cas d'erreur
        """
        if not self.cipher or not HAS_CRYPTOGRAPHY:
            return encrypted_data  # Retourner tel quel si le chiffrement n'est pas disponible
        
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"❌ Erreur lors du déchiffrement: {e}")
            return None
    
    def encrypt_file(self, file_path: Path, output_path: Optional[Path] = None):
        """Chiffre un fichier."""
        if not self.cipher or not HAS_CRYPTOGRAPHY:
            logger.warning("⚠️ Chiffrement non disponible")
            return False
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            encrypted = self.cipher.encrypt(data)
            
            output = output_path or file_path.with_suffix(file_path.suffix + '.encrypted')
            with open(output, 'wb') as f:
                f.write(encrypted)
            
            logger.info(f"✅ Fichier chiffré: {output}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur lors du chiffrement du fichier: {e}")
            return False
    
    def decrypt_file(self, encrypted_path: Path, output_path: Optional[Path] = None):
        """Déchiffre un fichier."""
        if not self.cipher or not HAS_CRYPTOGRAPHY:
            logger.warning("⚠️ Chiffrement non disponible")
            return False
        
        try:
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted = self.cipher.decrypt(encrypted_data)
            
            output = output_path or encrypted_path.with_suffix('')
            if output.suffix == '.encrypted':
                output = output.with_suffix('')
            
            with open(output, 'wb') as f:
                f.write(decrypted)
            
            logger.info(f"✅ Fichier déchiffré: {output}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur lors du déchiffrement du fichier: {e}")
            return False


# Instance globale
data_encryption = DataEncryption()

