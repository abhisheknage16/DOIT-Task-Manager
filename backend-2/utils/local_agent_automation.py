"""
Local AI Agent Automation & Task Execution
Enables task creation, assignment, sprint management with role-based access control
Uses Ollama to parse natural language commands into structured actions
"""

import json
import logging
import re
from typing import Dict, Any, Optional
from database import db
from models.user import User
from bson import ObjectId

logger = logging.getLogger(__name__)

# ─── Command Detection ─────────────────────────────────────────────────────


TASK_AUTOMATION_KEYWORDS = [
    # Task operations
    "create task",
    "create a task",
    "make a task",
    "add task",
    "new task",
    "assign task",
    "assign to",
    "give task to",
    "update task",
    "change status",
    "mark as",
    "set status",
    "list tasks",
    "show tasks",
    "my tasks",
    "get tasks",
    "find tasks",
    "tasks in",
    "tasks for",
    "update priority",
    "change priority",
    # Sprint operations
    "create sprint",
    "start sprint",
    "new sprint",
    "make sprint",
    "add to sprint",
    "add task to sprint",
    "put in sprint",
    "remove from sprint",
    "start the sprint",
    "complete sprint",
    "end sprint",
    "finish sprint",
    "list sprints",
    "show sprints",
    # Project operations
    "list projects",
    "show projects",
    "my projects",
    "get projects",
    "create project",
    "new project",
    "make project",
    # Member management
    "add member",
    "add user",
    "invite user",
    "add to project",
    "remove member",
    "remove user",
    "remove from project",
    "list members",
    "show members",
    "team members",
]


def detect_task_automation(message: str) -> bool:
    """Check if message contains task automation keywords."""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in TASK_AUTOMATION_KEYWORDS)


# ─── Command Parsing ──────────────────────────────────────────────────────


def parse_task_command_with_ollama(
    message: str,
    user_context: Dict[str, Any],
    ollama_llm,
) -> Dict[str, Any]:
    """
    Use Ollama LLM to parse natural language command into structured action.
    Falls back to regex-based parsing if LLM fails.
    """
    try:
        system_prompt = """You are a task management command parser for DOIT.
        
Extract the action and parameters from the user's command.

Available actions:
- create_task: Create a new task
- assign_task: Assign an existing task to someone
- update_task: Update task properties (status, priority, etc)
- create_sprint: Create a new sprint
- start_sprint: Make a sprint active
- complete_sprint: Mark a sprint as done
- add_task_to_sprint: Add a task to a sprint
- remove_task_from_sprint: Remove a task from a sprint
- list_tasks: List tasks (optionally filtered)
- list_sprints: List sprints
- list_projects: List user's projects
- create_project: Create a new project
- add_member: Add a member to a project
- remove_member: Remove a member from a project
- list_members: List project members

IMPORTANT: Return ONLY valid JSON with no markdown code fences. Example:
{"action": "create_task", "params": {"title": "Fix login bug", "project_name": "Auth", "priority": "High"}}

For create_task params, extract:
- title (required) - task name
- description (optional)
- project_name (IMPORTANT: extract from "in X project", "in X", "your X project" - NEVER use null, always try to find project name)
- assignee_email or assignee_name (optional)
- priority: Low/Medium/High/Critical (optional, default Medium)
- issue_type: task/bug/story (optional, default task)
- due_date: YYYY-MM-DD format (optional)
- labels: array of strings (optional)

CRITICAL: 
- Do NOT include null/None values in params
- Always extract project_name if visible in message
- Only include params that have actual values

For other actions, extract relevant parameters from context."""

        user_prompt = f"""Parse this command: {message}

User context: {json.dumps(user_context)}

Return ONLY valid JSON with action and params. NO markdown fences. NO null values."""

        # Try to get response from Ollama
        response = ollama_llm.complete(system_prompt + "\n\n" + user_prompt)
        response_text = response.text if hasattr(response, "text") else str(response)

        # Clean markdown code fences
        response_text = re.sub(r"```json\s*|\s*```", "", response_text).strip()

        parsed = json.loads(response_text)

        # Clean up None/null values from params
        if "params" in parsed and isinstance(parsed["params"], dict):
            cleaned_params = {
                k: v
                for k, v in parsed["params"].items()
                if v is not None and v != "None"
            }
            parsed["params"] = cleaned_params

        logger.info(f"✅ Parsed command via Ollama: {parsed}")
        return {"success": True, **parsed}

    except Exception as e:
        logger.warning(f"⚠️  Ollama parsing failed: {e}. Falling back to regex parsing.")
        return parse_task_command_regex(message)


def parse_task_command_regex(message: str) -> Dict[str, Any]:
    """
    Fallback regex-based command parsing when LLM fails.
    Handles common patterns for task creation.
    """
    message_lower = message.lower()

    # Create task pattern: "create task [title] [details]"
    if (
        "create task" in message_lower
        or "create a task" in message_lower
        or "add task" in message_lower
    ):
        # Extract title (usually between keywords and additional details)
        title_match = re.search(
            r'(?:create|add|new)\s+(?:a\s+)?task\s+(?:(?:called|named|titled)\s+)?["\']*([^,]+?)["\']*(?:\s+(?:in|for|project)|\s+(?:with|priority|due)|\s*$)',
            message,
            re.IGNORECASE,
        )
        title = title_match.group(1).strip() if title_match else "New Task"

        # More robust project extraction: look for "in [project]" or "project [name]"
        project_name = None

        # Pattern 1: "in project CDW" or "in CDW project" or "in CDW"
        project_match = re.search(
            r'in\s+(?:the\s+)?(?:project\s+)?["\']*([a-zA-Z0-9\s\-_]+?)["\']*(?:\s+project)?(?:\s|,|$)',
            message,
            re.IGNORECASE,
        )
        if project_match:
            project_name = project_match.group(1).strip()

        # Pattern 2: "for project CDW" or "for CDW"
        if not project_name:
            project_match = re.search(
                r'for\s+(?:project\s+)?["\']*([a-zA-Z0-9\s\-_]+?)["\']*(?:\s+project)?(?:\s|,|$)',
                message,
                re.IGNORECASE,
            )
            if project_match:
                project_name = project_match.group(1).strip()

        # Pattern 3: "your [project name] project"
        if not project_name:
            project_match = re.search(
                r"your\s+([a-zA-Z0-9\s\-_]+?)\s+project", message, re.IGNORECASE
            )
            if project_match:
                project_name = project_match.group(1).strip()

        # Extract priority
        priority = "Medium"
        if "high" in message_lower and "priority" in message_lower:
            priority = "High"
        elif "critical" in message_lower or "urgent" in message_lower:
            priority = "Critical"
        elif "low" in message_lower and "priority" in message_lower:
            priority = "Low"

        # Extract assignee
        assignee_match = re.search(
            r"(?:assign\s+to|assign|to)\s+([a-zA-Z\s\.@]+?)(?:\s+(?:in|for|project)|,|$)",
            message,
            re.IGNORECASE,
        )
        assignee = assignee_match.group(1).strip() if assignee_match else None

        params = {
            "title": title,
            "priority": priority,
        }
        if project_name:
            params["project_name"] = project_name
        if assignee:
            if "@" in assignee:
                params["assignee_email"] = assignee
            else:
                params["assignee_name"] = assignee

        logger.info(f"Regex parsed create_task: {params}")
        return {"success": True, "action": "create_task", "params": params}

    # List tasks pattern
    elif (
        "list task" in message_lower
        or "show task" in message_lower
        or "my tasks" in message_lower
    ):
        params = {}

        # Try to extract project name
        project_match = re.search(
            r'(?:in|for)\s+(?:project\s+)?["\']*([a-zA-Z0-9\s\-_]+?)["\']*(?:\s|,|$)',
            message,
            re.IGNORECASE,
        )
        if project_match:
            params["project_name"] = project_match.group(1).strip()

        logger.info(f"Regex parsed list_tasks: {params}")
        return {"success": True, "action": "list_tasks", "params": params}

    else:
        return {
            "success": False,
            "error": f"Could not parse command: {message}. Please be more specific.",
        }


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

        # Actions only super-admin can perform
        super_admin_only_actions = []

        # Check admin-only actions
        if action in admin_only_actions and user_role not in ["admin", "super-admin"]:
            return False, f"Only Admin users can {action.replace('_', ' ')}"

        # Check super-admin-only actions
        if action in super_admin_only_actions and user_role != "super-admin":
            return False, f"Only Super-Admin users can {action.replace('_', ' ')}"

        # Members can create tasks, assign tasks, update tasks, manage their own work
        allowed_for_members = [
            "create_task",
            "assign_task",
            "update_task",
            "add_task_to_sprint",
            "remove_task_from_sprint",
            "list_tasks",
            "list_sprints",
            "list_projects",
            "add_member",
            "remove_member",
            "list_members",
        ]

        if action in allowed_for_members:
            return True, None

        return False, f"User role '{user_role}' does not have permission for {action}"

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
        # 1. Try exact match (case-insensitive, ignoring 'project' suffix)
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
        # 3. Not found: log available projects for debugging
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
    Filtered to tasks user has access to (in their projects).
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
                # Get active sprint
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


# ─── User Resolution ──────────────────────────────────────────────────────


def find_user_by_email_or_name(identifier: str) -> Optional[Dict[str, Any]]:
    """
    Find a user by email or name.
    """
    try:
        # Try email first
        user = db.users.find_one({"email": identifier})
        if user:
            user["_id"] = str(user["_id"])
            return user

        # Try name
        user = db.users.find_one(
            {"name": {"$regex": f"^{identifier}$", "$options": "i"}}
        )
        if user:
            user["_id"] = str(user["_id"])
            return user

        return None
    except Exception as e:
        logger.error(f"Error finding user: {e}")
        return None
