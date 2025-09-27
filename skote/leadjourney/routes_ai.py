from flask import Blueprint, jsonify, request
from skote import db
from skote.leadjourney.models import LeadJourney, Nodo, NodoNextStep
from skote.leadjourney.models_ai import (
    NodoAIMetadata, BranchAIMetadata, JourneyProgress, 
    ConversationStateExtended
)
from skote.leadjourney.ai_helpers import (
    get_or_create_nodo_metadata, get_or_create_branch_metadata,
    get_user_progress, get_conversation_extended
)
from skote.usuarios.models import Usuario, ChatHistory
from skote.ticnochatbot.models import ConversationState, HitoJourney
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import json
from . import ai_bp


@ai_bp.route('/api/journey/<int:journey_id>/user/<int:user_id>/ai-overview', methods=['GET'])
def ai_journey_overview(journey_id: int, user_id: int):
    """
    Endpoint completo para el agente AI orquestador.
    Usa las tablas auxiliares sin tocar los modelos originales.
    """
    
    # Parámetros opcionales
    include_history = request.args.get('include_history', 'true').lower() == 'true'
    history_limit = request.args.get('history_limit', 50, type=int)
    include_hitos = request.args.get('include_hitos', 'true').lower() == 'true'
    
    # 1. Validaciones básicas
    usuario = Usuario.query.filter_by(id=user_id).first()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    journey = LeadJourney.query.get(journey_id)
    if not journey:
        return jsonify({"error": "Journey no encontrado"}), 404
    
    # 2. Obtener estado extendido de conversación
    conv_extended = get_conversation_extended(user_id)
    
    # 3. Obtener estado original de conversación (si existe)
    conv_original = ConversationState.query.filter_by(usuario_id=user_id).first()
    
    # 4. Construir estructura del journey con metadata AI
    journey_structure = build_enhanced_journey_structure(journey_id)
    
    # 5. Obtener progreso del usuario
    user_progress = get_enhanced_user_progress(usuario, journey, conv_extended)
    
    # 6. Historial de conversación
    chat_summary = None
    if include_history:
        chat_summary = process_chat_history(user_id, history_limit)
    
    # 7. Hitos completados
    completed_milestones = None
    if include_hitos:
        completed_milestones = get_user_milestones(user_id, journey_id)
    
    # 8. Calcular recomendación de siguiente paso
    next_recommendation = calculate_next_step_with_ai(
        journey_structure,
        user_progress,
        chat_summary,
        completed_milestones,
        conv_extended
    )
    
    # 9. Evaluación del estado actual
    evaluation = evaluate_current_state(
        user_progress,
        conv_extended,
        chat_summary,
        completed_milestones,
        journey_structure
    )
    
    # Respuesta completa
    return jsonify({
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "journey_id": journey_id,
            "journey_name": journey.nombre,
            "user_id": user_id,
            "user_status": usuario.estado.value if usuario.estado else "pendiente"
        },
        
        "journey_structure": journey_structure,
        "user_progress": user_progress,
        
        "conversation_context": {
            "current_state": {
                "current_node_id": conv_extended.current_node_id,
                "nodes_visited": conv_extended.nodes_visited or [],
                "nodes_completed": conv_extended.nodes_completed or [],
                "total_interactions": conv_extended.total_interactions,
                "context_summary": conv_extended.context_summary,
                "is_stuck": conv_extended.is_stuck,
                "stuck_reason": conv_extended.stuck_reason
            },
            "chat_summary": chat_summary
        },
        
        "completed_milestones": completed_milestones,
        "ai_recommendations": next_recommendation,
        "evaluation_criteria": evaluation
    })


def build_enhanced_journey_structure(journey_id):
    """
    Construye la estructura del journey incluyendo metadata AI.
    """
    journey = LeadJourney.query.get(journey_id)
    nodos = Nodo.query.filter_by(id_journey=journey_id).all()
    
    nodes_dict = {}
    for nodo in nodos:
        # Obtener metadata AI del nodo (si existe)
        ai_meta = NodoAIMetadata.query.filter_by(nodo_id=nodo.id).first()
        
        # Obtener branches con su metadata
        branches = []
        for step in nodo.next_steps:
            branch_meta = BranchAIMetadata.query.filter_by(branch_id=step.id).first()
            
            branches.append({
                "branch_id": step.id,
                "target_node_id": step.nodo_destino_id,
                "target_node_name": step.destino.nombre if step.destino else None,
                "condition_label": step.etiqueta,
                "condition_logic": step.condicion_logica,
                "order": step.orden,
                # Metadata AI
                "ai_evaluation_rules": branch_meta.evaluation_rules if branch_meta else None,
                "expected_keywords": branch_meta.expected_keywords if branch_meta else None,
                "confidence_threshold": branch_meta.confidence_threshold if branch_meta else 0.7
            })
        
        nodes_dict[nodo.id] = {
            "node_id": nodo.id,
            "name": nodo.nombre,
            "prompt": nodo.prompt_agent,
            "completion_condition": nodo.completion_condition,  # Campo original
            "position": {"x": nodo.pos_x, "y": nodo.pos_y},
            "branches": sorted(branches, key=lambda x: x.get("order", 0)),
            "is_start_node": (journey.primer_nodo_id == nodo.id),
            "is_end_node": len(branches) == 0,
            # Metadata AI
            "ai_metadata": {
                "completion_rules": ai_meta.ai_completion_rules if ai_meta else None,
                "instructions": ai_meta.ai_instructions if ai_meta else None,
                "expected_fields": ai_meta.expected_data_fields if ai_meta else None,
                "objection_handlers": ai_meta.objection_handlers if ai_meta else None,
                "timeout_minutes": ai_meta.timeout_minutes if ai_meta else None,
                "min_interactions": ai_meta.min_interaction_count if ai_meta else 1
            } if ai_meta else None
        }
    
    # Calcular el path principal
    main_path = []
    if journey.primer_nodo_id:
        current_id = journey.primer_nodo_id
        visited = set()
        
        while current_id and current_id not in visited:
            visited.add(current_id)
            main_path.append(current_id)
            
            node = nodes_dict.get(current_id)
            if node and node["branches"]:
                current_id = node["branches"][0]["target_node_id"]
            else:
                current_id = None
    
    return {
        "journey_id": journey_id,
        "journey_name": journey.nombre,
        "nodes": nodes_dict,
        "main_path": main_path,
        "total_nodes": len(nodes_dict)
    }


def get_enhanced_user_progress(usuario, journey, conv_extended):
    """
    Obtiene el progreso del usuario usando las tablas auxiliares.
    """
    # Nodo actual
    current_node_id = conv_extended.current_node_id or usuario.current_step_id
    if not current_node_id and journey.primer_nodo_id:
        current_node_id = journey.primer_nodo_id
    
    current_node = Nodo.query.get(current_node_id) if current_node_id else None
    
    # Progreso en cada nodo
    progress_records = JourneyProgress.query.filter_by(
        usuario_id=usuario.id,
        journey_id=journey.id
    ).all()
    
    nodes_progress = {}
    for prog in progress_records:
        nodes_progress[prog.nodo_id] = {
            "status": prog.status,
            "started_at": prog.started_at.isoformat() if prog.started_at else None,
            "completed_at": prog.completed_at.isoformat() if prog.completed_at else None,
            "interaction_count": prog.interaction_count,
            "completion_score": prog.completion_score,
            "collected_data": prog.collected_data,
            "branch_taken": prog.branch_taken_id
        }
    
    # Nodos completados
    completed_nodes = [nid for nid, p in nodes_progress.items() 
                      if p["status"] == "completed"]
    
    return {
        "current_node": {
            "id": current_node.id if current_node else None,
            "name": current_node.nombre if current_node else None,
            "prompt": current_node.prompt_agent if current_node else None
        },
        "nodes_visited": conv_extended.nodes_visited or [],
        "nodes_completed": completed_nodes,
        "nodes_progress": nodes_progress,
        "journey_assigned": usuario.leadjourney_id == journey.id,
        "journey_started_at": usuario.journey_started_at.isoformat() if usuario.journey_started_at else None,
        "user_data": usuario.user_data,
        "key_data_collected": conv_extended.key_data_collected or {},
        "estado": usuario.estado.value if usuario.estado else "pendiente"
    }


def process_chat_history(user_id, limit):
    """
    Procesa el historial de chat para extraer información relevante.
    """
    messages = ChatHistory.query.filter_by(
        usuario_id=user_id
    ).order_by(ChatHistory.created_at.desc()).limit(limit).all()
    
    if not messages:
        return None
    
    # Orden cronológico
    messages = list(reversed(messages))
    
    # Análisis básico
    questions = []
    objections = []
    last_user_msg = None
    last_agent_msg = None
    
    processed = []
    for msg in messages:
        processed.append({
            "role": msg.role,
            "content": msg.message,
            "type": msg.tipo,
            "timestamp": msg.created_at.isoformat()
        })
        
        if msg.role == "usuario":
            last_user_msg = msg.message
            if "?" in msg.message:
                questions.append(msg.message)
            if any(w in msg.message.lower() for w in ["no", "pero", "aunque", "sin embargo"]):
                objections.append(msg.message)
        elif msg.role == "agente":
            last_agent_msg = msg.message
    
    return {
        "total_messages": len(messages),
        "messages": processed[-10:],  # Últimos 10 mensajes
        "analysis": {
            "questions_detected": len(questions),
            "objections_detected": len(objections),
            "last_user_message": last_user_msg,
            "last_agent_message": last_agent_msg,
            "conversation_start": messages[0].created_at.isoformat() if messages else None,
            "last_interaction": messages[-1].created_at.isoformat() if messages else None
        }
    }


def get_user_milestones(user_id, journey_id):
    """
    Obtiene los hitos completados del usuario.
    """
    hitos = db.session.query(
        HitoJourney, Nodo
    ).join(
        Nodo, HitoJourney.step_id == Nodo.id
    ).filter(
        and_(
            HitoJourney.usuario_id == user_id,
            Nodo.id_journey == journey_id
        )
    ).order_by(HitoJourney.timestamp.asc()).all()
    
    milestones = []
    for hito, nodo in hitos:
        milestones.append({
            "milestone_id": hito.id,
            "node_id": nodo.id,
            "node_name": nodo.nombre,
            "status": hito.status,
            "generated_by": hito.generated_by,
            "timestamp": hito.timestamp.isoformat(),
            "attachment": hito.attachment,
            "comment": hito.comentario
        })
    
    return milestones


def calculate_next_step_with_ai(journey_structure, user_progress, chat_summary, 
                                milestones, conv_extended):
    """
    Calcula el siguiente paso usando las reglas AI.
    """
    current_node_id = user_progress["current_node"]["id"]
    
    if not current_node_id:
        # Buscar nodo inicial
        for node in journey_structure["nodes"].values():
            if node["is_start_node"]:
                return {
                    "recommended_action": "start_journey",
                    "target_node": node,
                    "reasoning": "Usuario no ha iniciado el journey",
                    "confidence": 1.0
                }
    
    current_node = journey_structure["nodes"].get(current_node_id)
    if not current_node:
        return {
            "recommended_action": "error",
            "reasoning": "Nodo actual no encontrado",
            "confidence": 0.0
        }
    
    # Verificar si el nodo actual está completado
    node_progress = user_progress["nodes_progress"].get(current_node_id)
    is_completed = evaluate_node_completion(
        current_node, 
        node_progress,
        chat_summary,
        milestones,
        conv_extended
    )
    
    if not is_completed["completed"]:
        return {
            "recommended_action": "continue_current_node",
            "current_node": current_node,
            "reasoning": is_completed["reason"],
            "pending_conditions": is_completed["pending"],
            "confidence": is_completed["confidence"]
        }
    
    # Evaluar branches para siguiente paso
    if current_node["branches"]:
        best_branch = None
        best_score = 0.0
        
        for branch in current_node["branches"]:
            score = evaluate_branch_with_ai(
                branch,
                user_progress,
                chat_summary,
                conv_extended
            )
            
            if score["matches"] and score["confidence"] > best_score:
                best_branch = branch
                best_score = score["confidence"]
        
        if best_branch:
            target_node = journey_structure["nodes"].get(best_branch["target_node_id"])
            return {
                "recommended_action": "move_to_next_node",
                "current_node": current_node,
                "target_node": target_node,
                "branch_taken": best_branch,
                "reasoning": f"Condición cumplida: {best_branch['condition_label']}",
                "confidence": best_score
            }
        
        # Tomar branch por defecto
        default_branch = current_node["branches"][0]
        target_node = journey_structure["nodes"].get(default_branch["target_node_id"])
        return {
            "recommended_action": "move_to_next_node",
            "current_node": current_node,
            "target_node": target_node,
            "branch_taken": default_branch,
            "reasoning": "Tomando rama por defecto (ninguna condición específica cumplida)",
            "confidence": 0.5
        }
    
    # No hay más branches - journey completado
    return {
        "recommended_action": "journey_completed",
        "current_node": current_node,
        "reasoning": "No hay más pasos en el journey",
        "confidence": 1.0
    }


def evaluate_node_completion(node, node_progress, chat_summary, milestones, conv_extended):
    """
    Evalúa si un nodo está completado usando múltiples criterios.
    """
    reasons = []
    pending = []
    
    # 1. Verificar por status en progress
    if node_progress and node_progress["status"] == "completed":
        return {
            "completed": True,
            "reason": "Nodo marcado como completado",
            "pending": [],
            "confidence": 1.0
        }
    
    # 2. Verificar por hitos validados
    node_milestones = [m for m in (milestones or []) 
                      if m["node_id"] == node["node_id"] and m["status"] == "validated"]
    if node_milestones:
        return {
            "completed": True,
            "reason": "Hito validado para este nodo",
            "pending": [],
            "confidence": 0.95
        }
    
    # 3. Evaluar reglas AI si existen
    if node.get("ai_metadata") and node["ai_metadata"].get("completion_rules"):
        rules = node["ai_metadata"]["completion_rules"]
        result = evaluate_completion_rules(rules, conv_extended, chat_summary)
        
        if result["completed"]:
            return {
                "completed": True,
                "reason": f"Reglas AI cumplidas: {result['matched_rules']}",
                "pending": [],
                "confidence": result["confidence"]
            }
        else:
            pending.extend(result["pending_rules"])
    
    # 4. Evaluar interacciones mínimas
    if node.get("ai_metadata") and node["ai_metadata"].get("min_interactions"):
        min_interactions = node["ai_metadata"]["min_interactions"]
        actual_interactions = node_progress["interaction_count"] if node_progress else 0
        
        if actual_interactions < min_interactions:
            pending.append(f"Requiere {min_interactions - actual_interactions} interacciones más")
    
    # 5. Evaluar campos de datos esperados
    if node.get("ai_metadata") and node["ai_metadata"].get("expected_fields"):
        expected = node["ai_metadata"]["expected_fields"]
        collected = conv_extended.key_data_collected or {}
        missing = [f for f in expected if f not in collected]
        
        if missing:
            pending.append(f"Faltan campos: {', '.join(missing)}")
    
    # 6. Verificar timeout
    if node_progress and node["ai_metadata"] and node["ai_metadata"].get("timeout_minutes"):
        timeout = node["ai_metadata"]["timeout_minutes"]
        if node_progress["started_at"]:
            elapsed = (datetime.utcnow() - datetime.fromisoformat(node_progress["started_at"])).total_seconds() / 60
            if elapsed > timeout:
                return {
                    "completed": True,
                    "reason": f"Timeout alcanzado ({timeout} minutos)",
                    "pending": [],
                    "confidence": 0.7
                }
    
    # Si hay interacción reciente, considerar parcialmente completado
    if chat_summary and chat_summary["analysis"]["last_user_message"]:
        confidence = 0.3 if pending else 0.6
    else:
        confidence = 0.1
    
    return {
        "completed": False,
        "reason": "Nodo no completado aún",
        "pending": pending if pending else ["Esperando interacción del usuario"],
        "confidence": confidence
    }


def evaluate_branch_with_ai(branch, user_progress, chat_summary, conv_extended):
    """
    Evalúa si una branch debe tomarse usando reglas AI.
    """
    score = {
        "matches": False,
        "confidence": 0.0,
        "reasons": []
    }
    
    # 1. Evaluar reglas estructuradas si existen
    if branch.get("ai_evaluation_rules"):
        rules = branch["ai_evaluation_rules"]
        result = evaluate_branch_rules(rules, user_progress, chat_summary, conv_extended)
        
        if result["matches"]:
            score["matches"] = True
            score["confidence"] = max(score["confidence"], result["confidence"])
            score["reasons"].append(f"Reglas AI: {result['matched']}")
    
    # 2. Evaluar keywords esperados
    if branch.get("expected_keywords") and chat_summary:
        last_msg = chat_summary["analysis"]["last_user_message"]
        if last_msg:
            keywords = branch["expected_keywords"]
            matched = [kw for kw in keywords if kw.lower() in last_msg.lower()]
            
            if matched:
                score["matches"] = True
                confidence = len(matched) / len(keywords)
                score["confidence"] = max(score["confidence"], confidence)
                score["reasons"].append(f"Keywords detectados: {matched}")
    
    # 3. Evaluar condición lógica original
    if branch.get("condition_logic"):
        # Aquí se podría evaluar la condición con un parser
        # Por ahora, detección simple
        condition = branch["condition_logic"].lower()
        
        if "si" in condition or "sí" in condition:
            if chat_summary and any(w in (chat_summary["analysis"]["last_user_message"] or "").lower() 
                                   for w in ["sí", "si", "claro", "correcto"]):
                score["matches"] = True
                score["confidence"] = max(score["confidence"], 0.8)
                score["reasons"].append("Respuesta afirmativa detectada")
    
    # Aplicar threshold de confianza
    threshold = branch.get("confidence_threshold", 0.7)
    if score["confidence"] < threshold:
        score["matches"] = False
    
    return score


def evaluate_completion_rules(rules, conv_extended, chat_summary):
    """
    Evalúa reglas de completitud estructuradas.
    """
    # Implementación simplificada
    if not rules:
        return {"completed": False, "matched_rules": [], "pending_rules": [], "confidence": 0.0}
    
    rule_type = rules.get("type", "all_of")
    conditions = rules.get("conditions", [])
    
    matched = []
    pending = []
    
    for condition in conditions:
        if evaluate_single_condition(condition, conv_extended, chat_summary):
            matched.append(condition)
        else:
            pending.append(condition)
    
    if rule_type == "all_of":
        completed = len(pending) == 0
        confidence = len(matched) / len(conditions) if conditions else 0
    elif rule_type == "any_of":
        completed = len(matched) > 0
        confidence = 1.0 if matched else 0.0
    else:
        completed = False
        confidence = 0.0
    
    return {
        "completed": completed,
        "matched_rules": matched,
        "pending_rules": pending,
        "confidence": confidence
    }


def evaluate_single_condition(condition, conv_extended, chat_summary):
    """
    Evalúa una condición individual.
    """
    # Implementación básica - expandir según necesidades
    field = condition.get("field")
    
    if field == "user_response" and chat_summary:
        last_msg = chat_summary["analysis"]["last_user_message"] or ""
        contains = condition.get("contains", [])
        return any(keyword in last_msg.lower() for keyword in contains)
    
    elif field == "data_collected":
        has_keys = condition.get("has_keys", [])
        collected = conv_extended.key_data_collected or {}
        return all(key in collected for key in has_keys)
    
    return False


def evaluate_branch_rules(rules, user_progress, chat_summary, conv_extended):
    """
    Evalúa reglas de branch estructuradas.
    """
    # Similar a evaluate_completion_rules pero para branches
    if not rules:
        return {"matches": False, "confidence": 0.0, "matched": []}
    
    # Implementación simplificada
    return {
        "matches": False,
        "confidence": 0.0,
        "matched": []
    }


def evaluate_current_state(user_progress, conv_extended, chat_summary, 
                          milestones, journey_structure):
    """
    Evaluación completa del estado actual.
    """
    total_nodes = journey_structure["total_nodes"]
    completed_nodes = len(user_progress["nodes_completed"])
    completion_percentage = (completed_nodes / total_nodes * 100) if total_nodes > 0 else 0
    
    # Detección de bloqueo
    stuck_detection = {
        "is_stuck": conv_extended.is_stuck,
        "reasons": [],
        "stuck_since": conv_extended.stuck_since.isoformat() if conv_extended.stuck_since else None
    }
    
    if conv_extended.is_stuck:
        stuck_detection["reasons"].append(conv_extended.stuck_reason or "Razón no especificada")
    
    # Verificar inactividad
    if chat_summary and chat_summary["analysis"]["last_interaction"]:
        last_interaction = datetime.fromisoformat(chat_summary["analysis"]["last_interaction"])
        time_since = datetime.utcnow() - last_interaction
        
        if time_since > timedelta(hours=24):
            stuck_detection["is_stuck"] = True
            stuck_detection["reasons"].append(f"Inactivo por {time_since.days} días")
    
    # Verificar loops
    if conv_extended.total_interactions > 20 and completion_percentage < 30:
        stuck_detection["is_stuck"] = True
        stuck_detection["reasons"].append("Muchas interacciones con poco progreso")
    
    # Acciones sugeridas
    suggested_actions = []
    
    if not user_progress["current_node"]["id"]:
        suggested_actions.append({
            "action": "initiate_journey",
            "priority": "high",
            "description": "Iniciar el journey con mensaje de bienvenida"
        })
    
    if conv_extended.questions_count > 0:
        suggested_actions.append({
            "action": "answer_pending_questions",
            "priority": "high",
            "description": f"Responder {conv_extended.questions_count} preguntas pendientes"
        })
    
    if conv_extended.objections_count > 0:
        suggested_actions.append({
            "action": "handle_objections",
            "priority": "medium",
            "description": f"Manejar {conv_extended.objections_count} objeciones detectadas"
        })
    
    if stuck_detection["is_stuck"]:
        suggested_actions.append({
            "action": "unstuck_user",
            "priority": "high",
            "description": "Desbloquear al usuario con mensaje personalizado"
        })
    
    if conv_extended.requires_human:
        suggested_actions.append({
            "action": "escalate_to_human",
            "priority": "critical",
            "description": f"Escalar a humano: {conv_extended.human_reason}"
        })
    
    return {
        "steps_completed": completed_nodes,
        "total_steps": total_nodes,
        "completion_percentage": round(completion_percentage, 2),
        "stuck_detection": stuck_detection,
        "suggested_actions": suggested_actions,
        "requires_human_intervention": conv_extended.requires_human,
        "human_reason": conv_extended.human_reason
    }


# ========================================
# ENDPOINT PARA ACTUALIZAR PROGRESO
# ========================================

@ai_bp.route('/api/journey/<int:journey_id>/user/<int:user_id>/update-progress', methods=['POST'])
def update_user_progress(journey_id: int, user_id: int):
    """
    Actualiza el progreso del usuario basado en la evaluación del AI.
    """
    data = request.get_json()
    action = data.get("action")
    
    # Obtener usuario y estado extendido
    usuario = Usuario.query.get_or_404(user_id)
    conv_extended = get_conversation_extended(user_id)
    
    try:
        if action == "move_to_node":
            new_node_id = data.get("target_node_id")
            previous_node_id = data.get("previous_node_id")
            branch_id = data.get("branch_taken_id")
            
            # Actualizar nodo actual
            usuario.current_step_id = new_node_id
            conv_extended.current_node_id = new_node_id
            
            # Agregar a nodos visitados
            if conv_extended.nodes_visited is None:
                conv_extended.nodes_visited = []
            if new_node_id not in conv_extended.nodes_visited:
                conv_extended.nodes_visited.append(new_node_id)
            
            # Marcar nodo anterior como completado
            if previous_node_id and data.get("mark_previous_complete"):
                if conv_extended.nodes_completed is None:
                    conv_extended.nodes_completed = []
                if previous_node_id not in conv_extended.nodes_completed:
                    conv_extended.nodes_completed.append(previous_node_id)
                
                # Actualizar JourneyProgress
                progress = get_user_progress(user_id, journey_id, previous_node_id)
                progress.status = "completed"
                progress.completed_at = datetime.utcnow()
                if branch_id:
                    progress.branch_taken_id = branch_id
        
        elif action == "update_context":
            conv_extended.context_summary = data.get("context_summary")
            
            # Actualizar datos recolectados
            new_data = data.get("collected_data", {})
            if conv_extended.key_data_collected is None:
                conv_extended.key_data_collected = {}
            conv_extended.key_data_collected.update(new_data)
        
        elif action == "mark_stuck":
            conv_extended.is_stuck = True
            conv_extended.stuck_reason = data.get("reason")
            conv_extended.stuck_since = datetime.utcnow()
            conv_extended.stuck_at_node_id = conv_extended.current_node_id
        
        elif action == "unstuck":
            conv_extended.is_stuck = False
            conv_extended.stuck_reason = None
            conv_extended.stuck_since = None
            conv_extended.stuck_at_node_id = None
        
        elif action == "request_human":
            conv_extended.requires_human = True
            conv_extended.human_reason = data.get("reason")
            conv_extended.escalated_at = datetime.utcnow()
        
        elif action == "complete_journey":
            usuario.journey_completed_at = datetime.utcnow()
            usuario.estado = "terminado"
        
        # Actualizar timestamps
        conv_extended.updated_at = datetime.utcnow()
        
        # Actualizar métricas si se proporcionan
        if "increment_interactions" in data:
            conv_extended.total_interactions += 1
        if "increment_questions" in data:
            conv_extended.questions_count += 1
        if "increment_objections" in data:
            conv_extended.objections_count += 1
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Acción '{action}' ejecutada correctamente",
            "current_node_id": conv_extended.current_node_id,
            "is_stuck": conv_extended.is_stuck,
            "requires_human": conv_extended.requires_human
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
