from datetime import datetime
from skote import db
from sqlalchemy import ForeignKey, Text, String, Integer, Boolean, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB


class NodoAIMetadata(db.Model):
    """
    Metadata adicional para nodos, específica para el agente AI.
    Se relaciona 1:1 con Nodo sin modificar la tabla original.
    """
    __tablename__ = 'nodo_ai_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    nodo_id = db.Column(db.Integer, ForeignKey('nodos.id'), unique=True, nullable=False)
    
    # Condiciones de completitud evaluables por AI
    ai_completion_rules = db.Column(JSONB, nullable=True)
    # Ejemplo: {
    #   "type": "any_of",  # "all_of", "any_of", "custom"
    #   "conditions": [
    #     {"field": "user_response", "contains": ["sí", "acepto", "correcto"]},
    #     {"field": "data_collected", "has_keys": ["email", "telefono"]}
    #   ]
    # }
    
    # Instrucciones específicas para el agente
    ai_instructions = db.Column(db.Text, nullable=True)
    expected_data_fields = db.Column(JSONB, nullable=True)  # Campos esperados en user_data
    objection_handlers = db.Column(JSONB, nullable=True)  # Respuestas a objeciones comunes
    
    # Timeout y validaciones
    timeout_minutes = db.Column(db.Integer, nullable=True)
    min_interaction_count = db.Column(db.Integer, default=1)  # Mínimo de interacciones
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación
    nodo = db.relationship('Nodo', backref='ai_metadata', uselist=False)


class BranchAIMetadata(db.Model):
    """
    Metadata adicional para branches, específica para evaluación AI.
    Se relaciona 1:1 con NodoNextStep sin modificar la tabla original.
    """
    __tablename__ = 'branch_ai_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, ForeignKey('nodo_next_steps.id'), unique=True, nullable=False)
    
    # Reglas de evaluación estructuradas
    evaluation_rules = db.Column(JSONB, nullable=True)
    # Ejemplo: {
    #   "type": "rule_based",
    #   "rules": [
    #     {"field": "user_data.experiencia_anos", "operator": ">", "value": 2},
    #     {"field": "last_response", "pattern": "afirmativo"}
    #   ]
    # }
    
    # Keywords y patrones esperados
    expected_keywords = db.Column(JSONB, nullable=True)  # ["sí", "claro", "correcto"]
    confidence_threshold = db.Column(db.Float, default=0.7)  # Umbral de confianza
    
    # Estadísticas
    times_evaluated = db.Column(db.Integer, default=0)
    times_selected = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación
    branch = db.relationship('NodoNextStep', backref='ai_metadata', uselist=False)


class JourneyProgress(db.Model):
    """
    Tracking detallado del progreso del usuario en cada nodo.
    Tabla completamente nueva, no afecta las existentes.
    """
    __tablename__ = 'journey_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, ForeignKey('usuarios.id'), nullable=False)
    journey_id = db.Column(db.Integer, ForeignKey('journeys.id'), nullable=False)
    nodo_id = db.Column(db.Integer, ForeignKey('nodos.id'), nullable=False)
    
    # Estado del nodo
    status = db.Column(db.String(50), default='not_started')
    # 'not_started', 'in_progress', 'completed', 'skipped', 'failed'
    
    # Timestamps
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    last_interaction = db.Column(db.DateTime, nullable=True)
    
    # Métricas
    interaction_count = db.Column(db.Integer, default=0)
    time_spent_seconds = db.Column(db.Integer, default=0)
    
    # Datos capturados
    collected_data = db.Column(JSONB, nullable=True)
    user_responses = db.Column(JSONB, nullable=True)  # Array de respuestas
    
    # Evaluación AI
    ai_evaluation = db.Column(JSONB, nullable=True)
    completion_score = db.Column(db.Float, nullable=True)  # 0.0 a 1.0
    completion_reason = db.Column(db.Text, nullable=True)
    
    # Branch tomada (si aplica)
    branch_taken_id = db.Column(db.Integer, ForeignKey('nodo_next_steps.id'), nullable=True)
    branch_evaluation = db.Column(JSONB, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    usuario = db.relationship('Usuario', backref='journey_progress')
    journey = db.relationship('LeadJourney', backref='user_progress')
    nodo = db.relationship('Nodo', backref='user_progress')
    branch_taken = db.relationship('NodoNextStep', foreign_keys=[branch_taken_id])
    
    # Índices únicos para evitar duplicados
    __table_args__ = (
        db.UniqueConstraint('usuario_id', 'journey_id', 'nodo_id', 
                           name='_usuario_journey_nodo_uc'),
    )


class ConversationStateExtended(db.Model):
    """
    Estado extendido de conversación para el orquestador AI.
    Complementa ConversationState sin modificarlo.
    """
    __tablename__ = 'conversation_state_extended'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, ForeignKey('usuarios.id'), unique=True, nullable=False)
    
    # Tracking detallado del journey
    current_node_id = db.Column(db.Integer, ForeignKey('nodos.id'), nullable=True)
    nodes_visited = db.Column(JSONB, default=list)  # [node_ids]
    nodes_completed = db.Column(JSONB, default=list)  # [node_ids]
    
    # Análisis de conversación
    detected_objections = db.Column(JSONB, default=list)
    detected_interests = db.Column(JSONB, default=list)
    sentiment_history = db.Column(JSONB, default=list)
    
    # Métricas
    total_interactions = db.Column(db.Integer, default=0)
    questions_count = db.Column(db.Integer, default=0)
    objections_count = db.Column(db.Integer, default=0)
    
    # Control de flujo
    is_stuck = db.Column(db.Boolean, default=False)
    stuck_at_node_id = db.Column(db.Integer, ForeignKey('nodos.id'), nullable=True)
    stuck_reason = db.Column(db.Text, nullable=True)
    stuck_since = db.Column(db.DateTime, nullable=True)
    
    # Evaluación para intervención humana
    requires_human = db.Column(db.Boolean, default=False)
    human_reason = db.Column(db.Text, nullable=True)
    escalated_at = db.Column(db.DateTime, nullable=True)
    
    # Contexto acumulado
    context_summary = db.Column(db.Text, nullable=True)
    key_data_collected = db.Column(JSONB, default=dict)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    usuario = db.relationship('Usuario', backref='conversation_extended', uselist=False)
    current_node = db.relationship('Nodo', foreign_keys=[current_node_id])
    stuck_at_node = db.relationship('Nodo', foreign_keys=[stuck_at_node_id])


