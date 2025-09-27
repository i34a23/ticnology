# skote/ticnochatbot/routes_integration.py

from flask import jsonify, request
from flask_login import login_required
from . import chatbot
from skote import db
from skote.usuarios.models import Usuario, ChatHistory, Cliente
from skote.leadjourney.models import LeadJourney, Nodo, NodoNextStep
from .models import ConversationState, LeadQueue
from datetime import datetime
from sqlalchemy import desc

@chatbot.route("/api/users", methods=["GET"])

def get_users():
    """Obtiene lista de usuarios para la interfaz de chat"""
    cliente_id = request.args.get('cliente_id', type=int)
    search = request.args.get('search', '').strip()
    limit = request.args.get('limit', 50, type=int)
    
    query = Usuario.query
    
    # Filtrar por cliente si se especifica
    if cliente_id:
        query = query.filter_by(cliente_id=cliente_id)
    
    # Buscar por nombre, email o teléfono
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                Usuario.nombre.ilike(search_pattern),
                Usuario.email.ilike(search_pattern),
                Usuario.telefono.ilike(search_pattern)
            )
        )
    
    # Ordenar por más recientes
    users = query.order_by(desc(Usuario.created_at)).limit(limit).all()
    
    users_data = []
    for user in users:
        user_data = {
            "id": user.id,
            "nombre": user.nombre or "Sin nombre",
            "email": user.email or "Sin email",
            "telefono": user.telefono or "Sin teléfono",
            "estado": user.estado.value,
            "leadjourney_id": user.leadjourney_id,
            "journey_name": user.journey.nombre if user.journey else "Sin journey",
            "cliente_id": user.cliente_id,
            "cliente_name": user.cliente.nombre if user.cliente else "Sin cliente",
            "created_at": user.created_at.isoformat(),
            "user_data": user.user_data or {}
        }
        users_data.append(user_data)
    
    return jsonify({
        "users": users_data,
        "total": len(users_data)
    })

@chatbot.route("/api/clients", methods=["GET"])
  
def get_clients():
    """Obtiene lista de clientes"""
    clients = Cliente.query.order_by(Cliente.nombre).all()
    
    clients_data = []
    for client in clients:
        user_count = Usuario.query.filter_by(cliente_id=client.id).count()
        clients_data.append({
            "id": client.id,
            "nombre": client.nombre,
            "user_count": user_count,
            "created_at": client.created_at.isoformat()
        })
    
    return jsonify({"clients": clients_data})

@chatbot.route("/api/journeys", methods=["GET"])
def get_journeys():
    """Obtiene lista de lead journeys disponibles"""
    journeys = LeadJourney.query.order_by(LeadJourney.nombre).all()
    
    journeys_data = []
    for journey in journeys:
        nodos_count = Nodo.query.filter_by(id_journey=journey.id).count()
        users_count = Usuario.query.filter_by(leadjourney_id=journey.id).count()
        
        journeys_data.append({
            "id": journey.id,
            "nombre": journey.nombre,
            "descripcion": journey.descripcion or "",
            "nodos_count": nodos_count,
            "users_count": users_count,
            "created_at": journey.created_at.isoformat()
        })
    
    return jsonify({"journeys": journeys_data})

@chatbot.route("/api/user/<int:user_id>/journey-overview", methods=["GET"])

def get_user_journey_overview(user_id):
    """
    Obtiene overview completo del journey para un usuario específico
    Útil para el agente AI orquestador
    """
    user = Usuario.query.get_or_404(user_id)
    
    if not user.leadjourney_id:
        return jsonify({
            "error": "Usuario no tiene journey asignado",
            "user": {
                "id": user.id,
                "nombre": user.nombre,
                "estado": user.estado.value
            }
        }), 400
    
    journey = user.journey
    
    # Obtener todos los nodos del journey
    nodos = Nodo.query.filter_by(id_journey=journey.id).order_by(Nodo.id).all()
    
    # Obtener historial de chat del usuario
    chat_history = ChatHistory.query.filter_by(
        usuario_id=user_id
    ).order_by(desc(ChatHistory.created_at)).limit(20).all()
    
    # Obtener estado de conversación actual
    conv_state = ConversationState.query.filter_by(usuario_id=user_id).first()
    
    # Mapear nodos con información de progreso
    nodos_data = []
    for nodo in nodos:
        # Buscar si hay mensajes que coincidan con este nodo
        nodo_completado = False
        ultimo_mensaje_nodo = None
        
        # Verificar si hay chat history que sugiera que completó este nodo
        for chat in chat_history:
            if chat.role == 'usuario' and nodo.prompt_agent:
                # Lógica simple: si el usuario respondió después de que se envió este nodo
                # En una implementación más avanzada, aquí usarías el classifier
                if any(keyword in chat.message.lower() for keyword in ['sí', 'si', 'ok', 'vale', 'perfecto']):
                    nodo_completado = True
                    ultimo_mensaje_nodo = chat.created_at
                    break
        
        nodos_data.append({
            "id": nodo.id,
            "nombre": nodo.nombre,
            "prompt_agent": nodo.prompt_agent,
            "completion_condition": nodo.completion_condition,
            "orden": nodo.id,
            "completado": nodo_completado,
            "ultimo_mensaje": ultimo_mensaje_nodo.isoformat() if ultimo_mensaje_nodo else None
        })
    
    # Obtener siguiente paso sugerido
    current_step = None
    if conv_state and conv_state.current_step_id:
        current_step = Nodo.query.get(conv_state.current_step_id)
    
    # Calcular progreso general
    nodos_completados = sum(1 for nodo in nodos_data if nodo['completado'])
    progreso_porcentaje = (nodos_completados / len(nodos_data) * 100) if nodos_data else 0
    
    # Formatear historial de chat para el AI
    chat_formatted = []
    for chat in chat_history:
        chat_formatted.append({
            "role": chat.role,
            "message": chat.message,
            "tipo": chat.tipo,
            "timestamp": chat.created_at.isoformat()
        })
    
    return jsonify({
        "user": {
            "id": user.id,
            "nombre": user.nombre,
            "email": user.email,
            "telefono": user.telefono,
            "estado": user.estado.value,
            "user_data": user.user_data or {}
        },
        "journey": {
            "id": journey.id,
            "nombre": journey.nombre,
            "descripcion": journey.descripcion,
            "nodos_count": len(nodos_data),
            "progreso_porcentaje": progreso_porcentaje,
            "nodos_completados": nodos_completados
        },
        "nodos": nodos_data,
        "current_step": {
            "id": current_step.id if current_step else None,
            "nombre": current_step.nombre if current_step else None,
            "prompt_agent": current_step.prompt_agent if current_step else None
        },
        "conversation_state": {
            "current_intent": conv_state.current_intent if conv_state else None,
            "last_interaction": conv_state.last_interaction.isoformat() if conv_state and conv_state.last_interaction else None
        },
        "chat_history": chat_formatted,
        "summary": {
            "total_messages": len(chat_formatted),
            "user_messages": len([c for c in chat_formatted if c['role'] == 'usuario']),
            "agent_messages": len([c for c in chat_formatted if c['role'] == 'agente']),
            "journey_progress": f"{nodos_completados}/{len(nodos_data)} nodos completados",
            "last_activity": chat_history[0].created_at.isoformat() if chat_history else None
        }
    })

@chatbot.route("/api/user/<int:user_id>/assign-journey", methods=["POST"])

def assign_journey_to_user(user_id):
    """Asigna un journey a un usuario"""
    data = request.get_json()
    journey_id = data.get('journey_id')
    
    if not journey_id:
        return jsonify({"error": "journey_id requerido"}), 400
    
    user = Usuario.query.get_or_404(user_id)
    journey = LeadJourney.query.get_or_404(journey_id)
    
    # Asignar journey
    user.leadjourney_id = journey_id
    user.estado = user.estado  # Mantener estado actual
    
    # Crear o actualizar estado de conversación
    conv_state = ConversationState.query.filter_by(usuario_id=user_id).first()
    if not conv_state:
        # Obtener primer nodo del journey
        primer_nodo = Nodo.query.filter_by(
            journey_id=journey_id
        ).order_by(Nodo.orden).first()
        
        conv_state = ConversationState(
            usuario_id=user_id,
            journey_id=journey_id,
            current_step_id=primer_nodo.id if primer_nodo else None,
            current_intent='journey',
            last_interaction=datetime.utcnow()
        )
        db.session.add(conv_state)
    else:
        conv_state.journey_id = journey_id
        conv_state.last_interaction = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": f"Journey '{journey.nombre}' asignado a usuario '{user.nombre}'",
        "user_id": user_id,
        "journey_id": journey_id
    })

@chatbot.route("/api/user/<int:user_id>/chat-history", methods=["GET"])

def get_user_chat_history(user_id):
    """Obtiene historial completo de chat de un usuario"""
    limit = request.args.get('limit', 50, type=int)
    
    user = Usuario.query.get_or_404(user_id)
    
    chat_history = ChatHistory.query.filter_by(
        usuario_id=user_id
    ).order_by(desc(ChatHistory.created_at)).limit(limit).all()
    
    history_data = []
    for chat in chat_history:
        history_data.append({
            "id": chat.id,
            "role": chat.role,
            "message": chat.message,
            "tipo": chat.tipo,
            "timestamp": chat.created_at.isoformat()
        })
    
    return jsonify({
        "user": {
            "id": user.id,
            "nombre": user.nombre
        },
        "history": history_data,
        "total": len(history_data)
    })

