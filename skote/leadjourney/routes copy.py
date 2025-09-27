from flask import render_template, redirect, url_for, flash, jsonify, request
from . import leadjourney
from .models import LeadJourney, Nodo, NodoNextStep
from .forms import CreateJourneyForm
from skote import db
from skote import csrf


@leadjourney.route('/')
def list_journeys():
    journeys = LeadJourney.query.all()
    return render_template('leadjourney/leadjourney_list.html', journeys=journeys)

@leadjourney.route('/crear', methods=['GET', 'POST'])
@leadjourney.route('/editar/<int:journey_id>', methods=['GET', 'POST'])
def create_or_edit_journey(journey_id=None):
    journey = None
    if journey_id:
        journey = LeadJourney.query.get_or_404(journey_id)
        form = CreateJourneyForm(obj=journey)
    else:
        form = CreateJourneyForm()

    if form.validate_on_submit():
        if journey:
            form.populate_obj(journey)
            flash('Journey actualizado con éxito!', 'success')
        else:
            new_journey = LeadJourney(
                nombre=form.nombre.data,
                descripcion=form.descripcion.data,
                primer_nodo_id=None
            )
            db.session.add(new_journey)
            flash('Journey creado con éxito!', 'success')
            journey = new_journey

        db.session.commit()
        return redirect(url_for('leadjourney.view_journey', journey_id=journey.id))

    return render_template('leadjourney/create_journey.html', form=form, journey=journey)

@leadjourney.route('/<int:journey_id>')
def view_journey(journey_id):
    journey = LeadJourney.query.get_or_404(journey_id)
    return render_template('leadjourney/view_journey.html', journey=journey)

@leadjourney.route('/eliminar/<int:journey_id>', methods=['POST'])
def delete_journey(journey_id):
    journey = LeadJourney.query.get_or_404(journey_id)

    NodoNextStep.query.filter(NodoNextStep.nodo_origen_id.in_([n.id for n in journey.nodos])).delete(synchronize_session=False)
    Nodo.query.filter_by(id_journey=journey_id).delete(synchronize_session=False)

    db.session.delete(journey)
    db.session.commit()
    flash('Journey y todos sus nodos eliminados con éxito.', 'success')
    return redirect(url_for('leadjourney.list_journeys'))

@leadjourney.route('/api/create_node', methods=['POST'])
def create_node_api():
    data = request.get_json()

    journey_id = data.get('journey_id')
    nombre = data.get('nombre')
    prompt_agent = data.get('prompt_agent')
    next_steps = data.get('next_steps', [])

    if not all([journey_id, nombre, prompt_agent]):
        return jsonify({'status': 'error', 'message': 'Faltan datos requeridos'}), 400

    new_node = Nodo(
        id_journey=journey_id,
        nombre=nombre,
        prompt_agent=prompt_agent
    )
    db.session.add(new_node)
    db.session.commit()

    for step in next_steps:
        nombre_hijo = step.get('nombre')
        condicion = step.get('condicion')
        if not nombre_hijo:
            continue

        nodo_hijo = Nodo(
            id_journey=journey_id,
            nombre=nombre_hijo,
            prompt_agent=''  # vacío por ahora
        )
        db.session.add(nodo_hijo)
        db.session.flush()  # obtener el ID antes de commit

        next_step = NodoNextStep(
            nodo_origen_id=new_node.id,
            nodo_destino_id=nodo_hijo.id,
            etiqueta=condicion or ''
        )
        db.session.add(next_step)

    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Nodo y next steps creados', 'node_id': new_node.id}), 201

@leadjourney.route('/api/journey_data/<int:journey_id>')
def get_journey_data(journey_id):
    journey = LeadJourney.query.get_or_404(journey_id)
    nodos = Nodo.query.filter_by(id_journey=journey_id).all()

    nodes = []
    connections = []

    for nodo in nodos:
        nodes.append({
            "id": str(nodo.id),
            "name": nodo.nombre,
            "prompt": nodo.prompt_agent,
            "x": nodo.pos_x if nodo.pos_x is not None else 100,
            "y": nodo.pos_y if nodo.pos_y is not None else 100
        })

    for origen in nodos:
        next_steps = NodoNextStep.query.filter_by(nodo_origen_id=origen.id).all()
        for step in next_steps:
            connections.append({
                "source": str(origen.id),
                "target": str(step.nodo_destino_id),
                "sourceEndpoint": "bottom",
                "targetEndpoint": "top"
            })

    return jsonify({
        "nodes": nodes,
        "connections": connections
    })

@leadjourney.route('/api/get_node/<int:node_id>')
def get_node_details(node_id):
    nodo = Nodo.query.get_or_404(node_id)
    next_steps = NodoNextStep.query.filter_by(nodo_origen_id=node_id).all()

    steps = []
    for s in next_steps:
        destino = Nodo.query.get(s.nodo_destino_id)
        steps.append({
            "id": s.id,
            "nombre": destino.nombre if destino else 'Desconocido',
            "condicion": s.etiqueta or ''
        })

    return jsonify({
        "id": nodo.id,
        "nombre": nodo.nombre,
        "prompt_agent": nodo.prompt_agent,
        "next_steps": steps
    })

@leadjourney.route('/api/save_journey_data', methods=['POST'])
def save_journey_data():
    data = request.get_json()
    journey_id = data.get('journey_id')
    nodes_data = data.get('nodes', [])
    connections_data = data.get('connections', [])

    if not journey_id:
        return jsonify({'status': 'error', 'message': 'ID de journey no proporcionado'}), 400

    try:
        valid_node_ids = [int(n['id']) for n in nodes_data if 'id' in n]

        NodoNextStep.query.filter(NodoNextStep.nodo_origen_id.in_(
            Nodo.query.filter(Nodo.id_journey == journey_id, ~Nodo.id.in_(valid_node_ids)).with_entities(Nodo.id)
        )).delete(synchronize_session=False)

        Nodo.query.filter(Nodo.id_journey == journey_id, ~Nodo.id.in_(valid_node_ids)).delete(synchronize_session=False)

        for node in nodes_data:
            node_id = int(node.get('id'))
            nombre = node.get('name')
            prompt = node.get('prompt')

            n = Nodo.query.filter_by(id=node_id).first()
            if not n:
                n = Nodo(id=node_id, id_journey=journey_id)
                db.session.add(n)

            n.nombre = nombre
            n.prompt_agent = prompt

        NodoNextStep.query.filter(
            NodoNextStep.nodo_origen_id.in_(valid_node_ids)
        ).delete(synchronize_session=False)

        for conn in connections_data:
            source = int(conn.get('source'))
            target = int(conn.get('target'))
            etiqueta = conn.get('etiqueta', '')

            next_step = NodoNextStep(
                nodo_origen_id=source,
                nodo_destino_id=target,
                etiqueta=etiqueta
            )
            db.session.add(next_step)

        db.session.commit()

        if valid_node_ids:
            first_node_id = min(valid_node_ids)
            journey = LeadJourney.query.get(journey_id)
            if journey and journey.primer_nodo_id != first_node_id:
                journey.primer_nodo_id = first_node_id
                db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'Error al guardar: {str(e)}'}), 500

    return jsonify({'status': 'success', 'message': 'Datos del flowchart guardados correctamente.'})

@leadjourney.route('/api/save_positions', methods=['POST'])
@csrf.exempt
def save_node_position():
    data = request.get_json()
    node_id = data.get('node_id')
    x = data.get('x')
    y = data.get('y')

    if not all([node_id, x is not None, y is not None]):
        return jsonify({'status': 'error', 'message': 'Faltan datos'}), 400

    nodo = Nodo.query.filter_by(id=int(node_id)).first()
    if not nodo:
        return jsonify({'status': 'error', 'message': 'Nodo no encontrado'}), 404

    nodo.pos_x = int(x)
    nodo.pos_y = int(y)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Posición actualizada'})

@leadjourney.route('/api/update_node/<int:node_id>', methods=['POST'])
@csrf.exempt
def update_node(node_id):
    data = request.get_json()
    nombre = data.get('nombre')
    prompt_agent = data.get('prompt_agent')
    next_steps = data.get('next_steps', [])

    nodo = Nodo.query.get_or_404(node_id)
    nodo.nombre = nombre
    nodo.prompt_agent = prompt_agent
    db.session.commit()

    for step in next_steps:
        step_id = step.get('id')
        condicion = step.get('condicion', '')

        if step_id:  
            # Actualizar next_step existente
            ns = NodoNextStep.query.get(step_id)
            if ns:
                ns.etiqueta = condicion
        else:
            # Crear nuevo hijo si corresponde
            nombre_hijo = step.get('nombre')
            if not nombre_hijo:
                continue
            nodo_hijo = Nodo(id_journey=nodo.id_journey, nombre=nombre_hijo, prompt_agent='')
            db.session.add(nodo_hijo)
            db.session.flush()
            nuevo = NodoNextStep(
                nodo_origen_id=nodo.id,
                nodo_destino_id=nodo_hijo.id,
                etiqueta=condicion
            )
            db.session.add(nuevo)

    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Nodo y next steps actualizados'})


@leadjourney.route('/api/delete_node/<int:node_id>', methods=['DELETE'])
def delete_node(node_id):
    nodo = Nodo.query.get_or_404(node_id)
    NodoNextStep.query.filter(
        (NodoNextStep.nodo_origen_id == node_id) |
        (NodoNextStep.nodo_destino_id == node_id)
    ).delete(synchronize_session=False)
    db.session.delete(nodo)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Nodo eliminado correctamente'})

@leadjourney.route('/api/get_next_steps/<int:node_id>')
def get_next_steps(node_id):
    nodo = Nodo.query.get_or_404(node_id)
    next_steps = NodoNextStep.query.filter_by(nodo_origen_id=node_id).all()

    steps_data = []
    for step in next_steps:
        destino = Nodo.query.get(step.nodo_destino_id)
        steps_data.append({
            "id": step.id,
            "nombre": destino.nombre if destino else "",
            "condicion": step.etiqueta,
            "nodo_destino_id": step.nodo_destino_id
        })

    return jsonify(steps_data)

@leadjourney.route('/api/create_connection', methods=['POST'])
def create_connection():
    data = request.get_json()
    journey_id = data.get("journey_id")
    source_id = data.get("source_id")
    target_id = data.get("target_id")

    if not all([journey_id, source_id, target_id]):
        return jsonify({"status": "error", "message": "Datos incompletos"}), 400

    # Validar que ambos nodos existan y pertenezcan al mismo journey
    source_node = Nodo.query.filter_by(id=source_id, id_journey=journey_id).first()
    target_node = Nodo.query.filter_by(id=target_id, id_journey=journey_id).first()

    if not source_node or not target_node:
        return jsonify({"status": "error", "message": "Nodo(s) no válidos"}), 404

    # Verificar si ya existe la conexión
    exists = NodoNextStep.query.filter_by(
        nodo_origen_id=source_id,
        nodo_destino_id=target_id
    ).first()

    if exists:
        return jsonify({"status": "success", "message": "Conexión ya existe"})

    # Crear la conexión
    nueva = NodoNextStep(
        nodo_origen_id=source_id,
        nodo_destino_id=target_id,
        etiqueta=""
    )
    db.session.add(nueva)
    db.session.commit()

    return jsonify({"status": "success", "message": "Conexión guardada"})


@leadjourney.route('/api/delete_connection', methods=['DELETE'])
@csrf.exempt
def delete_connection():
    data = request.get_json()
    source_id = data.get("source_id")
    target_id = data.get("target_id")

    if not all([source_id, target_id]):
        return jsonify({"status": "error", "message": "Datos incompletos"}), 400

    deleted = NodoNextStep.query.filter_by(
        nodo_origen_id=source_id,
        nodo_destino_id=target_id
    ).delete()

    db.session.commit()

    if deleted:
        return jsonify({"status": "success", "message": "Conexión eliminada"})
    else:
        return jsonify({"status": "error", "message": "Conexión no encontrada"}), 404

@leadjourney.route('/api/step_overview/<int:node_id>', methods=['GET'])
def step_overview(node_id: int):
    """
    Endpoint que retorna:
    - Información del paso actual
    - Próximos pasos (condiciones o siguiente paso simple)
    - Historial de chat limpio (solo content + type)
    """

    # Parámetros GET
    session_id = request.args.get("session_id", type=str)
    history_limit = request.args.get("history_limit", default=10, type=int)

    # 1. Obtener el nodo actual
    current = Nodo.query.get_or_404(node_id)

    # 2. Traer relaciones de posibles próximos pasos
    pairs = (
        db.session.query(NodoNextStep, Nodo)
        .outerjoin(Nodo, Nodo.id == NodoNextStep.nodo_destino_id)
        .filter(NodoNextStep.nodo_origen_id == node_id)
        .all()
    )

    branching_conditions = []
    default_next_step = None

    for link, destino in pairs:
        destino_data = {
            "target_node_id": link.nodo_destino_id,
            "target_node_name": destino.nombre if destino else None,
            "target_node_prompt": destino.prompt_agent if destino else None
        }

        # Si tiene etiqueta => condición de ramificación
        if link.etiqueta and link.etiqueta.strip() != "":
            branching_conditions.append({
                "condition_description": link.etiqueta.strip(),
                **destino_data
            })
        else:
            # Si no hay etiqueta => flujo lineal
            default_next_step = destino_data

    # 3. Traer historial limpio de chat desde n8n_chat_histories
    chat_history = []
    if session_id:
        rows = (
            N8nChatHistories.query
            .filter_by(session_id=session_id)
            .order_by(N8nChatHistories.created_at.desc())
            .limit(history_limit)
            .all()
        )

        # Invertir para que el historial sea cronológico
        for row in reversed(rows):
            # Determinar si el mensaje es del humano o IA
            msg_type = row.message.get("type") if isinstance(row.message, dict) else "human"
            content = row.message.get("content") if isinstance(row.message, dict) else str(row.message)
            chat_history.append({
                "type": msg_type,
                "content": content
            })

    # 4. Construir la respuesta final
    response = {
        "journey_id": current.id_journey,
        "step_id": current.id,
        "step_name": current.nombre,
        "step_prompt": current.prompt_agent,
        "chat_history": chat_history
    }

    if branching_conditions:
        response["branching_conditions"] = branching_conditions
    elif default_next_step:
        response["default_next_step"] = default_next_step
    else:
        response["default_next_step"] = None

    return jsonify(response)

@leadjourney.route('/api/journey_overview/<int:journey_id>', methods=['GET'])
def journey_overview(journey_id: int):
    # 1. Obtener journey principal
    journey = LeadJourney.query.get_or_404(journey_id)

    # 2. Obtener todos los nodos asociados al journey
    nodos = Nodo.query.filter_by(id_journey=journey_id).all()

    nodos_data = []
    for nodo in nodos:
        # Traer next steps de cada nodo
        next_steps = NodoNextStep.query.filter_by(nodo_origen_id=nodo.id).all()
        steps_data = []

        for step in next_steps:
            destino = Nodo.query.get(step.nodo_destino_id)
            steps_data.append({
                "branch_condition": step.etiqueta,
                "branch_destiny_id": step.nodo_destino_id,
                "branch_destiny_name": destino.nombre if destino else None,
            })

        nodos_data.append({
            "id": nodo.id,
            "step_name": nodo.nombre,
            "agent_task": nodo.prompt_agent,
            "next_steps": steps_data
        })

    # 3. Construir respuesta final
    response = {
        "journey_id": journey.id,
        "journey_name": journey.nombre,
        "steps_journey": nodos_data
    }

    return jsonify(response)


@leadjourney.route('/api/journey_steps_summary/<int:journey_id>', methods=['GET'])
def journey_steps_summary(journey_id: int):
    """
    Devuelve solo los nombres de las etapas del journey en un string concatenado.
    Útil para usar como contexto en prompts de clasificación de intenciones.
    """

    # 1. Obtener journey
    journey = LeadJourney.query.get_or_404(journey_id)

    # 2. Obtener steps asociados
    nodos = Nodo.query.filter_by(id_journey=journey_id).all()

    # 3. Crear lista simple de nombres
    step_names = [nodo.nombre for nodo in nodos]

    # 4. Concatenar como texto para el LLM
    steps_text = ", ".join(step_names)

    response = {
        "journey_id": journey.id,
        "journey_name": journey.nombre,
        "steps_text": f"Etapas principales del journey: {steps_text}"
    }

    return jsonify(response)