# backend-2/utils/langgraph_agent_automation.py
"""
LangGraph Agent Automation Helpers
Shared utilities for task/project/sprint resolution and access control
"""

import logging
import re
from typing import Dict, Any, Optional
from database import db
from models.user import User
from bson import ObjectId

logger = logging.getLogger(__name__)


# ─── Role-Based Access Control ────────────────────────────────────────────


def check_automation_permission(
    user_id: str, action: str
) -> tuple[bool, Optional[str]]:
    """
    Check if user has permission to execute an action.
    Returns (allowed, error_message)
    """
    try:
        user = User.find_by_id(user_id)
        if not user:
            return False, "User not found"

        user_role = user.get("role", "member").lower()

        # Actions only admins can perform
        admin_only_actions = [
            "create_sprint",
            "start_sprint",
            "complete_sprint",
            "create_project",
        ]

        # Check admin-only actions
        if action in admin_only_actions and user_role not in ["admin", "super-admin"]:
            return False, f"Only Admin users can {action.replace('_', ' ')}"

        # Members can create tasks, assign tasks, update tasks
        return True, None

    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        return False, f"Permission check failed: {str(e)}"


# ─── Project Resolution ────────────────────────────────────────────────────


def resolve_project_id(
    user_id: str,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve project_name to project_id if needed.
    Returns project_id or None if not found.
    """
    if project_id:
        try:
            ObjectId(project_id)
            return project_id
        except Exception:
            pass

    if not project_name:
        return None

    try:
        # Normalize input
        def normalize(name):
            return name.lower().replace(" project", "").strip()

        norm_input = normalize(project_name)

        # 1. Try exact match (case-insensitive)
        project = db.projects.find_one(
            {
                "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
                "$expr": {
                    "$eq": [{"$trim": {"input": {"$toLower": "$name"}}}, norm_input]
                },
            }
        )

        if project:
            return str(project["_id"])

        # 2. Try partial/substring match
        projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )

        for p in projects:
            pname = normalize(p.get("name", ""))
            if norm_input in pname or pname in norm_input:
                return str(p["_id"])

        # 3. Not found
        available = [p.get("name", "") for p in projects]
        logger.warning(
            f"Project '{project_name}' not found for user {user_id}. Available: {available}"
        )
        return None

    except Exception as e:
        logger.error(f"Error resolving project: {e}")
        return None


# ─── Task/Sprint Resolution ────────────────────────────────────────────────


def find_task_by_title_or_id(
    user_id: str,
    task_id: Optional[str] = None,
    task_title: Optional[str] = None,
    ticket_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Find a task by ID, title, or ticket ID.
    Filtered to tasks user has access to.
    """
    try:
        # Get user's projects
        projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )
        project_ids = [str(p["_id"]) for p in projects]

        # Try task_id first
        if task_id:
            try:
                task = db.tasks.find_one(
                    {"_id": ObjectId(task_id), "project_id": {"$in": project_ids}}
                )
                if task:
                    task["_id"] = str(task["_id"])
                    return task
            except Exception:
                pass

        # Try ticket_id
        if ticket_id:
            task = db.tasks.find_one(
                {"ticket_id": ticket_id, "project_id": {"$in": project_ids}}
            )
            if task:
                task["_id"] = str(task["_id"])
                return task

        # Try task_title
        if task_title:
            task = db.tasks.find_one(
                {
                    "project_id": {"$in": project_ids},
                    "title": {"$regex": task_title, "$options": "i"},
                }
            )
            if task:
                task["_id"] = str(task["_id"])
                return task

        return None

    except Exception as e:
        logger.error(f"Error finding task: {e}")
        return None


def find_sprint_by_name_or_id(
    user_id: str,
    project_id: Optional[str] = None,
    sprint_id: Optional[str] = None,
    sprint_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Find a sprint by ID or name.
    """
    try:
        query = {}

        if project_id:
            query["project_id"] = project_id
        else:
            # Get user's projects
            projects = list(
                db.projects.find(
                    {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
                )
            )
            project_ids = [str(p["_id"]) for p in projects]
            query["project_id"] = {"$in": project_ids}

        # Try sprint_id first
        if sprint_id:
            try:
                sprint = db.sprints.find_one({"_id": ObjectId(sprint_id), **query})
                if sprint:
                    sprint["_id"] = str(sprint["_id"])
                    return sprint
            except Exception:
                pass

        # Try sprint_name
        if sprint_name:
            if sprint_name.lower() == "active":
                sprint = db.sprints.find_one({**query, "status": "active"})
            else:
                sprint = db.sprints.find_one(
                    {**query, "name": {"$regex": f"^{sprint_name}$", "$options": "i"}}
                )

            if sprint:
                sprint["_id"] = str(sprint["_id"])
                return sprint

        return None

    except Exception as e:
        logger.error(f"Error finding sprint: {e}")
        return None
