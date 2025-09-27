"""
Orquestador Principal del Sistema de ChatBot
Coordina el flujo entre classifier, state_manager y engines
Ubicación: /ticnochatbot/core/orchestrator.py
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Tipos de mensajes que puede manejar el sistema"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT = "contact"

class MessageStatus(Enum):
    """Estados de procesamiento de mensajes"""
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Message:
    """Estructura básica de un mensaje normalizado"""
    id: str
    chat_id: str
    user_id: str
    content: str
    message_type: MessageType
    timestamp: datetime
    channel: str = "unknown"
    metadata: Dict[str, Any] = None
    status: MessageStatus = MessageStatus.RECEIVED
    classification: Optional[Dict[str, Any]] = None
    conversation_state: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class MessageProcessor:
    """Procesador básico de mensajes - se expandirá con los engines"""
    
    def __init__(self):
        self.response_templates = {
            "greeting": [
                "¡Hola! Soy el asistente de CFT CENCO. ¿En qué puedo ayudarte?",
                "¡Hola! ¿Te interesa conocer nuestras carreras?",
                "¡Bienvenido/a! Estoy aquí para resolver tus dudas sobre CFT CENCO."
            ],
            "help": [
                "Puedo ayudarte con información sobre nuestras carreras, procesos de matrícula, aranceles y más.",
                "¿Te gustaría conocer nuestras carreras disponibles o tienes alguna pregunta específica?",
            ],
            "ask_price": [
                "Los aranceles varían según la carrera. ¿Qué carrera te interesa?",
                "Te puedo dar información sobre costos. ¿Cuál es la carrera de tu interés?",
            ],
            "general": [
                "Entiendo tu consulta. ¿Podrías ser más específico para ayudarte mejor?",
                "Estoy aquí para ayudarte. ¿Qué información específica necesitas sobre CFT CENCO?",
            ],
            "goodbye": [
                "¡Gracias por contactarnos! Si tienes más preguntas, no dudes en escribir.",
                "¡Que tengas un excelente día! Espero haberte ayudado.",
            ]
        }
    
    async def process_text(self, message: Message) -> str:
        """Procesa mensajes de texto usando clasificación"""
        logger.info(f"Procesando mensaje de texto: {message.id}")
        
        # Usar clasificación si está disponible
        if message.classification:
            intent = message.classification.get("intent", "general")
            confidence = message.classification.get("confidence", 0.0)
            
            logger.info(f"Mensaje clasificado como: {intent} (confianza: {confidence:.2f})")
            
            # Obtener respuesta basada en intención
            templates = self.response_templates.get(intent, self.response_templates["general"])
            
            # Por ahora, usar la primera respuesta del template
            # Más adelante aquí entraríán los engines específicos
            base_response = templates[0]
            
            # Personalizar respuesta con contexto si está disponible
            if message.conversation_state:
                user_name = message.conversation_state.get("user_name")
                if user_name and intent == "greeting":
                    base_response = f"¡Hola {user_name}! " + base_response
            
            return base_response
        
        else:
            # Fallback si no hay clasificación
            return self._basic_text_processing(message.content)
    
    def _basic_text_processing(self, content: str) -> str:
        """Procesamiento básico sin clasificación (fallback)"""
        content_lower = content.lower()
        
        if any(greeting in content_lower for greeting in ['hola', 'hello', 'hi', 'hey']):
            return self.response_templates["greeting"][0]
        elif any(help_word in content_lower for help_word in ['help', 'ayuda', 'ayudar']):
            return self.response_templates["help"][0]
        elif any(price_word in content_lower for price_word in ['precio', 'costo', 'cuánto']):
            return self.response_templates["ask_price"][0]
        elif any(bye_word in content_lower for bye_word in ['chao', 'adiós', 'bye', 'gracias']):
            return self.response_templates["goodbye"][0]
        else:
            return self.response_templates["general"][0]
    
    async def process_image(self, message: Message) -> str:
        """Procesa mensajes con imágenes"""
        logger.info(f"Procesando imagen: {message.id}")
        return "He recibido tu imagen. El análisis de imágenes se implementará próximamente con los engines avanzados."
    
    async def process_audio(self, message: Message) -> str:
        """Procesa mensajes de audio"""
        logger.info(f"Procesando audio: {message.id}")
        return "He recibido tu mensaje de audio. La transcripción se implementará próximamente."
    
    async def process_document(self, message: Message) -> str:
        """Procesa documentos"""
        logger.info(f"Procesando documento: {message.id}")
        return "He recibido tu documento. El análisis de documentos se implementará próximamente."
    
    async def process_location(self, message: Message) -> str:
        """Procesa ubicaciones compartidas"""
        logger.info(f"Procesando ubicación: {message.id}")
        return "He recibido tu ubicación. Las funciones basadas en ubicación se implementarán próximamente."
    
    async def process_contact(self, message: Message) -> str:
        """Procesa contactos compartidos"""
        logger.info(f"Procesando contacto: {message.id}")
        return "He recibido el contacto. Las funciones de contactos se implementarán próximamente."

class Orchestrator:
    """Orquestador principal del sistema"""
    
    def __init__(self):
        self.processor = MessageProcessor()
        self.active_chats: Dict[str, Dict] = {}
        self.message_history: List[Message] = []
        self.max_history = 1000
        
        # Aquí se integrarán los engines cuando estén implementados
        self.journey_engine = None  # Se inicializará más tarde
        self.faq_engine = None      # Se inicializará más tarde
        self.proactive_engine = None # Se inicializará más tarde
        
    async def process_webhook_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Punto de entrada principal desde la API
        
        Args:
            message_data: Diccionario con los datos del mensaje normalizado
            
        Returns:
            Diccionario con la respuesta procesada
        """
        try:
            # Crear objeto Message desde los datos recibidos
            message = self._create_message_from_data(message_data)
            
            # Actualizar estado del chat
            self._update_chat_state(message)
            
            # Procesar el mensaje según su tipo y clasificación
            response_content = await self._route_message(message)
            
            # Marcar como completado
            message.status = MessageStatus.COMPLETED
            
            # Guardar en historial
            self._add_to_history(message)
            
            # Preparar respuesta
            response = {
                "success": True,
                "message_id": message.id,
                "chat_id": message.chat_id,
                "response": response_content,
                "timestamp": datetime.now().isoformat(),
                "processed_type": message.message_type.value,
                "classification": message.classification
            }
            
            logger.info(f"Mensaje procesado exitosamente: {message.id}")
            return response
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_message_from_data(self, data: Dict[str, Any]) -> Message:
        """Crea un objeto Message desde datos normalizados de la API"""
        
        # Detectar tipo de mensaje
        message_type = MessageType.TEXT  # Por defecto
        content = data.get('text', '')
        
        if data.get('photo'):
            message_type = MessageType.IMAGE
            content = data.get('caption', '[Imagen]')
        elif data.get('voice') or data.get('audio'):
            message_type = MessageType.AUDIO
            content = '[Mensaje de audio]'
        elif data.get('document'):
            message_type = MessageType.DOCUMENT
            content = f"[Documento: {data.get('document', {}).get('file_name', 'archivo')}]"
        elif data.get('location'):
            message_type = MessageType.LOCATION
            content = '[Ubicación compartida]'
        elif data.get('contact'):
            message_type = MessageType.CONTACT
            content = f"[Contacto: {data.get('contact', {}).get('first_name', 'Desconocido')}]"
        
        return Message(
            id=str(data.get('message_id', f"msg_{datetime.now().timestamp()}")),
            chat_id=str(data.get('chat', {}).get('id', 'unknown')),
            user_id=str(data.get('from', {}).get('id', 'unknown')),
            content=content,
            message_type=message_type,
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            channel=data.get('channel', 'unknown'),
            metadata=data,
            status=MessageStatus.PROCESSING,
            classification=data.get('classification'),
            conversation_state=data.get('conversation_state')
        )
    
    async def _route_message(self, message: Message) -> str:
        """Enruta el mensaje al procesador apropiado"""
        
        # Mapeo de tipos a procesadores
        processors = {
            MessageType.TEXT: self.processor.process_text,
            MessageType.IMAGE: self.processor.process_image,
            MessageType.AUDIO: self.processor.process_audio,
            MessageType.DOCUMENT: self.processor.process_document,
            MessageType.LOCATION: self.processor.process_location,
            MessageType.CONTACT: self.processor.process_contact
        }
        
        processor_func = processors.get(message.message_type)
        if processor_func:
            return await processor_func(message)
        else:
            return f"Tipo de mensaje no soportado: {message.message_type.value}"
    
    def _update_chat_state(self, message: Message):
        """Actualiza el estado del chat activo"""
        chat_id = message.chat_id
        
        if chat_id not in self.active_chats:
            self.active_chats[chat_id] = {
                "first_message": message.timestamp,
                "last_message": message.timestamp,
                "message_count": 0,
                "user_id": message.user_id,
                "channel": message.channel,
                "last_intent": None
            }
        
        # Actualizar información del chat
        self.active_chats[chat_id]["last_message"] = message.timestamp
        self.active_chats[chat_id]["message_count"] += 1
        
        if message.classification:
            self.active_chats[chat_id]["last_intent"] = message.classification.get("intent")
    
    def _add_to_history(self, message: Message):
        """Añade mensaje al historial con límite de memoria"""
        self.message_history.append(message)
        
        # Mantener solo los últimos N mensajes
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
    
    def get_chat_info(self, chat_id: str) -> Optional[Dict]:
        """Obtiene información de un chat específico"""
        return self.active_chats.get(chat_id)
    
    def get_recent_messages(self, chat_id: str, limit: int = 10) -> List[Message]:
        """Obtiene mensajes recientes de un chat"""
        return [
            msg for msg in self.message_history[-limit:]
            if msg.chat_id == chat_id
        ]
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Verifica el estado del orquestador"""
        return {
            "status": "healthy",
            "active_chats": len(self.active_chats),
            "total_messages": len(self.message_history),
            "engines_loaded": {
                "journey_engine": self.journey_engine is not None,
                "faq_engine": self.faq_engine is not None,
                "proactive_engine": self.proactive_engine is not None
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_active_chats(self) -> Dict[str, Dict]:
        """Obtiene información de chats activos"""
        return self.active_chats.copy()

# ===== INSTANCIA GLOBAL Y FUNCIONES DE CONVENIENCIA =====

# Instancia global del orquestador
orchestrator = Orchestrator()

# Funciones para uso desde la API
async def process_webhook_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """Función principal para procesar mensajes desde la API"""
    return await orchestrator.process_webhook_message(message_data)

async def get_system_health() -> Dict[str, Any]:
    """Obtiene el estado de salud del sistema"""
    return await orchestrator.get_system_health()

def get_active_chats() -> Dict[str, Dict]:
    """Obtiene información de chats activos"""
    return orchestrator.get_active_chats()

def get_chat_info(chat_id: str) -> Optional[Dict]:
    """Obtiene información de un chat específico"""
    return orchestrator.get_chat_info(chat_id)

def get_recent_messages(chat_id: str, limit: int = 10) -> List[Message]:
    """Obtiene mensajes recientes de un chat"""
    return orchestrator.get_recent_messages(chat_id, limit)

# ===== FUNCIONES PARA INTEGRACIÓN CON ENGINES (FUTURO) =====

def register_journey_engine(engine):
    """Registra el journey engine cuando esté implementado"""
    orchestrator.journey_engine = engine
    logger.info("Journey engine registrado exitosamente")

def register_faq_engine(engine):
    """Registra el FAQ engine cuando esté implementado"""
    orchestrator.faq_engine = engine
    logger.info("FAQ engine registrado exitosamente")

def register_proactive_engine(engine):
    """Registra el proactive engine cuando esté implementado"""
    orchestrator.proactive_engine = engine
    logger.info("Proactive engine registrado exitosamente")

if __name__ == "__main__":
    # Ejemplo de uso y pruebas básicas
    async def test_orchestrator():
        """Pruebas básicas del orquestador"""
        print("🚀 Iniciando pruebas del orquestador...")
        
        # Mensaje de prueba
        test_message = {
            "message_id": 123,
            "chat": {"id": "test_chat_1"},
            "from": {"id": "test_user_1"},
            "text": "Hola, ¿cómo estás?",
            "timestamp": datetime.now().isoformat(),
            "channel": "console",
            "classification": {
                "intent": "greeting",
                "confidence": 0.95
            }
        }
        
        # Procesar mensaje
        result = await process_webhook_message(test_message)
        print(f"✅ Resultado: {result}")
        
        # Verificar salud del sistema
        health = await get_system_health()
        print(f"💚 Estado del sistema: {health}")
        
        # Obtener chats activos
        chats = get_active_chats()
        print(f"💬 Chats activos: {chats}")
        
        print("🎉 Pruebas completadas exitosamente.")
    
    # Ejecutar pruebas si se ejecuta directamente
    asyncio.run(test_orchestrator())