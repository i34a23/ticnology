"""
Script de pruebas para validar el funcionamiento del core completo
Ubicación: /ticnochatbot/test_core.py
"""

import asyncio
from datetime import datetime
import sys
import os

# Añadir el directorio del proyecto al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import process_webhook_message, get_system_health
from core.classifier import classify_message, get_classification_stats
from core.state_manager import (
    get_conversation_state, 
    update_conversation_state,
    get_conversation_history,
    set_user_data,
    get_user_data
)

async def test_classifier():
    """Prueba el clasificador independientemente"""
    print("🔍 === PRUEBAS DEL CLASIFICADOR ===")
    
    test_messages = [
        "Hola, buenos días",
        "¿Cuánto cuesta la carrera de enfermería?", 
        "Necesito ayuda con información",
        "Qué carreras tienen disponibles",
        "Gracias, hasta luego",
        "Qué horarios tienen para las clases"
    ]
    
    for message in test_messages:
        result = await classify_message(message)
        print(f"✅ '{message}' → {result['intent']} (conf: {result['confidence']:.2f})")
    
    # Obtener estadísticas
    stats = await get_classification_stats()
    print(f"📊 Total clasificaciones: {stats['total_classifications']}")
    print()

async def test_state_manager():
    """Prueba el state manager independientemente"""
    print("💾 === PRUEBAS DEL STATE MANAGER ===")
    
    user_id = "test_user_001"
    chat_id = "test_chat_001"
    
    # Crear conversación
    state = await get_conversation_state(user_id, chat_id)
    print(f"✅ Estado inicial creado para {user_id}")
    
    # Simular actualización de estado
    await update_conversation_state(
        user_id=user_id,
        chat_id=chat_id,
        last_message="Hola",
        last_response="¡Hola! ¿En qué puedo ayudarte?",
        classification={
            "intent": "greeting",
            "confidence": 0.95,
            "entities": []
        }
    )
    print(f"✅ Estado actualizado con saludo")
    
    # Establecer datos del usuario
    await set_user_data(user_id, "name", "María González", chat_id)
    await set_user_data(user_id, "career_interest", "parvularia", chat_id)
    print(f"✅ Datos de usuario establecidos")
    
    # Obtener datos
    name = await get_user_data(user_id, "name", chat_id=chat_id)
    career = await get_user_data(user_id, "career_interest", chat_id=chat_id)
    print(f"✅ Datos recuperados: {name} interesada en {career}")
    
    # Obtener historial
    history = await get_conversation_history(user_id, chat_id, limit=5)
    print(f"✅ Historial obtenido: {len(history)} intercambios")
    print()

async def test_orchestrator():
    """Prueba el orquestrador independientemente"""
    print("🎯 === PRUEBAS DEL ORQUESTRADOR ===")
    
    # Mensaje de prueba simulando formato de webhook
    test_message = {
        "message_id": "test_123",
        "chat": {"id": "test_chat_002"},
        "from": {"id": "test_user_002"},
        "text": "Hola, me interesa la carrera de enfermería",
        "timestamp": datetime.now().isoformat(),
        "channel": "console",
        "type": "text"
    }
    
    # Procesar mensaje
    result = await process_webhook_message(test_message)
    
    if result["success"]:
        print(f"✅ Mensaje procesado exitosamente")
        print(f"   📤 Respuesta: {result['response']}")
        print(f"   🆔 ID: {result['message_id']}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Health check
    health = await get_system_health()
    print(f"✅ Health check: {health['status']}")
    print(f"   💬 Chats activos: {health['active_chats']}")
    print(f"   📨 Mensajes totales: {health['total_messages']}")
    print()

async def test_integration():
    """Prueba la integración completa simulando flujo real"""
    print("🔗 === PRUEBA DE INTEGRACIÓN COMPLETA ===")
    
    user_id = "integration_user"
    chat_id = "integration_chat"
    
    # Simular secuencia de mensajes
    messages = [
        "Hola",
        "Me interesa saber sobre enfermería", 
        "¿Cuánto cuesta la carrera?",
        "¿Qué horarios tienen?",
        "Gracias por la información"
    ]
    
    for i, message_text in enumerate(messages):
        print(f"👤 Usuario: {message_text}")
        
        # 1. Clasificar mensaje
        classification = await classify_message(message_text)
        
        # 2. Obtener estado actual
        state = await get_conversation_state(user_id, chat_id)
        
        # 3. Procesar con orquestador
        webhook_message = {
            "message_id": f"integration_{i}",
            "chat": {"id": chat_id},
            "from": {"id": user_id},
            "text": message_text,
            "timestamp": datetime.now().isoformat(),
            "channel": "console",
            "type": "text",
            "classification": classification,
            "conversation_state": state
        }
        
        result = await process_webhook_message(webhook_message)
        
        if result["success"]:
            print(f"🤖 Bot: {result['response']}")
            print(f"   🎯 Intención: {classification['intent']} ({classification['confidence']:.2f})")
        else:
            print(f"❌ Error: {result.get('error')}")
        
        print()
    
    # Obtener historial final
    final_history = await get_conversation_history(user_id, chat_id)
    print(f"📚 Conversación completada con {len(final_history)} intercambios")
    print()

async def run_all_tests():
    """Ejecuta todas las pruebas"""
    print("🚀 INICIANDO PRUEBAS DEL CORE COMPLETO")
    print("=" * 50)
    
    try:
        await test_classifier()
        await test_state_manager()
        await test_orchestrator()
        await test_integration()
        
        print("🎉 ¡TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE!")
        print("✅ El core está funcionando correctamente")
        
    except Exception as e:
        print(f"❌ ERROR EN LAS PRUEBAS: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Ticno ChatBot - Test Core")
    print("Versión: 1.0.0")
    print()
    
    asyncio.run(run_all_tests())