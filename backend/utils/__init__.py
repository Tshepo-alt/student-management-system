# backend/utils/__init__.py
"""
Utilities package for helper functions and chatbot
"""

try:
    from .chatbot import StudentManagementChatbot
except ImportError:
    StudentManagementChatbot = None

__all__ = ['StudentManagementChatbot']
