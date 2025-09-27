# skote/ticnochatbot/config/llm_manager.py

from typing import Dict, Optional, Any
from abc import ABC, abstractmethod
import openai
from anthropic import Anthropic
import requests
import json
from .credentials import credentials_manager

class LLMProvider(ABC):
    """Clase base para proveedores de LLM"""
    
    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        pass

class OpenAIProvider(LLMProvider):
    """Proveedor para OpenAI GPT"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
    
    def complete(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get('max_tokens', 150),
                temperature=kwargs.get('temperature', 0.3)
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error en OpenAI: {e}")
            return ""
    
    def count_tokens(self, text: str) -> int:
        # Aproximación simple: 1 token ≈ 4 caracteres
        return len(text) // 4

class ClaudeProvider(LLMProvider):
    """Proveedor para Anthropic Claude"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def complete(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get('max_tokens', 150),
                temperature=kwargs.get('temperature', 0.3),
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error en Claude: {e}")
            return ""
    
    def count_tokens(self, text: str) -> int:
        return len(text) // 4

class OllamaProvider(LLMProvider):
    """Proveedor para Ollama (local)"""
    
    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama2"):
        self.endpoint = endpoint
        self.model = model
    
    def complete(self, prompt: str, **kwargs) -> str:
        try:
            response = requests.post(
                f"{self.endpoint}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get('temperature', 0.3),
                        "num_predict": kwargs.get('max_tokens', 150)
                    }
                }
            )
            return response.json().get('response', '')
        except Exception as e:
            print(f"Error en Ollama: {e}")
            return ""
    
    def count_tokens(self, text: str) -> int:
        return len(text) // 4

class LLMManager:
    """Manager unificado para todos los proveedores de LLM"""
    
    # Configuración por defecto para cada proveedor
    DEFAULT_CONFIGS = {
        'openai': {
            'model': 'gpt-3.5-turbo',
            'temperature': 0.3,
            'max_tokens': 150
        },
        'claude': {
            'model': 'claude-3-haiku-20240307',
            'temperature': 0.3,
            'max_tokens': 150
        },
        'ollama': {
            'model': 'llama2',
            'temperature': 0.3,
            'max_tokens': 150
        }
    }
    
    def __init__(self, provider: str = 'openai', **override_config):
        """
        Inicializa el manager con un proveedor específico
        
        Args:
            provider: 'openai', 'claude', 'ollama'
            **override_config: Configuraciones para sobrescribir las default
        """
        self.provider_name = provider
        self.config = self.DEFAULT_CONFIGS.get(provider, {}).copy()
        self.config.update(override_config)
        
        # Obtener credenciales
        creds = credentials_manager.get_credential(provider)
        if not creds:
            raise ValueError(f"No hay credenciales configuradas para {provider}")
        
        # Inicializar el proveedor correcto
        self.provider = self._init_provider(provider, creds)
        self.total_tokens = 0
    
    def _init_provider(self, provider: str, creds: Dict) -> LLMProvider:
        """Inicializa el proveedor específico"""
        if provider == 'openai':
            return OpenAIProvider(
                api_key=creds['api_key'],
                model=self.config.get('model', 'gpt-3.5-turbo')
            )
        elif provider == 'claude':
            return ClaudeProvider(
                api_key=creds['api_key'],
                model=self.config.get('model', 'claude-3-haiku-20240307')
            )
        elif provider == 'ollama':
            return OllamaProvider(
                endpoint=creds.get('endpoint', 'http://localhost:11434'),
                model=self.config.get('model', 'llama2')
            )
        else:
            raise ValueError(f"Proveedor no soportado: {provider}")
    
    def complete(self, prompt: str, **kwargs) -> str:
        """
        Obtiene una completion del LLM
        
        Args:
            prompt: El prompt a enviar
            **kwargs: Parámetros adicionales (temperature, max_tokens, etc)
        
        Returns:
            La respuesta del LLM
        """
        # Combinar configuración default con kwargs
        params = self.config.copy()
        params.update(kwargs)
        
        # Contar tokens del prompt
        prompt_tokens = self.provider.count_tokens(prompt)
        self.total_tokens += prompt_tokens
        
        # Obtener respuesta
        response = self.provider.complete(prompt, **params)
        
        # Contar tokens de la respuesta
        response_tokens = self.provider.count_tokens(response)
        self.total_tokens += response_tokens
        
        return response
    
    def get_token_count(self) -> int:
        """Retorna el total de tokens usados"""
        return self.total_tokens
    
    def reset_token_count(self):
        """Resetea el contador de tokens"""
        self.total_tokens = 0
    
    def switch_provider(self, provider: str, **override_config):
        """Cambia a otro proveedor sin crear nueva instancia"""
        self.provider_name = provider
        self.config = self.DEFAULT_CONFIGS.get(provider, {}).copy()
        self.config.update(override_config)
        
        creds = credentials_manager.get_credential(provider)
        if not creds:
            raise ValueError(f"No hay credenciales configuradas para {provider}")
        
        self.provider = self._init_provider(provider, creds)

# Función helper para obtener un manager rápidamente
def get_llm(provider: str = None, **config) -> LLMManager:
    """
    Helper para obtener un LLM manager rápidamente
    
    Si no se especifica provider, intenta en orden: openai, claude, ollama
    """
    if provider:
        return LLMManager(provider, **config)
    
    # Intentar proveedores en orden de preferencia
    available = credentials_manager.list_providers()
    priority = ['openai', 'claude', 'ollama']
    
    for p in priority:
        if p in available:
            return LLMManager(p, **config)
    
    if available:
        return LLMManager(available[0], **config)
    
    raise ValueError("No hay proveedores de LLM configurados")