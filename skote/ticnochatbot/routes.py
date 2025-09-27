# skote/ticnochatbot/routes.py

from flask import request, jsonify, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from . import chatbot
from skote import db
from .models import (
    ConversationState, 
    LeadQueue, 
    AgentMetrics,
    MessageTemplate,
    AgentCredentials,
    Agent   # <- tu nuevo modelo de agentes IA
)
from skote.usuarios.models import Usuario, Cliente
from skote.leadjourney.models import LeadJourney
from .config import credentials_manager, get_llm, settings
import json
from datetime import datetime

# ============================================
# VISTAS ADMINISTRATIVAS (Integradas al CRM)
# ============================================

@chatbot.route("/admin", methods=["GET"])
@login_required
def admin_dashboard():
    """Dashboard principal del chatbot integrado al CRM"""
    stats = {
        'total_conversations': ConversationState.query.count(),
        'active_conversations': ConversationState.query.filter(
            ConversationState.last_interaction > datetime.now().replace(hour=0, minute=0)
        ).count(),
        'queued_leads': LeadQueue.query.filter_by(status='pending').count(),
        'providers': credentials_manager.list_providers()
    }

    recent_conversations = db.session.query(
        ConversationState, Usuario
    ).join(Usuario).order_by(ConversationState.last_update.desc()).limit(10).all()

    lead_queue = db.session.query(
        LeadQueue, Usuario
    ).join(Usuario).filter(
        LeadQueue.status == 'pending'
    ).order_by(LeadQueue.priority.desc()).limit(10).all()

    return render_template(
        "chatbot/admin_dashboard.html",
        stats=stats,
        recent_conversations=recent_conversations,
        lead_queue=lead_queue
    )


@chatbot.route("/admin/credentials", methods=["GET", "POST"])
@login_required
def manage_credentials():
    """Gestión de credenciales de LLM"""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        provider = data.get("provider")
        api_key = data.get("api_key")
        endpoint = data.get("endpoint")

        if not provider or not api_key:
            msg = "Provider y API key son requeridos"
            return (jsonify({"error": msg}), 400) if request.is_json else (
                flash(msg, "error"),
                redirect(url_for('chatbot.manage_credentials'))
            )

        try:
            settings_data = json.loads(data.get("settings", "{}"))
        except json.JSONDecodeError:
            msg = "El campo settings no contiene JSON válido"
            return (jsonify({"error": msg}), 400) if request.is_json else (
                flash(msg, "error"),
                redirect(url_for('chatbot.manage_credentials'))
            )

        success = credentials_manager.save_credential(
            provider=provider,
            api_key=api_key,
            endpoint=endpoint,
            settings=settings_data
        )

        if request.is_json:
            return (
                jsonify({"message": f"Credenciales para {provider} guardadas"}) if success
                else jsonify({"error": "Error guardando credenciales"}), 200 if success else 500
            )

        flash(
            f"Credenciales para {provider} guardadas correctamente" if success else "Error guardando credenciales",
            "success" if success else "error"
        )
        return redirect(url_for('chatbot.manage_credentials'))

    providers = AgentCredentials.query.all()
    return render_template("chatbot/credentials.html", providers=providers)


@chatbot.route("/admin/test-llm", methods=["POST"])
def test_llm():
    """Prueba la configuración del LLM"""
    data = request.get_json()
    provider = data.get("provider", "openai")
    test_prompt = data.get("prompt", "Di 'Hola, sistema funcionando' en 5 palabras")

    try:
        llm = get_llm(provider)
        response = llm.complete(test_prompt)
        tokens = llm.get_token_count()
        return jsonify({"provider": provider, "response": response, "tokens_used": tokens, "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@chatbot.route("/admin/settings", methods=["GET"])
def get_settings():
    """Obtiene las configuraciones globales"""
    section = request.args.get("section")
    config = settings.get_config(section)
    return jsonify(config)


@chatbot.route("/admin/templates", methods=["GET", "POST"])
@login_required
def manage_templates():
    """Gestión de plantillas de mensajes"""
    if request.method == "POST":
        data = request.form
        template = MessageTemplate(
            key=data.get("key"),
            category=data.get("category"),
            template=data.get("template"),
            variables=json.loads(data.get("variables", "[]"))
        )
        db.session.add(template)
        db.session.commit()
        flash("Template guardado", "success")
        return redirect(url_for('chatbot.manage_templates'))

    templates = MessageTemplate.query.all()
    return render_template("chatbot/templates.html", templates=templates)


@chatbot.route("/admin/settings/ui", methods=["GET", "POST"])
@login_required
def manage_settings():
    """Gestión de configuraciones UI del agente"""
    if request.method == "POST":
        settings.model = request.form.get("model")
        settings.temperature = float(request.form.get("temperature", 0.7))
        settings.max_tokens = int(request.form.get("max_tokens", 1024))
        settings.timeout = int(request.form.get("timeout", 30))
        settings.language = request.form.get("language", "es")
        flash("Configuraciones guardadas correctamente", "success")
        return redirect(url_for("chatbot.manage_settings"))

    current = {
        "model": getattr(settings, "model", ""),
        "temperature": getattr(settings, "temperature", 0.7),
        "max_tokens": getattr(settings, "max_tokens", 1024),
        "timeout": getattr(settings, "timeout", 30),
        "language": getattr(settings, "language", "es"),
    }
    return render_template("chatbot/settings.html", settings=current)

# ============================================
# CRUD DE AGENTES IA (Multi-cliente)
# ============================================

def _parse_json_or_csv(value, as_int=False):
    if not value or str(value).strip() == "":
        return None
    try:
        data = json.loads(value)
        if as_int and isinstance(data, list):
            return [int(x) for x in data]
        return data
    except Exception:
        items = [x.strip() for x in str(value).split(",") if x.strip()]
        return [int(x) for x in items] if as_int else items or None

def _agent_to_dict(agent: Agent):
    return {
        "id": agent.id,
        "cliente_id": agent.cliente_id,
        "nombre": agent.nombre,
        "rol_proposito": agent.rol_proposito,
        "estado": agent.estado,
        "credential_id": agent.credential_id,
        "journey_ids": agent.journey_ids or [],
        "tono": agent.tono,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }

@chatbot.route("/admin/clients", methods=["GET"])
@login_required
def admin_clients_list():
    clientes = Cliente.query.order_by(Cliente.nombre.asc()).all()
    return render_template("chatbot/admin/clients_list.html", clientes=clientes)

@chatbot.route("/admin/clients/<int:cliente_id>/agents", methods=["GET"])
@login_required
def admin_client_agents(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    agentes = Agent.query.filter_by(cliente_id=cliente_id).order_by(Agent.created_at.desc()).all()
    proveedores = AgentCredentials.query.filter_by(is_active=True).all()
    journeys = LeadJourney.query.order_by(LeadJourney.nombre.asc()).all()
    return render_template("chatbot/admin/agents_list.html",
        cliente=cliente, agentes=agentes, proveedores=proveedores, journeys=journeys)

@chatbot.route("/admin/clients/<int:cliente_id>/agents/new", methods=["POST"])
@login_required
def admin_client_agents_create(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    nombre = request.form.get("nombre", "").strip()
    if not nombre:
        return jsonify({"ok": False, "error": "El nombre es obligatorio."}), 400
    agent = Agent(
        cliente_id=cliente.id,
        nombre=nombre,
        rol_proposito=request.form.get("rol_proposito"),
        estado=request.form.get("estado", "activo"),
        credential_id=int(request.form["credential_id"]) if request.form.get("credential_id") else None,
        tono=request.form.get("tono"),
        alcance=_parse_json_or_csv(request.form.get("alcance")),
        guardrails=_parse_json_or_csv(request.form.get("guardrails")),
        nlp_tecnicas=_parse_json_or_csv(request.form.get("nlp_tecnicas")),
        canales=_parse_json_or_csv(request.form.get("canales")),
        plantillas=_parse_json_or_csv(request.form.get("plantillas")),
        memoria_config=_parse_json_or_csv(request.form.get("memoria_config")),
        context_summary=request.form.get("context_summary"),
        stats=_parse_json_or_csv(request.form.get("stats")),
        version=request.form.get("version", "v1"),
        journey_ids=_parse_json_or_csv(request.form.get("journey_ids"), as_int=True),
    )
    db.session.add(agent)
    db.session.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "agent": _agent_to_dict(agent)}), 201
    flash("Agente creado correctamente.", "success")
    return redirect(url_for("chatbot.admin_client_agents", cliente_id=cliente.id))

@chatbot.route("/admin/agents/<int:agent_id>/edit", methods=["GET"])
@login_required
def admin_agent_edit(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    return jsonify({"ok": True, "agent": _agent_to_dict(agent)})

@chatbot.route("/admin/agents/<int:agent_id>/update", methods=["POST"])
@login_required
def admin_agent_update(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    for field in ("nombre", "rol_proposito", "estado", "context_summary", "version"):
        if field in request.form:
            setattr(agent, field, request.form.get(field))
    if "credential_id" in request.form:
        cred_val = request.form.get("credential_id")
        agent.credential_id = int(cred_val) if cred_val else None
    # Campos JSON
    for field in ("tono","alcance","guardrails","nlp_tecnicas","canales",
                  "plantillas","memoria_config","stats","journey_ids"):
        if field in request.form:
            setattr(agent, field, _parse_json_or_csv(request.form.get(field),
                                                    as_int=(field=="journey_ids")))
    agent.updated_at = datetime.utcnow()
    db.session.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "agent": _agent_to_dict(agent)})
    flash("Agente actualizado correctamente.", "success")
    return redirect(url_for("chatbot.admin_client_agents", cliente_id=agent.cliente_id))

@chatbot.route("/admin/agents/<int:agent_id>/delete", methods=["POST"])
@login_required
def admin_agent_delete(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    cliente_id = agent.cliente_id
    db.session.delete(agent)
    db.session.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "deleted_id": agent_id})
    flash("Agente eliminado correctamente.", "success")
    return redirect(url_for("chatbot.admin_client_agents", cliente_id=cliente_id))

@chatbot.route("/admin/agents/<int:agent_id>/toggle", methods=["POST"])
@login_required
def admin_agent_toggle(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    agent.estado = "en_pausa" if agent.estado == "activo" else "activo"
    agent.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "agent": _agent_to_dict(agent)})


@chatbot.route("/admin/agents/<int:agent_id>", methods=["GET"])
@login_required
def admin_agent_detail(agent_id):
    """Vista avanzada para configurar el agente (ficha)."""
    agent = Agent.query.get_or_404(agent_id)
    # Puedes pasar también proveedores, journeys, métricas, etc.
    return render_template("chatbot/admin/agent_detail.html", agent=agent)
