# routers/__init__.py
"""
API Routers Package
Import all routers for easy access in main.py
"""

from .auth_router import router as auth_router
from .project_router import router as project_router
from .member_router import router as member_router
from .task_router import router as task_router
from .sprint_router import router as sprint_router
from .dashboard_router import router as dashboard_router
from .system_dashboard_router import router as system_dashboard_router
from .profile_router import router as profile_router
from .user_router import router as user_router
from .chat_router import router as chat_router
from .team_chat_router import router as team_chat_router
from .data_viz_router import router as data_viz_router
from .ai_assistant_router import router as ai_assistant_router  # ← NEW: AI Assistant


__all__ = [
    "auth_router",
    "project_router",
    "member_router",
    "task_router",
    "sprint_router",
    "dashboard_router",
    "system_dashboard_router",
    "profile_router",
    "user_router",
    "chat_router",
    "team_chat_router",
    "data_viz_router",
    "ai_assistant_router",  # ← NEW
]