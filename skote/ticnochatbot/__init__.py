# skote/ticnochatbot/__init__.py

from flask import Blueprint

chatbot = Blueprint("chatbot", __name__, template_folder="../templates")

# Importar routes
from . import routes
from . import routes_integration 