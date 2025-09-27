"""
Inicializador del módulo Core del ChatBot
Exporta las funciones principales de cada componente
Ubicación: /ticnochatbot/core/__init__.py
"""

# Importar funciones principales del orquestador
from .orchestrator import (
    process_webhook_message,
    get_system_health,
    get_active_chats,
    get_chat_info,
    get_recent_messages,
    register_journey_engine,
    register_faq_engine,
    register_proactive_engine
)

# Importar funciones principales del clasificador
from .classifier import (
    classify_message,
    get_classification_stats,
    configure_llm_classifier,
    get_available_intents,
    get_intent_keywords,
    test_classification_accuracy
)

# Importar funciones principales del state manager
from .state_manager import (
    get_conversation_state,
    update_conversation_state,
    create_conversation,
    get_conversation_history,
    get_state_manager_stats,
    get_active_conversations,
    set_user_data,
    get_user_data,
    set_context,
    get_context,
    set_flag,
    get_flag,
    cleanup_expired_conversations,
    start_cleanup_task
)

# Versión del core
__version__ = "1.0.0"

# Funciones disponibles
__all__ = [
    # Orquestador
    "process_webhook_message",
    "get_system_health", 
    "get_active_chats",
    "get_chat_info",
    "get_recent_messages",
    "register_journey_engine",
    "register_faq_engine", 
    "register_proactive_engine",
    
    # Clasificador
    "classify_message",
    "get_classification_stats",
    "configure_llm_classifier",
    "get_available_intents",
    "get_intent_keywords",
    "test_classification_accuracy",
    
    # State Manager
    "get_conversation_state",
    "update_conversation_state",
    "create_conversation", 
    "get_conversation_history",
    "get_state_manager_stats",
    "get_active_conversations",
    "set_user_data",
    "get_user_data",
    "set_context",
    "get_context",
    "set_flag",
    "get_flag",
    "cleanup_expired_conversations",
    "start_cleanup_task"
]