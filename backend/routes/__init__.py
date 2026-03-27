# backend/routes/__init__.py
from .auth import auth_bp
from .students import students_bp
from .api import api_bp
from .chatbot_routes import chatbot_bp
from .admin import admin_bp

__all__ = ['auth_bp', 'students_bp', 'api_bp', 'chatbot_bp', 'admin_bp']
