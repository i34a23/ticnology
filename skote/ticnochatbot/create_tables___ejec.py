#!/usr/bin/env python
# create_tables.py - Script para crear las migraciones y tablas del chatbot

from skote import create_app, db
import subprocess
import sys

def create_migrations():
    """Crea y ejecuta las migraciones para las nuevas tablas"""
    
    app = create_app()
    
    with app.app_context():
        print("=== Creando Migraciones para Chatbot ===\n")
        
        # Importar modelos para que Alembic los detecte
        from skote.ticnochatbot.models import (
            AgentCredentials, 
            LeadQueue, 
            ConversationState,
            AgentMetrics,
            MessageTemplate
        )
        
        try:
            # Crear migración
            print("1. Generando archivo de migración...")
            result = subprocess.run(
                ["flask", "db", "migrate", "-m", "Add chatbot tables"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Error en migrate: {result.stderr}")
                if "No changes" in result.stderr or "No changes" in result.stdout:
                    print("No hay cambios pendientes en la base de datos")
                    return False
            else:
                print(f"✓ Migración creada: {result.stdout}")
            
            # Aplicar migración
            print("\n2. Aplicando migración a la base de datos...")
            result = subprocess.run(
                ["flask", "db", "upgrade"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Error en upgrade: {result.stderr}")
                return False
            else:
                print("✓ Migración aplicada exitosamente")
            
            # Verificar tablas
            print("\n3. Verificando tablas creadas...")
            inspector = db.inspect(db.engine)
            expected_tables = [
                'agent_credentials',
                'lead_queue', 
                'conversation_states',
                'agent_metrics',
                'message_templates'
            ]
            
            existing_tables = inspector.get_table_names()
            for table in expected_tables:
                if table in existing_tables:
                    print(f"✓ Tabla '{table}' creada correctamente")
                else:
                    print(f"✗ Tabla '{table}' no encontrada")
            
            print("\n=== Migraciones Completadas ===")
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            return False

def create_initial_templates():
    """Crea templates de mensajes iniciales"""
    app = create_app()
    
    with app.app_context():
        from skote.ticnochatbot.models import MessageTemplate
        
        print("\n=== Creando Templates Iniciales ===")
        
        templates = [
            {
                'key': 'welcome',
                'category': 'greeting',
                'template': "¡Hola {nombre}! Soy {agent_name} de {company} 📚 Te escribo por tu interés en **{carrera}**. ¡Excelente elección para tu futuro profesional! ¿Estás listo para comenzar con el proceso de matrícula?",
                'variables': ['nombre', 'agent_name', 'company', 'carrera']
            },
            {
                'key': 'objection_price',
                'category': 'objection',
                'template': "Entiendo tu preocupación por el costo. Lo bueno es que tenemos planes de pago flexibles y puedes dividirlo hasta en {cuotas} cuotas. Además, la inversión en tu educación siempre vale la pena 💪",
                'variables': ['cuotas']
            },
            {
                'key': 'objection_time',
                'category': 'objection',
                'template': "Te comprendo perfectamente. Por eso tenemos el Plan Especial que dura solo 14 meses si tienes experiencia laboral. ¿Te gustaría saber si calificas?",
                'variables': []
            },
            {
                'key': 'documents_request',
                'category': 'journey',
                'template': "Para continuar con tu matrícula, necesito que me envíes:\n{documentos}\n\n¿Tienes estos documentos a mano?",
                'variables': ['documentos']
            }
        ]
        
        for tmpl in templates:
            existing = MessageTemplate.query.filter_by(key=tmpl['key']).first()
            if not existing:
                new_template = MessageTemplate(**tmpl)
                db.session.add(new_template)
                print(f"✓ Template '{tmpl['key']}' creado")
            else:
                print(f"- Template '{tmpl['key']}' ya existe")
        
        db.session.commit()
        print("=== Templates Creados ===")

if __name__ == "__main__":
    success = create_migrations()
    
    if success and len(sys.argv) > 1 and sys.argv[1] == "--with-templates":
        create_initial_templates()