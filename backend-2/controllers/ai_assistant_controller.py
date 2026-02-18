"""
AI Assistant Controller - COMPLETE WITH ALL OPERATIONS
Handles ChatGPT-like AI interactions using Azure AI Foundry (GPT-5.2-chat + FLUX-1.1-pro)
NOW with: Task automation, Sprint management, Member management, and intelligent insights
"""

from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from models.ai_conversation import AIConversation, AIMessage
from utils.azure_ai_utils import (
    chat_completion,
    chat_completion_streaming,
    generate_image,
    get_context_with_system_prompt,
    truncate_context,
)
from utils.ai_data_analyzer import (
    analyze_user_data_for_ai,
    build_ai_system_prompt,
    extract_insights_from_data,
)
from controllers.agent_task_controller import agent_create_task, agent_assign_task
from controllers.agent_sprint_controller import agent_create_sprint
from controllers import task_controller, sprint_controller, member_controller
from models.user import User
from models.project import Project
from models.task import Task
from models.sprint import Sprint
from database import db
from bson import ObjectId
import json
from typing import Optional, List
import os
from datetime import datetime, timezone
from utils.file_parser import extract_file_content, summarize_file_content
import re


# ============================================================================
# CONVERSATION MANAGEMENT
# ============================================================================


def create_conversation(user_id: str, title: str = "New Conversation"):
    """Create a new AI conversation"""
    try:
        conversation_id = AIConversation.create(user_id, title)
        conversation = AIConversation.get_by_id(conversation_id)

        if conversation:
            conversation["_id"] = str(conversation["_id"])
            return {
                "success": True,
                "conversation": conversation,
                "message": "Conversation created successfully",
            }

        raise HTTPException(status_code=500, detail="Failed to create conversation")

    except Exception as e:
        print(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def get_user_conversations(user_id: str):
    """Get all conversations for a user"""
    try:
        conversations = AIConversation.get_user_conversations(user_id)

        for conv in conversations:
            conv["_id"] = str(conv["_id"])

        return {"success": True, "conversations": conversations}

    except Exception as e:
        print(f"Error fetching conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def get_conversation_messages(conversation_id: str):
    """Get all messages in a conversation"""
    try:
        messages = AIMessage.get_conversation_messages(conversation_id)

        for msg in messages:
            msg["_id"] = str(msg["_id"])

        return {"success": True, "messages": messages}

    except Exception as e:
        print(f"Error fetching messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TASK AUTOMATION - COMMAND DETECTION
# ============================================================================


def detect_task_command(message: str) -> bool:
    """Detect if message contains a task automation command"""
    command_keywords = [
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
        "list all tasks",
        "show all tasks",
        "tasks in",
        "tasks for",
        "update priority",
        "change priority",
        "set priority",
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
        # Member operations
        "add member",
        "add user",
        "invite member",
        "add to project",
        "remove member",
        "remove user",
        "kick member",
        "list members",
        "show members",
        "project members",
    ]

    message_lower = message.lower()
    return any(keyword in message_lower for keyword in command_keywords)


# ============================================================================
# TASK AUTOMATION - COMMAND PARSING
# ============================================================================


def parse_task_command(command: str, context: dict = None):
    """Use Azure OpenAI to parse natural language commands into structured actions"""
    try:
        system_prompt = """You are a task management command parser. Extract the action and parameters from user commands.

Available actions:
- create_task: Create a new task
- assign_task: Assign a task to someone
- update_task: Update task properties
- create_sprint: Create a new sprint
- start_sprint: Start a sprint (make it active)
- complete_sprint: Complete a sprint
- add_task_to_sprint: Add task to a sprint
- remove_task_from_sprint: Remove task from sprint
- list_tasks: List tasks with filters
- list_sprints: List sprints for a project
- list_projects: List user's projects
- create_project: Create a new project
- add_member: Add member to project
- remove_member: Remove member from project
- list_members: List project members

Return ONLY a JSON object with this structure:
{
    "action": "action_name",
    "params": {
        // relevant parameters
    }
}

For create_task, extract:
- title (required)
- description (optional)
- project_id or project_name (required)
- assignee_email or assignee_name (optional)
- priority (Low/Medium/High/Critical)
- issue_type (task/bug/story/epic)
- due_date (YYYY-MM-DD format)
- labels (array of strings)

For create_sprint, extract:
- name (required)
- project_id or project_name (required)
- start_date (YYYY-MM-DD)
- end_date (YYYY-MM-DD)
- goal (optional)

For start_sprint, extract:
- sprint_id or sprint_name (required)
- project_id or project_name (optional)

For complete_sprint, extract:
- sprint_id or sprint_name (required)
- project_id or project_name (optional)

For add_task_to_sprint, extract:
- task_id or task_title or ticket_id (required)
- sprint_id or sprint_name (optional - will use active sprint if not provided)
- project_id or project_name (optional)

For remove_task_from_sprint, extract:
- task_id or task_title or ticket_id (required)
- sprint_id or sprint_name (required)

For create_project, extract:
- name (required)
- description (optional)

For add_member, extract:
- email (required)
- project_id or project_name (required)

For remove_member, extract:
- email or user_id (required)
- project_id or project_name (required)

For list_members, extract:
- project_id or project_name (required)

For list_sprints, extract:
- project_id or project_name (required)

For list_tasks, extract:
- project_id or project_name (optional)
- status (optional)
- priority (optional)
- assignee (optional) - use "me" for current user

Examples:
"Create a high priority bug for payment gateway timeout in CDW, assign to kamlesh@gmail.com, due 2026-03-15"
→ {"action": "create_task", "params": {"title": "Payment gateway timeout issue", "priority": "High", "project_name": "CDW", "assignee_email": "kamlesh@gmail.com", "issue_type": "bug", "due_date": "2026-03-15"}}

"Create sprint Sprint 5 for Project CDW from 2026-03-01 to 2026-03-14"
→ {"action": "create_sprint", "params": {"name": "Sprint 5", "project_name": "CDW", "start_date": "2026-03-01", "end_date": "2026-03-14"}}

"Start the sprint1 sprint"
→ {"action": "start_sprint", "params": {"sprint_name": "sprint1"}}

"Complete the active sprint in CDW"
→ {"action": "complete_sprint", "params": {"sprint_name": "active", "project_name": "CDW"}}

"Add john@example.com to Project Alpha"
→ {"action": "add_member", "params": {"email": "john@example.com", "project_name": "Project Alpha"}}

"Remove sarah@example.com from CDW project"
→ {"action": "remove_member", "params": {"email": "sarah@example.com", "project_name": "CDW"}}

"List all members in CDW"
→ {"action": "list_members", "params": {"project_name": "CDW"}}

"Show all sprints in Project Alpha"
→ {"action": "list_sprints", "params": {"project_name": "Project Alpha"}}

"Create a new project called Mobile App"
→ {"action": "create_project", "params": {"name": "Mobile App"}}
"""

        user_message = f"Command: {command}"
        if context:
            user_message += f"\nContext: {json.dumps(context)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = chat_completion(messages=messages, max_tokens=500)

        # Parse JSON response
        content = response["content"].strip()
        content = re.sub(r"```json\s*|\s*```", "", content).strip()

        parsed = json.loads(content)

        print(f"   📋 Parsed command: {parsed}")

        return {"success": True, **parsed}

    except Exception as e:
        print(f"Error parsing command: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": f"Failed to parse command: {str(e)}"}


# ============================================================================
# TASK AUTOMATION - COMMAND EXECUTION
# ============================================================================


def execute_task_command(user_id: str, command: str, context: dict = None):
    """Execute task-related commands from AI Assistant"""
    print(f"\n{'=' * 60}")
    print(f"🎯 EXECUTING TASK COMMAND")
    print(f"{'=' * 60}")
    print(f"User ID: {user_id}")
    print(f"Command: {command}")
    print(f"Context: {context}")

    try:
        # Get user info
        user = User.find_by_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        user_email = user.get("email")
        user_role = user.get("role", "member").lower()

        print(f"   👤 User: {user_email} (Role: {user_role})")

        # Parse command using LLM
        parsed_command = parse_task_command(command, context)

        if not parsed_command["success"]:
            return parsed_command

        action = parsed_command["action"]
        params = parsed_command["params"]

        print(f"   ⚡ Action: {action}")
        print(f"   📝 Params: {params}")

        # Route to appropriate handler
        if action == "create_task":
            return handle_create_task(user_email, user_id, params)

        elif action == "assign_task":
            return handle_assign_task(user_email, user_id, params)

        elif action == "update_task":
            return handle_update_task(user_email, user_id, params)

        elif action == "create_sprint":
            if user_role != "admin":
                return {
                    "success": False,
                    "error": "Only Admin users can create sprints",
                }
            return handle_create_sprint(user_email, user_id, params)

        elif action == "start_sprint":
            return handle_start_sprint(user_id, params)

        elif action == "complete_sprint":
            return handle_complete_sprint(user_id, params)

        elif action == "add_task_to_sprint":
            return handle_add_task_to_sprint(user_email, user_id, params)

        elif action == "remove_task_from_sprint":
            return handle_remove_task_from_sprint(user_id, params)

        elif action == "list_tasks":
            return handle_list_tasks(user_id, params)

        elif action == "list_sprints":
            return handle_list_sprints(user_id, params)

        elif action == "list_projects":
            return handle_list_projects(user_id)

        elif action == "create_project":
            if user_role not in ["admin", "super-admin"]:
                return {
                    "success": False,
                    "error": "Only Admin users can create projects",
                }
            return handle_create_project(user_id, params)

        elif action == "add_member":
            return handle_add_member(user_id, params)

        elif action == "remove_member":
            return handle_remove_member(user_id, params)

        elif action == "list_members":
            return handle_list_members(user_id, params)

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        print(f"❌ Error executing task command: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": f"Failed to execute command: {str(e)}"}


# ============================================================================
# TASK AUTOMATION - ACTION HANDLERS
# ============================================================================


def handle_create_task(user_email: str, user_id: str, params: dict):
    """Handle task creation"""
    try:
        print(f"   🔨 Creating task...")

        # Resolve project_id
        project_id = params.get("project_id")
        if not project_id and params.get("project_name"):
            project = db.projects.find_one(
                {
                    "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
                    "name": {"$regex": f"^{params['project_name']}$", "$options": "i"},
                }
            )
            if project:
                project_id = str(project["_id"])
            else:
                return {
                    "success": False,
                    "error": f"Project '{params['project_name']}' not found",
                }

        if not project_id:
            return {"success": False, "error": "Project ID or name is required"}

        print(f"   📁 Project ID: {project_id}")

        # Create task using agent controller
        result = agent_create_task(
            requesting_user=user_email,
            title=params.get("title"),
            project_id=project_id,
            user_id=user_id,
            description=params.get("description", ""),
            assignee_email=params.get("assignee_email"),
            assignee_name=params.get("assignee_name"),
            priority=params.get("priority", "Medium"),
            status=params.get("status", "To Do"),
            due_date=params.get("due_date"),
            issue_type=params.get("issue_type", "task"),
            labels=params.get("labels", []),
        )

        print(f"   ✅ Task created: {result}")

        return {
            "success": True,
            "action": "create_task",
            "result": result,
            "message": f"✅ Task '{params.get('title')}' created successfully!",
        }

    except Exception as e:
        print(f"   ❌ Error creating task: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def handle_assign_task(user_email: str, user_id: str, params: dict):
    """Handle task assignment"""
    try:
        task_id = params.get("task_id")

        if not task_id and params.get("task_title"):
            projects = list(
                db.projects.find(
                    {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
                )
            )
            project_ids = [str(p["_id"]) for p in projects]

            task = db.tasks.find_one(
                {
                    "project_id": {"$in": project_ids},
                    "title": {"$regex": params["task_title"], "$options": "i"},
                }
            )

            if task:
                task_id = str(task["_id"])
            else:
                return {
                    "success": False,
                    "error": f"Task '{params['task_title']}' not found",
                }

        if not task_id:
            return {"success": False, "error": "Task ID or title is required"}

        assignee_identifier = params.get("assignee_email") or params.get(
            "assignee_name"
        )
        if not assignee_identifier:
            return {"success": False, "error": "Assignee email or name is required"}

        result = agent_assign_task(
            requesting_user=user_email,
            task_id=task_id,
            assignee_identifier=assignee_identifier,
            user_id=user_id,
        )

        return {
            "success": True,
            "action": "assign_task",
            "result": result,
            "message": f"✅ Task assigned to {assignee_identifier}",
        }

    except Exception as e:
        print(f"Error assigning task: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_update_task(user_email: str, user_id: str, params: dict):
    """Handle task updates"""
    try:
        task_id = params.get("task_id")

        if not task_id and params.get("task_title"):
            projects = list(
                db.projects.find(
                    {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
                )
            )
            project_ids = [str(p["_id"]) for p in projects]

            task = db.tasks.find_one(
                {
                    "project_id": {"$in": project_ids},
                    "title": {"$regex": params["task_title"], "$options": "i"},
                }
            )

            if task:
                task_id = str(task["_id"])

        if not task_id:
            return {"success": False, "error": "Task ID or title is required"}

        # Build update data
        update_data = {}
        for key in ["status", "priority", "description", "due_date", "labels"]:
            if key in params:
                update_data[key] = params[key]

        if not update_data:
            return {"success": False, "error": "No fields to update"}

        body = json.dumps(update_data)
        response = task_controller.update_task(body, task_id, user_id)

        if response.get("statusCode", 200) >= 400:
            error_body = (
                json.loads(response["body"])
                if isinstance(response["body"], str)
                else response["body"]
            )
            return {"success": False, "error": error_body.get("error", "Update failed")}

        result = (
            json.loads(response["body"])
            if isinstance(response["body"], str)
            else response["body"]
        )

        return {
            "success": True,
            "action": "update_task",
            "result": result,
            "message": f"✅ Task updated successfully",
        }

    except Exception as e:
        print(f"Error updating task: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_create_sprint(user_email: str, user_id: str, params: dict):
    """Handle sprint creation (Admin only)"""
    try:
        # Resolve project_id
        project_id = params.get("project_id")
        if not project_id and params.get("project_name"):
            project = db.projects.find_one(
                {
                    "user_id": user_id,
                    "name": {"$regex": f"^{params['project_name']}$", "$options": "i"},
                }
            )
            if project:
                project_id = str(project["_id"])
            else:
                return {
                    "success": False,
                    "error": f"Project '{params['project_name']}' not found or you don't own it",
                }

        if not project_id:
            return {"success": False, "error": "Project ID or name is required"}

        result = agent_create_sprint(
            requesting_user=user_email,
            name=params.get("name"),
            project_id=project_id,
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            user_id=user_id,
            goal=params.get("goal", ""),
            status=params.get("status", "planned"),
        )

        return {
            "success": True,
            "action": "create_sprint",
            "result": result,
            "message": f"✅ Sprint '{params.get('name')}' created successfully!",
        }

    except Exception as e:
        print(f"Error creating sprint: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_start_sprint(user_id: str, params: dict):
    """Handle starting a sprint"""
    try:
        sprint_id = params.get("sprint_id")

        # Find sprint by name if not provided
        if not sprint_id and params.get("sprint_name"):
            project_id = params.get("project_id")

            # If no project_id, try to find from context
            if not project_id and params.get("project_name"):
                project = db.projects.find_one(
                    {
                        "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
                        "name": {
                            "$regex": f"^{params['project_name']}$",
                            "$options": "i",
                        },
                    }
                )
                if project:
                    project_id = str(project["_id"])

            if project_id:
                sprint = db.sprints.find_one(
                    {
                        "project_id": project_id,
                        "name": {"$regex": params["sprint_name"], "$options": "i"},
                    }
                )
                if sprint:
                    sprint_id = str(sprint["_id"])

        if not sprint_id:
            return {"success": False, "error": "Sprint not found"}

        # Use sprint_controller to start sprint
        response = sprint_controller.start_sprint(sprint_id, user_id)

        if response.get("statusCode", 200) >= 400:
            error_body = (
                json.loads(response["body"])
                if isinstance(response["body"], str)
                else response["body"]
            )
            return {
                "success": False,
                "error": error_body.get("error", "Failed to start sprint"),
            }

        return {
            "success": True,
            "action": "start_sprint",
            "message": "✅ Sprint started successfully!",
        }

    except Exception as e:
        print(f"Error starting sprint: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_complete_sprint(user_id: str, params: dict):
    """Handle completing a sprint"""
    try:
        sprint_id = params.get("sprint_id")

        # Find sprint by name
        if not sprint_id and params.get("sprint_name"):
            project_id = params.get("project_id")

            if not project_id and params.get("project_name"):
                project = db.projects.find_one(
                    {
                        "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
                        "name": {
                            "$regex": f"^{params['project_name']}$",
                            "$options": "i",
                        },
                    }
                )
                if project:
                    project_id = str(project["_id"])

            if project_id:
                # Handle "active" keyword
                if params["sprint_name"].lower() == "active":
                    sprint = db.sprints.find_one(
                        {"project_id": project_id, "status": "active"}
                    )
                else:
                    sprint = db.sprints.find_one(
                        {
                            "project_id": project_id,
                            "name": {"$regex": params["sprint_name"], "$options": "i"},
                        }
                    )

                if sprint:
                    sprint_id = str(sprint["_id"])

        if not sprint_id:
            return {"success": False, "error": "Sprint not found"}

        # Use sprint_controller to complete sprint
        response = sprint_controller.complete_sprint(sprint_id, user_id)

        if response.get("statusCode", 200) >= 400:
            error_body = (
                json.loads(response["body"])
                if isinstance(response["body"], str)
                else response["body"]
            )
            return {
                "success": False,
                "error": error_body.get("error", "Failed to complete sprint"),
            }

        result = (
            json.loads(response["body"])
            if isinstance(response["body"], str)
            else response["body"]
        )

        return {
            "success": True,
            "action": "complete_sprint",
            "message": result.get("message", "✅ Sprint completed successfully!"),
        }

    except Exception as e:
        print(f"Error completing sprint: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_add_task_to_sprint(user_email: str, user_id: str, params: dict):
    """Handle adding task to sprint"""
    try:
        print(f"   🏃 Adding task to sprint...")

        task_id = params.get("task_id")
        sprint_id = params.get("sprint_id")

        # Find task by title or ticket_id
        if not task_id and (params.get("task_title") or params.get("ticket_id")):
            projects = list(
                db.projects.find(
                    {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
                )
            )
            project_ids = [str(p["_id"]) for p in projects]

            search_term = params.get("task_title") or params.get("ticket_id")
            task = db.tasks.find_one(
                {
                    "project_id": {"$in": project_ids},
                    "$or": [
                        {"title": {"$regex": search_term, "$options": "i"}},
                        {"ticket_id": {"$regex": search_term, "$options": "i"}},
                    ],
                }
            )

            if task:
                task_id = str(task["_id"])
            else:
                return {"success": False, "error": f"Task '{search_term}' not found"}

        # Find sprint by name
        if not sprint_id and params.get("sprint_name"):
            project_id = params.get("project_id")
            if not project_id and task_id:
                task = Task.find_by_id(task_id)
                if task:
                    project_id = task["project_id"]

            if project_id:
                if params["sprint_name"].lower() == "active":
                    sprint = db.sprints.find_one(
                        {"project_id": project_id, "status": "active"}
                    )
                else:
                    sprint = db.sprints.find_one(
                        {
                            "project_id": project_id,
                            "name": {"$regex": params["sprint_name"], "$options": "i"},
                        }
                    )

                if sprint:
                    sprint_id = str(sprint["_id"])
                else:
                    return {
                        "success": False,
                        "error": f"Sprint '{params['sprint_name']}' not found",
                    }

        # If still no sprint_id, find active sprint
        if not sprint_id and task_id:
            task = Task.find_by_id(task_id)
            if task:
                active_sprint = db.sprints.find_one(
                    {"project_id": task["project_id"], "status": "active"}
                )
                if active_sprint:
                    sprint_id = str(active_sprint["_id"])
                else:
                    return {"success": False, "error": "No active sprint found"}

        if not task_id or not sprint_id:
            return {"success": False, "error": "Task ID and Sprint ID are required"}

        print(f"   📌 Task ID: {task_id}, Sprint ID: {sprint_id}")

        # Add task to sprint
        body = json.dumps({"task_id": task_id})
        response = sprint_controller.add_task_to_sprint(sprint_id, body, user_id)

        if response.get("statusCode", 200) >= 400:
            error_body = (
                json.loads(response["body"])
                if isinstance(response["body"], str)
                else response["body"]
            )
            return {
                "success": False,
                "error": error_body.get("error", "Failed to add task to sprint"),
            }

        # Get task and sprint details
        task = Task.find_by_id(task_id)
        sprint = Sprint.find_by_id(sprint_id)

        print(f"   ✅ Task added to sprint successfully")

        return {
            "success": True,
            "action": "add_task_to_sprint",
            "result": {
                "task": {
                    "ticket_id": task.get("ticket_id", ""),
                    "title": task.get("title", ""),
                    "status": task.get("status", ""),
                },
                "sprint": {
                    "name": sprint.get("name", ""),
                    "status": sprint.get("status", ""),
                    "start_date": str(sprint.get("start_date", "")),
                    "end_date": str(sprint.get("end_date", "")),
                },
            },
            "message": f"✅ Task '{task.get('title', '')}' added to sprint '{sprint.get('name', '')}'",
        }

    except Exception as e:
        print(f"❌ Error adding task to sprint: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def handle_remove_task_from_sprint(user_id: str, params: dict):
    """Handle removing task from sprint"""
    try:
        task_id = params.get("task_id")
        sprint_id = params.get("sprint_id")

        # Find task
        if not task_id and params.get("task_title"):
            projects = list(
                db.projects.find(
                    {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
                )
            )
            project_ids = [str(p["_id"]) for p in projects]

            task = db.tasks.find_one(
                {
                    "project_id": {"$in": project_ids},
                    "title": {"$regex": params["task_title"], "$options": "i"},
                }
            )

            if task:
                task_id = str(task["_id"])

        # Find sprint
        if not sprint_id and params.get("sprint_name"):
            if task_id:
                task = Task.find_by_id(task_id)
                if task:
                    sprint = db.sprints.find_one(
                        {
                            "project_id": task["project_id"],
                            "name": {"$regex": params["sprint_name"], "$options": "i"},
                        }
                    )
                    if sprint:
                        sprint_id = str(sprint["_id"])

        if not task_id or not sprint_id:
            return {"success": False, "error": "Task ID and Sprint ID are required"}

        # Remove task from sprint
        response = sprint_controller.remove_task_from_sprint(
            sprint_id, task_id, user_id
        )

        if response.get("statusCode", 200) >= 400:
            error_body = (
                json.loads(response["body"])
                if isinstance(response["body"], str)
                else response["body"]
            )
            return {
                "success": False,
                "error": error_body.get("error", "Failed to remove task"),
            }

        return {
            "success": True,
            "action": "remove_task_from_sprint",
            "message": "✅ Task removed from sprint (moved to backlog)",
        }

    except Exception as e:
        print(f"Error removing task from sprint: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_list_tasks(user_id: str, params: dict):
    """Handle task listing"""
    try:
        print(f"   📋 Listing tasks with params: {params}")

        query = {}

        # Filter by assignee
        if params.get("assignee") == "me":
            query["assignee_id"] = user_id
        elif params.get("assignee"):
            if "@" in params["assignee"]:
                assignee = User.find_by_email(params["assignee"])
            else:
                assignee = db.users.find_one(
                    {"name": {"$regex": f"^{params['assignee']}$", "$options": "i"}}
                )

            if assignee:
                query["assignee_id"] = str(assignee["_id"])
            else:
                return {
                    "success": False,
                    "error": f"User '{params['assignee']}' not found",
                }

        # Filter by status
        if params.get("status"):
            if params["status"] == "overdue":
                query["due_date"] = {
                    "$lt": datetime.now(timezone.utc).replace(tzinfo=None)
                }
                query["status"] = {"$nin": ["Done", "Closed"]}
            else:
                query["status"] = params["status"]

        # Filter by priority
        if params.get("priority"):
            query["priority"] = params["priority"]

        # Filter by project
        if params.get("project_id"):
            query["project_id"] = params["project_id"]
        elif params.get("project_name"):
            project = db.projects.find_one(
                {
                    "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
                    "name": {"$regex": f"^{params['project_name']}$", "$options": "i"},
                }
            )
            if project:
                query["project_id"] = str(project["_id"])
            else:
                return {
                    "success": False,
                    "error": f"Project '{params['project_name']}' not found",
                }

        print(f"   🔍 Query: {query}")

        tasks = list(db.tasks.find(query).limit(50))

        print(f"   ✅ Found {len(tasks)} tasks")

        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append(
                {
                    "ticket_id": task.get("ticket_id", ""),
                    "title": task.get("title", ""),
                    "status": task.get("status", ""),
                    "priority": task.get("priority", ""),
                    "assignee": task.get("assignee_name", "Unassigned"),
                    "due_date": str(task.get("due_date", "No due date")),
                }
            )

        return {
            "success": True,
            "action": "list_tasks",
            "tasks": formatted_tasks,
            "count": len(formatted_tasks),
            "message": f"Found {len(formatted_tasks)} task(s)",
        }

    except Exception as e:
        print(f"Error listing tasks: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def handle_list_sprints(user_id: str, params: dict):
    """Handle sprint listing"""
    try:
        project_id = params.get("project_id")

        if not project_id and params.get("project_name"):
            project = db.projects.find_one(
                {
                    "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
                    "name": {"$regex": f"^{params['project_name']}$", "$options": "i"},
                }
            )
            if project:
                project_id = str(project["_id"])
            else:
                return {
                    "success": False,
                    "error": f"Project '{params['project_name']}' not found",
                }

        if not project_id:
            return {"success": False, "error": "Project ID or name is required"}

        sprints = list(db.sprints.find({"project_id": project_id}))

        formatted_sprints = []
        for sprint in sprints:
            formatted_sprints.append(
                {
                    "id": str(sprint["_id"]),
                    "name": sprint.get("name", ""),
                    "status": sprint.get("status", ""),
                    "start_date": str(sprint.get("start_date", "")),
                    "end_date": str(sprint.get("end_date", "")),
                    "goal": sprint.get("goal", ""),
                }
            )

        return {
            "success": True,
            "action": "list_sprints",
            "sprints": formatted_sprints,
            "count": len(formatted_sprints),
            "message": f"Found {len(formatted_sprints)} sprint(s)",
        }

    except Exception as e:
        print(f"Error listing sprints: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_list_projects(user_id: str):
    """Handle project listing"""
    try:
        projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )

        formatted_projects = []
        for project in projects:
            formatted_projects.append(
                {
                    "id": str(project["_id"]),
                    "name": project.get("name", ""),
                    "description": project.get("description", ""),
                    "status": project.get("status", ""),
                    "role": "Owner" if project.get("user_id") == user_id else "Member",
                }
            )

        return {
            "success": True,
            "action": "list_projects",
            "projects": formatted_projects,
            "count": len(formatted_projects),
            "message": f"Found {len(formatted_projects)} project(s)",
        }

    except Exception as e:
        print(f"Error listing projects: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_create_project(user_id: str, params: dict):
    """Handle project creation (Admin only)"""
    try:
        from controllers import project_controller

        project_data = {
            "name": params.get("name"),
            "description": params.get("description", ""),
        }

        body = json.dumps(project_data)
        response = project_controller.create_project(body, user_id)

        if response.get("statusCode", 200) >= 400:
            error_body = (
                json.loads(response["body"])
                if isinstance(response["body"], str)
                else response["body"]
            )
            return {
                "success": False,
                "error": error_body.get("error", "Failed to create project"),
            }

        result = (
            json.loads(response["body"])
            if isinstance(response["body"], str)
            else response["body"]
        )

        return {
            "success": True,
            "action": "create_project",
            "result": result.get("project"),
            "message": f"✅ Project '{params.get('name')}' created successfully!",
        }

    except Exception as e:
        print(f"Error creating project: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_add_member(user_id: str, params: dict):
    """Handle adding member to project"""
    try:
        project_id = params.get("project_id")

        if not project_id and params.get("project_name"):
            project = db.projects.find_one(
                {
                    "user_id": user_id,
                    "name": {"$regex": f"^{params['project_name']}$", "$options": "i"},
                }
            )
            if project:
                project_id = str(project["_id"])
            else:
                return {
                    "success": False,
                    "error": f"Project '{params['project_name']}' not found or you don't own it",
                }

        if not project_id:
            return {"success": False, "error": "Project ID or name is required"}

        email = params.get("email")
        if not email:
            return {"success": False, "error": "Email is required"}

        body = json.dumps({"email": email})
        response = member_controller.add_project_member(body, project_id, user_id)

        if response.get("statusCode", 200) >= 400:
            error_body = (
                json.loads(response["body"])
                if isinstance(response["body"], str)
                else response["body"]
            )
            return {
                "success": False,
                "error": error_body.get("error", "Failed to add member"),
            }

        result = (
            json.loads(response["body"])
            if isinstance(response["body"], str)
            else response["body"]
        )

        return {
            "success": True,
            "action": "add_member",
            "result": result.get("member"),
            "message": result.get("message", f"✅ Member {email} added successfully!"),
        }

    except Exception as e:
        print(f"Error adding member: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_remove_member(user_id: str, params: dict):
    """Handle removing member from project"""
    try:
        project_id = params.get("project_id")

        if not project_id and params.get("project_name"):
            project = db.projects.find_one(
                {
                    "user_id": user_id,
                    "name": {"$regex": f"^{params['project_name']}$", "$options": "i"},
                }
            )
            if project:
                project_id = str(project["_id"])
            else:
                return {
                    "success": False,
                    "error": f"Project '{params['project_name']}' not found or you don't own it",
                }

        if not project_id:
            return {"success": False, "error": "Project ID or name is required"}

        # Find member by email
        member_email = params.get("email")
        member_user_id = params.get("user_id")

        if member_email and not member_user_id:
            member = User.find_by_email(member_email)
            if member:
                member_user_id = str(member["_id"])
            else:
                return {"success": False, "error": f"User '{member_email}' not found"}

        if not member_user_id:
            return {"success": False, "error": "User email or ID is required"}

        response = member_controller.remove_project_member(
            project_id, member_user_id, user_id
        )

        if response.get("statusCode", 200) >= 400:
            error_body = (
                json.loads(response["body"])
                if isinstance(response["body"], str)
                else response["body"]
            )
            return {
                "success": False,
                "error": error_body.get("error", "Failed to remove member"),
            }

        return {
            "success": True,
            "action": "remove_member",
            "message": "✅ Member removed successfully!",
        }

    except Exception as e:
        print(f"Error removing member: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_list_members(user_id: str, params: dict):
    """Handle listing project members"""
    try:
        project_id = params.get("project_id")

        if not project_id and params.get("project_name"):
            project = db.projects.find_one(
                {
                    "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
                    "name": {"$regex": f"^{params['project_name']}$", "$options": "i"},
                }
            )
            if project:
                project_id = str(project["_id"])
            else:
                return {
                    "success": False,
                    "error": f"Project '{params['project_name']}' not found",
                }

        if not project_id:
            return {"success": False, "error": "Project ID or name is required"}

        response = member_controller.get_project_members(project_id, user_id)

        if response.get("statusCode", 200) >= 400:
            error_body = (
                json.loads(response["body"])
                if isinstance(response["body"], str)
                else response["body"]
            )
            return {
                "success": False,
                "error": error_body.get("error", "Failed to list members"),
            }

        result = (
            json.loads(response["body"])
            if isinstance(response["body"], str)
            else response["body"]
        )

        members = result.get("members", [])
        formatted_members = []
        for member in members:
            formatted_members.append(
                {
                    "name": member.get("name", ""),
                    "email": member.get("email", ""),
                    "role": member.get("role", "Member"),
                    "is_owner": member.get("is_owner", False),
                }
            )

        return {
            "success": True,
            "action": "list_members",
            "members": formatted_members,
            "count": len(formatted_members),
            "message": f"Found {len(formatted_members)} member(s)",
        }

    except Exception as e:
        print(f"Error listing members: {str(e)}")
        return {"success": False, "error": str(e)}


# ============================================================================
# MAIN MESSAGE HANDLER
# ============================================================================


def send_message(
    conversation_id: str, user_id: str, content: str, stream: bool = False
):
    """
    Send a message and get AI response with intelligent data-driven insights
    🆕 ENHANCED: Now analyzes user's MongoDB data to provide personalized responses
    🤖 NEW: Supports comprehensive task automation commands
    """
    try:
        print(f"\n🤖 Processing message for conversation {conversation_id}")
        print(f"   User: {user_id}, Content: {content[:50]}...")

        # Verify conversation exists and belongs to user
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        print(f"   ✅ Conversation verified")

        # 🤖 CHECK IF THIS IS A TASK AUTOMATION COMMAND
        is_command = detect_task_command(content)

        if is_command:
            print(f"   🔧 Detected task automation command: {content}")

            # Save user message
            user_message_id = AIMessage.create(
                conversation_id=conversation_id, role="user", content=content
            )
            print(f"   ✅ User message saved: {user_message_id}")

            # 🚨 CRITICAL: Actually execute the command
            print(f"   ⚡ Executing command...")
            command_result = execute_task_command(user_id, content)
            print(f"   📊 Command result: {command_result.get('success')}")

            # Create AI response based on command result
            if command_result.get("success"):
                ai_content = command_result.get(
                    "message", "Command executed successfully"
                )

                # Add detailed result information
                if command_result.get("result"):
                    result_data = command_result["result"]
                    if isinstance(result_data, dict):
                        # Format task result
                        if "task" in result_data:
                            task = result_data["task"]
                            ai_content += f"\n\n**Task Details:**\n"
                            ai_content += f"- **ID:** {task.get('ticket_id', 'N/A')}\n"
                            ai_content += f"- **Title:** {task.get('title', 'N/A')}\n"
                            ai_content += f"- **Status:** {task.get('status', 'N/A')}\n"
                            ai_content += (
                                f"- **Priority:** {task.get('priority', 'N/A')}\n"
                            )
                            if task.get("assignee_name"):
                                ai_content += (
                                    f"- **Assigned to:** {task['assignee_name']}\n"
                                )

                        # Format sprint result
                        elif "sprint" in result_data:
                            sprint = result_data["sprint"]
                            ai_content += f"\n\n**Sprint Details:**\n"
                            ai_content += f"- **Name:** {sprint.get('name', 'N/A')}\n"
                            ai_content += (
                                f"- **Status:** {sprint.get('status', 'N/A')}\n"
                            )
                            ai_content += f"- **Duration:** {sprint.get('start_date', 'N/A')} to {sprint.get('end_date', 'N/A')}\n"

                # Add task list if present
                if command_result.get("tasks"):
                    ai_content += f"\n\n**Tasks ({command_result['count']}):**\n"
                    for task in command_result["tasks"][:10]:
                        ai_content += f"- **[{task['ticket_id']}]** {task['title']}\n"
                        ai_content += f"  Status: {task['status']} | Priority: {task['priority']} | Assignee: {task.get('assignee', 'Unassigned')}\n"

                    if command_result["count"] > 10:
                        ai_content += (
                            f"\n_...and {command_result['count'] - 10} more tasks_\n"
                        )

                # Add sprint list if present
                if command_result.get("sprints"):
                    ai_content += f"\n\n**Sprints ({command_result['count']}):**\n"
                    for sprint in command_result["sprints"]:
                        ai_content += f"- **{sprint['name']}** ({sprint['status']})\n"
                        ai_content += (
                            f"  {sprint['start_date']} to {sprint['end_date']}\n"
                        )

                # Add project list if present
                if command_result.get("projects"):
                    ai_content += f"\n\n**Projects ({command_result['count']}):**\n"
                    for project in command_result["projects"]:
                        ai_content += f"- **{project['name']}** ({project['role']})\n"
                        if project.get("description"):
                            ai_content += f"  _{project['description']}_\n"

                # Add member list if present
                if command_result.get("members"):
                    ai_content += f"\n\n**Members ({command_result['count']}):**\n"
                    for member in command_result["members"]:
                        role_badge = "👑" if member.get("is_owner") else "👤"
                        ai_content += (
                            f"- {role_badge} **{member['name']}** ({member['email']})\n"
                        )
                        ai_content += f"  Role: {member['role']}\n"
            else:
                ai_content = f"❌ **Command failed:** {command_result.get('error', 'Unknown error')}\n\n"
                ai_content += "Please check your command and try again. You can ask me for help with the correct format."

            # Save AI response
            ai_message_id = AIMessage.create(
                conversation_id=conversation_id, role="assistant", content=ai_content
            )
            print(f"   ✅ AI response saved: {ai_message_id}")

            # Update conversation title if it's the first message
            if conversation.get("message_count", 0) <= 2:
                title = content[:50] + ("..." if len(content) > 50 else "")
                AIConversation.update_title(conversation_id, title)

            return {
                "success": True,
                "message": {
                    "_id": str(ai_message_id),
                    "role": "assistant",
                    "content": ai_content,
                    "created_at": datetime.utcnow().isoformat(),
                },
                "command_executed": True,
                "command_result": command_result,
            }

        # REGULAR AI CONVERSATION (No command detected)
        # Save user message
        user_message_id = AIMessage.create(
            conversation_id=conversation_id, role="user", content=content
        )
        print(f"   ✅ User message saved: {user_message_id}")

        # Get conversation history for context
        recent_messages = AIMessage.get_recent_context(conversation_id, limit=20)
        print(f"   📚 Loaded {len(recent_messages)} previous messages")

        # 🆕 ANALYZE USER DATA for intelligent insights
        print(f"   🔍 Analyzing user data from MongoDB...")

        user_data = analyze_user_data_for_ai(user_id)

        # Build system prompt with user's data context
        if user_data:
            system_prompt = build_ai_system_prompt(user_data)
            print(f"   ✅ Enhanced system prompt with user data:")
            print(f"      - Tasks: {user_data['stats']['tasks']['total']}")
            print(f"      - Projects: {user_data['stats']['projects']['total']}")
            print(f"      - Overdue: {user_data['stats']['tasks']['overdue']}")
            print(
                f"      - Velocity: {user_data['velocity']['completed_last_30_days']} tasks/30d"
            )
        else:
            system_prompt = None
            print(f"   ⚠️ Using default system prompt (no user data available)")

        # Prepare messages for API with enhanced context
        api_messages = get_context_with_system_prompt(
            recent_messages, system_prompt=system_prompt
        )
        print(f"   📝 Prepared {len(api_messages)} messages for API")

        # Truncate if needed
        api_messages = truncate_context(api_messages, max_tokens=8000)
        print(f"   ✂️ Truncated to {len(api_messages)} messages")

        # Handle streaming vs non-streaming
        if stream:
            return stream_ai_response(conversation_id, api_messages)
        else:
            print(f"   🚀 Calling Azure OpenAI with data-driven context...")
            response = chat_completion(messages=api_messages, max_tokens=2000)
            print(f"   ✅ Got AI response: {response['content'][:100]}...")

            # Save AI response
            ai_message_id = AIMessage.create(
                conversation_id=conversation_id,
                role="assistant",
                content=response["content"],
            )
            print(f"   ✅ AI response saved: {ai_message_id}")

            # Update token usage
            if "tokens" in response:
                AIMessage.update_tokens(ai_message_id, response["tokens"]["total"])

            # Update conversation title if it's the first message
            if conversation.get("message_count", 0) <= 2:
                title = content[:50] + ("..." if len(content) > 50 else "")
                AIConversation.update_title(conversation_id, title)

            # 🆕 Extract insights from user data for frontend display
            insights = extract_insights_from_data(user_data) if user_data else []

            return {
                "success": True,
                "message": {
                    "_id": str(ai_message_id),
                    "role": "assistant",
                    "content": response["content"],
                    "created_at": datetime.utcnow().isoformat(),
                    "tokens_used": response.get("tokens", {}).get("total", 0),
                },
                "tokens": response.get("tokens", {}),
                "insights": insights,
                "user_data_summary": {
                    "tasks_total": user_data["stats"]["tasks"]["total"]
                    if user_data
                    else 0,
                    "tasks_overdue": user_data["stats"]["tasks"]["overdue"]
                    if user_data
                    else 0,
                    "projects_total": user_data["stats"]["projects"]["total"]
                    if user_data
                    else 0,
                    "velocity": user_data["velocity"]["avg_per_week"]
                    if user_data
                    else 0,
                }
                if user_data
                else None,
                "command_executed": False,
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in send_message: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STREAMING & OTHER FEATURES (Keep existing implementations)
# ============================================================================


def stream_ai_response(conversation_id: str, api_messages: List[dict]):
    """Stream AI response chunks"""

    async def generate():
        try:
            full_content = ""
            for chunk in chat_completion_streaming(api_messages):
                full_content += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            ai_message_id = AIMessage.create(
                conversation_id=conversation_id, role="assistant", content=full_content
            )
            yield f"data: {json.dumps({'done': True, 'message_id': str(ai_message_id)})}\n\n"
        except Exception as e:
            print(f"Error in stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


def generate_ai_image(conversation_id: str, user_id: str, prompt: str):
    """Generate an image using FLUX-1.1-pro"""
    try:
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        user_message_id = AIMessage.create(
            conversation_id=conversation_id,
            role="user",
            content=f"Generate image: {prompt}",
        )

        result = generate_image(prompt)

        if result.get("success"):
            ai_message_id = AIMessage.create(
                conversation_id=conversation_id,
                role="assistant",
                content=f"I've generated an image based on your prompt: '{prompt}'",
                image_url=result.get("image_url") or result.get("filepath"),
            )
            return {
                "success": True,
                "message": {
                    "_id": str(ai_message_id),
                    "role": "assistant",
                    "content": f"Here's your generated image for: '{prompt}'",
                    "image_url": result.get("image_url") or result.get("filepath"),
                    "created_at": datetime.utcnow().isoformat(),
                },
                "image": result,
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Image generation failed: {result.get('error', 'Unknown error')}",
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def upload_file_to_conversation(
    conversation_id: str, user_id: str, file: UploadFile, message: Optional[str] = None
):
    """Upload a file and add it to conversation context"""
    try:
        print(f"\n📎 Processing file upload for conversation {conversation_id}")
        print(f"   File: {file.filename}, Type: {file.content_type}")

        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        upload_dir = "uploads/ai_attachments"
        os.makedirs(upload_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(upload_dir, filename)

        with open(filepath, "wb") as f:
            f.write(file.file.read())

        print(f"   ✅ File saved: {filepath}")

        extraction_result = extract_file_content(filepath, file.content_type)

        if not extraction_result.get("success"):
            print(f"   ⚠️ Could not extract content: {extraction_result.get('error')}")
            content = (
                message
                or f"Uploaded file: {file.filename} (content extraction not supported)"
            )
        else:
            print(f"   ✅ Content extracted: {extraction_result.get('content_type')}")
            file_content = extraction_result.get("content", "")
            file_content = summarize_file_content(file_content, max_tokens=3000)
            content = f"User uploaded file '{file.filename}'.\n\nFile Contents:\n{file_content}"

        message_id = AIMessage.create(
            conversation_id=conversation_id,
            role="user",
            content=content,
            attachments=[
                {
                    "filename": file.filename,
                    "filepath": filepath,
                    "content_type": file.content_type,
                    "size": os.path.getsize(filepath),
                    "extracted": extraction_result.get("success", False),
                }
            ],
        )

        print(f"   ✅ Message created with file content: {message_id}")

        if extraction_result.get("success"):
            file_type = extraction_result.get("content_type", "file")
            ai_content = (
                f"I've received and analyzed your {file_type} file '{file.filename}'. "
            )

            if file_type == "csv":
                rows = extraction_result.get("rows", 0)
                columns = extraction_result.get("columns", 0)
                ai_content += f"It contains {rows} rows and {columns} columns. "
            elif file_type == "pdf":
                pages = extraction_result.get("pages", 0)
                ai_content += f"It has {pages} pages. "

            ai_content += "I can now answer questions about this file. What would you like to know?"

            ai_message_id = AIMessage.create(
                conversation_id=conversation_id, role="assistant", content=ai_content
            )

            return {
                "success": True,
                "message": ai_content,
                "file": {
                    "filename": file.filename,
                    "filepath": filepath,
                    "url": f"/{filepath}",
                    "extracted": True,
                    "metadata": {
                        "type": file_type,
                        **{
                            k: v
                            for k, v in extraction_result.items()
                            if k not in ["success", "content", "error"]
                        },
                    },
                },
                "message_id": str(message_id),
                "ai_message_id": str(ai_message_id),
            }
        else:
            return {
                "success": True,
                "message": f"File '{file.filename}' uploaded, but content extraction not supported for this file type.",
                "file": {
                    "filename": file.filename,
                    "filepath": filepath,
                    "url": f"/{filepath}",
                    "extracted": False,
                },
                "message_id": str(message_id),
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading file: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def delete_conversation(conversation_id: str, user_id: str):
    """Delete a conversation and all its messages"""
    try:
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        AIConversation.delete(conversation_id)
        return {"success": True, "message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def update_conversation_title(conversation_id: str, user_id: str, title: str):
    """Update conversation title"""
    try:
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        AIConversation.update_title(conversation_id, title)
        return {"success": True, "message": "Title updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating title: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def get_user_insights(user_id: str):
    """Get data-driven insights for user"""
    try:
        user_data = analyze_user_data_for_ai(user_id)

        if not user_data:
            return {"success": False, "error": "Could not analyze user data"}

        insights = extract_insights_from_data(user_data)

        return {
            "success": True,
            "insights": insights,
            "summary": {
                "tasks": user_data["stats"]["tasks"],
                "projects": user_data["stats"]["projects"],
                "velocity": user_data["velocity"],
                "team": {
                    "collaborators": user_data["team"]["total_collaborators"],
                    "blocked_tasks": user_data["blockers"]["blocked_tasks"],
                },
            },
            "recent_activity": user_data["recentTasks"][:5],
            "top_projects": user_data["topProjects"][:5],
        }
    except Exception as e:
        print(f"Error getting user insights: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADDITIONAL BULK OPERATIONS - ADD THESE TO YOUR CONTROLLER
# ============================================================================


def handle_bulk_approve_close(user_id: str, params: dict):
    """Handle bulk approve and close operations"""
    try:
        print(f"   📋 Bulk approve and close tasks...")

        # Find all tasks pending approval assigned to user
        query = {
            "assignee_id": user_id,
            "status": {"$in": ["Dev Complete", "Testing", "Pending Approval"]},
        }

        # Filter by project if specified
        if params.get("project_id"):
            query["project_id"] = params["project_id"]
        elif params.get("project_name"):
            project = db.projects.find_one(
                {
                    "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
                    "name": {"$regex": f"^{params['project_name']}$", "$options": "i"},
                }
            )
            if project:
                query["project_id"] = str(project["_id"])

        # Find all tasks matching criteria
        tasks = list(db.tasks.find(query))

        if not tasks:
            return {
                "success": True,
                "action": "bulk_approve_close",
                "count": 0,
                "message": "No tasks found pending approval",
            }

        # Update all tasks to Closed
        updated_count = 0
        closed_tasks = []

        for task in tasks:
            task_id = str(task["_id"])

            # Update task to Closed
            update_data = {"status": "Closed"}
            body = json.dumps(update_data)

            response = task_controller.update_task(body, task_id, user_id)

            if response.get("statusCode", 200) < 400:
                updated_count += 1
                closed_tasks.append(
                    {
                        "ticket_id": task.get("ticket_id", ""),
                        "title": task.get("title", ""),
                        "old_status": task.get("status", ""),
                        "new_status": "Closed",
                    }
                )

        return {
            "success": True,
            "action": "bulk_approve_close",
            "count": updated_count,
            "tasks": closed_tasks,
            "message": f"✅ Approved and closed {updated_count} task(s)",
        }

    except Exception as e:
        print(f"Error in bulk approve/close: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def handle_bulk_status_update(user_id: str, params: dict):
    """Handle bulk status updates"""
    try:
        print(f"   📋 Bulk status update...")

        # Get target status
        target_status = params.get("target_status", "Closed")

        # Build query
        query = {}

        # Filter by current status
        if params.get("current_status"):
            if isinstance(params["current_status"], list):
                query["status"] = {"$in": params["current_status"]}
            else:
                query["status"] = params["current_status"]

        # Filter by assignee
        if params.get("assignee") == "me":
            query["assignee_id"] = user_id

        # Filter by project
        if params.get("project_id"):
            query["project_id"] = params["project_id"]
        elif params.get("project_name"):
            project = db.projects.find_one(
                {
                    "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
                    "name": {"$regex": f"^{params['project_name']}$", "$options": "i"},
                }
            )
            if project:
                query["project_id"] = str(project["_id"])

        # Find matching tasks
        tasks = list(db.tasks.find(query))

        if not tasks:
            return {
                "success": True,
                "action": "bulk_status_update",
                "count": 0,
                "message": "No tasks found matching criteria",
            }

        # Update all tasks
        updated_count = 0
        updated_tasks = []

        for task in tasks:
            task_id = str(task["_id"])

            update_data = {"status": target_status}
            body = json.dumps(update_data)

            response = task_controller.update_task(body, task_id, user_id)

            if response.get("statusCode", 200) < 400:
                updated_count += 1
                updated_tasks.append(
                    {
                        "ticket_id": task.get("ticket_id", ""),
                        "title": task.get("title", ""),
                        "old_status": task.get("status", ""),
                        "new_status": target_status,
                    }
                )

        return {
            "success": True,
            "action": "bulk_status_update",
            "count": updated_count,
            "tasks": updated_tasks,
            "message": f"✅ Updated {updated_count} task(s) to {target_status}",
        }

    except Exception as e:
        print(f"Error in bulk status update: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ============================================================================
# UPDATE THESE FUNCTIONS IN YOUR CONTROLLER
# ============================================================================


def detect_task_command(message: str) -> bool:
    """Detect if message contains a task automation command"""
    command_keywords = [
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
        "list all tasks",
        "show all tasks",
        "tasks in",
        "tasks for",
        "update priority",
        "change priority",
        "set priority",
        # Bulk operations - NEW
        "approve all",
        "close all",
        "approve and close",
        "bulk approve",
        "approve pending",
        "close pending",
        "approve all pending",
        "mark all as",
        "update all to",
        "change all to",
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
        # Member operations
        "add member",
        "add user",
        "invite member",
        "add to project",
        "add as member",
        "add someone",
        "invite to project",
        "remove member",
        "remove user",
        "kick member",
        "list members",
        "show members",
        "project members",
    ]

    message_lower = message.lower()
    return any(keyword in message_lower for keyword in command_keywords)


def parse_task_command(command: str, context: dict = None):
    """Use Azure OpenAI to parse natural language commands into structured actions"""
    try:
        system_prompt = """You are a task management command parser. Extract the action and parameters from user commands.

Available actions:
- create_task: Create a new task
- assign_task: Assign a task to someone
- update_task: Update task properties
- bulk_approve_close: Approve and close all pending tasks
- bulk_status_update: Update status for multiple tasks
- create_sprint: Create a new sprint
- start_sprint: Start a sprint (make it active)
- complete_sprint: Complete a sprint
- add_task_to_sprint: Add task to a sprint
- remove_task_from_sprint: Remove task from sprint
- list_tasks: List tasks with filters
- list_sprints: List sprints for a project
- list_projects: List user's projects
- create_project: Create a new project
- add_member: Add member to project
- remove_member: Remove member from project
- list_members: List project members

Return ONLY a JSON object with this structure:
{
    "action": "action_name",
    "params": {
        // relevant parameters
    }
}

For bulk_approve_close, extract:
- project_id or project_name (optional - if not specified, applies to all user's tasks)
- current_status (optional - defaults to ["Dev Complete", "Testing", "Pending Approval"])

For bulk_status_update, extract:
- target_status (required - e.g., "Closed", "Done")
- current_status (optional - filter which tasks to update)
- project_id or project_name (optional)
- assignee (optional - "me" for current user)

For add_member, extract:
- email (required)
- project_id or project_name (required)

Examples:
"Approve all pending tasks and close them"
→ {"action": "bulk_approve_close", "params": {}}

"Approve all pending approve and close tasks from my side"
→ {"action": "bulk_approve_close", "params": {}}

"Close all testing tasks in DOIT project"
→ {"action": "bulk_status_update", "params": {"target_status": "Closed", "current_status": "Testing", "project_name": "DOIT"}}

"Mark all my Dev Complete tasks as Done"
→ {"action": "bulk_status_update", "params": {"target_status": "Done", "current_status": "Dev Complete", "assignee": "me"}}

"Add kamlesh@gmail.com to my DOIT project as member"
→ {"action": "add_member", "params": {"email": "kamlesh@gmail.com", "project_name": "DOIT"}}

"Add john@example.com to Project Alpha"
→ {"action": "add_member", "params": {"email": "john@example.com", "project_name": "Project Alpha"}}
"""

        user_message = f"Command: {command}"
        if context:
            user_message += f"\nContext: {json.dumps(context)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = chat_completion(messages=messages, max_tokens=500)

        # Parse JSON response
        content = response["content"].strip()
        content = re.sub(r"```json\s*|\s*```", "", content).strip()

        parsed = json.loads(content)

        print(f"   📋 Parsed command: {parsed}")

        return {"success": True, **parsed}

    except Exception as e:
        print(f"Error parsing command: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": f"Failed to parse command: {str(e)}"}


def execute_task_command(user_id: str, command: str, context: dict = None):
    """Execute task-related commands from AI Assistant"""
    print(f"\n{'=' * 60}")
    print(f"🎯 EXECUTING TASK COMMAND")
    print(f"{'=' * 60}")
    print(f"User ID: {user_id}")
    print(f"Command: {command}")
    print(f"Context: {context}")

    try:
        # Get user info
        user = User.find_by_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        user_email = user.get("email")
        user_role = user.get("role", "member").lower()

        print(f"   👤 User: {user_email} (Role: {user_role})")

        # Parse command using LLM
        parsed_command = parse_task_command(command, context)

        if not parsed_command["success"]:
            return parsed_command

        action = parsed_command["action"]
        params = parsed_command["params"]

        print(f"   ⚡ Action: {action}")
        print(f"   📝 Params: {params}")

        # Route to appropriate handler
        if action == "create_task":
            return handle_create_task(user_email, user_id, params)

        elif action == "assign_task":
            return handle_assign_task(user_email, user_id, params)

        elif action == "update_task":
            return handle_update_task(user_email, user_id, params)

        elif action == "bulk_approve_close":
            return handle_bulk_approve_close(user_id, params)

        elif action == "bulk_status_update":
            return handle_bulk_status_update(user_id, params)

        elif action == "create_sprint":
            if user_role != "admin":
                return {
                    "success": False,
                    "error": "Only Admin users can create sprints",
                }
            return handle_create_sprint(user_email, user_id, params)

        elif action == "start_sprint":
            return handle_start_sprint(user_id, params)

        elif action == "complete_sprint":
            return handle_complete_sprint(user_id, params)

        elif action == "add_task_to_sprint":
            return handle_add_task_to_sprint(user_email, user_id, params)

        elif action == "remove_task_from_sprint":
            return handle_remove_task_from_sprint(user_id, params)

        elif action == "list_tasks":
            return handle_list_tasks(user_id, params)

        elif action == "list_sprints":
            return handle_list_sprints(user_id, params)

        elif action == "list_projects":
            return handle_list_projects(user_id)

        elif action == "create_project":
            if user_role not in ["admin", "super-admin"]:
                return {
                    "success": False,
                    "error": "Only Admin users can create projects",
                }
            return handle_create_project(user_id, params)

        elif action == "add_member":
            return handle_add_member(user_id, params)

        elif action == "remove_member":
            return handle_remove_member(user_id, params)

        elif action == "list_members":
            return handle_list_members(user_id, params)

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        print(f"❌ Error executing task command: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": f"Failed to execute command: {str(e)}"}
