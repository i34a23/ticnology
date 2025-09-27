from skote import db
from sqlalchemy import Enum, ForeignKey, Integer, Text, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum


# Enum explícito para estado del usuario
class EstadoUsuarioEnum(enum.Enum):
    pendiente = 'pendiente'
    en_curso = 'en_curso'
    en_pausa = 'en_pausa'
    terminado = 'terminado'
    cancelado = 'cancelado'


class Cliente(db.Model):
    __tablename__ = 'clientes'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    usuarios = db.relationship('Usuario', backref='cliente', lazy=True)


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    
    # Datos básicos
    nombre = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    telefono = db.Column(db.String(50), nullable=True, index=True)
    
    # Estado y journey
    leadjourney_id = db.Column(db.Integer, db.ForeignKey('journeys.id'), nullable=True)
    estado = db.Column(db.Enum(EstadoUsuarioEnum), default=EstadoUsuarioEnum.pendiente, nullable=False)
    
    # Datos dinámicos adicionales
    user_data = db.Column(JSONB, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    current_step_id = db.Column(db.Integer, db.ForeignKey('nodos.id'), nullable=True)
    journey_started_at = db.Column(db.DateTime, nullable=True)
    journey_completed_at = db.Column(db.DateTime, nullable=True)

    # Relaciones
    journey = db.relationship('LeadJourney', backref='usuarios', lazy=True)
    chat_histories = db.relationship('ChatHistory', backref='usuario', lazy=True)
    current_step = db.relationship('Nodo', foreign_keys=[current_step_id], lazy=True)


class ChatHistory(db.Model):
    __tablename__ = "chat_histories"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'usuario' o 'agente'
    message = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # 'journey', 'faq', 'fallback'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
