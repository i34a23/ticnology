from flask import render_template, request, jsonify
from . import usuarios
from .models import Usuario, Cliente, EstadoUsuarioEnum
from skote.ticnochatbot.models import HitoJourney
from skote.leadjourney.models import LeadJourney
from .forms import UsuarioForm, ClienteForm
from skote import db
from sqlalchemy.exc import SQLAlchemyError
import json

# ----------------------------
# VISTA PRINCIPAL (HTML)
# ----------------------------

@usuarios.route('/', methods=['GET'])
@usuarios.route('/usuarios', methods=['GET'])
def vista_principal_usuarios():
    clientes = Cliente.query.all()
    form = ClienteForm()
    return render_template('usuarios/list_clientes.html', clientes=clientes, form=form)

# ----------------------------
# API: CLIENTES (AJAX)
# ----------------------------

@usuarios.route('/api/clientes', methods=['GET'])
def api_listar_clientes():
    clientes = Cliente.query.all()
    data = [{"id": c.id, "nombre": c.nombre} for c in clientes]
    return jsonify(data)

@usuarios.route('/api/clientes', methods=['POST'])
def api_crear_cliente():
    data = request.get_json()
    nombre = data.get("nombre", "").strip()

    if not nombre:
        return jsonify({"errors": {"nombre": ["El nombre es obligatorio."]}}), 400

    nuevo = Cliente(nombre=nombre)
    db.session.add(nuevo)
    db.session.commit()

    return jsonify({"id": nuevo.id, "nombre": nuevo.nombre}), 201

@usuarios.route('/api/clientes/<int:cliente_id>', methods=['PUT'])
def api_editar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    data = request.get_json()
    nombre = data.get("nombre", "").strip()

    if not nombre:
        return jsonify({"errors": {"nombre": ["El nombre es obligatorio."]}}), 400

    cliente.nombre = nombre
    db.session.commit()

    return jsonify({"id": cliente.id, "nombre": cliente.nombre})

@usuarios.route('/api/clientes/<int:cliente_id>', methods=['DELETE'])
def api_eliminar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    try:
        db.session.delete(cliente)
        db.session.commit()
        return jsonify({"success": True, "message": "Cliente eliminado"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500



# -------------------------------
# VISTA: listar usuarios del cliente
# -------------------------------
@usuarios.route('/clientes/<int:cliente_id>/usuarios', methods=['GET'])
def vista_usuarios_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    usuarios_list = Usuario.query.filter_by(cliente_id=cliente_id).all()
    form = UsuarioForm()
    return render_template("usuarios/list_usuarios.html", cliente=cliente, usuarios=usuarios_list, form=form)

# -------------------------------
# API: listar usuarios (JSON)
# -------------------------------
@usuarios.route('/api/clientes/<int:cliente_id>/usuarios', methods=['GET'])
def api_listar_usuarios(cliente_id):
    # Consulta con join manual para obtener el nombre del journey
    usuarios = Usuario.query.filter_by(cliente_id=cliente_id).all()
    
    result = []
    for usuario in usuarios:
        journey_nombre = None
        if usuario.leadjourney_id:
            journey = LeadJourney.query.get(usuario.leadjourney_id)
            journey_nombre = journey.nombre if journey else None
        
        usuario_data = {
            'id': usuario.id,
            'user_data': usuario.user_data or {},
            'estado': usuario.estado.value if hasattr(usuario.estado, 'value') else str(usuario.estado),
            'current_step_id': usuario.current_step_id,
            'current_step_nombre': usuario.current_step.nombre if usuario.current_step else None,
            'leadjourney_id': usuario.leadjourney_id,
            'leadjourney_nombre': journey_nombre
        }
        result.append(usuario_data)
    
    return jsonify(result)

# -------------------------------
# API: crear usuario
# -------------------------------
@usuarios.route('/api/clientes/<int:cliente_id>/usuarios', methods=['POST'])
def api_crear_usuario(cliente_id):
    data = request.get_json()

    # Verificación de los datos enviados
    if not data or 'user_data' not in data:
        return jsonify({"error": "Faltan datos de usuario"}), 400

    user_data = data.get("user_data", {})
    estado_raw = data.get("estado", "pendiente")
    step_id = data.get("step", None)
    leadjourney_id = data.get("leadjourney_id", None)

    # Validaciones mínimas: nombre y apellido
    if not user_data.get("nombre") or not user_data.get("apellido"):
        return jsonify({"error": "Nombre y apellido son obligatorios"}), 400

    try:
        # Crear nuevo usuario con los datos proporcionados
        nuevo_usuario = Usuario(
            cliente_id=cliente_id,
            nombre=user_data.get("nombre"),
            email=user_data.get("email"),
            telefono=user_data.get("telefono"),
            user_data=user_data,
            estado=EstadoUsuarioEnum[estado_raw] if estado_raw in EstadoUsuarioEnum.__members__ else EstadoUsuarioEnum.pendiente,
            current_step_id=int(step_id) if step_id else None,
            leadjourney_id = leadjourney_id
        )

        # Guardar el nuevo usuario en la base de datos
        db.session.add(nuevo_usuario)
        db.session.commit()

        # Retornar respuesta con ID del usuario creado
        return jsonify({"id": nuevo_usuario.id}), 201

    except Exception as e:
        # En caso de error, realizar rollback y enviar el detalle del error
        db.session.rollback()
        return jsonify({"error": "Error interno del servidor", "detalles": str(e)}), 500



# -------------------------------
# API: editar usuario
# -------------------------------
@usuarios.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
def api_editar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    data = request.get_json()

    # Check if the user data exists in the payload
    if not data or 'user_data' not in data:
        return jsonify({"error": "Datos incompletos"}), 400

    user_data = data.get("user_data", {})
    estado_raw = data.get("estado", "pendiente")
    step_id = data.get("step", None)
    leadjourney_id = data.get("leadjourney_id", None)

    # Validate required fields
    if not user_data.get("nombre") or not user_data.get("apellido"):
        return jsonify({"error": "Nombre y apellido son obligatorios"}), 400

    try:
        # Update user information
        usuario.nombre = user_data.get("nombre")
        usuario.email = user_data.get("email")
        usuario.telefono = user_data.get("telefono")
        usuario.user_data = user_data

        # Set the state based on the provided enum, defaulting to "pendiente"
        estado_enum = EstadoUsuarioEnum[estado_raw] if estado_raw in EstadoUsuarioEnum.__members__ else EstadoUsuarioEnum.pendiente
        usuario.estado = estado_enum

        # Set current step and journey id if provided
        usuario.current_step_id = int(step_id) if step_id else None
        usuario.leadjourney_id = leadjourney_id

        # Commit changes to the database
        db.session.commit()
        return jsonify({"id": usuario.id}), 200

    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        return jsonify({"error": "Error interno del servidor", "detalles": str(e)}), 500



# -------------------------------
# API: eliminar usuario
# -------------------------------
@usuarios.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
def api_eliminar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    try:
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({"success": True}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    

@usuarios.route('/api/journeys')
def api_listar_journeys():
    journeys = LeadJourney.query.with_entities(LeadJourney.id, LeadJourney.nombre).all()
    return jsonify([{'id': j.id, 'nombre': j.nombre} for j in journeys])


@usuarios.route('/clientes/<int:cliente_id>/usuarios/<int:usuario_id>', methods=['GET'])
def vista_usuario(cliente_id, usuario_id):
    usuario = Usuario.query.filter_by(id=usuario_id, cliente_id=cliente_id).first_or_404()
    hitos = HitoJourney.query.filter_by(usuario_id=usuario.id).order_by(HitoJourney.timestamp.asc()).all()
    chat_histories = N8nChatHistories.query.filter_by(session_id=str(usuario.id)).order_by(N8nChatHistories.created_at.asc()).all()
    
    # Procesar los mensajes del chat
    chat_messages_processed = []
    for chat in chat_histories:
        # Si chat.message ya es un diccionario, usarlo directamente
        if isinstance(chat.message, dict):
            message_data = chat.message
        else:
            # Si es string, intentar parsearlo como JSON
            try:
                message_data = json.loads(chat.message)
            except (json.JSONDecodeError, TypeError):
                # Si hay error al parsear, crear un mensaje básico
                message_data = {'type': 'unknown', 'content': str(chat.message)}
        
        chat_messages_processed.append({
            'id': chat.id,
            'message_data': message_data,
            'created_at': chat.created_at,
            'status': chat.status
        })
    
    return render_template(
        "usuarios/usuario.html",
        usuario=usuario,
        user_data=usuario.user_data,  # Pasamos el user_data completo
        hitos=hitos,
        chat_histories=chat_messages_processed
    )