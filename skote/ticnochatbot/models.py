from skote import db
from sqlalchemy import ForeignKey, Text, String, Integer, Boolean, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

class Agent(db.Model):
    """Agentes IA multi-cliente"""
    __tablename__ = "agents"

    id = db.Column(db.Integer, primary_key=True)

    # Relación con Cliente
    cliente_id = db.Column(db.Integer, ForeignKey("clientes.id"), nullable=False)

    # Identidad del agente
    nombre = db.Column(db.String(255), nullable=False)          # Ej: "Mia – Admisión CFT"
    rol_proposito = db.Column(db.Text, nullable=True)           # Texto corto del rol
    estado = db.Column(db.String(50), default="activo")         # activo | en_pausa | archivado

    # Configuración estática
    alcance = db.Column(JSONB, nullable=True)                   # Qué hace / no hace
    tono = db.Column(db.String(100), nullable=True)             # formal, empático, etc.
    guardrails = db.Column(JSONB, nullable=True)                # Palabras prohibidas, disclaimers
    nlp_tecnicas = db.Column(JSONB, nullable=True)              # Técnicas NLP autorizadas
    canales = db.Column(JSONB, nullable=True)                   # Canales y horarios
    plantillas = db.Column(JSONB, nullable=True)                # IDs/keys de MessageTemplate

    # Configuración dinámica
    memoria_config = db.Column(JSONB, nullable=True)            # Nº turnos, compresión cada X
    context_summary = db.Column(db.Text, nullable=True)         # Resumen vivo de contexto
    stats = db.Column(JSONB, nullable=True)                     # Tokens, interacciones, ratio éxito
    version = db.Column(db.String(50), default="v1")            # Versionado para clonar

    # Relaciones con journeys y credenciales
    journey_ids = db.Column(JSONB, nullable=True)               # Lista de journeys asociados
    credential_id = db.Column(db.Integer, ForeignKey("agent_credentials.id"), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones ORM
    cliente = db.relationship("Cliente", backref="agents", lazy=True)
    credentials = db.relationship("AgentCredentials", backref="agents", lazy=True)



class AgentCredentials(db.Model):
    """Almacena credenciales de forma segura para diferentes proveedores de LLM"""
    __tablename__ = 'agent_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), unique=True, nullable=False)  # 'openai', 'claude', 'ollama'
    api_key = db.Column(db.Text, nullable=False)  # Encriptado
    endpoint = db.Column(db.String(255))  # Para Ollama u otros locales
    settings = db.Column(JSONB)  # Configuraciones específicas como modelo, temperature, etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeadQueue(db.Model):
    """Cola de leads para contacto proactivo"""
    __tablename__ = 'lead_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, ForeignKey('usuarios.id'), nullable=False)
    journey_id = db.Column(db.Integer, ForeignKey('journeys.id'), nullable=False)
    priority = db.Column(db.Integer, default=5)  # 1-10, donde 10 es máxima prioridad
    scheduled_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending')  # 'pending', 'processing', 'contacted', 'failed', 'completed'
    attempts = db.Column(db.Integer, default=0)
    last_attempt = db.Column(db.DateTime)
    channel = db.Column(db.String(50), default='webchat')  # 'webchat', 'whatsapp'
    extra_metadata = db.Column(JSONB)  # Datos adicionales del lead
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuario = db.relationship('Usuario', backref='lead_queues', lazy=True)
    journey = db.relationship('LeadJourney', backref='queued_leads', lazy=True)


class ConversationState(db.Model):
    """Estado compacto de la conversación"""
    __tablename__ = 'conversation_states'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, ForeignKey('usuarios.id'), nullable=False, unique=True)
    journey_id = db.Column(db.Integer, ForeignKey('journeys.id'))
    current_step_id = db.Column(db.Integer, ForeignKey('nodos.id'))
    current_intent = db.Column(db.String(50))  # 'journey', 'faq', 'general'
    journey_progress = db.Column(db.Float, default=0.0)  # 0.0 a 1.0
    
    # Contexto de la conversación
    context_summary = db.Column(db.Text)  # Resumen comprimido de la conversación
    lead_data = db.Column(JSONB)  # Datos específicos del lead
    conversation_metadata = db.Column(JSONB)  # Metadata adicional
    
    # Tracking
    tokens_used = db.Column(db.Integer, default=0)
    messages_count = db.Column(db.Integer, default=0)
    last_provider = db.Column(db.String(50))  # último LLM usado
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_interaction = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuario = db.relationship('Usuario', backref='conversation_state', uselist=False)
    journey = db.relationship('LeadJourney', backref='active_conversations')
    current_step = db.relationship('Nodo', backref='active_states')


class HitoJourney(db.Model):
    """Eventos o hitos generados durante la ejecución del journey"""
    __tablename__ = 'hitos_journey'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, ForeignKey('usuarios.id'), nullable=False)
    step_id = db.Column(db.Integer, ForeignKey('nodos.id'), nullable=False)
    attachment = db.Column(db.String(1024), nullable=True)  # URL o path del documento
    comentario = db.Column(db.Text, nullable=True)
    generated_by = db.Column(db.String(50), nullable=False)  # 'agente', 'usuario', 'humano'
    status = db.Column(db.String(50), default='pending')  # 'pending', 'validated', 'rejected'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    step = db.relationship('Nodo', foreign_keys=[step_id], lazy=True)
    usuario = db.relationship('Usuario', backref='hitos', lazy=True)


class AgentMetrics(db.Model):
    """Métricas del agente para análisis y optimización"""
    __tablename__ = 'agent_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, ForeignKey('usuarios.id'))
    journey_id = db.Column(db.Integer, ForeignKey('journeys.id'))
    
    # Métricas de rendimiento
    response_time_ms = db.Column(db.Integer)  # Tiempo de respuesta en ms
    tokens_prompt = db.Column(db.Integer)
    tokens_completion = db.Column(db.Integer)
    provider = db.Column(db.String(50))
    
    # Métricas de conversación
    intent_detected = db.Column(db.String(50))
    confidence_score = db.Column(db.Float)
    step_from = db.Column(db.Integer, ForeignKey('nodos.id'))
    step_to = db.Column(db.Integer, ForeignKey('nodos.id'))
    
    # Resultado
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MessageTemplate(db.Model):
    """Templates de mensajes reutilizables"""
    __tablename__ = 'message_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)  # 'welcome', 'objection_price', etc
    category = db.Column(db.String(50))  # 'greeting', 'objection', 'closing'
    template = db.Column(db.Text, nullable=False)
    variables = db.Column(JSONB)  # Lista de variables esperadas
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
