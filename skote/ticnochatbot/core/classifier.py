"""
Clasificador de Intenciones y Entidades
Determina la intención del usuario y extrae entidades relevantes
Ubicación: /ticnochatbot/core/classifier.py
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntentType(Enum):
    """Tipos de intenciones que puede detectar el sistema"""
    GREETING = "greeting"
    GOODBYE = "goodbye" 
    HELP = "help"
    ASK_PRICE = "ask_price"
    ASK_CAREER = "ask_career"
    ASK_SCHEDULE = "ask_schedule"
    ASK_REQUIREMENTS = "ask_requirements"
    ASK_CONTACT = "ask_contact"
    ASK_ENROLLMENT = "ask_enrollment"
    COMPLAIN = "complain"
    GENERAL = "general"
    UNKNOWN = "unknown"

@dataclass
class Entity:
    """Estructura para entidades extraídas del mensaje"""
    type: str
    value: str
    confidence: float
    start_pos: int = 0
    end_pos: int = 0

@dataclass
class Classification:
    """Resultado de la clasificación de un mensaje"""
    intent: IntentType
    confidence: float
    entities: List[Entity]
    method: str
    timestamp: datetime
    raw_message: str

class KeywordClassifier:
    """Clasificador basado en palabras clave - rápido y eficiente"""
    
    def __init__(self):
        # Diccionario de palabras clave para cada intención
        self.intent_keywords = {
            IntentType.GREETING: [
                'hola', 'hello', 'hi', 'hey', 'buenos días', 'buenas tardes', 
                'buenas noches', 'saludos', 'qué tal', 'cómo estás'
            ],
            IntentType.GOODBYE: [
                'chao', 'adiós', 'bye', 'hasta luego', 'nos vemos', 
                'gracias', 'muchas gracias', 'perfecto gracias'
            ],
            IntentType.HELP: [
                'ayuda', 'help', 'información', 'info', 'puedes ayudar', 
                'necesito saber', 'quiero saber', 'me puedes decir'
            ],
            IntentType.ASK_PRICE: [
                'precio', 'costo', 'cuánto cuesta', 'valor', 'arancel', 
                'matrícula', 'mensualidad', 'financiamiento'
            ],
            IntentType.ASK_CAREER: [
                'carrera', 'carreras', 'programa', 'curso', 'especialidad', 
                'técnico', 'enfermería', 'parvularia', 'administración'
            ],
            IntentType.ASK_SCHEDULE: [
                'horario', 'horarios', 'clases', 'cuando', 'tiempo', 
                'duración', 'vespertino', 'diurno', 'días'
            ],
            IntentType.ASK_REQUIREMENTS: [
                'requisitos', 'documentos', 'necesito', 'qué necesito', 
                'papeles', 'certificados', 'licencia'
            ],
            IntentType.ASK_CONTACT: [
                'contacto', 'teléfono', 'dirección', 'dónde', 'ubicación', 
                'mail', 'correo', 'email'
            ],
            IntentType.ASK_ENROLLMENT: [
                'matrícula', 'inscripción', 'postular', 'inscribir', 
                'proceso', 'admisión', 'matricular'
            ],
            IntentType.COMPLAIN: [
                'problema', 'queja', 'malo', 'terrible', 'disgusto', 
                'molesto', 'enojado', 'reclamo'
            ]
        }
        
        # Patrones regex para entidades
        self.entity_patterns = {
            'career': re.compile(r'\b(enfermería|parvularia|administración|técnico|contabilidad)\b', re.IGNORECASE),
            'phone': re.compile(r'(\+?56\s?)?[0-9]\s?[0-9]{4}\s?[0-9]{4}'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'time': re.compile(r'\b(mañana|tarde|noche|vespertino|diurno)\b', re.IGNORECASE),
        }
        
        # Estadísticas de uso
        self.classification_stats = {
            "total_classifications": 0,
            "intent_counts": {intent.value: 0 for intent in IntentType},
            "method_counts": {"keyword": 0, "llm": 0},
            "average_confidence": 0.0
        }
    
    def classify(self, message: str, context: Optional[Dict] = None) -> Classification:
        """
        Clasifica un mensaje usando palabras clave
        
        Args:
            message: Texto del mensaje
            context: Contexto de la conversación (opcional)
            
        Returns:
            Classification con intención, confianza y entidades
        """
        message_lower = message.lower().strip()
        
        # Buscar intenciones por palabras clave
        intent_scores = {}
        
        for intent, keywords in self.intent_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in message_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                # Calcular confianza basada en coincidencias
                confidence = min(0.95, 0.60 + (score * 0.10))
                intent_scores[intent] = {
                    'confidence': confidence,
                    'matches': matched_keywords
                }
        
        # Seleccionar la intención con mayor confianza
        if intent_scores:
            best_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x]['confidence'])
            confidence = intent_scores[best_intent]['confidence']
        else:
            best_intent = IntentType.GENERAL if message_lower else IntentType.UNKNOWN
            confidence = 0.50 if message_lower else 0.10
        
        # Extraer entidades
        entities = self._extract_entities(message)
        
        # Ajustar confianza basada en contexto
        if context:
            confidence = self._adjust_confidence_with_context(
                best_intent, confidence, context
            )
        
        # Crear resultado de clasificación
        classification = Classification(
            intent=best_intent,
            confidence=confidence,
            entities=entities,
            method="keyword",
            timestamp=datetime.now(),
            raw_message=message
        )
        
        # Actualizar estadísticas
        self._update_stats(classification)
        
        logger.info(f"Mensaje clasificado: '{message[:50]}...' → {best_intent.value} (conf: {confidence:.2f})")
        
        return classification
    
    def _extract_entities(self, message: str) -> List[Entity]:
        """Extrae entidades del mensaje usando regex"""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = pattern.finditer(message)
            
            for match in matches:
                entity = Entity(
                    type=entity_type,
                    value=match.group(),
                    confidence=0.90,
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                entities.append(entity)
        
        return entities
    
    def _adjust_confidence_with_context(self, intent: IntentType, confidence: float, context: Dict) -> float:
        """Ajusta la confianza basada en el contexto de la conversación"""
        
        # Si el usuario ya saludó, reducir confianza de otro saludo
        if intent == IntentType.GREETING and context.get('last_intent') == 'greeting':
            confidence *= 0.7
        
        # Si está en medio de una consulta, reducir despedidas
        if intent == IntentType.GOODBYE and context.get('current_step'):
            confidence *= 0.8
        
        # Si ya preguntó por precios, aumentar confianza en preguntas relacionadas
        if intent == IntentType.ASK_CAREER and context.get('last_intent') == 'ask_price':
            confidence = min(0.95, confidence * 1.2)
        
        return confidence
    
    def _update_stats(self, classification: Classification):
        """Actualiza estadísticas de clasificación"""
        self.classification_stats["total_classifications"] += 1
        self.classification_stats["intent_counts"][classification.intent.value] += 1
        self.classification_stats["method_counts"][classification.method] += 1
        
        # Actualizar confianza promedio
        total = self.classification_stats["total_classifications"]
        current_avg = self.classification_stats["average_confidence"]
        new_avg = ((current_avg * (total - 1)) + classification.confidence) / total
        self.classification_stats["average_confidence"] = new_avg
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de clasificación"""
        return self.classification_stats.copy()

class LLMClassifier:
    """Clasificador basado en LLM - más preciso pero más lento y costoso"""
    
    def __init__(self):
        self.enabled = False  # Se habilitará cuando tengamos LLM configurado
        self.model_name = "gpt-3.5-turbo"  # Por defecto
        self.classification_stats = {
            "total_classifications": 0,
            "intent_counts": {intent.value: 0 for intent in IntentType},
            "method_counts": {"keyword": 0, "llm": 0},
            "average_confidence": 0.0
        }
    
    def classify(self, message: str, context: Optional[Dict] = None) -> Classification:
        """
        Clasifica usando LLM (implementación futura)
        Por ahora retorna clasificación básica
        """
        if not self.enabled:
            logger.warning("LLM Classifier no está habilitado, usando clasificación básica")
            
            return Classification(
                intent=IntentType.GENERAL,
                confidence=0.75,
                entities=[],
                method="llm_fallback",
                timestamp=datetime.now(),
                raw_message=message
            )
        
        # TODO: Implementar llamada real al LLM
        # prompt = self._build_classification_prompt(message, context)
        # result = llm_client.complete(prompt)
        # return self._parse_llm_response(result, message)
        
        pass
    
    def _build_classification_prompt(self, message: str, context: Optional[Dict]) -> str:
        """Construye el prompt para clasificación con LLM"""
        intents_list = [intent.value for intent in IntentType]
        
        prompt = f"""
        Clasifica el siguiente mensaje de un usuario interesado en CFT CENCO.
        
        Mensaje: "{message}"
        
        Intenciones posibles: {', '.join(intents_list)}
        
        Responde en formato JSON:
        {{
            "intent": "nombre_de_intencion",
            "confidence": 0.95,
            "entities": [
                {{"type": "career", "value": "enfermería", "confidence": 0.90}}
            ],
            "reasoning": "breve explicación"
        }}
        """
        
        if context:
            prompt += f"\n\nContexto de la conversación: {context}"
        
        return prompt


class ClassificationManager:
    """Gestor que coordina los diferentes clasificadores"""
    
    def __init__(self):
        self.keyword_classifier = KeywordClassifier()
        self.llm_classifier = LLMClassifier()
        self.use_llm_threshold = 0.70  # Si confianza keyword < 0.70, usar LLM
        self.combined_stats = {
            "total_classifications": 0,
            "keyword_used": 0,
            "llm_used": 0,
            "combined_confidence": 0.0
        }
    
    async def classify(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Clasifica un mensaje usando la estrategia híbrida:
        1. Intenta con keywords primero (rápido)
        2. Si confianza es baja, usa LLM (preciso)
        """
        
        # Paso 1: Clasificación con keywords
        keyword_result = self.keyword_classifier.classify(message, context)
        
        # Paso 2: Decidir si usar LLM
        final_result = keyword_result
        
        if keyword_result.confidence < self.use_llm_threshold and self.llm_classifier.enabled:
            logger.info(f"Confianza keyword baja ({keyword_result.confidence:.2f}), usando LLM")
            llm_result = self.llm_classifier.classify(message, context)
            
            # Usar el resultado con mayor confianza
            if llm_result.confidence > keyword_result.confidence:
                final_result = llm_result
                self.combined_stats["llm_used"] += 1
            else:
                self.combined_stats["keyword_used"] += 1
        else:
            self.combined_stats["keyword_used"] += 1
        
        # Actualizar estadísticas combinadas
        self.combined_stats["total_classifications"] += 1
        
        # Convertir resultado a diccionario para la API
        return {
            "intent": final_result.intent.value,
            "confidence": final_result.confidence,
            "entities": [
                {
                    "type": entity.type,
                    "value": entity.value,
                    "confidence": entity.confidence,
                    "start_pos": entity.start_pos,
                    "end_pos": entity.end_pos
                }
                for entity in final_result.entities
            ],
            "method": final_result.method,
            "timestamp": final_result.timestamp.isoformat(),
            "raw_message": final_result.raw_message
        }
    
    def get_combined_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas combinadas de ambos clasificadores"""
        keyword_stats = self.keyword_classifier.get_stats()
        
        return {
            "total_classifications": self.combined_stats["total_classifications"],
            "method_usage": {
                "keyword": self.combined_stats["keyword_used"],
                "llm": self.combined_stats["llm_used"]
            },
            "keyword_classifier": keyword_stats,
            "llm_enabled": self.llm_classifier.enabled,
            "use_llm_threshold": self.use_llm_threshold,
            "timestamp": datetime.now().isoformat()
        }
    
    def set_llm_threshold(self, threshold: float):
        """Configura el umbral para usar LLM"""
        if 0.0 <= threshold <= 1.0:
            self.use_llm_threshold = threshold
            logger.info(f"Umbral LLM actualizado a {threshold}")
        else:
            logger.error("El umbral debe estar entre 0.0 y 1.0")
    
    def enable_llm_classifier(self, model_name: str = "gpt-3.5-turbo"):
        """Habilita el clasificador LLM"""
        self.llm_classifier.enabled = True
        self.llm_classifier.model_name = model_name
        logger.info(f"LLM Classifier habilitado con modelo {model_name}")
    
    def disable_llm_classifier(self):
        """Deshabilita el clasificador LLM"""
        self.llm_classifier.enabled = False
        logger.info("LLM Classifier deshabilitado")

# ===== INSTANCIA GLOBAL Y FUNCIONES DE CONVENIENCIA =====

# Instancia global del gestor de clasificación
classification_manager = ClassificationManager()

# Funciones para uso desde la API y orquestador
async def classify_message(message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Función principal para clasificar mensajes desde otros módulos
    
    Args:
        message: Texto del mensaje a clasificar
        context: Contexto opcional de la conversación
        
    Returns:
        Diccionario con la clasificación completa
    """
    return await classification_manager.classify(message, context)

async def get_classification_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de clasificación"""
    return classification_manager.get_combined_stats()

def configure_llm_classifier(enabled: bool = True, model: str = "gpt-3.5-turbo", threshold: float = 0.70):
    """
    Configura el clasificador LLM
    
    Args:
        enabled: Habilitar/deshabilitar LLM
        model: Modelo a usar
        threshold: Umbral de confianza para activar LLM
    """
    if enabled:
        classification_manager.enable_llm_classifier(model)
    else:
        classification_manager.disable_llm_classifier()
    
    classification_manager.set_llm_threshold(threshold)

def get_available_intents() -> List[str]:
    """Obtiene lista de intenciones disponibles"""
    return [intent.value for intent in IntentType]

def get_intent_keywords(intent: str) -> List[str]:
    """Obtiene palabras clave para una intención específica"""
    try:
        intent_enum = IntentType(intent)
        return classification_manager.keyword_classifier.intent_keywords.get(intent_enum, [])
    except ValueError:
        return []

# ===== UTILIDADES PARA TESTING =====

def test_classification_accuracy(test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Prueba la precisión del clasificador con casos de test
    
    Args:
        test_cases: Lista de casos con 'message' e 'expected_intent'
        
    Returns:
        Estadísticas de precisión
    """
    correct = 0
    total = len(test_cases)
    results = []
    
    for case in test_cases:
        message = case['message']
        expected = case['expected_intent']
        
        # Clasificar usando solo keywords para testing
        result = classification_manager.keyword_classifier.classify(message)
        predicted = result.intent.value
        
        is_correct = predicted == expected
        correct += is_correct
        
        results.append({
            'message': message,
            'expected': expected,
            'predicted': predicted,
            'confidence': result.confidence,
            'correct': is_correct
        })
    
    accuracy = correct / total if total > 0 else 0
    
    return {
        'accuracy': accuracy,
        'correct': correct,
        'total': total,
        'results': results
    }

if __name__ == "__main__":
    # Casos de test para validar el clasificador
    async def test_classifier():
        """Pruebas básicas del clasificador"""
        print("🚀 Iniciando pruebas del clasificador...")
        
        test_cases = [
            {"message": "Hola, buenos días", "expected_intent": "greeting"},
            {"message": "¿Cuánto cuesta la carrera de enfermería?", "expected_intent": "ask_price"},
            {"message": "Qué carreras tienen disponibles", "expected_intent": "ask_career"},
            {"message": "Necesito ayuda con información", "expected_intent": "help"},
            {"message": "Gracias, hasta luego", "expected_intent": "goodbye"},
            {"message": "Me pueden dar horarios de clases", "expected_intent": "ask_schedule"},
            {"message": "Qué documentos necesito para matricularme", "expected_intent": "ask_requirements"}
        ]
        
        print("🔍 Clasificando mensajes de prueba...")
        for case in test_cases:
            result = await classify_message(case["message"])
            print(f"✅ '{case['message'][:40]}...' → {result['intent']} (conf: {result['confidence']:.2f})")
        
        # Probar precisión
        accuracy_results = test_classification_accuracy(test_cases)
        print(f"\n📊 Precisión del clasificador: {accuracy_results['accuracy']:.2%}")
        
        # Obtener estadísticas
        stats = await get_classification_stats()
        print(f"📈 Estadísticas: {stats}")
        
        print("🎉 Pruebas completadas exitosamente.")
    
    import asyncio
    asyncio.run(test_classifier())