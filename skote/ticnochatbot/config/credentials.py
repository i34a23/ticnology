# skote/ticnochatbot/config/credentials.py

import os
from typing import Dict, Optional
from cryptography.fernet import Fernet
from skote import db
from datetime import datetime
import json

# Importamos el modelo desde models.py
from ..models import AgentCredentials

class CredentialsManager:
    """Gestiona las credenciales de forma segura"""
    
    def __init__(self):
        # Generar o cargar clave de encriptación
        self.cipher_key = self._get_or_create_cipher_key()
        self.cipher = Fernet(self.cipher_key)
    
    def _get_or_create_cipher_key(self) -> bytes:
        """Obtiene o crea una clave de encriptación"""
        key_file = os.path.join(os.path.dirname(__file__), '.encryption_key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def save_credential(self, provider: str, api_key: str, 
                       endpoint: Optional[str] = None, 
                       settings: Optional[Dict] = None) -> bool:
        """Guarda una credencial de forma segura"""
        try:
            # Encriptar API key
            encrypted_key = self.cipher.encrypt(api_key.encode()).decode()
            
            # Buscar si ya existe
            cred = AgentCredentials.query.filter_by(provider=provider).first()
            
            if cred:
                # Actualizar existente
                cred.api_key = encrypted_key
                cred.endpoint = endpoint
                cred.settings = settings or {}
                cred.updated_at = datetime.utcnow()
            else:
                # Crear nueva
                cred = AgentCredentials(
                    provider=provider,
                    api_key=encrypted_key,
                    endpoint=endpoint,
                    settings=settings or {}
                )
                db.session.add(cred)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error guardando credencial: {e}")
            return False
    
    def get_credential(self, provider: str) -> Optional[Dict]:
        """Obtiene y desencripta una credencial"""
        try:
            cred = AgentCredentials.query.filter_by(
                provider=provider, 
                is_active=True
            ).first()
            
            if not cred:
                return None
            
            # Desencriptar API key
            decrypted_key = self.cipher.decrypt(cred.api_key.encode()).decode()
            
            return {
                'api_key': decrypted_key,
                'endpoint': cred.endpoint,
                'settings': cred.settings or {}
            }
            
        except Exception as e:
            print(f"Error obteniendo credencial: {e}")
            return None
    
    def list_providers(self) -> list:
        """Lista todos los proveedores configurados"""
        creds = AgentCredentials.query.filter_by(is_active=True).all()
        return [c.provider for c in creds]
    
    def deactivate_credential(self, provider: str) -> bool:
        """Desactiva una credencial sin eliminarla"""
        try:
            cred = AgentCredentials.query.filter_by(provider=provider).first()
            if cred:
                cred.is_active = False
                db.session.commit()
                return True
            return False
        except Exception:
            db.session.rollback()
            return False

# Instancia singleton
credentials_manager = CredentialsManager()