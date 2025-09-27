from skote import db, csrf
from sqlalchemy import func
from skote.leadjourney.models_ai import NodoAIMetadata, BranchAIMetadata, JourneyProgress, ConversationStateExtended

def get_or_create_nodo_metadata(nodo_id):
    """Obtiene o crea metadata AI para un nodo"""
    metadata = NodoAIMetadata.query.filter_by(nodo_id=nodo_id).first()
    if not metadata:
        metadata = NodoAIMetadata(nodo_id=nodo_id)
        db.session.add(metadata)
        db.session.flush()
    return metadata


def get_or_create_branch_metadata(branch_id):
    """Obtiene o crea metadata AI para una branch"""
    metadata = BranchAIMetadata.query.filter_by(branch_id=branch_id).first()
    if not metadata:
        metadata = BranchAIMetadata(branch_id=branch_id)
        db.session.add(metadata)
        db.session.flush()
    return metadata


def get_user_progress(usuario_id, journey_id, nodo_id):
    """Obtiene o crea el progreso del usuario en un nodo"""
    progress = JourneyProgress.query.filter_by(
        usuario_id=usuario_id,
        journey_id=journey_id,
        nodo_id=nodo_id
    ).first()
    
    if not progress:
        progress = JourneyProgress(
            usuario_id=usuario_id,
            journey_id=journey_id,
            nodo_id=nodo_id,
            status='not_started'
        )
        db.session.add(progress)
        db.session.flush()
    
    return progress


def get_conversation_extended(usuario_id):
    """Obtiene o crea el estado extendido de conversación"""
    state = ConversationStateExtended.query.filter_by(usuario_id=usuario_id).first()
    if not state:
        state = ConversationStateExtended(usuario_id=usuario_id)
        db.session.add(state)
        db.session.flush()
    return state