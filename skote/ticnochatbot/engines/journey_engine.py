"""
Journey Engine - Motor de Ejecución de Lead Journeys
Evalúa progreso de nodos y genera respuestas usando prompts configurados
Ubicación: /ticnochatbot/engines/journey_engine.py
"""

import logging
import httpx
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import re
import json

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """Estados posibles de un nodo en el journey"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"

class JourneyAction(Enum):
    """Acciones que puede tomar el journey engine"""
    START_JOURNEY = "start_journey"
    CONTINUE_NODE = "continue_node"
    COMPLETE_NODE = "complete_node"
    MOVE_TO_NEXT = "move_to_next"
    WAIT_FOR_INPUT = "wait_for_input"
    REQUEST_HUMAN = "request_human"
    END_JOURNEY = "end_journey"

@dataclass
class JourneyDecision:
    """Resultado de evaluación del journey engine"""
    action: JourneyAction
    current_node_id: Optional[int]
    target_node_id: Optional[int]
    response_message: str
    confidence: float
    reasoning: str
    branch_taken: Optional[Dict] = None
    collected_data: Optional[Dict] = None
    next_evaluation_needed: bool = True

class MessageTemplateEngine:
    """Engine para procesar templates de mensajes con variables"""
    
    def __init__(self):
        self.variable_pattern = re.compile(r'\{([^}]+)\}')
    
    def process_template(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Procesa un template reemplazando variables con valores
        
        Args:
            template: String con variables en formato {variable}
            variables: Diccionario con valores para reemplazar
            
        Returns:
            String procesado con variables reemplazadas
        """
        try:
            # Función para reemplazar cada variable encontrada
            def replace_var(match):
                var_name = match.group(1)
                
                # Soporte para acceso anidado (ej: user_data.nombre)
                if '.' in var_name:
                    keys = var_name.split('.')
                    value = variables
                    for key in keys:
                        if isinstance(value, dict) and key in value:
                            value = value[key]
                        else:
                            return f"{{{var_name}}}"  # Mantener variable si no se encuentra
                    return str(value)
                else:
                    return str(variables.get(var_name, f"{{{var_name}}}"))
            
            return self.variable_pattern.sub(replace_var, template)
            
        except Exception as e:
            logger.error(f"Error procesando template: {e}")
            return template

class NodeEvaluator:
    """Evaluador de completitud de nodos"""
    
    def __init__(self):
        self.template_engine = MessageTemplateEngine()
    
    def evaluate_node_completion(
        self,
        node_data: Dict[str, Any],
        user_progress: Dict[str, Any],
        chat_summary: Optional[Dict[str, Any]],
        conversation_context: Dict[str, Any]
    ) -> Tuple[bool, float, str, Dict[str, Any]]:
        """
        Evalúa si un nodo está completado
        
        Returns:
            (is_completed, confidence, reasoning, collected_data)
        """
        node_id = node_data.get("node_id")
        
        # 1. Verificar si está marcado como completado en progreso
        node_progress = user_progress.get("nodes_progress", {}).get(str(node_id), {})
        if node_progress.get("status") == "completed":
            return True, 1.0, "Nodo previamente completado", node_progress.get("collected_data", {})
        
        # 2. Evaluar reglas AI si existen
        ai_metadata = node_data.get("ai_metadata")
        if ai_metadata and ai_metadata.get("completion_rules"):
            return self._evaluate_ai_rules(
                ai_metadata["completion_rules"],
                chat_summary,
                conversation_context,
                node_progress
            )
        
        # 3. Evaluación básica basada en interacción
        return self._evaluate_basic_completion(
            node_data,
            chat_summary,
            conversation_context,
            node_progress
        )
    
    def _evaluate_ai_rules(
        self,
        rules: Dict[str, Any],
        chat_summary: Optional[Dict[str, Any]],
        conversation_context: Dict[str, Any],
        node_progress: Dict[str, Any]
    ) -> Tuple[bool, float, str, Dict[str, Any]]:
        """Evalúa reglas AI estructuradas"""
        
        if not rules:
            return False, 0.0, "Sin reglas definidas", {}
        
        rule_type = rules.get("type", "all_of")
        conditions = rules.get("conditions", [])
        
        if not conditions:
            return False, 0.0, "Sin condiciones definidas", {}
        
        matched_conditions = 0
        collected_data = {}
        
        for condition in conditions:
            if self._evaluate_single_condition(condition, chat_summary, conversation_context):
                matched_conditions += 1
                
                # Extraer datos si la condición los especifica
                if "extract_field" in condition:
                    field_value = self._extract_field_value(condition, chat_summary, conversation_context)
                    if field_value:
                        collected_data[condition["extract_field"]] = field_value
        
        # Calcular resultado según tipo de regla
        if rule_type == "all_of":
            is_completed = matched_conditions == len(conditions)
            confidence = matched_conditions / len(conditions)
            reasoning = f"Cumplidas {matched_conditions}/{len(conditions)} condiciones (requiere todas)"
        elif rule_type == "any_of":
            is_completed = matched_conditions > 0
            confidence = 1.0 if matched_conditions > 0 else 0.0
            reasoning = f"Cumplidas {matched_conditions}/{len(conditions)} condiciones (requiere una)"
        else:
            is_completed = False
            confidence = 0.0
            reasoning = f"Tipo de regla no soportado: {rule_type}"
        
        return is_completed, confidence, reasoning, collected_data
    
    def _evaluate_single_condition(
        self,
        condition: Dict[str, Any],
        chat_summary: Optional[Dict[str, Any]],
        conversation_context: Dict[str, Any]
    ) -> bool:
        """Evalúa una condición individual"""
        
        field = condition.get("field")
        
        if field == "user_response" and chat_summary:
            last_msg = chat_summary.get("analysis", {}).get("last_user_message", "")
            contains = condition.get("contains", [])
            return any(keyword.lower() in last_msg.lower() for keyword in contains)
        
        elif field == "data_collected":
            has_keys = condition.get("has_keys", [])
            collected = conversation_context.get("key_data_collected", {})
            return all(key in collected for key in has_keys)
        
        elif field == "interaction_count":
            current_count = conversation_context.get("total_interactions", 0)
            min_count = condition.get("min_value", 1)
            return current_count >= min_count
        
        elif field == "message_contains":
            if chat_summary:
                last_msg = chat_summary.get("analysis", {}).get("last_user_message", "")
                patterns = condition.get("patterns", [])
                return any(pattern.lower() in last_msg.lower() for pattern in patterns)
        
        return False
    
    def _extract_field_value(
        self,
        condition: Dict[str, Any],
        chat_summary: Optional[Dict[str, Any]],
        conversation_context: Dict[str, Any]
    ) -> Optional[str]:
        """Extrae valor de un campo según la condición"""
        
        if chat_summary and "extract_pattern" in condition:
            last_msg = chat_summary.get("analysis", {}).get("last_user_message", "")
            pattern = condition["extract_pattern"]
            
            # Extracción simple por regex
            import re
            match = re.search(pattern, last_msg, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def _evaluate_basic_completion(
        self,
        node_data: Dict[str, Any],
        chat_summary: Optional[Dict[str, Any]],
        conversation_context: Dict[str, Any],
        node_progress: Dict[str, Any]
    ) -> Tuple[bool, float, str, Dict[str, Any]]:
        """Evaluación básica sin reglas AI"""
        
        # Si el usuario ha respondido algo, considerar parcialmente completado
        if chat_summary and chat_summary.get("analysis", {}).get("last_user_message"):
            last_msg = chat_summary["analysis"]["last_user_message"].lower()
            
            # Buscar respuestas afirmativas simples
            affirmative_words = ["sí", "si", "vale", "ok", "claro", "correcto", "exacto"]
            if any(word in last_msg for word in affirmative_words):
                return True, 0.8, "Respuesta afirmativa detectada", {}
            
            # Si hay cualquier respuesta, considerar en progreso
            if len(last_msg.strip()) > 0:
                return False, 0.5, "Usuario ha respondido, esperando más información", {}
        
        # Sin interacción suficiente
        return False, 0.1, "Sin suficiente interacción del usuario", {}

class BranchEvaluator:
    """Evaluador de branches para determinar siguiente nodo"""
    
    def evaluate_branches(
        self,
        branches: List[Dict[str, Any]],
        user_progress: Dict[str, Any],
        chat_summary: Optional[Dict[str, Any]],
        conversation_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Evalúa qué branch tomar basado en el contexto
        
        Returns:
            Branch seleccionado o None si ninguno aplica
        """
        
        best_branch = None
        best_score = 0.0
        
        for branch in branches:
            score = self._evaluate_single_branch(
                branch, user_progress, chat_summary, conversation_context
            )
            
            if score > best_score and score > 0.6:  # Threshold mínimo
                best_branch = branch
                best_score = score
        
        return best_branch
    
    def _evaluate_single_branch(
        self,
        branch: Dict[str, Any],
        user_progress: Dict[str, Any],
        chat_summary: Optional[Dict[str, Any]],
        conversation_context: Dict[str, Any]
    ) -> float:
        """Evalúa un branch individual y retorna score 0.0-1.0"""
        
        # 1. Evaluar keywords esperados
        if branch.get("expected_keywords") and chat_summary:
            last_msg = chat_summary.get("analysis", {}).get("last_user_message", "")
            keywords = branch["expected_keywords"]
            
            matched = sum(1 for kw in keywords if kw.lower() in last_msg.lower())
            if matched > 0:
                return min(1.0, matched / len(keywords) + 0.3)
        
        # 2. Evaluar condición textual simple
        condition_label = branch.get("condition_label", "").lower()
        if condition_label and chat_summary:
            last_msg = chat_summary.get("analysis", {}).get("last_user_message", "").lower()
            
            if "sí" in condition_label or "si" in condition_label:
                if any(word in last_msg for word in ["sí", "si", "claro", "correcto"]):
                    return 0.9
            elif "no" in condition_label:
                if any(word in last_msg for word in ["no", "nunca", "jamás"]):
                    return 0.9
            elif "experiencia" in condition_label:
                if any(word in last_msg for word in ["experiencia", "trabajé", "años", "tiempo"]):
                    return 0.8
        
        # 3. Branch por defecto (primer branch si no hay condiciones específicas)
        if not branch.get("expected_keywords") and not branch.get("ai_evaluation_rules"):
            return 0.3  # Score bajo para branches por defecto
        
        return 0.0

class JourneyEngineManager:
    """Gestor principal del Journey Engine"""
    
    def __init__(self, ai_api_base_url: str = "http://127.0.0.1:5000/ai"):
        self.ai_api_base_url = ai_api_base_url
        self.node_evaluator = NodeEvaluator()
        self.branch_evaluator = BranchEvaluator()
        self.template_engine = MessageTemplateEngine()
        
        # Cache para datos de journeys
        self._journey_cache = {}
        self._cache_expiry = {}
        
        # Estadísticas
        self.stats = {
            "decisions_made": 0,
            "nodes_completed": 0,
            "branches_taken": 0,
            "errors": 0,
            "cache_hits": 0
        }
    
    async def make_journey_decision(
        self,
        user_id: int,
        journey_id: int,
        message: str,
        classification: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> JourneyDecision:
        """
        Toma una decisión sobre qué hacer en el journey basado en el contexto actual
        
        Args:
            user_id: ID del usuario
            journey_id: ID del journey
            message: Último mensaje del usuario
            classification: Resultado del classifier
            conversation_state: Estado actual de la conversación
            
        Returns:
            JourneyDecision con la acción a tomar
        """
        
        try:
            self.stats["decisions_made"] += 1
            
            # 1. Obtener datos completos del journey y usuario
            ai_overview = await self._get_ai_overview(user_id, journey_id)
            
            if not ai_overview:
                return JourneyDecision(
                    action=JourneyAction.REQUEST_HUMAN,
                    current_node_id=None,
                    target_node_id=None,
                    response_message="No pude acceder a la información del journey. Un agente humano te ayudará pronto.",
                    confidence=0.0,
                    reasoning="Error obteniendo datos del journey"
                )
            
            # 2. Analizar estado actual
            current_node_id = ai_overview["user_progress"]["current_node"]["id"]
            
            # Si no hay nodo actual, iniciar journey
            if not current_node_id:
                return await self._handle_journey_start(ai_overview)
            
            # 3. Evaluar nodo actual
            current_node = self._find_node_in_structure(ai_overview["journey_structure"], current_node_id)
            
            if not current_node:
                return JourneyDecision(
                    action=JourneyAction.REQUEST_HUMAN,
                    current_node_id=current_node_id,
                    target_node_id=None,
                    response_message="Hay un problema con tu journey actual. Un agente te contactará.",
                    confidence=0.0,
                    reasoning="Nodo actual no encontrado en estructura"
                )
            
            # 4. Evaluar si el nodo actual está completado
            is_completed, confidence, reasoning, collected_data = self.node_evaluator.evaluate_node_completion(
                current_node,
                ai_overview["user_progress"],
                ai_overview["conversation_context"]["chat_summary"],
                ai_overview["conversation_context"]["current_state"]
            )
            
            # 5. Decidir siguiente acción
            if is_completed:
                return await self._handle_node_completion(
                    current_node, ai_overview, collected_data, reasoning
                )
            else:
                return await self._handle_node_continuation(
                    current_node, ai_overview, confidence, reasoning
                )
                
        except Exception as e:
            logger.error(f"Error en make_journey_decision: {e}")
            self.stats["errors"] += 1
            
            return JourneyDecision(
                action=JourneyAction.WAIT_FOR_INPUT,
                current_node_id=None,
                target_node_id=None,
                response_message="Disculpa, tuve un problema procesando tu mensaje. ¿Puedes repetirlo?",
                confidence=0.0,
                reasoning=f"Error interno: {str(e)}"
            )
    
    async def _get_ai_overview(self, user_id: int, journey_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene datos completos del AI overview"""
        
        cache_key = f"{user_id}_{journey_id}"
        
        # Verificar cache (válido por 30 segundos)
        if cache_key in self._journey_cache:
            cache_time = self._cache_expiry.get(cache_key, 0)
            if datetime.now().timestamp() - cache_time < 30:
                self.stats["cache_hits"] += 1
                return self._journey_cache[cache_key]
        
        try:
            url = f"{self.ai_api_base_url}/api/journey/{journey_id}/user/{user_id}/ai-overview"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Actualizar cache
                    self._journey_cache[cache_key] = data
                    self._cache_expiry[cache_key] = datetime.now().timestamp()
                    
                    return data
                else:
                    logger.error(f"Error obteniendo AI overview: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error llamando AI overview: {e}")
            return None
    
    def _find_node_in_structure(self, journey_structure: Dict[str, Any], node_id: int) -> Optional[Dict[str, Any]]:
        """Encuentra un nodo en la estructura del journey"""
        nodes = journey_structure.get("nodes", {})
        return nodes.get(str(node_id))
    
    async def _handle_journey_start(self, ai_overview: Dict[str, Any]) -> JourneyDecision:
        """Maneja el inicio del journey"""
        
        journey_structure = ai_overview["journey_structure"]
        main_path = journey_structure.get("main_path", [])
        
        if not main_path:
            return JourneyDecision(
                action=JourneyAction.REQUEST_HUMAN,
                current_node_id=None,
                target_node_id=None,
                response_message="Este journey no tiene pasos configurados. Un agente te ayudará.",
                confidence=0.0,
                reasoning="Journey sin main_path"
            )
        
        # Tomar primer nodo del journey
        first_node_id = main_path[0]
        first_node = self._find_node_in_structure(journey_structure, first_node_id)
        
        if not first_node:
            return JourneyDecision(
                action=JourneyAction.REQUEST_HUMAN,
                current_node_id=None,
                target_node_id=None,
                response_message="Hay un problema con la configuración del journey.",
                confidence=0.0,
                reasoning="Primer nodo no encontrado"
            )
        
        # Generar mensaje de bienvenida
        welcome_message = self._generate_node_message(first_node, ai_overview)
        
        return JourneyDecision(
            action=JourneyAction.START_JOURNEY,
            current_node_id=None,
            target_node_id=first_node_id,
            response_message=welcome_message,
            confidence=1.0,
            reasoning="Iniciando journey desde primer nodo"
        )
    
    async def _handle_node_completion(
        self,
        current_node: Dict[str, Any],
        ai_overview: Dict[str, Any],
        collected_data: Dict[str, Any],
        reasoning: str
    ) -> JourneyDecision:
        """Maneja cuando un nodo está completado"""
        
        self.stats["nodes_completed"] += 1
        current_node_id = current_node["node_id"]
        
        # Evaluar branches para siguiente paso
        branches = current_node.get("branches", [])
        
        if not branches:
            # Nodo terminal - journey completado
            return JourneyDecision(
                action=JourneyAction.END_JOURNEY,
                current_node_id=current_node_id,
                target_node_id=None,
                response_message="¡Felicitaciones! Has completado el proceso. Un asesor se contactará contigo pronto para finalizar tu matrícula.",
                confidence=1.0,
                reasoning="Journey completado - nodo terminal",
                collected_data=collected_data
            )
        
        # Evaluar qué branch tomar
        selected_branch = self.branch_evaluator.evaluate_branches(
            branches,
            ai_overview["user_progress"],
            ai_overview["conversation_context"]["chat_summary"],
            ai_overview["conversation_context"]["current_state"]
        )
        
        if selected_branch:
            self.stats["branches_taken"] += 1
            target_node_id = selected_branch["target_node_id"]
            target_node = self._find_node_in_structure(ai_overview["journey_structure"], target_node_id)
            
            if target_node:
                next_message = self._generate_node_message(target_node, ai_overview)
                
                return JourneyDecision(
                    action=JourneyAction.MOVE_TO_NEXT,
                    current_node_id=current_node_id,
                    target_node_id=target_node_id,
                    response_message=next_message,
                    confidence=0.9,
                    reasoning=f"Nodo completado, tomando branch: {selected_branch['condition_label']}",
                    branch_taken=selected_branch,
                    collected_data=collected_data
                )
        
        # Si no se puede determinar branch, tomar el primero por defecto
        if branches:
            default_branch = branches[0]
            target_node_id = default_branch["target_node_id"]
            target_node = self._find_node_in_structure(ai_overview["journey_structure"], target_node_id)
            
            if target_node:
                next_message = self._generate_node_message(target_node, ai_overview)
                
                return JourneyDecision(
                    action=JourneyAction.MOVE_TO_NEXT,
                    current_node_id=current_node_id,
                    target_node_id=target_node_id,
                    response_message=next_message,
                    confidence=0.6,
                    reasoning="Nodo completado, tomando branch por defecto",
                    branch_taken=default_branch,
                    collected_data=collected_data
                )
        
        # Fallback
        return JourneyDecision(
            action=JourneyAction.REQUEST_HUMAN,
            current_node_id=current_node_id,
            target_node_id=None,
            response_message="He completado esta etapa contigo. Un asesor tomará el caso desde aquí.",
            confidence=0.7,
            reasoning="Nodo completado pero no se pudo determinar siguiente paso",
            collected_data=collected_data
        )
    
    async def _handle_node_continuation(
        self,
        current_node: Dict[str, Any],
        ai_overview: Dict[str, Any],
        confidence: float,
        reasoning: str
    ) -> JourneyDecision:
        """Maneja cuando un nodo necesita continuar"""
        
        current_node_id = current_node["node_id"]
        
        # Generar mensaje de continuación o aclaración
        if confidence < 0.3:
            # Usuario no ha interactuado suficiente
            continuation_message = self._generate_node_message(current_node, ai_overview)
        else:
            # Usuario ha respondido parcialmente, pedir aclaración
            continuation_message = self._generate_clarification_message(current_node, ai_overview)
        
        return JourneyDecision(
            action=JourneyAction.CONTINUE_NODE,
            current_node_id=current_node_id,
            target_node_id=current_node_id,
            response_message=continuation_message,
            confidence=confidence,
            reasoning=reasoning,
            next_evaluation_needed=True
        )
    
    def _generate_node_message(self, node: Dict[str, Any], ai_overview: Dict[str, Any]) -> str:
        """Genera mensaje usando el prompt del nodo y datos del usuario"""
        
        prompt_template = node.get("prompt", "")
        
        if not prompt_template:
            return "Continúemos con el siguiente paso de tu proceso."
        
        # Preparar variables para el template
        variables = {
            "nombre": ai_overview["user_progress"].get("user_data", {}).get("nombre", ""),
            "journey_name": ai_overview["metadata"]["journey_name"],
            "step_name": node.get("name", ""),
            **ai_overview["user_progress"].get("user_data", {}),
            **ai_overview["conversation_context"]["current_state"].get("key_data_collected", {})
        }
        
        # Procesar template
        processed_message = self.template_engine.process_template(prompt_template, variables)
        
        return processed_message
    
    def _generate_clarification_message(self, node: Dict[str, Any], ai_overview: Dict[str, Any]) -> str:
        """Genera mensaje de aclaración cuando el usuario no ha completado el nodo"""
        
        node_name = node.get("name", "paso actual")
        
        clarifications = [
            f"Para continuar con {node_name}, necesito más información. ¿Puedes ser más específico?",
            f"Entiendo tu respuesta, pero necesito algunos detalles adicionales para {node_name}.",
            f"Me ayudarías si pudieras darme más información sobre {node_name}.",
            "¿Podrías darme más detalles para poder ayudarte mejor?"
        ]
        
        # Rotar mensajes para evitar repetición
        rotation_index = self.stats["decisions_made"] % len(clarifications)
        return clarifications[rotation_index]
    
    async def update_journey_progress(
        self,
        user_id: int,
        journey_id: int,
        decision: JourneyDecision
    ) -> bool:
        """Actualiza el progreso del journey basado en la decisión tomada"""
        
        try:
            url = f"{self.ai_api_base_url}/api/journey/{journey_id}/user/{user_id}/update-progress"
            
            # Preparar payload según la acción
            payload = {"action": self._map_action_to_update(decision)}
            
            if decision.target_node_id:
                payload["target_node_id"] = decision.target_node_id
            
            if decision.current_node_id:
                payload["previous_node_id"] = decision.current_node_id
                
            if decision.action == JourneyAction.MOVE_TO_NEXT:
                payload["mark_previous_complete"] = True
                
            if decision.branch_taken:
                payload["branch_taken_id"] = decision.branch_taken.get("branch_id")
            
            if decision.collected_data:
                payload["collected_data"] = decision.collected_data
            
            payload["increment_interactions"] = True
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                
                if response.status_code == 200:
                    # Limpiar cache para forzar recarga
                    cache_key = f"{user_id}_{journey_id}"
                    if cache_key in self._journey_cache:
                        del self._journey_cache[cache_key]
                    
                    return True
                else:
                    logger.error(f"Error actualizando progreso: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error en update_journey_progress: {e}")
            return False
    
    def _map_action_to_update(self, decision: JourneyDecision) -> str:
        """Mapea acción del decision al formato esperado por la API"""
        
        mapping = {
            JourneyAction.START_JOURNEY: "move_to_node",
            JourneyAction.MOVE_TO_NEXT: "move_to_node",
            JourneyAction.CONTINUE_NODE: "update_context",
            JourneyAction.COMPLETE_NODE: "move_to_node",
            JourneyAction.END_JOURNEY: "complete_journey",
            JourneyAction.REQUEST_HUMAN: "request_human"
        }
        
        return mapping.get(decision.action, "update_context")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del journey engine"""
        return {
            **self.stats,
            "timestamp": datetime.now().isoformat(),
            "cache_size": len(self._journey_cache)
        }

# ===== INSTANCIA GLOBAL Y FUNCIONES DE CONVENIENCIA =====

# Instancia global del journey engine
journey_engine_manager = JourneyEngineManager()

# Funciones para uso desde el orquestador
async def process_journey_message(
    user_id: int,
    journey_id: int,
    message: str,
    classification: Dict[str, Any],
    conversation_state: Dict[str, Any]
) -> JourneyDecision:
    """
    Función principal para procesar mensajes del journey desde el orquestador
    
    Args:
        user_id: ID del usuario
        journey_id: ID del journey
        message: Último mensaje del usuario
        classification: Resultado del classifier
        conversation_state: Estado actual de la conversación
        
    Returns:
        JourneyDecision con la acción a tomar
    """
    return await journey_engine_manager.make_journey_decision(
        user_id, journey_id, message, classification, conversation_state
    )

async def update_user_journey_progress(
    user_id: int,
    journey_id: int,
    decision: JourneyDecision
) -> bool:
    """Actualiza el progreso del usuario en el journey"""
    return await journey_engine_manager.update_journey_progress(
        user_id, journey_id, decision
    )

async def get_journey_engine_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del journey engine"""
    return journey_engine_manager.get_stats()

def configure_journey_engine(ai_api_base_url: str):
    """Configura la URL base para la API AI"""
    global journey_engine_manager
    journey_engine_manager.ai_api_base_url = ai_api_base_url
    logger.info(f"Journey engine configurado con URL: {ai_api_base_url}")

# ===== UTILIDADES PARA TESTING =====

async def test_journey_engine():
    """Pruebas básicas del journey engine"""
    print("🚀 Iniciando pruebas del journey engine...")
    
    # Test de template engine
    template_engine = MessageTemplateEngine()
    test_template = "Hola {nombre}, tu carrera de interés es {carrera}. ¿Tienes {experiencia_anos} años de experiencia?"
    test_variables = {
        "nombre": "Juan",
        "carrera": "Enfermería",
        "experiencia_anos": 2
    }
    
    processed = template_engine.process_template(test_template, test_variables)
    print(f"✅ Template procesado: {processed}")
    
    # Test de node evaluator
    evaluator = NodeEvaluator()
    test_node = {
        "node_id": 1,
        "name": "Bienvenida",
        "ai_metadata": {
            "completion_rules": {
                "type": "any_of",
                "conditions": [
                    {"field": "user_response", "contains": ["sí", "si", "claro"]}
                ]
            }
        }
    }
    
    test_chat = {
        "analysis": {
            "last_user_message": "Sí, me interesa mucho"
        }
    }
    
    is_completed, confidence, reasoning, data = evaluator.evaluate_node_completion(
        test_node, {}, test_chat, {}
    )
    
    print(f"✅ Evaluación de nodo: completado={is_completed}, confianza={confidence:.2f}")
    print(f"   Razón: {reasoning}")
    
    # Test de branch evaluator
    branch_evaluator = BranchEvaluator()
    test_branches = [
        {
            "condition_label": "sí tiene experiencia",
            "expected_keywords": ["sí", "experiencia", "trabajé"],
            "target_node_id": 2
        },
        {
            "condition_label": "no tiene experiencia",
            "expected_keywords": ["no", "nunca", "sin experiencia"],
            "target_node_id": 3
        }
    ]
    
    selected_branch = branch_evaluator.evaluate_branches(
        test_branches, {}, test_chat, {}
    )
    
    if selected_branch:
        print(f"✅ Branch seleccionado: {selected_branch['condition_label']}")
    else:
        print("❌ No se seleccionó ningún branch")
    
    # Test de estadísticas
    stats = await get_journey_engine_stats()
    print(f"📊 Estadísticas: {stats}")
    
    print("🎉 Pruebas completadas exitosamente.")

if __name__ == "__main__":
    # Ejecutar pruebas si se ejecuta directamente
    asyncio.run(test_journey_engine())