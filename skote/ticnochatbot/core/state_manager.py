"""
Gestor de Estados de Conversación
Maneja el estado de las conversaciones, contexto y progreso del usuario
Ubicación: /ticnochatbot/core/state_manager.py
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import asyncio

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConversationState:
    """Estado de una conversación individual"""
    user_id: str
    chat_id: str
    channel: str
    created_at: datetime
    last_updated: datetime
    message_count: int
    current_intent: Optional[str] = None
    last_intent: Optional[str] = None
    context: Dict[str, Any] = None
    user_data: Dict[str, Any] = None
    journey_data: Dict[str, Any] = None
    flags: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.user_data is None:
            self.user_data = {}
        if self.journey_data is None:
            self.journey_data = {}
        if self.flags is None:
            self.flags = {}

@dataclass
class MessageHistory:
    """Historial de un mensaje en la conversación"""
    message_id: str
    timestamp: datetime
    user_message: str
    bot_response: str
    intent: str
    confidence: float
    entities: List[Dict]

class ConversationStateManager:
    """Gestor principal de estados de conversación"""
    
    def __init__(self):
        # Almacén temporal en memoria (en producción será base de datos)
        self.conversations: Dict[str, ConversationState] = {}
        self.message_histories: Dict[str, List[MessageHistory]] = {}
        
        # Configuración
        self.max_history_per_conversation = 100
        self.conversation_timeout_hours = 24
        self.cleanup_interval_minutes = 30
        
        # Estadísticas
        self.stats = {
            "total_conversations": 0,
            "active_conversations": 0,
            "messages_processed": 0,
            "average_messages_per_conversation": 0.0
        }
        
    def _generate_conversation_key(self, user_id: str, chat_id: str) -> str:
        """Genera clave única para la conversación"""
        return f"{user_id}_{chat_id}"
    
    async def get_conversation_state(self, user_id: str, chat_id: str = None) -> ConversationState:
        """
        Obtiene o crea el estado de conversación para un usuario
        
        Args:
            user_id: ID único del usuario
            chat_id: ID del chat (opcional, usa user_id si no se proporciona)
            
        Returns:
            ConversationState actual o nuevo
        """
        if chat_id is None:
            chat_id = user_id
            
        conv_key = self._generate_conversation_key(user_id, chat_id)
        
        # Si la conversación ya existe, actualizarla
        if conv_key in self.conversations:
            conversation = self.conversations[conv_key]
            conversation.last_updated = datetime.now()
            logger.debug(f"Estado recuperado para {user_id}")
            return conversation
        
        # Crear nueva conversación
        new_conversation = ConversationState(
            user_id=user_id,
            chat_id=chat_id,
            channel="unknown",  # Se actualizará cuando llegue el primer mensaje
            created_at=datetime.now(),
            last_updated=datetime.now(),
            message_count=0
        )
        
        self.conversations[conv_key] = new_conversation
        self.message_histories[conv_key] = []
        self.stats["total_conversations"] += 1
        
        logger.info(f"Nueva conversación creada para usuario {user_id}")
        return new_conversation
    
    async def update_conversation_state(
        self, 
        user_id: str, 
        chat_id: str = None,
        last_message: str = "",
        last_response: str = "",
        classification: Dict[str, Any] = None,
        **kwargs
    ) -> ConversationState:
        """
        Actualiza el estado de una conversación existente
        
        Args:
            user_id: ID del usuario
            chat_id: ID del chat
            last_message: Último mensaje del usuario
            last_response: Última respuesta del bot
            classification: Clasificación del mensaje
            **kwargs: Campos adicionales para actualizar
            
        Returns:
            ConversationState actualizado
        """
        conversation = await self.get_conversation_state(user_id, chat_id)
        
        # Actualizar datos básicos
        conversation.last_updated = datetime.now()
        conversation.message_count += 1
        
        # Actualizar intenciones si hay clasificación
        if classification:
            conversation.last_intent = conversation.current_intent
            conversation.current_intent = classification.get("intent")
            
            # Agregar entidades al contexto
            entities = classification.get("entities", [])
            if entities:
                if "entities" not in conversation.context:
                    conversation.context["entities"] = []
                conversation.context["entities"].extend(entities)
        
        # Actualizar campos adicionales
        for key, value in kwargs.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)
        
        # Guardar en historial
        if last_message and last_response:
            await self._add_to_message_history(
                user_id=user_id,
                chat_id=chat_id,
                user_message=last_message,
                bot_response=last_response,
                classification=classification
            )
        
        # Actualizar estadísticas
        self._update_stats()
        
        logger.debug(f"Estado actualizado para {user_id}: {conversation.message_count} mensajes")
        return conversation
    
    async def _add_to_message_history(
        self,
        user_id: str,
        chat_id: str,
        user_message: str,
        bot_response: str,
        classification: Dict[str, Any] = None
    ):
        """Añade intercambio al historial de mensajes"""
        conv_key = self._generate_conversation_key(user_id, chat_id or user_id)
        
        if conv_key not in self.message_histories:
            self.message_histories[conv_key] = []
        
        history_entry = MessageHistory(
            message_id=f"msg_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            user_message=user_message,
            bot_response=bot_response,
            intent=classification.get("intent", "unknown") if classification else "unknown",
            confidence=classification.get("confidence", 0.0) if classification else 0.0,
            entities=classification.get("entities", []) if classification else []
        )
        
        self.message_histories[conv_key].append(history_entry)
        
        # Mantener límite de historial
        if len(self.message_histories[conv_key]) > self.max_history_per_conversation:
            self.message_histories[conv_key] = self.message_histories[conv_key][-self.max_history_per_conversation:]
        
        self.stats["messages_processed"] += 1
    
    async def get_conversation_history(self, user_id: str, chat_id: str = None, limit: int = 10) -> List[Dict]:
        """
        Obtiene el historial de mensajes de una conversación
        
        Args:
            user_id: ID del usuario
            chat_id: ID del chat (opcional)
            limit: Número máximo de mensajes a retornar
            
        Returns:
            Lista de intercambios de mensajes
        """
        conv_key = self._generate_conversation_key(user_id, chat_id or user_id)
        
        if conv_key not in self.message_histories:
            return []
        
        history = self.message_histories[conv_key]
        recent_history = history[-limit:] if len(history) > limit else history
        
        # Convertir a diccionarios para serialización
        return [
            {
                "message_id": entry.message_id,
                "timestamp": entry.timestamp.isoformat(),
                "user_message": entry.user_message,
                "bot_response": entry.bot_response,
                "intent": entry.intent,
                "confidence": entry.confidence,
                "entities": entry.entities
            }
            for entry in recent_history
        ]
    
    async def create_conversation(self, user_id: str, chat_id: str, channel: str = "unknown") -> ConversationState:
        """
        Crea explícitamente una nueva conversación
        
        Args:
            user_id: ID del usuario
            chat_id: ID del chat
            channel: Canal de comunicación
            
        Returns:
            Nueva ConversationState
        """
        conv_key = self._generate_conversation_key(user_id, chat_id)
        
        # Si ya existe, limpiar estado anterior
        if conv_key in self.conversations:
            logger.warning(f"Recreando conversación existente para {user_id}")
        
        new_conversation = ConversationState(
            user_id=user_id,
            chat_id=chat_id,
            channel=channel,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            message_count=0
        )
        
        self.conversations[conv_key] = new_conversation
        self.message_histories[conv_key] = []
        
        if conv_key not in self.conversations:  # Solo incrementar si es realmente nuevo
            self.stats["total_conversations"] += 1
        
        logger.info(f"Conversación creada/recreada para {user_id} en canal {channel}")
        return new_conversation
    
    async def set_user_data(self, user_id: str, key: str, value: Any, chat_id: str = None):
        """Establece datos específicos del usuario en su estado"""
        conversation = await self.get_conversation_state(user_id, chat_id)
        conversation.user_data[key] = value
        conversation.last_updated = datetime.now()
        logger.debug(f"Usuario {user_id}: {key} = {value}")
    
    async def get_user_data(self, user_id: str, key: str, default: Any = None, chat_id: str = None) -> Any:
        """Obtiene datos específicos del usuario"""
        conversation = await self.get_conversation_state(user_id, chat_id)
        return conversation.user_data.get(key, default)
    
    async def set_context(self, user_id: str, key: str, value: Any, chat_id: str = None):
        """Establece contexto de la conversación"""
        conversation = await self.get_conversation_state(user_id, chat_id)
        conversation.context[key] = value
        conversation.last_updated = datetime.now()
        logger.debug(f"Contexto {user_id}: {key} = {value}")
    
    async def get_context(self, user_id: str, key: str = None, chat_id: str = None) -> Any:
        """Obtiene contexto de la conversación"""
        conversation = await self.get_conversation_state(user_id, chat_id)
        
        if key is None:
            return conversation.context
        else:
            return conversation.context.get(key)
    
    async def set_flag(self, user_id: str, flag: str, value: bool = True, chat_id: str = None):
        """Establece una bandera en el estado de conversación"""
        conversation = await self.get_conversation_state(user_id, chat_id)
        conversation.flags[flag] = value
        conversation.last_updated = datetime.now()
        logger.debug(f"Flag {user_id}: {flag} = {value}")
    
    async def get_flag(self, user_id: str, flag: str, chat_id: str = None) -> bool:
        """Obtiene el valor de una bandera"""
        conversation = await self.get_conversation_state(user_id, chat_id)
        return conversation.flags.get(flag, False)
    
    async def clear_conversation(self, user_id: str, chat_id: str = None):
        """Limpia completamente una conversación"""
        conv_key = self._generate_conversation_key(user_id, chat_id or user_id)
        
        if conv_key in self.conversations:
            del self.conversations[conv_key]
            logger.info(f"Conversación eliminada para {user_id}")
        
        if conv_key in self.message_histories:
            del self.message_histories[conv_key]
            logger.info(f"Historial eliminado para {user_id}")
    
    async def cleanup_expired_conversations(self):
        """Limpia conversaciones que han expirado"""
        cutoff_time = datetime.now() - timedelta(hours=self.conversation_timeout_hours)
        expired_keys = []
        
        for key, conversation in self.conversations.items():
            if conversation.last_updated < cutoff_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            if key in self.conversations:
                del self.conversations[key]
            if key in self.message_histories:
                del self.message_histories[key]
            logger.info(f"Conversación expirada eliminada: {key}")
        
        if expired_keys:
            logger.info(f"Limpieza completada: {len(expired_keys)} conversaciones eliminadas")
    
    def _update_stats(self):
        """Actualiza estadísticas internas"""
        self.stats["active_conversations"] = len(self.conversations)
        
        if self.stats["total_conversations"] > 0:
            self.stats["average_messages_per_conversation"] = (
                self.stats["messages_processed"] / self.stats["total_conversations"]
            )
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas del sistema"""
        self._update_stats()
        
        return {
            **self.stats,
            "configuration": {
                "max_history_per_conversation": self.max_history_per_conversation,
                "conversation_timeout_hours": self.conversation_timeout_hours,
                "cleanup_interval_minutes": self.cleanup_interval_minutes
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_active_conversations(self) -> List[Dict]:
        """Obtiene lista de conversaciones activas"""
        active_convs = []
        
        for key, conversation in self.conversations.items():
            # Considerar activas las conversaciones de las últimas 2 horas
            if datetime.now() - conversation.last_updated < timedelta(hours=2):
                active_convs.append({
                    "user_id": conversation.user_id,
                    "chat_id": conversation.chat_id,
                    "channel": conversation.channel,
                    "message_count": conversation.message_count,
                    "current_intent": conversation.current_intent,
                    "last_updated": conversation.last_updated.isoformat(),
                    "created_at": conversation.created_at.isoformat()
                })
        
        return active_convs

# ===== INSTANCIA GLOBAL Y FUNCIONES DE CONVENIENCIA =====

# Instancia global del gestor de estado
state_manager = ConversationStateManager()

# Funciones para uso desde otros módulos
async def get_conversation_state(user_id: str, chat_id: str = None) -> Dict[str, Any]:
    """Obtiene estado de conversación como diccionario"""
    state = await state_manager.get_conversation_state(user_id, chat_id)
    return asdict(state)

async def update_conversation_state(user_id: str, chat_id: str = None, **kwargs) -> Dict[str, Any]:
    """Actualiza estado de conversación"""
    state = await state_manager.update_conversation_state(user_id, chat_id, **kwargs)
    return asdict(state)

async def create_conversation(user_id: str, chat_id: str, channel: str = "unknown") -> Dict[str, Any]:
    """Crea nueva conversación"""
    state = await state_manager.create_conversation(user_id, chat_id, channel)
    return asdict(state)

async def get_conversation_history(user_id: str, chat_id: str = None, limit: int = 10) -> List[Dict]:
    """Obtiene historial de conversación"""
    return await state_manager.get_conversation_history(user_id, chat_id, limit)

async def get_state_manager_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del state manager"""
    return await state_manager.get_system_stats()

async def get_active_conversations() -> List[Dict]:
    """Obtiene conversaciones activas"""
    return await state_manager.get_active_conversations()

# Funciones de conveniencia para datos de usuario y contexto
async def set_user_data(user_id: str, key: str, value: Any, chat_id: str = None):
    """Establece dato del usuario"""
    await state_manager.set_user_data(user_id, key, value, chat_id)

async def get_user_data(user_id: str, key: str, default: Any = None, chat_id: str = None) -> Any:
    """Obtiene dato del usuario"""
    return await state_manager.get_user_data(user_id, key, default, chat_id)

async def set_context(user_id: str, key: str, value: Any, chat_id: str = None):
    """Establece contexto de conversación"""
    await state_manager.set_context(user_id, key, value, chat_id)

async def get_context(user_id: str, key: str = None, chat_id: str = None) -> Any:
    """Obtiene contexto de conversación"""
    return await state_manager.get_context(user_id, key, chat_id)

async def set_flag(user_id: str, flag: str, value: bool = True, chat_id: str = None):
    """Establece bandera"""
    await state_manager.set_flag(user_id, flag, value, chat_id)

async def get_flag(user_id: str, flag: str, chat_id: str = None) -> bool:
    """Obtiene bandera"""
    return await state_manager.get_flag(user_id, flag, chat_id)

# ===== FUNCIONES DE MANTENIMIENTO =====

async def cleanup_expired_conversations():
    """Limpia conversaciones expiradas"""
    await state_manager.cleanup_expired_conversations()

async def start_cleanup_task():
    """Inicia tarea de limpieza periódica"""
    async def cleanup_loop():
        while True:
            await asyncio.sleep(state_manager.cleanup_interval_minutes * 60)
            await cleanup_expired_conversations()
    
    asyncio.create_task(cleanup_loop())
    logger.info("Tarea de limpieza periódica iniciada")

if __name__ == "__main__":
    # Pruebas básicas del state manager
    async def test_state_manager():
        """Pruebas básicas del gestor de estado"""
        print("🚀 Iniciando pruebas del state manager...")
        
        user_id = "test_user_123"
        chat_id = "test_chat_456"
        
        # Crear conversación
        print("📝 Creando conversación...")
        conversation = await create_conversation(user_id, chat_id, "console")
        print(f"✅ Conversación creada: {conversation['user_id']}")
        
        # Actualizar estado
        print("🔄 Actualizando estado...")
        await update_conversation_state(
            user_id=user_id,
            chat_id=chat_id,
            last_message="Hola, ¿cómo estás?",
            last_response="¡Hola! ¿En qué puedo ayudarte?",
            classification={
                "intent": "greeting",
                "confidence": 0.95,
                "entities": []
            }
        )
        
        # Establecer datos del usuario
        print("👤 Estableciendo datos del usuario...")
        await set_user_data(user_id, "name", "Juan Pérez", chat_id)
        await set_user_data(user_id, "interest", "enfermería", chat_id)
        
        # Establecer contexto
        print("🎯 Estableciendo contexto...")
        await set_context(user_id, "current_topic", "career_info", chat_id)
        await set_flag(user_id, "interested_in_prices", True, chat_id)
        
        # Obtener estado actualizado
        print("📊 Obteniendo estado...")
        final_state = await get_conversation_state(user_id, chat_id)
        print(f"✅ Estado final: {final_state['message_count']} mensajes")
        
        # Obtener historial
        print("📚 Obteniendo historial...")
        history = await get_conversation_history(user_id, chat_id, limit=5)
        print(f"✅ Historial obtenido: {len(history)} intercambios")
        
        # Obtener estadísticas
        print("📈 Obteniendo estadísticas...")
        stats = await get_state_manager_stats()
        print(f"✅ Estadísticas: {stats['active_conversations']} conversaciones activas")
        
        # Obtener conversaciones activas
        active = await get_active_conversations()
        print(f"✅ Conversaciones activas: {len(active)}")
        
        print("🎉 Pruebas completadas exitosamente.")
    
    import asyncio
    asyncio.run(test_state_manager())