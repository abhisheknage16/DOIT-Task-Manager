"""
LangGraph Agent Tools
LangChain tool definitions for DOIT task management automation
"""

import logging
from typing import Optional
from langchain_core.tools import tool
from database import db
from bson import ObjectId

logger = logging.getLogger(__name__)

# ─── Global context for tools (set per request) ───────────────────────────────
_tool_context = {}


def set_tool_context(user_id: str, user_email: str, user_role: str):
    """Set context that tools can access."""
    global _tool_context
    _tool_context = {
        "user_id": user_id,
        "user_email": user_email,
        "user_role": user_role,
    }


def get_tool_context():
    """Get current tool context."""
    return _tool_context


# ─── Task Management Tools ────────────────────────────────────────────────────


@tool
def create_task_tool(
    title: str,
    project_name: str,
    description: str = "",
    priority: str = "Medium",
    assignee_email: Optional[str] = None,
    due_date: Optional[str] = None,
) -> str:
    """
    Create a new task in a project.

    Args:
        title: Task title (required)
        project_name: Name of the project (required)
        description: Task description
        priority: Priority level (Low, Medium, High, Critical)
        assignee_email: Email of person to assign task to
        due_date: Due date in YYYY-MM-DD format

    Returns:
        Success message with ticket ID
    """
    try:
        from controllers.agent_task_controller import agent_create_task_sync
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")
        user_email = ctx.get("user_email")

        # Resolve project name to ID
        project_id = resolve_project_id(user_id, project_name=project_name)

        if not project_id:
            projects = list(
                db.projects.find(
                    {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
                )
            )
            available = [p.get("name", "") for p in projects]
            return f"❌ Project '{project_name}' not found. Available projects: {available}"

        logger.info(f"   📁 Creating task '{title}' in project: {project_id}")

        # Create task using sync version
        result = agent_create_task_sync(
            requesting_user=user_email,
            title=title,
            project_id=project_id,
            user_id=user_id,
            description=description,
            assignee_email=assignee_email,
            priority=priority,
            status="To Do",
            due_date=due_date,
            issue_type="task",
        )

        logger.info(f"   ✅ Task created successfully")

        # Build user-friendly message
        ticket_id = result.get("ticket_id", "")

        msg = f"✅ Task '{title}' created successfully in project {project_name}!"
        if assignee_email:
            msg += f" Assigned to {assignee_email}."
        if due_date:
            msg += f" Due date: {due_date}."
        if ticket_id:
            msg += f" Ticket ID: {ticket_id}"

        return msg

    except Exception as e:
        logger.error(f"create_task_tool error: {e}")
        import traceback

        traceback.print_exc()
        return f"❌ Failed to create task: {str(e)}"


@tool
def list_tasks_tool(
    project_name: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
) -> str:
    """
    List tasks with optional filtering.

    Args:
        project_name: Filter by project name
        status: Filter by status (To Do, In Progress, Done, etc.)
        priority: Filter by priority (Low, Medium, High, Critical)

    Returns:
        List of tasks with details
    """
    try:
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Build query
        projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )
        project_ids = [str(p["_id"]) for p in projects]

        query = {"project_id": {"$in": project_ids}}

        if project_name:
            project_id = resolve_project_id(user_id, project_name=project_name)
            if project_id:
                query["project_id"] = project_id

        if status:
            query["status"] = status

        if priority:
            query["priority"] = priority

        tasks = list(db.tasks.find(query).limit(10))

        if not tasks:
            return "No tasks found matching the criteria."

        result = f"Found {len(tasks)} task(s):\n\n"
        for task in tasks:
            result += f"• [{task.get('ticket_id', 'N/A')}] {task.get('title')}\n"
            result += (
                f"  Status: {task.get('status')} | Priority: {task.get('priority')}\n"
            )
            if task.get("assignee_email"):
                result += f"  Assigned to: {task.get('assignee_email')}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"list_tasks_tool error: {e}")
        return f"❌ Failed to list tasks: {str(e)}"


@tool
def update_task_status_tool(
    task_identifier: str,
    new_status: str,
) -> str:
    """
    Update a task's status.

    Args:
        task_identifier: Task title, ticket ID, or task ID
        new_status: New status (To Do, In Progress, In Review, Done, Blocked)

    Returns:
        Success message
    """
    try:
        from utils.langgraph_agent_automation import find_task_by_title_or_id
        from datetime import datetime

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Find task
        task = find_task_by_title_or_id(user_id, task_title=task_identifier)

        if not task:
            return f"❌ Task '{task_identifier}' not found."

        # Update task directly in database
        db.tasks.update_one(
            {"_id": ObjectId(task["_id"])},
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}},
        )

        return f"✅ Task '{task['title']}' status updated to '{new_status}'"

    except Exception as e:
        logger.error(f"update_task_status_tool error: {e}")
        return f"❌ Failed to update task: {str(e)}"


@tool
def assign_task_tool(
    task_identifier: str,
    assignee_email: str,
) -> str:
    """
    Assign a task to a team member.

    Args:
        task_identifier: Task title, ticket ID, or task ID
        assignee_email: Email of the person to assign to

    Returns:
        Success message
    """
    try:
        from utils.langgraph_agent_automation import find_task_by_title_or_id
        from controllers.agent_task_controller import agent_assign_task_sync

        ctx = get_tool_context()
        user_id = ctx.get("user_id")
        user_email = ctx.get("user_email")

        # Find task
        task = find_task_by_title_or_id(user_id, task_title=task_identifier)

        if not task:
            return f"❌ Task '{task_identifier}' not found."

        result = agent_assign_task_sync(
            requesting_user=user_email,
            task_id=task["_id"],
            assignee_identifier=assignee_email,
            user_id=user_id,
        )

        return f"✅ Task '{task['title']}' assigned to {assignee_email}"

    except Exception as e:
        logger.error(f"assign_task_tool error: {e}")
        return f"❌ Failed to assign task: {str(e)}"


# ─── Sprint Management Tools ───────────────────────────────────────────────────


@tool
def create_sprint_tool(
    sprint_name: str,
    project_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    goal: str = "",
) -> str:
    """
    Create a new sprint in a project.

    Args:
        sprint_name: Name of the sprint
        project_name: Name of the project
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        goal: Sprint goal/objective

    Returns:
        Success message
    """
    try:
        from controllers.agent_sprint_controller import agent_create_sprint_sync
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")
        user_email = ctx.get("user_email")

        # Resolve project
        project_id = resolve_project_id(user_id, project_name=project_name)

        if not project_id:
            return f"❌ Project '{project_name}' not found."

        result = agent_create_sprint_sync(
            requesting_user=user_email,
            name=sprint_name,
            project_id=project_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            goal=goal,
        )

        return (
            f"✅ Sprint '{sprint_name}' created successfully in project {project_name}"
        )

    except Exception as e:
        logger.error(f"create_sprint_tool error: {e}")
        return f"❌ Failed to create sprint: {str(e)}"


@tool
def add_task_to_sprint_tool(
    task_identifier: str,
    sprint_name: str,
) -> str:
    """
    Add a task to a sprint.

    Args:
        task_identifier: Task title, ticket ID, or task ID
        sprint_name: Name of the sprint

    Returns:
        Success message
    """
    try:
        from utils.langgraph_agent_automation import (
            find_task_by_title_or_id,
            find_sprint_by_name_or_id,
        )
        from datetime import datetime

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Find task
        task = find_task_by_title_or_id(user_id, task_title=task_identifier)
        if not task:
            return f"❌ Task '{task_identifier}' not found."

        # Find sprint
        sprint = find_sprint_by_name_or_id(user_id, sprint_name=sprint_name)
        if not sprint:
            return f"❌ Sprint '{sprint_name}' not found."

        # Add task to sprint
        db.tasks.update_one(
            {"_id": ObjectId(task["_id"])},
            {"$set": {"sprint_id": sprint["_id"], "updated_at": datetime.utcnow()}},
        )

        return f"✅ Task '{task['title']}' added to sprint '{sprint['name']}'"

    except Exception as e:
        logger.error(f"add_task_to_sprint_tool error: {e}")
        return f"❌ Failed to add task to sprint: {str(e)}"


@tool
def list_sprints_tool(project_name: Optional[str] = None) -> str:
    """
    List sprints, optionally filtered by project.

    Args:
        project_name: Filter by project name

    Returns:
        List of sprints
    """
    try:
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        query = {}

        if project_name:
            project_id = resolve_project_id(user_id, project_name=project_name)
            if project_id:
                query["project_id"] = project_id
        else:
            # Get all user's projects
            projects = list(
                db.projects.find(
                    {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
                )
            )
            project_ids = [str(p["_id"]) for p in projects]
            query["project_id"] = {"$in": project_ids}

        sprints = list(db.sprints.find(query))

        if not sprints:
            return "No sprints found."

        result = f"Found {len(sprints)} sprint(s):\n\n"
        for sprint in sprints:
            result += (
                f"• {sprint.get('name')} - Status: {sprint.get('status', 'planned')}\n"
            )
            if sprint.get("start_date"):
                result += f"  Start: {sprint.get('start_date')}\n"
            if sprint.get("end_date"):
                result += f"  End: {sprint.get('end_date')}\n"
            if sprint.get("goal"):
                result += f"  Goal: {sprint.get('goal')}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"list_sprints_tool error: {e}")
        return f"❌ Failed to list sprints: {str(e)}"


# ─── Project & Member Tools ────────────────────────────────────────────────────


@tool
def list_projects_tool() -> str:
    """
    List all projects the user has access to.

    Returns:
        List of projects
    """
    try:
        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )

        if not projects:
            return "You don't have any projects yet."

        result = f"You have access to {len(projects)} project(s):\n\n"
        for project in projects:
            result += f"• {project.get('name')}\n"
            result += f"  Description: {project.get('description', 'N/A')}\n"
            result += f"  Members: {len(project.get('members', []))}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"list_projects_tool error: {e}")
        return f"❌ Failed to list projects: {str(e)}"


@tool
def list_team_members_tool(project_name: str) -> str:
    """
    List team members in a project.

    Args:
        project_name: Name of the project

    Returns:
        List of team members
    """
    try:
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        project_id = resolve_project_id(user_id, project_name=project_name)

        if not project_id:
            return f"❌ Project '{project_name}' not found."

        project = db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            return f"❌ Project '{project_name}' not found."

        members = project.get("members", [])

        if not members:
            return f"Project '{project_name}' has no members yet."

        result = f"Team members in '{project_name}' ({len(members)}):\n\n"
        for member in members:
            result += f"• {member.get('name', 'N/A')} ({member.get('email', 'N/A')})\n"
            result += f"  Role: {member.get('role', 'member')}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"list_team_members_tool error: {e}")
        return f"❌ Failed to list team members: {str(e)}"


# backend-2/utils/langgraph_agent_tools.py
"""
LangGraph Agent Tools - EXPANDED AUTOMATION SCOPE
LangChain tool definitions for comprehensive DOIT task management automation
"""

import logging
from typing import Optional, List
from langchain_core.tools import tool
from database import db
from bson import ObjectId
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─── Global context for tools (set per request) ───────────────────────────────
_tool_context = {}


def set_tool_context(user_id: str, user_email: str, user_role: str):
    """Set context that tools can access."""
    global _tool_context
    _tool_context = {
        "user_id": user_id,
        "user_email": user_email,
        "user_role": user_role,
    }


def get_tool_context():
    """Get current tool context."""
    return _tool_context


# ═══════════════════════════════════════════════════════════════════════════════
# TASK MANAGEMENT TOOLS (Enhanced)
# ═══════════════════════════════════════════════════════════════════════════════


@tool
def create_task_tool(
    title: str,
    project_name: str,
    description: str = "",
    priority: str = "Medium",
    assignee_email: Optional[str] = None,
    due_date: Optional[str] = None,
    issue_type: str = "task",
    labels: Optional[str] = None,
) -> str:
    """
    Create a new task in a project.

    Args:
        title: Task title (required)
        project_name: Name of the project (required)
        description: Task description
        priority: Priority level (Low, Medium, High, Critical)
        assignee_email: Email of person to assign task to
        due_date: Due date in YYYY-MM-DD format
        issue_type: Type (task, bug, story, epic)
        labels: Comma-separated labels (e.g., "frontend,urgent")

    Returns:
        Success message with ticket ID
    """
    try:
        from controllers.agent_task_controller import agent_create_task_sync
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")
        user_email = ctx.get("user_email")

        # Resolve project name to ID
        project_id = resolve_project_id(user_id, project_name=project_name)

        if not project_id:
            projects = list(
                db.projects.find(
                    {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
                )
            )
            available = [p.get("name", "") for p in projects]
            return f"❌ Project '{project_name}' not found. Available projects: {available}"

        # Parse labels
        labels_list = [l.strip() for l in labels.split(",")] if labels else []

        logger.info(f"   📁 Creating task '{title}' in project: {project_id}")

        # Create task using sync version
        result = agent_create_task_sync(
            requesting_user=user_email,
            title=title,
            project_id=project_id,
            user_id=user_id,
            description=description,
            assignee_email=assignee_email,
            priority=priority,
            status="To Do",
            due_date=due_date,
            issue_type=issue_type,
            labels=labels_list,
        )

        logger.info(f"   ✅ Task created successfully")

        # Build user-friendly message
        ticket_id = result.get("ticket_id", "")

        msg = f"✅ Task '{title}' created successfully in project {project_name}!"
        if assignee_email:
            msg += f" Assigned to {assignee_email}."
        if due_date:
            msg += f" Due date: {due_date}."
        if ticket_id:
            msg += f" Ticket ID: {ticket_id}"

        return msg

    except Exception as e:
        logger.error(f"create_task_tool error: {e}")
        import traceback

        traceback.print_exc()
        return f"❌ Failed to create task: {str(e)}"


@tool
def create_multiple_tasks_tool(
    project_name: str,
    tasks_description: str,
) -> str:
    """
    Create multiple tasks at once from a description.

    Args:
        project_name: Name of the project
        tasks_description: Description of tasks, one per line (e.g., "Fix login bug\nAdd user profile\nUpdate README")

    Returns:
        Summary of created tasks
    """
    try:
        from controllers.agent_task_controller import agent_create_task_sync
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")
        user_email = ctx.get("user_email")

        # Resolve project
        project_id = resolve_project_id(user_id, project_name=project_name)
        if not project_id:
            return f"❌ Project '{project_name}' not found."

        # Parse tasks (split by newline)
        task_titles = [t.strip() for t in tasks_description.split("\n") if t.strip()]

        if not task_titles:
            return "❌ No tasks to create."

        created = []
        failed = []

        for title in task_titles:
            try:
                result = agent_create_task_sync(
                    requesting_user=user_email,
                    title=title,
                    project_id=project_id,
                    user_id=user_id,
                    status="To Do",
                    issue_type="task",
                )
                created.append(result.get("ticket_id", title))
            except Exception as e:
                failed.append(f"{title}: {str(e)}")

        msg = f"✅ Created {len(created)} tasks in {project_name}"
        if created:
            msg += f"\nTickets: {', '.join(created)}"
        if failed:
            msg += f"\n❌ Failed ({len(failed)}): {', '.join(failed[:3])}"

        return msg

    except Exception as e:
        logger.error(f"create_multiple_tasks_tool error: {e}")
        return f"❌ Failed to create tasks: {str(e)}"


@tool
def list_tasks_tool(
    project_name: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_email: Optional[str] = None,
    overdue_only: bool = False,
) -> str:
    """
    List tasks with optional filtering.

    Args:
        project_name: Filter by project name
        status: Filter by status (To Do, In Progress, Done, etc.)
        priority: Filter by priority (Low, Medium, High, Critical)
        assignee_email: Filter by assignee email
        overdue_only: Show only overdue tasks

    Returns:
        List of tasks with details
    """
    try:
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Build query
        projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )
        project_ids = [str(p["_id"]) for p in projects]

        query = {"project_id": {"$in": project_ids}}

        if project_name:
            project_id = resolve_project_id(user_id, project_name=project_name)
            if project_id:
                query["project_id"] = project_id

        if status:
            query["status"] = status

        if priority:
            query["priority"] = priority

        if assignee_email:
            query["assignee_email"] = assignee_email

        if overdue_only:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            query["due_date"] = {"$lt": today}
            query["status"] = {"$ne": "Done"}

        tasks = list(db.tasks.find(query).limit(20))

        if not tasks:
            return "No tasks found matching the criteria."

        result = f"Found {len(tasks)} task(s):\n\n"
        for task in tasks:
            result += f"• [{task.get('ticket_id', 'N/A')}] {task.get('title')}\n"
            result += (
                f"  Status: {task.get('status')} | Priority: {task.get('priority')}\n"
            )
            if task.get("assignee_email"):
                result += f"  Assigned to: {task.get('assignee_email')}\n"
            if task.get("due_date"):
                result += f"  Due: {task.get('due_date')}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"list_tasks_tool error: {e}")
        return f"❌ Failed to list tasks: {str(e)}"


@tool
def update_task_status_tool(
    task_identifier: str,
    new_status: str,
) -> str:
    """
    Update a task's status.

    Args:
        task_identifier: Task title, ticket ID, or task ID
        new_status: New status (To Do, In Progress, In Review, Done, Blocked)

    Returns:
        Success message
    """
    try:
        from utils.langgraph_agent_automation import find_task_by_title_or_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Find task
        task = find_task_by_title_or_id(user_id, task_title=task_identifier)

        if not task:
            return f"❌ Task '{task_identifier}' not found."

        # Update task directly in database
        db.tasks.update_one(
            {"_id": ObjectId(task["_id"])},
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}},
        )

        return f"✅ Task '{task['title']}' status updated to '{new_status}'"

    except Exception as e:
        logger.error(f"update_task_status_tool error: {e}")
        return f"❌ Failed to update task: {str(e)}"


@tool
def bulk_update_tasks_tool(
    project_name: str,
    filter_status: Optional[str] = None,
    filter_priority: Optional[str] = None,
    new_status: Optional[str] = None,
    new_priority: Optional[str] = None,
    new_assignee_email: Optional[str] = None,
) -> str:
    """
    Bulk update multiple tasks at once.

    Args:
        project_name: Project to update tasks in
        filter_status: Filter tasks by current status
        filter_priority: Filter tasks by priority
        new_status: New status to set
        new_priority: New priority to set
        new_assignee_email: New assignee to set

    Returns:
        Summary of updates
    """
    try:
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Resolve project
        project_id = resolve_project_id(user_id, project_name=project_name)
        if not project_id:
            return f"❌ Project '{project_name}' not found."

        # Build filter query
        query = {"project_id": project_id}
        if filter_status:
            query["status"] = filter_status
        if filter_priority:
            query["priority"] = filter_priority

        # Build update data
        update_data = {"updated_at": datetime.utcnow()}
        if new_status:
            update_data["status"] = new_status
        if new_priority:
            update_data["priority"] = new_priority
        if new_assignee_email:
            # Resolve assignee
            assignee = db.users.find_one({"email": new_assignee_email})
            if assignee:
                update_data["assignee_email"] = assignee["email"]
                update_data["assignee_name"] = assignee.get("name", new_assignee_email)
                update_data["assignee_id"] = str(assignee["_id"])

        # Update tasks
        result = db.tasks.update_many(query, {"$set": update_data})

        return f"✅ Updated {result.modified_count} tasks in {project_name}"

    except Exception as e:
        logger.error(f"bulk_update_tasks_tool error: {e}")
        return f"❌ Failed to bulk update: {str(e)}"


@tool
def assign_task_tool(
    task_identifier: str,
    assignee_email: str,
) -> str:
    """
    Assign a task to a team member.

    Args:
        task_identifier: Task title, ticket ID, or task ID
        assignee_email: Email of the person to assign to

    Returns:
        Success message
    """
    try:
        from utils.langgraph_agent_automation import find_task_by_title_or_id
        from controllers.agent_task_controller import agent_assign_task_sync

        ctx = get_tool_context()
        user_id = ctx.get("user_id")
        user_email = ctx.get("user_email")

        # Find task
        task = find_task_by_title_or_id(user_id, task_title=task_identifier)

        if not task:
            return f"❌ Task '{task_identifier}' not found."

        result = agent_assign_task_sync(
            requesting_user=user_email,
            task_id=task["_id"],
            assignee_identifier=assignee_email,
            user_id=user_id,
        )

        return f"✅ Task '{task['title']}' assigned to {assignee_email}"

    except Exception as e:
        logger.error(f"assign_task_tool error: {e}")
        return f"❌ Failed to assign task: {str(e)}"


@tool
def delete_task_tool(task_identifier: str) -> str:
    """
    Delete a task.

    Args:
        task_identifier: Task title, ticket ID, or task ID

    Returns:
        Success message
    """
    try:
        from utils.langgraph_agent_automation import find_task_by_title_or_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Find task
        task = find_task_by_title_or_id(user_id, task_title=task_identifier)

        if not task:
            return f"❌ Task '{task_identifier}' not found."

        # Delete task
        db.tasks.delete_one({"_id": ObjectId(task["_id"])})

        return f"✅ Task '{task['title']}' deleted successfully"

    except Exception as e:
        logger.error(f"delete_task_tool error: {e}")
        return f"❌ Failed to delete task: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT MANAGEMENT TOOLS (Enhanced)
# ═══════════════════════════════════════════════════════════════════════════════


@tool
def create_sprint_tool(
    sprint_name: str,
    project_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    goal: str = "",
    duration_weeks: Optional[int] = None,
) -> str:
    """
    Create a new sprint in a project.

    Args:
        sprint_name: Name of the sprint
        project_name: Name of the project
        start_date: Start date in YYYY-MM-DD format (defaults to today)
        end_date: End date in YYYY-MM-DD format
        goal: Sprint goal/objective
        duration_weeks: Auto-calculate end date (e.g., 2 for 2-week sprint)

    Returns:
        Success message
    """
    try:
        from controllers.agent_sprint_controller import agent_create_sprint_sync
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")
        user_email = ctx.get("user_email")

        # Resolve project
        project_id = resolve_project_id(user_id, project_name=project_name)

        if not project_id:
            return f"❌ Project '{project_name}' not found."

        # Auto-calculate dates if duration provided
        if duration_weeks and not end_date:
            if not start_date:
                start_date = datetime.utcnow().strftime("%Y-%m-%d")
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = start_dt + timedelta(weeks=duration_weeks)
            end_date = end_dt.strftime("%Y-%m-%d")

        result = agent_create_sprint_sync(
            requesting_user=user_email,
            name=sprint_name,
            project_id=project_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            goal=goal,
        )

        msg = (
            f"✅ Sprint '{sprint_name}' created successfully in project {project_name}"
        )
        if start_date and end_date:
            msg += f" ({start_date} to {end_date})"

        return msg

    except Exception as e:
        logger.error(f"create_sprint_tool error: {e}")
        return f"❌ Failed to create sprint: {str(e)}"


@tool
def add_task_to_sprint_tool(
    task_identifier: str,
    sprint_name: str,
) -> str:
    """
    Add a task to a sprint.

    Args:
        task_identifier: Task title, ticket ID, or task ID
        sprint_name: Name of the sprint

    Returns:
        Success message
    """
    try:
        from utils.langgraph_agent_automation import (
            find_task_by_title_or_id,
            find_sprint_by_name_or_id,
        )

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Find task
        task = find_task_by_title_or_id(user_id, task_title=task_identifier)
        if not task:
            return f"❌ Task '{task_identifier}' not found."

        # Find sprint
        sprint = find_sprint_by_name_or_id(user_id, sprint_name=sprint_name)
        if not sprint:
            return f"❌ Sprint '{sprint_name}' not found."

        # Add task to sprint
        db.tasks.update_one(
            {"_id": ObjectId(task["_id"])},
            {"$set": {"sprint_id": sprint["_id"], "updated_at": datetime.utcnow()}},
        )

        return f"✅ Task '{task['title']}' added to sprint '{sprint['name']}'"

    except Exception as e:
        logger.error(f"add_task_to_sprint_tool error: {e}")
        return f"❌ Failed to add task to sprint: {str(e)}"


@tool
def add_multiple_tasks_to_sprint_tool(
    project_name: str,
    sprint_name: str,
    filter_status: Optional[str] = None,
    filter_priority: Optional[str] = None,
) -> str:
    """
    Add multiple tasks to a sprint based on filters.

    Args:
        project_name: Project name
        sprint_name: Sprint name
        filter_status: Filter tasks by status (e.g., "To Do")
        filter_priority: Filter tasks by priority (e.g., "High")

    Returns:
        Summary of added tasks
    """
    try:
        from utils.langgraph_agent_automation import (
            resolve_project_id,
            find_sprint_by_name_or_id,
        )

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Resolve project and sprint
        project_id = resolve_project_id(user_id, project_name=project_name)
        if not project_id:
            return f"❌ Project '{project_name}' not found."

        sprint = find_sprint_by_name_or_id(user_id, sprint_name=sprint_name)
        if not sprint:
            return f"❌ Sprint '{sprint_name}' not found."

        # Build query
        query = {"project_id": project_id, "sprint_id": {"$exists": False}}
        if filter_status:
            query["status"] = filter_status
        if filter_priority:
            query["priority"] = filter_priority

        # Update tasks
        result = db.tasks.update_many(
            query,
            {"$set": {"sprint_id": sprint["_id"], "updated_at": datetime.utcnow()}},
        )

        return f"✅ Added {result.modified_count} tasks to sprint '{sprint_name}'"

    except Exception as e:
        logger.error(f"add_multiple_tasks_to_sprint_tool error: {e}")
        return f"❌ Failed to add tasks: {str(e)}"


@tool
def list_sprints_tool(
    project_name: Optional[str] = None, status: Optional[str] = None
) -> str:
    """
    List sprints, optionally filtered by project and status.

    Args:
        project_name: Filter by project name
        status: Filter by status (planned, active, completed)

    Returns:
        List of sprints
    """
    try:
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        query = {}

        if project_name:
            project_id = resolve_project_id(user_id, project_name=project_name)
            if project_id:
                query["project_id"] = project_id
        else:
            # Get all user's projects
            projects = list(
                db.projects.find(
                    {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
                )
            )
            project_ids = [str(p["_id"]) for p in projects]
            query["project_id"] = {"$in": project_ids}

        if status:
            query["status"] = status

        sprints = list(db.sprints.find(query))

        if not sprints:
            return "No sprints found."

        result = f"Found {len(sprints)} sprint(s):\n\n"
        for sprint in sprints:
            # Count tasks
            task_count = db.tasks.count_documents({"sprint_id": sprint["_id"]})

            result += (
                f"• {sprint.get('name')} - Status: {sprint.get('status', 'planned')}\n"
            )
            result += f"  Tasks: {task_count}\n"
            if sprint.get("start_date"):
                result += f"  Start: {sprint.get('start_date')}\n"
            if sprint.get("end_date"):
                result += f"  End: {sprint.get('end_date')}\n"
            if sprint.get("goal"):
                result += f"  Goal: {sprint.get('goal')}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"list_sprints_tool error: {e}")
        return f"❌ Failed to list sprints: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT MANAGEMENT TOOLS (New)
# ═══════════════════════════════════════════════════════════════════════════════


@tool
def create_project_tool(
    project_name: str,
    description: str = "",
) -> str:
    """
    Create a new project (requires admin role).

    Args:
        project_name: Name of the project
        description: Project description

    Returns:
        Success message
    """
    try:
        ctx = get_tool_context()
        user_id = ctx.get("user_id")
        user_role = ctx.get("user_role", "").lower()

        # Check permission
        if user_role not in ["admin", "super-admin"]:
            return "❌ Only admins can create projects."

        # Check if project already exists
        existing = db.projects.find_one({"user_id": user_id, "name": project_name})

        if existing:
            return f"❌ Project '{project_name}' already exists."

        # Create project
        project = {
            "name": project_name,
            "description": description,
            "user_id": user_id,
            "members": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = db.projects.insert_one(project)

        # Create channel for project
        from utils.websocket_manager import manager

        channel_id = f"project-{str(result.inserted_id)}"
        # Note: Channel creation happens automatically on first connection

        return f"✅ Project '{project_name}' created successfully!"

    except Exception as e:
        logger.error(f"create_project_tool error: {e}")
        return f"❌ Failed to create project: {str(e)}"


@tool
def list_projects_tool() -> str:
    """
    List all projects the user has access to.

    Returns:
        List of projects with task counts
    """
    try:
        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )

        if not projects:
            return "You don't have any projects yet."

        result = f"You have access to {len(projects)} project(s):\n\n"
        for project in projects:
            # Count tasks
            task_count = db.tasks.count_documents({"project_id": str(project["_id"])})
            done_count = db.tasks.count_documents(
                {"project_id": str(project["_id"]), "status": "Done"}
            )

            result += f"• {project.get('name')}\n"
            result += f"  Description: {project.get('description', 'N/A')}\n"
            result += f"  Members: {len(project.get('members', []))}\n"
            result += f"  Tasks: {done_count}/{task_count} completed\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"list_projects_tool error: {e}")
        return f"❌ Failed to list projects: {str(e)}"


@tool
def add_project_member_tool(
    project_name: str,
    member_email: str,
) -> str:
    """
    Add a member to a project (owner only).

    Args:
        project_name: Name of the project
        member_email: Email of member to add

    Returns:
        Success message
    """
    try:
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Resolve project
        project_id = resolve_project_id(user_id, project_name=project_name)
        if not project_id:
            return f"❌ Project '{project_name}' not found."

        # Check ownership
        project = db.projects.find_one({"_id": ObjectId(project_id)})
        if project["user_id"] != user_id:
            return "❌ Only project owner can add members."

        # Find member
        member = db.users.find_one({"email": member_email})
        if not member:
            return f"❌ User '{member_email}' not found."

        member_id = str(member["_id"])

        # Check if already member
        if any(m["user_id"] == member_id for m in project.get("members", [])):
            return f"❌ {member_email} is already a member."

        # Add member
        member_data = {
            "user_id": member_id,
            "email": member["email"],
            "name": member.get("name", member_email),
            "added_at": datetime.utcnow().isoformat(),
        }

        db.projects.update_one(
            {"_id": ObjectId(project_id)}, {"$push": {"members": member_data}}
        )

        return f"✅ {member['name']} added to project '{project_name}'"

    except Exception as e:
        logger.error(f"add_project_member_tool error: {e}")
        return f"❌ Failed to add member: {str(e)}"


@tool
def list_team_members_tool(project_name: str) -> str:
    """
    List team members in a project.

    Args:
        project_name: Name of the project

    Returns:
        List of team members
    """
    try:
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        project_id = resolve_project_id(user_id, project_name=project_name)

        if not project_id:
            return f"❌ Project '{project_name}' not found."

        project = db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            return f"❌ Project '{project_name}' not found."

        # Get owner
        owner = db.users.find_one({"_id": ObjectId(project["user_id"])})

        members = project.get("members", [])

        result = f"Team members in '{project_name}':\n\n"

        # Show owner first
        if owner:
            result += f"• {owner.get('name')} ({owner.get('email')}) - Owner\n"

        # Show members
        for member in members:
            result += f"• {member.get('name', 'N/A')} ({member.get('email', 'N/A')}) - Member\n"

        result += f"\nTotal: {1 + len(members)} members"

        return result

    except Exception as e:
        logger.error(f"list_team_members_tool error: {e}")
        return f"❌ Failed to list team members: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS & REPORTING TOOLS (New)
# ═══════════════════════════════════════════════════════════════════════════════


@tool
def get_project_analytics_tool(project_name: str) -> str:
    """
    Get analytics and insights for a project.

    Args:
        project_name: Name of the project

    Returns:
        Project analytics summary
    """
    try:
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        project_id = resolve_project_id(user_id, project_name=project_name)
        if not project_id:
            return f"❌ Project '{project_name}' not found."

        # Get all tasks
        tasks = list(db.tasks.find({"project_id": project_id}))

        if not tasks:
            return f"No tasks found in project '{project_name}'."

        # Calculate metrics
        total = len(tasks)
        by_status = {}
        by_priority = {}
        overdue = 0
        today = datetime.utcnow().strftime("%Y-%m-%d")

        for task in tasks:
            # Status breakdown
            status = task.get("status", "To Do")
            by_status[status] = by_status.get(status, 0) + 1

            # Priority breakdown
            priority = task.get("priority", "Medium")
            by_priority[priority] = by_priority.get(priority, 0) + 1

            # Overdue count
            if (
                task.get("due_date")
                and task.get("due_date") < today
                and status != "Done"
            ):
                overdue += 1

        # Build report
        result = f"📊 Analytics for '{project_name}':\n\n"
        result += f"Total Tasks: {total}\n"
        result += f"Overdue: {overdue}\n\n"

        result += "Status Breakdown:\n"
        for status, count in by_status.items():
            pct = (count / total * 100) if total > 0 else 0
            result += f"  {status}: {count} ({pct:.1f}%)\n"

        result += "\nPriority Breakdown:\n"
        for priority, count in by_priority.items():
            result += f"  {priority}: {count}\n"

        # Completion rate
        done = by_status.get("Done", 0)
        completion_rate = (done / total * 100) if total > 0 else 0
        result += f"\n✅ Completion Rate: {completion_rate:.1f}%"

        return result

    except Exception as e:
        logger.error(f"get_project_analytics_tool error: {e}")
        return f"❌ Failed to get analytics: {str(e)}"


@tool
def get_user_workload_tool(user_email: Optional[str] = None) -> str:
    """
    Get workload summary for a user.

    Args:
        user_email: Email of user (defaults to current user)

    Returns:
        Workload summary
    """
    try:
        ctx = get_tool_context()
        current_user_email = ctx.get("user_email")

        # Use provided email or current user
        target_email = user_email or current_user_email

        # Get tasks assigned to user
        tasks = list(db.tasks.find({"assignee_email": target_email}))

        if not tasks:
            return f"No tasks assigned to {target_email}."

        total = len(tasks)
        by_status = {}
        by_priority = {}
        overdue = 0
        today = datetime.utcnow().strftime("%Y-%m-%d")

        for task in tasks:
            status = task.get("status", "To Do")
            by_status[status] = by_status.get(status, 0) + 1

            priority = task.get("priority", "Medium")
            by_priority[priority] = by_priority.get(priority, 0) + 1

            if (
                task.get("due_date")
                and task.get("due_date") < today
                and status != "Done"
            ):
                overdue += 1

        result = f"👤 Workload for {target_email}:\n\n"
        result += f"Total Tasks: {total}\n"
        result += f"Overdue: {overdue}\n\n"

        result += "By Status:\n"
        for status, count in sorted(by_status.items()):
            result += f"  {status}: {count}\n"

        result += "\nBy Priority:\n"
        for priority in ["Critical", "High", "Medium", "Low"]:
            count = by_priority.get(priority, 0)
            if count > 0:
                result += f"  {priority}: {count}\n"

        return result

    except Exception as e:
        logger.error(f"get_user_workload_tool error: {e}")
        return f"❌ Failed to get workload: {str(e)}"


@tool
def get_overdue_tasks_tool(project_name: Optional[str] = None) -> str:
    """
    Get all overdue tasks.

    Args:
        project_name: Filter by project (optional)

    Returns:
        List of overdue tasks
    """
    try:
        from utils.langgraph_agent_automation import resolve_project_id

        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Build query
        query = {
            "due_date": {"$lt": datetime.utcnow().strftime("%Y-%m-%d")},
            "status": {"$ne": "Done"},
        }

        if project_name:
            project_id = resolve_project_id(user_id, project_name=project_name)
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

        tasks = list(db.tasks.find(query).limit(20))

        if not tasks:
            return "No overdue tasks found! 🎉"

        result = f"⚠️ Found {len(tasks)} overdue task(s):\n\n"
        for task in tasks:
            result += f"• [{task.get('ticket_id', 'N/A')}] {task.get('title')}\n"
            result += (
                f"  Due: {task.get('due_date')} | Priority: {task.get('priority')}\n"
            )
            if task.get("assignee_email"):
                result += f"  Assigned to: {task.get('assignee_email')}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"get_overdue_tasks_tool error: {e}")
        return f"❌ Failed to get overdue tasks: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# PROFILE MANAGEMENT TOOLS (New)
# ═══════════════════════════════════════════════════════════════════════════════


@tool
def update_user_profile_tool(
    phone: Optional[str] = None,
    bio: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    """
    Update user profile information.

    Args:
        phone: Phone number
        bio: Bio/description
        location: Location

    Returns:
        Success message
    """
    try:
        ctx = get_tool_context()
        user_id = ctx.get("user_id")

        # Get or create profile
        profile = db.profiles.find_one({"user_id": user_id})

        if not profile:
            profile = {
                "user_id": user_id,
                "personal": {},
                "created_at": datetime.utcnow(),
            }
            db.profiles.insert_one(profile)

        # Update personal info
        update_data = {}
        if phone:
            update_data["personal.phone"] = phone
        if bio:
            update_data["personal.bio"] = bio
        if location:
            update_data["personal.location"] = location

        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            db.profiles.update_one({"user_id": user_id}, {"$set": update_data})

        return "✅ Profile updated successfully"

    except Exception as e:
        logger.error(f"update_user_profile_tool error: {e}")
        return f"❌ Failed to update profile: {str(e)}"


# ─── Helper: Get all tools ─────────────────────────────────────────────────────


def get_all_langgraph_tools():
    """Return all available LangGraph tools."""
    return [
        # Task Management (Enhanced)
        create_task_tool,
        create_multiple_tasks_tool,
        list_tasks_tool,
        update_task_status_tool,
        bulk_update_tasks_tool,
        assign_task_tool,
        delete_task_tool,
        # Sprint Management (Enhanced)
        create_sprint_tool,
        add_task_to_sprint_tool,
        add_multiple_tasks_to_sprint_tool,
        list_sprints_tool,
        # Project Management (New)
        create_project_tool,
        list_projects_tool,
        add_project_member_tool,
        list_team_members_tool,
        # Analytics & Reporting (New)
        get_project_analytics_tool,
        get_user_workload_tool,
        get_overdue_tasks_tool,
        # Profile Management (New)
        update_user_profile_tool,
    ]
