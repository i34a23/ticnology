"""
API Routes Centralizada - Coordina Orchestrator, Classifier y State Manager
Separada del CRM administrativo (routes.py)
Ubicación: /ticnochatbot/api_routes.py
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime
import os
from abc import ABC, abstractmethod

# Importar componentes del core implementados
from core.orchestrator import process_webhook_message, get_system_health, get_active_chats
from core.classifier import classify_message, get_classification_stats
from core.state_manager import (
    get_conversation_state, 
    update_conversation_state, 
    create_conversation,
    get_conversation_history,
    get_state_manager_stats,
    get_active_conversations as get_state_active_conversations
)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear instancia de FastAPI separada del Flask CRM
app = FastAPI(
    title="Ticno ChatBot - Multi Channel API",
    description="API centralizada que coordina orchestrator, classifier y state_manager",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== ABSTRACCIÓN DE CANALES =====

class ChannelAdapter(ABC):
    """Adaptador abstracto para diferentes canales"""
    
    @abstractmethod
    async def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte mensaje del canal al formato estándar"""
        pass
    
    @abstractmethod
    async def send_message(self, chat_id: str, message: str, **kwargs) -> Dict[str, Any]:
        """Envía mensaje através del canal"""
        pass
    
    @abstractmethod
    def verify_webhook(self, request: Request) -> bool:
        """Verifica la autenticidad del webhook"""
        pass
    
    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Nombre del canal"""
        pass

class ConsoleAdapter(ChannelAdapter):
    """Adaptador para pruebas desde consola/API - ideal para desarrollo"""
    
    def __init__(self):
        self.console_messages = []
    
    async def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte mensaje de consola al formato estándar"""
        return {
            "message_id": raw_data.get("id", f"console_{datetime.now().timestamp()}"),
            "chat": {"id": raw_data.get("chat_id", "console_chat")},
            "from": {"id": raw_data.get("user_id", "console_user")},
            "text": raw_data.get("message", ""),
            "timestamp": datetime.now().isoformat(),
            "type": "text",
            "channel": "console"
        }
    
    async def send_message(self, chat_id: str, message: str, **kwargs) -> Dict[str, Any]:
        """Simula envío de mensaje para desarrollo"""
        response = {
            "success": True,
            "message_id": f"console_out_{datetime.now().timestamp()}",
            "chat_id": chat_id,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "channel": "console"
        }
        
        self.console_messages.append(response)
        logger.info(f"📤 CONSOLE [{chat_id}]: {message}")
        return response
    
    def verify_webhook(self, request: Request) -> bool:
        return True
    
    @property
    def channel_name(self) -> str:
        return "console"

class WhatsAppAdapter(ChannelAdapter):
    """Adaptador para WhatsApp Business API"""
    
    def __init__(self):
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
        self.version = os.getenv("WHATSAPP_API_VERSION", "v21.0")
    
    async def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte webhook de WhatsApp al formato estándar"""
        try:
            entry = raw_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                return None
            
            message = messages[0]
            msg_type = message.get("type", "text")
            
            adapted = {
                "message_id": message.get("id"),
                "chat": {"id": message.get("from")},
                "from": {"id": message.get("from")},
                "timestamp": message.get("timestamp"),
                "type": msg_type,
                "channel": "whatsapp"
            }
            
            if msg_type == "text":
                adapted["text"] = message.get("text", {}).get("body", "")
            elif msg_type == "image":
                adapted["photo"] = message.get("image", {})
                adapted["caption"] = message.get("image", {}).get("caption", "")
            # Añadir más tipos según necesidad
            
            return adapted
            
        except Exception as e:
            logger.error(f"❌ Error parseando WhatsApp: {str(e)}")
            return None
    
    async def send_message(self, chat_id: str, message: str, **kwargs) -> Dict[str, Any]:
        """Envía mensaje via WhatsApp API"""
        import httpx
        
        if not self.access_token or not self.phone_number_id:
            return {"error": "WhatsApp not configured"}
        
        url = f"https://graph.facebook.com/{self.version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": chat_id,
            "type": "text",
            "text": {"body": message}
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def verify_webhook(self, request: Request) -> bool:
        if request.method == "GET":
            mode = request.query_params.get("hub.mode")
            token = request.query_params.get("hub.verify_token")
            return mode == "subscribe" and token == self.verify_token
        return True
    
    @property
    def channel_name(self) -> str:
        return "whatsapp"

class TelegramAdapter(ChannelAdapter):
    """Adaptador para Telegram Bot API"""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    
    async def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte update de Telegram al formato estándar"""
        message = raw_data.get("message")
        if not message:
            return None
        
        return {
            "message_id": str(message.get("message_id")),
            "chat": {"id": str(message.get("chat", {}).get("id"))},
            "from": {"id": str(message.get("from", {}).get("id"))},
            "text": message.get("text", ""),
            "timestamp": datetime.now().isoformat(),
            "type": "text",
            "channel": "telegram"
        }
    
    async def send_message(self, chat_id: str, message: str, **kwargs) -> Dict[str, Any]:
        """Envía mensaje via Telegram API"""
        import httpx
        
        if not self.bot_token:
            return {"error": "Telegram not configured"}
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def verify_webhook(self, request: Request) -> bool:
        return True
    
    @property
    def channel_name(self) -> str:
        return "telegram"

# ===== GESTOR DE CANALES =====

class ChannelManager:
    """Gestor central de todos los adaptadores de canal"""
    
    def __init__(self):
        self.adapters = {
            "console": ConsoleAdapter(),
            "whatsapp": WhatsAppAdapter(),
            "telegram": TelegramAdapter()
        }
        self.default_channel = "console"
    
    def get_adapter(self, channel: str) -> ChannelAdapter:
        return self.adapters.get(channel, self.adapters[self.default_channel])
    
    def list_channels(self) -> List[str]:
        return list(self.adapters.keys())
    
    def is_channel_configured(self, channel: str) -> bool:
        if channel == "console":
            return True
        elif channel == "whatsapp":
            adapter = self.adapters[channel]
            return bool(adapter.access_token and adapter.phone_number_id)
        elif channel == "telegram":
            adapter = self.adapters[channel]
            return bool(adapter.bot_token)
        return False

# Instancia global
channel_manager = ChannelManager()

# ===== MODELOS PYDANTIC =====

class UniversalMessage(BaseModel):
    """Modelo universal para mensajes de cualquier canal"""
    message: str = Field(..., description="Contenido del mensaje")
    chat_id: str = Field(default="console_chat", description="ID del chat")
    user_id: str = Field(default="console_user", description="ID del usuario")
    channel: str = Field(default="console", description="Canal de origen")

class SendMessageRequest(BaseModel):
    """Modelo para envío de mensajes"""
    channel: str = Field(..., description="Canal a usar")
    chat_id: str = Field(..., description="ID del destinatario")
    message: str = Field(..., description="Mensaje a enviar")

class ClassificationRequest(BaseModel):
    """Modelo para testing del classifier"""
    message: str = Field(..., description="Mensaje a clasificar")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")

class StateRequest(BaseModel):
    """Modelo para gestión de estado"""
    user_id: str = Field(..., description="ID del usuario")
    chat_id: str = Field(..., description="ID del chat")

class HealthResponse(BaseModel):
    """Respuesta del health check completo"""
    status: str
    timestamp: str
    orchestrator: Dict[str, Any]
    classifier: Dict[str, Any]
    state_manager: Dict[str, Any]
    channels: Dict[str, Any]

# ===== MIDDLEWARE =====

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    logger.info(f"📨 {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"📤 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response

# ===== RUTAS PRINCIPALES =====

@app.get("/")
async def root():
    """Endpoint raíz con información del sistema completo"""
    return {
        "message": "Ticno ChatBot - Multi Channel API",
        "version": "1.0.0",
        "status": "running",
        "components": ["orchestrator", "classifier", "state_manager"],
        "available_channels": channel_manager.list_channels(),
        "configured_channels": [
            ch for ch in channel_manager.list_channels() 
            if channel_manager.is_channel_configured(ch)
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health", response_model=HealthResponse)
async def comprehensive_health_check():
    """Health check completo de todos los componentes del core"""
    try:
        # Health check del orquestador
        orchestrator_health = await get_system_health()
        
        # Stats del clasificador
        classifier_stats = await get_classification_stats()
        
        # Estado del state manager
        state_manager_status = await get_state_manager_stats()
        
        # Estado de canales
        channels_status = {
            "available": channel_manager.list_channels(),
            "configured": [
                ch for ch in channel_manager.list_channels() 
                if channel_manager.is_channel_configured(ch)
            ]
        }
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            orchestrator=orchestrator_health,
            classifier=classifier_stats,
            state_manager=state_manager_status,
            channels=channels_status
        )
    except Exception as e:
        logger.error(f"❌ Error en health check: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/api/message")
async def process_universal_message(message: UniversalMessage):
    """
    Endpoint principal que coordina todo el flujo:
    Mensaje → Classifier → Orchestrator → State Manager → Respuesta
    """
    try:
        logger.info(f"🔄 Procesando mensaje desde {message.channel}")
        
        # 1. Obtener adaptador del canal
        adapter = channel_manager.get_adapter(message.channel)
        
        # 2. Convertir a formato estándar
        standard_message = await adapter.parse_incoming_message({
            "message": message.message,
            "chat_id": message.chat_id,
            "user_id": message.user_id,
            "id": f"{message.channel}_{datetime.now().timestamp()}"
        })
        
        # 3. Obtener/crear estado de conversación
        conversation_state = await get_conversation_state(message.user_id, message.chat_id)
        
        # 4. Clasificar mensaje (usando contexto de la conversación)
        classification = await classify_message(
            message.message, 
            context=conversation_state
        )
        
        # 5. Procesar con el orquestador (incluyendo clasificación)
        enriched_message = {
            **standard_message,
            "classification": classification,
            "conversation_state": conversation_state
        }
        
        result = await process_webhook_message(enriched_message)
        
        if result["success"]:
            # 6. Actualizar estado de conversación
            await update_conversation_state(
                user_id=message.user_id,
                chat_id=message.chat_id,
                last_message=message.message,
                last_response=result["response"],
                classification=classification
            )
            
            # 7. Enviar respuesta através del canal
            response_sent = await adapter.send_message(
                message.chat_id,
                result["response"]
            )
            
            return {
                "success": True,
                "channel": message.channel,
                "message_id": result["message_id"],
                "classification": classification,
                "response": result["response"],
                "sent_via_channel": not response_sent.get("error"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error en orquestador: {result.get('error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en mensaje universal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ENDPOINTS ESPECÍFICOS DE CADA COMPONENTE =====

@app.post("/api/classify")
async def test_classifier(request: ClassificationRequest):
    """Endpoint para testing del classifier independientemente"""
    try:
        classification = await classify_message(request.message, context=request.context)
        return {
            "message": request.message,
            "classification": classification,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error en clasificación: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/classifier/stats")
async def get_classifier_statistics():
    """Estadísticas del clasificador"""
    try:
        stats = await get_classification_stats()
        return stats
    except Exception as e:
        logger.error(f"❌ Error obteniendo stats del classifier: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{user_id}")
async def get_user_conversation_state(user_id: str):
    """Obtiene el estado de conversación de un usuario"""
    try:
        state = await get_conversation_state(user_id)
        return {
            "user_id": user_id,
            "state": state,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{user_id}/history")
async def get_user_conversation_history(user_id: str, limit: int = 10):
    """Obtiene el historial de conversación de un usuario"""
    try:
        history = await get_conversation_history(user_id, limit=limit)
        return {
            "user_id": user_id,
            "history": history,
            "count": len(history),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo historial: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversations/create")
async def create_new_conversation(request: StateRequest):
    """Crea una nueva conversación"""
    try:
        conversation = await create_conversation(request.user_id, request.chat_id)
        return {
            "user_id": request.user_id,
            "chat_id": request.chat_id,
            "conversation": conversation,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error creando conversación: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== WEBHOOKS MULTI-CANAL =====

@app.get("/api/webhook/{channel}")
@app.post("/api/webhook/{channel}")
async def universal_webhook_handler(channel: str, request: Request):
    """
    Webhook universal que maneja todos los canales
    Flujo: Webhook → Parse → Classify → Orchestrator → State → Response
    """
    try:
        adapter = channel_manager.get_adapter(channel)
        
        # Verificación del webhook
        if not adapter.verify_webhook(request):
            raise HTTPException(status_code=403, detail="Webhook verification failed")
        
        # Para GET (verificaciones)
        if request.method == "GET":
            if channel == "whatsapp":
                challenge = request.query_params.get("hub.challenge")
                return int(challenge) if challenge else {"status": "verified"}
            return {"status": "verified"}
        
        # Para POST (mensajes)
        webhook_data = await request.json()
        logger.info(f"🔄 Webhook {channel}: {webhook_data.get('object', 'message')}")
        
        # Parsear mensaje
        message_data = await adapter.parse_incoming_message(webhook_data)
        
        if not message_data:
            return JSONResponse(content={"status": "no_message"}, status_code=200)
        
        # Obtener estado de conversación
        user_id = message_data["from"]["id"]
        chat_id = message_data["chat"]["id"]
        conversation_state = await get_conversation_state(user_id, chat_id)
        
        # Clasificar mensaje
        classification = await classify_message(
            message_data.get("text", ""),
            context=conversation_state
        )
        
        # Enriquecer mensaje con contexto
        enriched_message = {
            **message_data,
            "classification": classification,
            "conversation_state": conversation_state
        }
        
        # Procesar con orquestador
        result = await process_webhook_message(enriched_message)
        
        if result["success"]:
            # Actualizar estado
            await update_conversation_state(
                user_id=user_id,
                chat_id=chat_id,
                last_message=message_data.get("text", ""),
                last_response=result["response"],
                classification=classification
            )
            
            # Enviar respuesta
            await adapter.send_message(chat_id, result["response"])
            
            return {"status": "processed", "message_id": result["message_id"]}
        else:
            return {"status": "error", "error": result.get("error")}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en webhook {channel}: {str(e)}")
        return JSONResponse(content={"status": "error"}, status_code=500)

# ===== ENDPOINTS DE DESARROLLO =====

@app.post("/api/console/quick-test")
async def quick_console_test(message: str = "Hola, ¿cómo estás?"):
    """Prueba rápida del flujo completo desde consola"""
    test_message = UniversalMessage(
        message=message,
        chat_id="test_chat",
        user_id="test_user",
        channel="console"
    )
    
    return await process_universal_message(test_message)

@app.get("/api/console/messages")
async def get_console_messages():
    """Obtiene mensajes de consola para debugging"""
    adapter = channel_manager.get_adapter("console")
    return {
        "messages": adapter.console_messages[-10:],
        "total": len(adapter.console_messages),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/channels/status")
async def get_channels_status():
    """Estado detallado de todos los canales"""
    channels_status = {}
    
    for channel in channel_manager.list_channels():
        adapter = channel_manager.get_adapter(channel)
        channels_status[channel] = {
            "name": adapter.channel_name,
            "configured": channel_manager.is_channel_configured(channel),
            "adapter_type": type(adapter).__name__
        }
    
    return {
        "channels": channels_status,
        "default_channel": channel_manager.default_channel,
        "timestamp": datetime.now().isoformat()
    }

# ===== MANEJO DE ERRORES =====

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint no encontrado",
            "path": request.url.path,
            "available_endpoints": [
                "/api/health", "/api/message", "/api/webhook/{channel}",
                "/api/classify", "/api/conversations/{user_id}", "/api/channels/status"
            ],
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Iniciando Ticno ChatBot API...")
    print(f"📍 Servidor: http://localhost:8000")
    print(f"📖 API Docs: http://localhost:8000/api/docs")
    print(f"🧪 Prueba rápida: POST /api/console/quick-test")
    print(f"💬 Mensaje: POST /api/message")
    print(f"🔍 Clasificar: POST /api/classify")
    print(f"📱 Canales: {channel_manager.list_channels()}")
    
    uvicorn.run(
        "api_routes:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )