"""
Local Private AI Agent Controller
Stack: Ollama (local LLM) + LlamaIndex + ChromaDB

Mirrors azure_agent_controller.py — same conversation model,
same context enrichment, same response shape.
"""

from fastapi import HTTPException
from datetime import datetime
from models.ai_conversation import AIConversation, AIMessage
from utils.local_agent_utils import (
    send_message_to_local_agent,
    clear_chat_history,
    get_chat_history,
    check_local_agent_health,
    OLLAMA_MODEL,
    CHROMA_DB_PATH,
)
from utils.ai_data_analyzer import analyze_user_data_for_ai
from utils.cache_utils import (
    get_cached_user_context,
    cache_user_context,
    clear_user_context_cache,
)
from utils.local_agent_automation import (
    detect_task_automation,
    parse_task_command_with_ollama,
    check_automation_permission,
    resolve_project_id,
    find_task_by_title_or_id,
    find_sprint_by_name_or_id,
)
from controllers.agent_task_controller import agent_create_task, agent_assign_task
from controllers.agent_sprint_controller import agent_create_sprint
from controllers import task_controller
from models.user import User
from database import db
from bson import ObjectId
import json


# ─── Conversation CRUD (reuse DOIT AIConversation model) ──────────────────────


def create_local_conversation(user_id: str, title: str = "Local AI Chat"):
    try:
        conversation_id = AIConversation.create(user_id, title)
        conversation = AIConversation.get_by_id(conversation_id)
        if conversation:
            conversation["_id"] = str(conversation["_id"])
        return {"success": True, "conversation": conversation}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def get_local_conversations(user_id: str):
    try:
        conversations = AIConversation.get_user_conversations(user_id)
        for c in conversations:
            c["_id"] = str(c["_id"])
        return {"success": True, "conversations": conversations}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def get_local_conversation_messages(conversation_id: str):
    try:
        messages = AIMessage.get_conversation_messages(conversation_id)
        for m in messages:
            m["_id"] = str(m["_id"])
        return {"success": True, "messages": messages}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def delete_local_conversation(conversation_id: str, user_id: str):
    try:
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Clear in-memory chat history so the next conversation starts clean
        clear_chat_history(user_id)
        clear_user_context_cache(user_id)  # Also clear user context cache
        AIConversation.delete(conversation_id)
        return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Core: send message ────────────────────────────────────────────────────────


def send_message_to_local(
    conversation_id: str,
    user_id: str,
    content: str,
    include_user_context: bool = True,
):
    """
    Route a user message through Ollama + LlamaIndex + ChromaDB (RAG)
    and persist both the user message and the local agent reply.
    """
    print(f"\n🦙 [Local Agent] Processing message for user {user_id}")
    print(f"   Conversation: {conversation_id}")
    print(f"   Content: {content[:80]}...")

    try:
        # ── Verify conversation ──────────────────────────────────────────────
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # ── Save user message ────────────────────────────────────────────────
        AIMessage.create(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )

        # ── Check for task automation commands ────────────────────────────────
        if detect_task_automation(content):
            print("   🔧 Task automation detected")
            automation_result = handle_local_automation(user_id, content)
            if automation_result.get("success"):
                print(f"   ✅ Automation executed: {automation_result.get('action')}")
                # Log automation result
                ai_content = f"✅ **Action Completed**\n\n{automation_result.get('message', 'Action executed successfully')}\n\nDetails:\n{json.dumps(automation_result.get('result', {}), indent=2)}"
                ai_message_id = AIMessage.create(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=ai_content,
                )
                return {
                    "success": True,
                    "message": {
                        "_id": str(ai_message_id),
                        "role": "assistant",
                        "content": ai_content,
                        "created_at": datetime.utcnow().isoformat(),
                        "automation": True,
                        "action": automation_result.get("action"),
                    },
                    "model": "ollama-automation",
                }
            else:
                print(f"   ⚠️  Automation failed: {automation_result.get('error')}")

        # ── Build user context (identical shape to Foundry controller) ───────
        context = None
        if include_user_context:
            # Check cache first (60s TTL) to avoid database hit on every message
            context = get_cached_user_context(user_id)

            if context is None:
                # Cache miss — fetch and cache user data
                user_data = analyze_user_data_for_ai(user_id)
                if user_data:
                    stats = user_data.get("stats", {})
                    tasks = stats.get("tasks", {})
                    projects = stats.get("projects", {})
                    sprints = stats.get("sprints", {})
                    velocity = user_data.get("velocity", {})
                    blockers = user_data.get("blockers", {})

                    context = {
                        "user_name": user_data["user"]["name"],
                        "user_role": user_data["user"]["role"],
                        "tasks_total": tasks.get("total", 0),
                        "tasks_overdue": tasks.get("overdue", 0),
                        "tasks_due_soon": tasks.get("dueSoon", 0),
                        "tasks_done_week": tasks.get("completedWeek", 0),
                        "status_breakdown": tasks.get("statusBreakdown", {}),
                        "priority_breakdown": tasks.get("priorityBreakdown", {}),
                        "projects_total": projects.get("total", 0),
                        "sprints_active": sprints.get("active", 0),
                        "velocity_30d": velocity.get("completed_last_30_days", 0),
                        "blocked_tasks": blockers.get("blocked_tasks", 0),
                        "recent_tasks": [
                            {
                                "ticket": t.get("ticket_id"),
                                "title": t.get("title"),
                                "status": t.get("status"),
                                "due": t.get("dueDate"),
                            }
                            for t in user_data.get("recentTasks", [])[:8]
                        ],
                    }
                    # Cache for 60 seconds to reduce DB queries
                    cache_user_context(user_id, context, ttl=60)
                    print(
                        f"   📊 Context: {tasks.get('total')} tasks, "
                        f"{tasks.get('overdue')} overdue [from DB]"
                    )
                else:
                    print("   ⚠️  User context unavailable")
            else:
                # Cache hit — faster path
                print(f"   ⚡ Context cached: {context.get('tasks_total')} tasks")

        # ── Call local agent (Ollama + RAG) ──────────────────────────────────
        result = send_message_to_local_agent(
            user_id=user_id,
            message=content,
            context=context,
        )

        if not result["success"]:
            err = result.get("error", "Local agent call failed")
            print(f"   ❌ Local agent error: {err}")
            ai_content = (
                f"❌ Local AI error: {err}\n\n"
                "Make sure Ollama is running (`ollama serve`) and the model is pulled "
                f"(`ollama pull {OLLAMA_MODEL}`)."
            )
        else:
            ai_content = result["response"]
            rag_label = " [+RAG]" if result.get("rag_used") else ""
            print(f"   ✅ Local agent replied ({len(ai_content)} chars){rag_label}")

        # ── Save agent reply ──────────────────────────────────────────────────
        ai_message_id = AIMessage.create(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_content,
        )

        tokens = result.get("tokens", {})
        if tokens.get("total"):
            AIMessage.update_tokens(ai_message_id, tokens["total"])

        # Auto-title from first message
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
                "tokens_used": tokens.get("total", 0),
            },
            "model": result.get("model", OLLAMA_MODEL),
            "rag_used": result.get("rag_used", False),
            "tokens": tokens,
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ [Local Agent] Unexpected error: {exc}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ─── History management ────────────────────────────────────────────────────────


def reset_local_history(user_id: str):
    """Wipe the in-memory chat history for this user."""
    clear_chat_history(user_id)
    return {
        "success": True,
        "message": "Local chat history cleared. Next message starts fresh.",
    }


def get_local_history(user_id: str):
    """Return the current in-memory chat history (for debugging)."""
    history = get_chat_history(user_id)
    return {"success": True, "history": history, "turns": len(history) // 2}


# ─── Health ────────────────────────────────────────────────────────────────────


def local_agent_health_check():
    health = check_local_agent_health()
    return {
        "service": "Local AI (Ollama + LlamaIndex + ChromaDB)",
        "healthy": health.get("healthy", False),
        "ollama_url": health.get("ollama_url"),
        "model": health.get("model"),
        "model_available": health.get("model_available", False),
        "available_models": health.get("available_models", []),
        "chroma_path": CHROMA_DB_PATH,
        "error": health.get("error"),
    }


# ─── Task Automation Handlers ─────────────────────────────────────────────────


def handle_local_automation(user_id: str, command: str):
    """
    Handle task automation commands in local agent.
    Supports task creation, assignment, sprint management with role-based access.
    """
    print(f"\n🎯 [Local Automation] Processing command for user {user_id}")

    try:
        # Get user info
        user = User.find_by_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        user_email = user.get("email")
        user_role = user.get("role", "member").lower()

        # Get user context for command parsing
        context = get_cached_user_context(user_id)
        if not context:
            user_data = analyze_user_data_for_ai(user_id)
            if user_data:
                stats = user_data.get("stats", {})
                context = {
                    "user_role": user_role,
                    "projects": stats.get("projects", {}),
                    "sprints": stats.get("sprints", {}),
                }
            else:
                context = {"user_role": user_role}

        # Parse command using Ollama
        from utils.local_agent_utils import get_llm

        llm = get_llm()

        parsed = parse_task_command_with_ollama(command, context, llm)

        if not parsed.get("success"):
            return parsed

        action = parsed.get("action")
        params = parsed.get("params", {})

        print(f"   ⚡ Action: {action}")
        print(f"   📝 Params: {params}")

        # Check permission
        allowed, error_msg = check_automation_permission(user_id, action)
        if not allowed:
            return {"success": False, "error": error_msg}

        # Route to handler
        if action == "create_task":
            return local_handle_create_task(user_email, user_id, params)

        elif action == "assign_task":
            return local_handle_assign_task(user_email, user_id, params)

        elif action == "update_task":
            return local_handle_update_task(user_email, user_id, params)

        elif action == "create_sprint":
            return local_handle_create_sprint(user_email, user_id, params)

        elif action == "list_tasks":
            return local_handle_list_tasks(user_id, params)

        elif action == "list_projects":
            return local_handle_list_projects(user_id)

        elif action == "list_sprints":
            return local_handle_list_sprints(user_id, params)

        elif action == "add_task_to_sprint":
            return local_handle_add_task_to_sprint(user_email, user_id, params)

        elif action == "list_members":
            return local_handle_list_members(user_id, params)

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        print(f"❌ Automation error: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def local_handle_create_task(user_email: str, user_id: str, params: dict):
    """Handle task creation via local agent."""
    try:
        print(f"   🔨 Creating task: {params.get('title')}")

        # Validate required parameters
        if not params.get("title"):
            return {
                "success": False,
                "error": "Task title is required. Example: 'Create a task called Fix Login in CDW project'",
            }

        # Resolve project - try project_name first, then project_id
        project_id = params.get("project_id")
        project_name = params.get("project_name")

        # If project_id is "None" (string), treat as None
        if project_id == "None" or project_id is None:
            project_id = None

        resolved_project_id = resolve_project_id(user_id, project_id, project_name)

        if not resolved_project_id:
            # Suggest available projects for user
            projects = list(
                db.projects.find(
                    {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
                )
            )
            available = [p.get("name", "") for p in projects]
            if project_name:
                return {
                    "success": False,
                    "error": f"Project '{project_name}' not found. Make sure you have access to it. Available projects: {available}",
                }
            else:
                return {
                    "success": False,
                    "error": f"Project name or ID is required. Example: 'Create task in CDW project' or specify project by name. Available projects: {available}",
                }

        print(f"   📁 Project ID: {resolved_project_id}")

        # Create task using agent controller
        result = agent_create_task(
            requesting_user=user_email,
            title=params.get("title"),
            project_id=resolved_project_id,
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

        # Build a user-friendly message
        ticket_id = None
        if isinstance(result, dict):
            ticket_id = result.get("task", {}).get("ticket_id") or result.get(
                "ticket_id"
            )
        msg = f"✅ Task '{params.get('title')}' created successfully in project {project_name or resolved_project_id}!"
        if params.get("assignee_email"):
            msg += f" Assigned to {params['assignee_email']}."
        if params.get("due_date"):
            msg += f" Due date: {params['due_date']}."
        if ticket_id:
            msg += f" (Ticket: {ticket_id})"
        return {
            "success": True,
            "action": "create_task",
            "message": msg,
        }

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def local_handle_assign_task(user_email: str, user_id: str, params: dict):
    """Handle task assignment via local agent."""
    try:
        print("   🔄 Assigning task")

        # Find task
        task = find_task_by_title_or_id(
            user_id,
            params.get("task_id"),
            params.get("task_title"),
            params.get("ticket_id"),
        )

        if not task:
            return {
                "success": False,
                "error": f"Task '{params.get('task_title', params.get('task_id'))}' not found",
            }

        assignee_identifier = params.get("assignee_email") or params.get(
            "assignee_name"
        )
        if not assignee_identifier:
            return {"success": False, "error": "Assignee email or name required"}

        result = agent_assign_task(
            requesting_user=user_email,
            task_id=task["_id"],
            assignee_identifier=assignee_identifier,
            user_id=user_id,
        )

        return {
            "success": True,
            "action": "assign_task",
            "result": result,
            "message": f"Task '{task['title']}' assigned to {assignee_identifier}",
        }

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e)}


def local_handle_update_task(user_email: str, user_id: str, params: dict):
    """Handle task updates via local agent."""
    try:
        print("   📝 Updating task")

        # Find task
        task = find_task_by_title_or_id(
            user_id,
            params.get("task_id"),
            params.get("task_title"),
            params.get("ticket_id"),
        )

        if not task:
            return {
                "success": False,
                "error": f"Task '{params.get('task_title', params.get('task_id'))}' not found",
            }

        # Build update data
        update_data = {}
        for key in ["status", "priority", "description", "due_date", "labels"]:
            if key in params:
                update_data[key] = params[key]

        if not update_data:
            return {"success": False, "error": "No fields to update"}

        body = json.dumps(update_data)
        response = task_controller.update_task(body, task["_id"], user_id)

        if response.get("statusCode", 200) >= 400:
            return {"success": False, "error": "Failed to update task"}

        result = (
            json.loads(response["body"])
            if isinstance(response["body"], str)
            else response["body"]
        )

        return {
            "success": True,
            "action": "update_task",
            "result": result,
            "message": f"Task '{task['title']}' updated successfully",
        }

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e)}


def local_handle_create_sprint(user_email: str, user_id: str, params: dict):
    """Handle sprint creation via local agent."""
    try:
        print(f"   📅 Creating sprint: {params.get('name')}")

        # Resolve project
        project_id = resolve_project_id(
            user_id,
            params.get("project_id"),
            params.get("project_name"),
        )

        if not project_id:
            return {
                "success": False,
                "error": f"Project '{params.get('project_name', params.get('project_id'))}' not found",
            }

        result = agent_create_sprint(
            requesting_user=user_email,
            name=params.get("name"),
            project_id=project_id,
            user_id=user_id,
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            goal=params.get("goal", ""),
        )

        return {
            "success": True,
            "action": "create_sprint",
            "result": result,
            "message": f"Sprint '{params.get('name')}' created successfully",
        }

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e)}


def local_handle_list_tasks(user_id: str, params: dict):
    """List tasks with optional filtering."""
    try:
        print("   📋 Listing tasks")

        # Get user's projects
        projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )
        project_ids = [str(p["_id"]) for p in projects]

        # Build query
        query = {"project_id": {"$in": project_ids}}

        if params.get("project_name"):
            project_id = resolve_project_id(
                user_id, project_name=params["project_name"]
            )
            if project_id:
                query["project_id"] = project_id

        if params.get("status"):
            query["status"] = params["status"]

        if params.get("priority"):
            query["priority"] = params["priority"]

        tasks = list(db.tasks.find(query).limit(20))
        for t in tasks:
            t["_id"] = str(t["_id"])

        return {
            "success": True,
            "action": "list_tasks",
            "result": {"count": len(tasks), "tasks": tasks},
            "message": f"Found {len(tasks)} task(s)",
        }

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e)}


def local_handle_list_projects(user_id: str):
    """List user's projects."""
    try:
        print("   📁 Listing projects")

        projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )

        for p in projects:
            p["_id"] = str(p["_id"])

        return {
            "success": True,
            "action": "list_projects",
            "result": {"count": len(projects), "projects": projects},
            "message": f"Found {len(projects)} project(s)",
        }

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e)}


def local_handle_list_sprints(user_id: str, params: dict):
    """List sprints for a project."""
    try:
        print("   🏃 Listing sprints")

        project_id = resolve_project_id(
            user_id,
            params.get("project_id"),
            params.get("project_name"),
        )

        if not project_id:
            return {"success": False, "error": "Project not found"}

        sprints = list(db.sprints.find({"project_id": project_id}))
        for s in sprints:
            s["_id"] = str(s["_id"])

        return {
            "success": True,
            "action": "list_sprints",
            "result": {"count": len(sprints), "sprints": sprints},
            "message": f"Found {len(sprints)} sprint(s)",
        }

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e)}


def local_handle_add_task_to_sprint(user_email: str, user_id: str, params: dict):
    """Add task to sprint."""
    try:
        print("   ➕ Adding task to sprint")

        # Find task
        task = find_task_by_title_or_id(
            user_id,
            params.get("task_id"),
            params.get("task_title"),
            params.get("ticket_id"),
        )

        if not task:
            return {"success": False, "error": "Task not found"}

        # Find sprint
        sprint = find_sprint_by_name_or_id(
            user_id,
            params.get("project_id"),
            params.get("sprint_id"),
            params.get("sprint_name"),
        )

        if not sprint:
            return {"success": False, "error": "Sprint not found"}

        # Add task to sprint
        db.tasks.update_one(
            {"_id": ObjectId(task["_id"])},
            {"$set": {"sprint_id": sprint["_id"]}},
        )

        return {
            "success": True,
            "action": "add_task_to_sprint",
            "result": {"task_id": task["_id"], "sprint_id": sprint["_id"]},
            "message": f"Task '{task['title']}' added to sprint '{sprint['name']}'",
        }

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e)}


def local_handle_list_members(user_id: str, params: dict):
    """List members in a project."""
    try:
        print("   👥 Listing members")

        project_id = resolve_project_id(
            user_id,
            params.get("project_id"),
            params.get("project_name"),
        )

        if not project_id:
            return {"success": False, "error": "Project not found"}

        project = db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            return {"success": False, "error": "Project not found"}

        members = project.get("members", [])

        return {
            "success": True,
            "action": "list_members",
            "result": {"count": len(members), "members": members},
            "message": f"Found {len(members)} member(s) in project",
        }

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e)}
