from flask import Blueprint

ai_bp = Blueprint("ai_bp", __name__, template_folder="../templates")
from . import routes_ai
leadjourney = Blueprint("leadjourney", __name__, template_folder="../templates")
from . import routes



