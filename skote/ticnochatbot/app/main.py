from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

db = SQLAlchemy()

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {"sslmode": "require"}
    }

    db.init_app(app)

    # Importa solo los modelos mínimos
    from . import models  

    # Blueprints del chatbot
    from .routes import chatbot_bp
    app.register_blueprint(chatbot_bp, url_prefix="/chat")

    return app

app = create_app()
