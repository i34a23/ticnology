from flask import render_template, redirect, url_for, flash, jsonify, request
from . import leadjourney
from .models import LeadJourney, Nodo, NodoNextStep
from .forms import CreateJourneyForm
from skote import db, csrf
from sqlalchemy import func


@leadjourney.route('/')
def list_journeys():
    journeys = (
        db.session.query(LeadJourney, func.count(Nodo.id).label("nodos_count"))
        .outerjoin(Nodo, LeadJourney.id == Nodo.id_journey)
        .group_by(LeadJourney.id)
        .all()
    )
    form = CreateJourneyForm()  # 👈 instancia vacía para el modal
    return render_template(
        "leadjourney/leadjourney_list.html",
        journeys=journeys,
        form=form
    )

# ============================
#   CREATE / UPDATE
# ============================

@leadjourney.route('/crear', methods=['GET', 'POST'])
@leadjourney.route('/editar/<int:journey_id>', methods=['GET', 'POST'])
def create_or_edit_journey(journey_id=None):
    """
    Crear un nuevo journey o editar uno existente.
    Al crear, se genera automáticamente un nodo inicial.
    """
    journey = None
    if journey_id:
        journey = LeadJourney.query.get_or_404(journey_id)
        form = CreateJourneyForm(obj=journey)
    else:
        form = CreateJourneyForm()

    if form.validate_on_submit():
        if journey:  # update
            form.populate_obj(journey)
            flash("Journey actualizado con éxito.", "success")
        else:  # create
            # 1. Crear Journey sin primer_nodo_id todavía
            journey = LeadJourney(
                nombre=form.nombre.data,
                descripcion=form.descripcion.data
            )
            db.session.add(journey)
            db.session.flush()  # necesitamos el ID del journey

            # 2. Crear nodo inicial
            nodo_inicial = Nodo(
                id_journey=journey.id,
                nombre="Inicio",
                prompt_agent="Este es el nodo inicial del Journey.",
                pos_x=100,
                pos_y=100
            )
            db.session.add(nodo_inicial)
            db.session.flush()

            # 3. Actualizar journey con primer_nodo_id
            journey.primer_nodo_id = nodo_inicial.id
            flash("Journey y nodo inicial creados con éxito.", "success")

        db.session.commit()
        return redirect(url_for("leadjourney.view_journey", journey_id=journey.id))

    return render_template("leadjourney/create_journey.html", form=form, journey=journey)

# ============================
#   READ
# ============================

@leadjourney.route('/<int:journey_id>')
def view_journey(journey_id):
    """
    Vista detalle de un Journey con sus nodos.
    """
    journey = LeadJourney.query.get_or_404(journey_id)
    return render_template("leadjourney/view_journey.html", journey=journey)


# ============================
#   DELETE
# ============================

@leadjourney.route('/eliminar/<int:journey_id>', methods=['POST'])
def delete_journey(journey_id):
    journey = LeadJourney.query.get_or_404(journey_id)

    # 1. Quitar referencia al primer nodo
    journey.primer_nodo_id = None
    db.session.flush()  # asegura update en DB antes de borrar nodos

    # 2. Eliminar steps (usamos subquery para mayor robustez)
    nodo_ids = [n.id for n in journey.nodos]
    if nodo_ids:
        NodoNextStep.query.filter(NodoNextStep.nodo_origen_id.in_(nodo_ids)).delete(synchronize_session=False)

    # 3. Expulsar nodos de la sesión antes de borrarlos
    for n in list(journey.nodos):
        db.session.expunge(n)

    # 4. Borrar nodos directamente con query
    Nodo.query.filter_by(id_journey=journey.id).delete(synchronize_session=False)

    # 5. Ahora sí borrar journey
    db.session.delete(journey)
    db.session.commit()

    flash("Journey y todos sus nodos eliminados con éxito.", "success")
    return redirect(url_for("leadjourney.list_journeys"))

# ============================
#   CREATE Nodo
# ============================
@leadjourney.route('/api/nodos', methods=['POST'])
def create_node():
    data = request.get_json()
    journey_id = data.get("journey_id")
    nombre = data.get("nombre")
    prompt_agent = data.get("prompt_agent")
    pos_x = data.get("pos_x", 100)
    pos_y = data.get("pos_y", 100)
    completion_condition = data.get("completion_condition")

    if not all([journey_id, nombre, prompt_agent]):
        return jsonify({"status": "error", "message": "Faltan datos requeridos"}), 400

    nodo = Nodo(
        id_journey=journey_id,
        nombre=nombre,
        prompt_agent=prompt_agent,
        pos_x=pos_x,
        pos_y=pos_y,
        completion_condition=completion_condition
    )
    db.session.add(nodo)
    db.session.flush()  # necesitamos el ID antes de guardar ramas

    # Crear next_steps si vienen en el payload
    next_steps = data.get("next_steps", [])
    for step in next_steps:
        branch = NodoNextStep(
            nodo_origen_id=nodo.id,
            etiqueta=step.get("etiqueta"),
            condicion_logica=step.get("condicion_logica"),
            orden=step.get("orden", 1),
            nodo_destino_id=step.get("nodo_destino_id")
        )
        db.session.add(branch)

    db.session.commit()

    return jsonify({"status": "success", "node_id": nodo.id}), 201


# ============================
#   READ Nodo
# ============================
@leadjourney.route('/api/nodos/<int:node_id>', methods=['GET'])
def get_node(node_id):
    nodo = Nodo.query.get_or_404(node_id)

    # 🔎 Debug en consola
    print(f"📌 Nodo {nodo.id} - {nodo.nombre}")
    print("👉 next_steps encontrados:")
    for step in nodo.next_steps:
        print({
            "id": step.id,
            "etiqueta": step.etiqueta,
            "condicion_logica": step.condicion_logica,
            "orden": step.orden,
            "destino_id": step.nodo_destino_id,
            "destino_nombre": step.destino.nombre if step.destino else None
        })

    next_steps = [
        {
            "id": step.id,
            "etiqueta": step.etiqueta,
            "condicion_logica": step.condicion_logica,
            "orden": step.orden,
            "destino_id": step.nodo_destino_id,
            "destino_nombre": step.destino.nombre if step.destino else None
        }
        for step in nodo.next_steps
    ]

    return jsonify({
        "id": nodo.id,
        "nombre": nodo.nombre,
        "prompt_agent": nodo.prompt_agent,
        "pos_x": nodo.pos_x,
        "pos_y": nodo.pos_y,
        "completion_condition": nodo.completion_condition,
        "next_steps": next_steps
    })


# ============================
#   UPDATE Nodo
# ============================
@leadjourney.route('/api/nodos/<int:node_id>', methods=['PUT'])
def update_node(node_id):
    data = request.get_json()
    nodo = Nodo.query.get_or_404(node_id)

    nodo.nombre = data.get("nombre", nodo.nombre)
    nodo.prompt_agent = data.get("prompt_agent", nodo.prompt_agent)
    nodo.pos_x = data.get("pos_x", nodo.pos_x)
    nodo.pos_y = data.get("pos_y", nodo.pos_y)
    nodo.completion_condition = data.get("completion_condition", nodo.completion_condition)

    # Actualizar next_steps si vienen en payload
    if "next_steps" in data:
        # Borramos los existentes y volvemos a crearlos
        NodoNextStep.query.filter_by(nodo_origen_id=node_id).delete(synchronize_session=False)
        for step in data["next_steps"]:
            branch = NodoNextStep(
                nodo_origen_id=node_id,
                etiqueta=step.get("etiqueta"),
                condicion_logica=step.get("condicion_logica"),
                orden=step.get("orden", 1),
                nodo_destino_id=step.get("nodo_destino_id")
            )
            db.session.add(branch)

    db.session.commit()
    return jsonify({"status": "success", "message": "Nodo actualizado"})


# ============================
#   DELETE Nodo
# ============================
@leadjourney.route('/api/nodos/<int:node_id>', methods=['DELETE'])
def delete_node(node_id):
    nodo = Nodo.query.get_or_404(node_id)

    # borrar conexiones relacionadas
    NodoNextStep.query.filter(
        (NodoNextStep.nodo_origen_id == node_id) |
        (NodoNextStep.nodo_destino_id == node_id)
    ).delete(synchronize_session=False)

    db.session.delete(nodo)
    db.session.commit()
    return jsonify({"status": "success", "message": "Nodo eliminado"})



# ============================
#   CREATE Branch
# ============================
@leadjourney.route('/api/nodos/<int:node_id>/branches', methods=['POST'])
def create_branch(node_id):
    data = request.get_json()
    etiqueta = data.get("etiqueta", "")
    destino_id = data.get("nodo_destino_id")
    condicion_logica = data.get("condicion_logica")
    orden = data.get("orden", 1)

    if not destino_id:
        return jsonify({"status": "error", "message": "Falta nodo_destino_id"}), 400

    branch = NodoNextStep(
        nodo_origen_id=node_id,
        nodo_destino_id=destino_id,
        etiqueta=etiqueta,
        condicion_logica=condicion_logica,
        orden=orden
    )
    db.session.add(branch)
    db.session.commit()

    return jsonify({"status": "success", "branch_id": branch.id}), 201


# ============================
#   READ Branch
# ============================
@leadjourney.route('/api/branches/<int:branch_id>', methods=['GET'])
def get_branch(branch_id):
    branch = NodoNextStep.query.get_or_404(branch_id)
    return jsonify({
        "id": branch.id,
        "etiqueta": branch.etiqueta,
        "condicion_logica": branch.condicion_logica,
        "orden": branch.orden,
        "origen_id": branch.nodo_origen_id,
        "destino_id": branch.nodo_destino_id
    })


# ============================
#   UPDATE Branch
# ============================
@leadjourney.route('/api/branches/<int:branch_id>', methods=['PUT'])
def update_branch(branch_id):
    data = request.get_json()
    branch = NodoNextStep.query.get_or_404(branch_id)

    branch.etiqueta = data.get("etiqueta", branch.etiqueta)
    branch.condicion_logica = data.get("condicion_logica", branch.condicion_logica)
    branch.orden = data.get("orden", branch.orden)
    branch.nodo_destino_id = data.get("nodo_destino_id", branch.nodo_destino_id)

    db.session.commit()
    return jsonify({"status": "success", "message": "Branch actualizado"})


# ============================
#   DELETE Branch
# ============================
@leadjourney.route('/api/branches/<int:branch_id>', methods=['DELETE'])
def delete_branch(branch_id):
    branch = NodoNextStep.query.get_or_404(branch_id)
    db.session.delete(branch)
    db.session.commit()
    return jsonify({"status": "success", "message": "Branch eliminado"})


@leadjourney.route('/api/save_positions', methods=['POST'])
@csrf.exempt
def save_positions():
    """
    Actualiza la posición (x,y) de un nodo en el canvas.
    """
    data = request.get_json()
    node_id = data.get("node_id")
    x = data.get("x")
    y = data.get("y")

    if not all([node_id, x is not None, y is not None]):
        return jsonify({"status": "error", "message": "Faltan datos"}), 400

    nodo = Nodo.query.get_or_404(int(node_id))
    nodo.pos_x = int(x)
    nodo.pos_y = int(y)
    db.session.commit()

    return jsonify({"status": "success", "message": "Posición actualizada"})


@leadjourney.route('/api/journey_data/<int:journey_id>')
def journey_data(journey_id):
    journey = LeadJourney.query.get_or_404(journey_id)
    nodos = Nodo.query.filter_by(id_journey=journey_id).all()

    nodes = [{
        "id": str(n.id),
        "name": n.nombre,
        "prompt": n.prompt_agent,
        "x": n.pos_x or 100,
        "y": n.pos_y or 100
    } for n in nodos]

    connections = [{
        "source": str(link.nodo_origen_id),
        "target": str(link.nodo_destino_id),
        "label": link.etiqueta or ""
    } for link in NodoNextStep.query.filter(NodoNextStep.nodo_origen_id.in_([n.id for n in nodos])).all()]

    return jsonify({"nodes": nodes, "connections": connections})



@leadjourney.route('/api/create_connection', methods=['POST'])
def create_connection():
    data = request.get_json() or {}
    try:
        journey_id = int(data.get("journey_id"))
        source_id  = int(data.get("source_id"))
        target_id  = int(data.get("target_id"))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Datos inválidos"}), 400

    # Validar nodos pertenecen al mismo Journey
    source_node = Nodo.query.filter_by(id=source_id, id_journey=journey_id).first()
    target_node = Nodo.query.filter_by(id=target_id, id_journey=journey_id).first()
    if not source_node or not target_node:
        return jsonify({"status": "error", "message": "Nodos no válidos"}), 404

    # Evitar duplicados (origen -> destino)
    exists = NodoNextStep.query.filter_by(
        nodo_origen_id=source_id,
        nodo_destino_id=target_id
    ).first()
    if exists:
        return jsonify({
            "status": "success",
            "message": "Conexión ya existe",
            "branch": {
                "id": exists.id,
                "etiqueta": exists.etiqueta or target_node.nombre,
                "origen_id": source_id,
                "destino_id": target_id,
                "destino_nombre": target_node.nombre
            }
        })

    # Asignar orden al final de las ramas existentes del nodo origen
    next_index = (NodoNextStep.query
                  .filter_by(nodo_origen_id=source_id)
                  .count()) + 1

    # Crear el branch con etiqueta = nombre del nodo destino (requisito)
    new_conn = NodoNextStep(
        nodo_origen_id=source_id,
        nodo_destino_id=target_id,
        etiqueta=target_node.nombre,
        orden=next_index
    )
    db.session.add(new_conn)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Conexión creada",
        "branch": {
            "id": new_conn.id,
            "etiqueta": new_conn.etiqueta,
            "origen_id": source_id,
            "destino_id": target_id,
            "destino_nombre": target_node.nombre,
            "orden": next_index
        }
    }), 201



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

