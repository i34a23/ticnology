from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from sqlalchemy import text  # ⟵ para ping-db
import os
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()

from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = b'_5#y2L"F4Q8z\n\xec]/'
    app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

    # Conexión a Supabase (Postgres)
    # app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres.fnbfwklafldrjamohbid:Nd9lVJjEoyzu6aUM@aws-1-us-east-2.pooler.supabase.com:6543/postgres"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {"sslmode": "require"}
    }

    db.init_app(app)
    migrate.init_app(app, db)   # ⟵ IMPORTANTE: habilita Alembic/Flask-Migrate
    csrf.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'authentication.login'


    CORS(app)


    # IMPORTA MODELOS para que Alembic los vea
    from .models import User
    
    # IMPORTAR MODELOS DEL CHATBOT - AGREGADO
    from .ticnochatbot.models import (
        AgentCredentials,
        LeadQueue,
        ConversationState,
        AgentMetrics,
        MessageTemplate
    )
    
    # IMPORTAR MODELOS DE LEADJOURNEY Y USUARIOS (si no están ya importados)
    from .leadjourney.models import LeadJourney, Nodo, NodoNextStep
    from .usuarios.models import Cliente, Usuario, ChatHistory
    from .ticnochatbot.models import HitoJourney

    @login_manager.user_loader
    def load_user(user_id):
        # Si tu PK es int, ok; si es UUID usa db.session.get(User, user_id)
        return User.query.get(int(user_id))

    # Blueprints
    from .dashboards import dashboards
    from .apps import apps
    from .ecommerce import ecommerce
    from .crypto import crypto
    from .email import email
    from .invoices import invoices
    from .projects import projects
    from .tasks import tasks
    from .contacts import contacts
    from .blogs import blogs
    from .jobs import jobs
    from .authentication import authentication
    from .utility import utility
    from .components import components
    from .layouts import layouts
    
    from .leadjourney import leadjourney
    from .leadjourney import ai_bp
    from .usuarios import usuarios
    from .ticnochatbot import chatbot

    app.register_blueprint(dashboards, url_prefix="/")
    app.register_blueprint(apps, url_prefix="/")
    app.register_blueprint(ecommerce, url_prefix="/")
    app.register_blueprint(crypto, url_prefix="/")
    app.register_blueprint(email, url_prefix="/")
    app.register_blueprint(invoices, url_prefix="/")
    app.register_blueprint(projects, url_prefix="/")
    app.register_blueprint(tasks, url_prefix="/")
    app.register_blueprint(contacts, url_prefix="/")
    app.register_blueprint(blogs, url_prefix="/")
    app.register_blueprint(jobs, url_prefix="/")
    app.register_blueprint(authentication, url_prefix="/")
    app.register_blueprint(utility, url_prefix="/")
    app.register_blueprint(components, url_prefix="/")
    app.register_blueprint(layouts, url_prefix="/")
    app.register_blueprint(leadjourney, url_prefix="/leadjourney")
    app.register_blueprint(ai_bp, url_prefix="/ai")
    app.register_blueprint(usuarios, url_prefix="/usuarios")
    app.register_blueprint(chatbot, url_prefix="/chatbot")
    

    csrf.exempt(chatbot)
    return app