from flask import jsonify, request
from . import chatbot
from skote import db
from skote.usuarios.models import Usuario, ChatHistory, Cliente
from skote.leadjourney.models import LeadJourney, Nodo
from .models import ConversationState
from datetime import datetime
from sqlalchemy import desc, or_

@chatbot.route("/api/users", methods=["GET"])
def get_users():
    """Obtiene lista de usuarios para la interfaz de chat"""
    try:
        cliente_id = request.args.get('cliente_id', type=int)
        search = request.args.get('search', '').strip()
        limit = request.args.get('limit', 50, type=int)
        
        query = Usuario.query
        
        if cliente_id:
            query = query.filter_by(cliente_id=cliente_id)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Usuario.nombre.ilike(search_pattern),
                    Usuario.email.ilike(search_pattern),
                    Usuario.telefono.ilike(search_pattern)
                )
            )
        
        users = query.order_by(desc(Usuario.created_at)).limit(limit).all()
        
        users_data = []
        for user in users:
            users_data.append({
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
            })
        
        return jsonify({
            "users": users_data,
            "total": len(users_data)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chatbot.route("/api/clients", methods=["GET"])
def get_clients():
    """Obtiene lista de clientes"""
    try:
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chatbot.route("/api/journeys", methods=["GET"])
def get_journeys():
    """Obtiene lista de journeys"""
    try:
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chatbot.route("/api/user/<int:user_id>/journey-overview", methods=["GET"])
def get_user_journey_overview(user_id):
    """Obtiene overview del journey para un usuario"""
    try:
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
        nodos = Nodo.query.filter_by(id_journey=journey.id).order_by(Nodo.nombre).all()
        
        # Obtener historial de chat
        chat_history = ChatHistory.query.filter_by(
            usuario_id=user_id
        ).order_by(desc(ChatHistory.created_at)).limit(10).all()
        
        # Mapear nodos (lógica simple de completado)
        nodos_data = []
        for nodo in nodos:
            # Lógica básica: si el usuario actual está en este step, marcarlo como current
            is_current = (user.current_step_id == nodo.id) if user.current_step_id else False
            is_completed = False
            
            # Si hay mensajes después de este nodo, considerarlo completado
            if chat_history:
                is_completed = len([msg for msg in chat_history if 'sí' in msg.message.lower() or 'ok' in msg.message.lower()]) > 0
            
            nodos_data.append({
                "id": nodo.id,
                "nombre": nodo.nombre,
                "prompt_agent": nodo.prompt_agent,
                "completion_condition": nodo.completion_condition,
                "completado": is_completed,
                "is_current": is_current
            })
        
        # Calcular progreso
        completados = sum(1 for n in nodos_data if n['completado'])
        progreso = (completados / len(nodos_data) * 100) if nodos_data else 0
        
        return jsonify({
            "user": {
                "id": user.id,
                "nombre": user.nombre,
                "email": user.email,
                "estado": user.estado.value
            },
            "journey": {
                "id": journey.id,
                "nombre": journey.nombre,
                "descripcion": journey.descripcion,
                "progreso_porcentaje": progreso,
                "nodos_completados": completados
            },
            "nodos": nodos_data,
            "current_step": {
                "id": user.current_step_id,
                "nombre": user.current_step.nombre if user.current_step else None
            } if user.current_step_id else None,
            "chat_history": [
                {
                    "role": msg.role,
                    "message": msg.message,
                    "timestamp": msg.created_at.isoformat()
                } for msg in chat_history
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500