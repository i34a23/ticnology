from datetime import datetime
from skote import db
from sqlalchemy import ForeignKey


class LeadJourney(db.Model):
    __tablename__ = 'journeys'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    primer_nodo_id = db.Column(db.Integer, ForeignKey('nodos.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    primer_nodo = db.relationship('Nodo', foreign_keys=[primer_nodo_id], lazy=True)
    nodos = db.relationship(
        'Nodo',
        backref='journey',
        lazy=True,
        foreign_keys="Nodo.id_journey"
    )


class Nodo(db.Model):
    __tablename__ = 'nodos'

    id = db.Column(db.Integer, primary_key=True)
    id_journey = db.Column(db.Integer, ForeignKey('journeys.id'), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    prompt_agent = db.Column(db.Text, nullable=False)
    pos_x = db.Column(db.Integer, nullable=True)
    pos_y = db.Column(db.Integer, nullable=True)

    # NUEVO: condición que determina si este nodo está cumplido
    completion_condition = db.Column(db.Text, nullable=True)

    # Relaciones
    next_steps = db.relationship(
        'NodoNextStep',
        foreign_keys='NodoNextStep.nodo_origen_id',
        backref='origen',
        lazy=True,
        cascade="all, delete-orphan"
    )


class NodoNextStep(db.Model):
    __tablename__ = 'nodo_next_steps'

    id = db.Column(db.Integer, primary_key=True)
    nodo_origen_id = db.Column(db.Integer, ForeignKey('nodos.id'), nullable=False)
    etiqueta = db.Column(db.String(255), nullable=False)  # ej: "sí tiene experiencia", "no tiene"
    nodo_destino_id = db.Column(db.Integer, ForeignKey('nodos.id'), nullable=True)
    condicion_logica = db.Column(db.Text, nullable=True)  # reglas dinámicas
    orden = db.Column(db.Integer, default=1)  # prioridad de evaluación

    # Relaciones
    destino = db.relationship('Nodo', foreign_keys=[nodo_destino_id], lazy=True)
