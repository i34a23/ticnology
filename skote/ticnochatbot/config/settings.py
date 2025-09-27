# skote/ticnochatbot/config/settings.py

import os
from typing import Dict, Any

class AgentSettings:
    """Configuraciones generales del agente"""
    
    # Configuración de comportamiento del agente
    AGENT_CONFIG = {
        'name': 'Mia',
        'company': 'CFT CENCO',
        'language': 'es',
        'timezone': 'America/Santiago',
        'business_hours': {
            'start': 9,  # 9 AM
            'end': 20,   # 8 PM
            'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        }
    }
    
    # Configuración de Journey
    JOURNEY_CONFIG = {
        'default_journey_id': 1,  # CFT CENCO Journey
        'max_steps_per_conversation': 20,
        'session_timeout_minutes': 30,
        'followup_delay_hours': 24
    }
    
    # Configuración de respuestas
    RESPONSE_CONFIG = {
        'max_response_length': 150,  # caracteres
        'typing_delay_ms': 1500,  # simular typing
        'max_retries': 3,
        'timeout_seconds': 30
    }
    
    # Configuración de clasificación
    CLASSIFICATION_CONFIG = {
        'use_llm_threshold': 0.7,  # Si confidence < 0.7, usar LLM
        'faq_keywords': [
            'precio', 'costo', 'valor', 'pagar', 'cuota',
            'horario', 'hora', 'cuando', 'días',
            'duración', 'tiempo', 'meses', 'años',
            'requisitos', 'documentos', 'papeles',
            'carrera', 'programa', 'estudiar'
        ],
        'objection_keywords': [
            'caro', 'costoso', 'no puedo pagar',
            'no tengo tiempo', 'muy largo',
            'no estoy seguro', 'tengo que pensarlo',
            'después', 'más adelante'
        ]
    }
    
    # Configuración de métricas
    METRICS_CONFIG = {
        'track_tokens': True,
        'track_response_time': True,
        'track_conversation_flow': True,
        'report_interval_minutes': 60
    }
    
    # Configuración de base de conocimientos (Qdrant)
    QDRANT_CONFIG = {
        'host': os.getenv('QDRANT_HOST', 'localhost'),
        'port': int(os.getenv('QDRANT_PORT', 6333)),
        'collection_name': 'cft_cenco_knowledge',
        'embedding_model': 'text-embedding-ada-002',
        'similarity_threshold': 0.75
    }
    
    # Configuración de canales
    CHANNELS_CONFIG = {
        'whatsapp': {
            'enabled': False,  # Por ahora en desarrollo
            'api_endpoint': os.getenv('WHATSAPP_API_URL'),
            'token': os.getenv('WHATSAPP_TOKEN')
        },
        'webchat': {
            'enabled': True,
            'widget_config': {
                'position': 'bottom-right',
                'color': '#007bff',
                'welcome_message': '¡Hola! Soy Mia de CFT CENCO 📚'
            }
        }
    }
    
    # Templates de mensajes comunes
    MESSAGE_TEMPLATES = {
        'welcome': "¡Hola {nombre}! Soy {agent_name} de {company} 📚 Te escribo por tu interés en **{carrera}**. ¡Excelente elección para tu futuro profesional! ¿Estás listo para comenzar con el proceso de matrícula?",
        
        'objection_price': "Entiendo tu preocupación por el costo. Lo bueno es que tenemos planes de pago flexibles y puedes dividirlo hasta en {cuotas} cuotas. Además, la inversión en tu educación siempre vale la pena 💪",
        
        'objection_time': "Te comprendo perfectamente. Por eso tenemos el Plan Especial que dura solo 14 meses si tienes experiencia laboral. ¿Te gustaría saber si calificas?",
        
        'followup': "Hola {nombre} 👋 Ayer conversamos sobre {carrera}. ¿Pudiste revisar la información que te envié? Estoy aquí para resolver cualquier duda",
        
        'documents_request': "Para continuar con tu matrícula, necesito que me envíes:\n{documentos}\n\n¿Tienes estos documentos a mano?",
        
        'closing': "¡Perfecto {nombre}! He registrado toda tu información. El equipo de admisión revisará tus documentos y te contactará en las próximas 24-48 horas. ¿Tienes alguna pregunta antes de finalizar?"
    }
    
    @classmethod
    def get_config(cls, section: str = None) -> Dict[str, Any]:
        """Obtiene una sección de configuración o toda"""
        if section:
            return getattr(cls, f"{section.upper()}_CONFIG", {})
        
        # Retornar toda la configuración
        config = {}
        for attr in dir(cls):
            if attr.endswith('_CONFIG'):
                config[attr.lower().replace('_config', '')] = getattr(cls, attr)
        return config
    
    @classmethod
    def get_template(cls, template_name: str, **kwargs) -> str:
        """Obtiene y formatea un template de mensaje"""
        template = cls.MESSAGE_TEMPLATES.get(template_name, '')
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

# Singleton de configuración
settings = AgentSettings()