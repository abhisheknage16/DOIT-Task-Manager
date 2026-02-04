# Import all controllers for easy access
from controllers import auth_controller
from controllers import task_controller
from controllers import project_controller
from controllers import sprint_controller
from controllers import dashboard_controller
from controllers import system_dashboard_controller
from controllers import profile_controller
from controllers import user_controller
from controllers import chat_controller
from controllers import member_controller
from controllers import git_controller
from controllers import team_chat_controller
from controllers import data_viz_controller

__all__ = [
    'auth_controller',
    'task_controller',
    'project_controller',
    'sprint_controller',
    'dashboard_controller',
    'system_dashboard_controller',
    'profile_controller',
    'user_controller',
    'chat_controller',
    'member_controller',
    'git_controller',
    'team_chat_controller',
    'data_viz_controller'
]
