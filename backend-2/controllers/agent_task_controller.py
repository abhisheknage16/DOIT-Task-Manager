# """
# Agent Task Controller
# Simplified interface for AI Agent to create and manage tasks
# """

# from fastapi import HTTPException
# from controllers import task_controller
# from models.user import User
# from models.project import Project
# import json


# def agent_create_task(
#     requesting_user: str,
#     title: str,
#     project_id: str,
#     user_id: str,
#     assignee_email: str = None,
#     assignee_name: str = None,
#     **kwargs,
# ):
#     """
#     Agent-friendly task creation with automatic assignee resolution and RBAC

#     Args:
#         requesting_user: Email of the actual user making this request (for permission check)
#         title: Task title
#         project_id: Target project
#         user_id: Service account user ID (from agent auth)
#         assignee_email: Optional email to assign to
#         assignee_name: Optional name to search for
#         **kwargs: Additional task fields
#     """
#     try:
#         # Step 1: Validate requesting user exists and has permission
#         actual_user = User.find_by_email(requesting_user)
#         if not actual_user:
#             raise HTTPException(
#                 status_code=404, detail=f"User with email '{requesting_user}' not found"
#             )

#         # Step 2: Check if user has permission to create tasks (Admin or Member)
#         user_role = actual_user.get("role", "").lower()
#         if user_role not in ["admin", "member"]:
#             raise HTTPException(
#                 status_code=403,
#                 detail=f"Only Admin and Member users can create tasks. Your role is '{actual_user.get('role')}'",
#             )

#         # Step 3: Use actual user's ID for task creation (for audit trail)
#         creator_id = str(actual_user["_id"])

#         # Resolve assignee if email or name provided
#         assignee_id = None

#         if assignee_email:
#             assignee = User.find_by_email(assignee_email)
#             if assignee:
#                 assignee_id = str(assignee["_id"])
#             else:
#                 raise HTTPException(
#                     status_code=404,
#                     detail=f"User with email '{assignee_email}' not found",
#                 )

#         elif assignee_name:
#             # Search by name (case-insensitive)
#             from database import db

#             assignee = db.users.find_one(
#                 {"name": {"$regex": f"^{assignee_name}$", "$options": "i"}}
#             )
#             if assignee:
#                 # Verify they're a project member
#                 if Project.is_member(project_id, str(assignee["_id"])):
#                     assignee_id = str(assignee["_id"])
#                 else:
#                     raise HTTPException(
#                         status_code=403,
#                         detail=f"User '{assignee_name}' is not a member of this project",
#                     )
#             else:
#                 raise HTTPException(
#                     status_code=404, detail=f"User '{assignee_name}' not found"
#                 )

#         # Build task data
#         task_data = {
#             "title": title,
#             "project_id": project_id,
#             "assignee_id": assignee_id,
#             **kwargs,
#         }

#         # Create task using existing controller with actual user ID
#         body = json.dumps(task_data)
#         response = task_controller.create_task(body, creator_id)

#         # Check if response contains an error status code
#         status_code = response.get("statusCode", 200)
#         if status_code >= 400:
#             # Parse error message
#             if isinstance(response.get("body"), str):
#                 error_body = json.loads(response["body"])
#             else:
#                 error_body = response.get("body", {})

#             error_message = error_body.get("error", "Task creation failed")
#             raise HTTPException(status_code=status_code, detail=error_message)

#         # Parse successful response
#         if isinstance(response.get("body"), str):
#             result = json.loads(response["body"])
#         else:
#             result = response.get("body", {})

#         return result

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


# def agent_assign_task(
#     requesting_user: str, task_id: str, assignee_identifier: str, user_id: str
# ):
#     """
#     Assign task to user by email or name with RBAC validation

#     Args:
#         requesting_user: Email of the actual user making this request
#         task_id: Task to assign
#         assignee_identifier: Email or name of assignee
#         user_id: Service account user ID
#     """
#     try:
#         # Step 1: Validate requesting user
#         actual_user = User.find_by_email(requesting_user)
#         if not actual_user:
#             raise HTTPException(
#                 status_code=404, detail=f"User with email '{requesting_user}' not found"
#             )

#         # Step 2: Check permission (Admin or Member)
#         user_role = actual_user.get("role", "").lower()
#         if user_role not in ["admin", "member"]:
#             raise HTTPException(
#                 status_code=403,
#                 detail=f"Only Admin and Member users can assign tasks. Your role is '{actual_user.get('role')}'",
#             )

#         modifier_id = str(actual_user["_id"])

#         # Try email first
#         assignee = User.find_by_email(assignee_identifier)

#         # Try name if email fails
#         if not assignee:
#             from database import db

#             assignee = db.users.find_one(
#                 {"name": {"$regex": f"^{assignee_identifier}$", "$options": "i"}}
#             )

#         if not assignee:
#             raise HTTPException(
#                 status_code=404, detail=f"User '{assignee_identifier}' not found"
#             )

#         assignee_id = str(assignee["_id"])

#         # Resolve task_id - could be ticket_id (FTP-005) or MongoDB _id
#         from models.task import Task

#         task = (
#             Task.find_by_ticket_id(task_id)
#             if task_id.startswith(("FTP-", "SLS-", "TMP-", "TST-", "NP-"))
#             else Task.find_by_id(task_id)
#         )

#         if not task:
#             raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

#         actual_task_id = str(task["_id"])

#         # Update task using actual user ID
#         update_data = {"assignee_id": assignee_id}
#         body = json.dumps(update_data)

#         response = task_controller.update_task(body, actual_task_id, modifier_id)

#         # Check if response contains an error status code
#         status_code = response.get("statusCode", 200)
#         if status_code >= 400:
#             # Parse error message
#             if isinstance(response.get("body"), str):
#                 error_body = json.loads(response["body"])
#             else:
#                 error_body = response.get("body", {})

#             error_message = error_body.get("error", "Task assignment failed")
#             raise HTTPException(status_code=status_code, detail=error_message)

#         # Parse successful response
#         if isinstance(response.get("body"), str):
#             result = json.loads(response["body"])
#         else:
#             result = response.get("body", {})

#         return result

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")


# def agent_create_task_sync(
#     requesting_user: str,
#     title: str,
#     project_id: str,
#     user_id: str,
#     description: str = "",
#     assignee_email: Optional[str] = None,
#     assignee_name: Optional[str] = None,
#     priority: str = "Medium",
#     status: str = "To Do",
#     due_date: Optional[str] = None,
#     issue_type: str = "task",
#     labels: Optional[list] = None,
# ):
#     """
#     Synchronous version of agent_create_task for use in LangGraph tools.
#     """
#     # All the same logic as agent_create_task but without async operations
#     # Simply don't call websocket broadcast
#     from controllers import task_controller
#     import json

#     task_data = {
#         "title": title,
#         "description": description,
#         "priority": priority,
#         "status": status,
#         "issue_type": issue_type,
#         "labels": labels or [],
#     }

#     if assignee_email:
#         task_data["assignee_email"] = assignee_email
#     if assignee_name:
#         task_data["assignee_name"] = assignee_name
#     if due_date:
#         task_data["due_date"] = due_date

#     body = json.dumps(task_data)
#     response = task_controller.create_task(body, project_id, user_id)

#     if response.get("statusCode", 200) >= 400:
#         error_body = (
#             json.loads(response["body"])
#             if isinstance(response["body"], str)
#             else response["body"]
#         )
#         raise Exception(error_body.get("error", "Failed to create task"))

#     result = (
#         json.loads(response["body"])
#         if isinstance(response["body"], str)
#         else response["body"]
#     )
#     return result


# def agent_assign_task_sync(
#     requesting_user: str,
#     task_id: str,
#     assignee_identifier: str,
#     user_id: str,
# ):
#     """
#     Synchronous version of agent_assign_task for use in LangGraph tools.
#     """
#     from controllers import task_controller
#     import json

#     # Resolve assignee
#     assignee = db.users.find_one(
#         {
#             "$or": [
#                 {"email": assignee_identifier},
#                 {"name": {"$regex": f"^{assignee_identifier}$", "$options": "i"}},
#             ]
#         }
#     )

#     if not assignee:
#         raise Exception(f"User '{assignee_identifier}' not found")

#     update_data = {
#         "assignee_email": assignee["email"],
#         "assignee_name": assignee["name"],
#     }

#     body = json.dumps(update_data)
#     response = task_controller.update_task(body, task_id, user_id)

#     if response.get("statusCode", 200) >= 400:
#         raise Exception("Failed to assign task")

#     result = (
#         json.loads(response["body"])
#         if isinstance(response["body"], str)
#         else response["body"]
#     )
#     return result
# backend-2/controllers/agent_task_controller.py
"""
Agent Task Controller
Simplified interface for AI Agent to create and manage tasks
"""

from fastapi import HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime
from controllers import task_controller
from models.user import User
from models.project import Project
from database import db
from bson import ObjectId
import json
import re


ALLOWED_BULK_TASK_UPDATE_FIELDS = {
    "title",
    "description",
    "priority",
    "status",
    "assignee_id",
    "due_date",
    "issue_type",
    "labels",
    "comment",
}


def _resolve_task_by_identifier(task_identifier: str):
    """Resolve task by Mongo _id or ticket_id like AA-003."""
    from models.task import Task

    identifier = (task_identifier or "").strip()
    is_object_id_like = bool(re.fullmatch(r"[0-9a-fA-F]{24}", identifier))
    is_ticket_like = bool(re.fullmatch(r"[A-Za-z]{2,}-\d+", identifier))

    if is_object_id_like:
        return Task.find_by_id(identifier) or Task.find_by_ticket_id(identifier)
    if is_ticket_like:
        return Task.find_by_ticket_id(identifier) or Task.find_by_id(identifier)
    return Task.find_by_id(identifier) or Task.find_by_ticket_id(identifier)


def _normalize_due_date_to_iso(due_date: str) -> str:
    """Normalize due date to YYYY-MM-DD, accepting common human formats."""
    if not due_date or not str(due_date).strip():
        raise HTTPException(status_code=400, detail="due_date is required")

    raw = str(due_date).strip()

    # Accept ISO formats first.
    try:
        return datetime.fromisoformat(raw).date().isoformat()
    except Exception:
        pass

    patterns = [
        "%Y-%m-%d",
        "%B %d %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]

    for pattern in patterns:
        try:
            return datetime.strptime(raw, pattern).date().isoformat()
        except Exception:
            continue

    raise HTTPException(
        status_code=400,
        detail="Invalid due_date format. Use YYYY-MM-DD or a parseable date string.",
    )


def agent_create_task(
    requesting_user: str,
    title: str,
    project_id: str,
    user_id: str,
    assignee_email: str = None,
    assignee_name: str = None,
    **kwargs,
):
    """
    Agent-friendly task creation with automatic assignee resolution and RBAC

    Args:
        requesting_user: Email of the actual user making this request (for permission check)
        title: Task title
        project_id: Target project
        user_id: Service account user ID (from agent auth)
        assignee_email: Optional email to assign to
        assignee_name: Optional name to search for
        **kwargs: Additional task fields
    """
    try:
        # Step 1: Validate requesting user exists and has permission
        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        # Step 2: Check if user has permission to create tasks (Admin/Member/Super-Admin)
        user_role = actual_user.get("role", "").lower()
        if user_role not in ["admin", "member", "super-admin"]:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only Admin, Member, and Super-Admin users can create tasks. "
                    f"Your role is '{actual_user.get('role')}'"
                ),
            )

        # Step 3: Use actual user's ID for task creation (for audit trail)
        creator_id = str(actual_user["_id"])

        # Resolve assignee if email or name provided
        assignee_id = None

        if assignee_email:
            assignee = User.find_by_email(assignee_email)
            if assignee:
                assignee_id = str(assignee["_id"])
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"User with email '{assignee_email}' not found",
                )

        elif assignee_name:
            # Search by name (case-insensitive)
            assignee = db.users.find_one(
                {"name": {"$regex": f"^{assignee_name}$", "$options": "i"}}
            )
            if assignee:
                # Verify they're a project member
                if Project.is_member(project_id, str(assignee["_id"])):
                    assignee_id = str(assignee["_id"])
                else:
                    raise HTTPException(
                        status_code=403,
                        detail=f"User '{assignee_name}' is not a member of this project",
                    )
            else:
                raise HTTPException(
                    status_code=404, detail=f"User '{assignee_name}' not found"
                )

        # Build task data
        task_data = {
            "title": title,
            "project_id": project_id,
            "assignee_id": assignee_id,
            **kwargs,
        }

        # Create task using existing controller with actual user ID
        body = json.dumps(task_data)
        response = task_controller.create_task(body, creator_id)

        # Check if response contains an error status code
        status_code = response.get("statusCode", 200)
        if status_code >= 400:
            # Parse error message
            if isinstance(response.get("body"), str):
                error_body = json.loads(response["body"])
            else:
                error_body = response.get("body", {})

            error_message = error_body.get("error", "Task creation failed")
            raise HTTPException(status_code=status_code, detail=error_message)

        # Parse successful response
        if isinstance(response.get("body"), str):
            result = json.loads(response["body"])
        else:
            result = response.get("body", {})

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


def agent_assign_task(
    requesting_user: str, task_id: str, assignee_identifier: str, user_id: str
):
    """
    Assign task to user by email or name with RBAC validation

    Args:
        requesting_user: Email of the actual user making this request
        task_id: Task to assign
        assignee_identifier: Email or name of assignee
        user_id: Service account user ID
    """
    try:
        # Step 1: Validate requesting user
        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        # Step 2: Check permission (Admin/Member/Super-Admin)
        user_role = actual_user.get("role", "").lower()
        if user_role not in ["admin", "member", "super-admin"]:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only Admin, Member, and Super-Admin users can assign tasks. "
                    f"Your role is '{actual_user.get('role')}'"
                ),
            )

        modifier_id = str(actual_user["_id"])

        assignee_identifier = (assignee_identifier or "").strip()

        # Try email first
        assignee = User.find_by_email(assignee_identifier)

        # Try direct user_id (Mongo ObjectId) if email lookup fails
        if not assignee and re.fullmatch(r"[0-9a-fA-F]{24}", assignee_identifier):
            assignee = User.find_by_id(assignee_identifier)

        # Try exact display name if still unresolved
        if not assignee:
            assignee = db.users.find_one(
                {
                    "name": {
                        "$regex": f"^{re.escape(assignee_identifier)}$",
                        "$options": "i",
                    }
                }
            )

        if not assignee:
            raise HTTPException(
                status_code=404, detail=f"User '{assignee_identifier}' not found"
            )

        assignee_id = str(assignee["_id"])

        # Resolve task_id - could be ticket_id (FTP-005) or MongoDB _id
        from models.task import Task

        is_object_id_like = bool(re.fullmatch(r"[0-9a-fA-F]{24}", task_id or ""))
        is_ticket_like = bool(re.fullmatch(r"[A-Za-z]{2,}-\d+", task_id or ""))

        if is_object_id_like:
            task = Task.find_by_id(task_id)
            if not task:
                task = Task.find_by_ticket_id(task_id)
        elif is_ticket_like:
            task = Task.find_by_ticket_id(task_id)
            if not task:
                task = Task.find_by_id(task_id)
        else:
            task = Task.find_by_id(task_id) or Task.find_by_ticket_id(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

        actual_task_id = str(task["_id"])

        # Update task using actual user ID
        update_data = {"assignee_id": assignee_id}
        body = json.dumps(update_data)

        response = task_controller.update_task(body, actual_task_id, modifier_id)

        # Check if response contains an error status code
        status_code = response.get("statusCode", 200)
        if status_code >= 400:
            # Parse error message
            if isinstance(response.get("body"), str):
                error_body = json.loads(response["body"])
            else:
                error_body = response.get("body", {})

            error_message = error_body.get("error", "Task assignment failed")
            raise HTTPException(status_code=status_code, detail=error_message)

        # Parse successful response
        if isinstance(response.get("body"), str):
            result = json.loads(response["body"])
        else:
            result = response.get("body", {})

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")


def agent_update_task(
    requesting_user: str,
    task_id: str,
    user_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    due_date: Optional[str] = None,
):
    """
    Agent-friendly task update with ticket-id or _id resolution and RBAC checks.
    """
    try:
        # Validate requesting user
        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        # Allow the same actor roles as task create/update flows
        user_role = actual_user.get("role", "").lower()
        if user_role not in ["admin", "member", "super-admin"]:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only Admin, Member, and Super-Admin users can update tasks. "
                    f"Your role is '{actual_user.get('role')}'"
                ),
            )

        modifier_id = str(actual_user["_id"])

        # Resolve task identifier from ticket_id (AA-003) or Mongo _id
        task = _resolve_task_by_identifier(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

        actual_task_id = str(task["_id"])

        # Validate user is still a member of target project
        if not Project.is_member(task["project_id"], modifier_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied. Requesting user is not a member of this project.",
            )

        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if priority is not None:
            update_data["priority"] = priority
        if status is not None:
            update_data["status"] = status
        if due_date is not None:
            update_data["due_date"] = due_date

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        body = json.dumps(update_data)
        response = task_controller.update_task(body, actual_task_id, modifier_id)

        status_code = response.get("statusCode", 200)
        if status_code >= 400:
            if isinstance(response.get("body"), str):
                error_body = json.loads(response["body"])
            else:
                error_body = response.get("body", {})

            error_message = error_body.get("error", "Task update failed")
            raise HTTPException(status_code=status_code, detail=error_message)

        if isinstance(response.get("body"), str):
            return json.loads(response["body"])
        return response.get("body", {})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


def agent_bulk_update_task_due_dates(
    requesting_user: str,
    project_id: str,
    due_date: str,
    task_identifiers: List[str],
    user_id: str,
):
    """
    Bulk update due_date for one or more tasks using ticket IDs or Mongo _ids.
    """
    try:
        # Validate requesting user
        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        user_role = actual_user.get("role", "").lower()
        if user_role not in ["admin", "member", "super-admin"]:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only Admin, Member, and Super-Admin users can update tasks. "
                    f"Your role is '{actual_user.get('role')}'"
                ),
            )

        modifier_id = str(actual_user["_id"])

        # Validate project existence and membership
        project = Project.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project with ID '{project_id}' not found"
            )

        if not Project.is_member(project_id, modifier_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied. Requesting user is not a member of this project.",
            )

        if not task_identifiers:
            raise HTTPException(
                status_code=400,
                detail="task_identifiers must include at least one task identifier",
            )

        normalized_due_date = _normalize_due_date_to_iso(due_date)

        updated_tasks = []
        errors = []

        for identifier in task_identifiers:
            task = _resolve_task_by_identifier(identifier)
            if not task:
                errors.append({"task_identifier": identifier, "error": "Task not found"})
                continue

            if task.get("project_id") != project_id:
                errors.append(
                    {
                        "task_identifier": identifier,
                        "error": "Task does not belong to provided project_id",
                    }
                )
                continue

            actual_task_id = str(task["_id"])
            response = task_controller.update_task(
                json.dumps({"due_date": normalized_due_date}), actual_task_id, modifier_id
            )

            status_code = response.get("statusCode", 200)
            if status_code >= 400:
                if isinstance(response.get("body"), str):
                    error_body = json.loads(response["body"])
                else:
                    error_body = response.get("body", {})
                errors.append(
                    {
                        "task_identifier": identifier,
                        "error": error_body.get("error", "Task update failed"),
                    }
                )
                continue

            if isinstance(response.get("body"), str):
                success_body = json.loads(response["body"])
            else:
                success_body = response.get("body", {})

            task_payload = success_body.get("task", {})
            updated_tasks.append(
                {
                    "task_identifier": identifier,
                    "task_id": str(task_payload.get("_id", actual_task_id)),
                    "ticket_id": task_payload.get("ticket_id", task.get("ticket_id")),
                    "due_date": task_payload.get("due_date", normalized_due_date),
                }
            )

        return {
            "success": len(updated_tasks) > 0,
            "message": "Bulk due-date update completed",
            "project_id": project_id,
            "due_date": normalized_due_date,
            "total_requested": len(task_identifiers),
            "updated_count": len(updated_tasks),
            "failed_count": len(errors),
            "updated_tasks": updated_tasks,
            "errors": errors,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed bulk due-date update: {str(e)}"
        )


def agent_bulk_update_tasks(
    requesting_user: str,
    project_id: str,
    task_identifiers: List[str],
    updates: Dict[str, Any],
    user_id: str,
):
    """
    Bulk update allowed task fields for one or more tasks using ticket IDs or Mongo _ids.
    """
    try:
        # Validate requesting user
        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        user_role = actual_user.get("role", "").lower()
        if user_role not in ["admin", "member", "super-admin"]:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only Admin, Member, and Super-Admin users can update tasks. "
                    f"Your role is '{actual_user.get('role')}'"
                ),
            )

        modifier_id = str(actual_user["_id"])

        # Validate project existence and membership
        project = Project.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project with ID '{project_id}' not found"
            )

        if not Project.is_member(project_id, modifier_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied. Requesting user is not a member of this project.",
            )

        if not task_identifiers:
            raise HTTPException(
                status_code=400,
                detail="task_identifiers must include at least one task identifier",
            )

        if not isinstance(updates, dict) or not updates:
            raise HTTPException(status_code=400, detail="updates object is required")

        # Keep only explicitly allowed fields and reject unsupported fields early.
        provided_fields = set(updates.keys())
        unsupported_fields = sorted(
            field for field in provided_fields if field not in ALLOWED_BULK_TASK_UPDATE_FIELDS
        )
        if unsupported_fields:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported update fields: "
                    + ", ".join(unsupported_fields)
                    + ". Allowed fields: "
                    + ", ".join(sorted(ALLOWED_BULK_TASK_UPDATE_FIELDS))
                ),
            )

        normalized_updates: Dict[str, Any] = {
            key: value
            for key, value in updates.items()
            if key in ALLOWED_BULK_TASK_UPDATE_FIELDS
        }

        if "due_date" in normalized_updates and normalized_updates.get("due_date") is not None:
            normalized_updates["due_date"] = _normalize_due_date_to_iso(
                str(normalized_updates.get("due_date"))
            )

        updated_tasks = []
        errors = []

        for identifier in task_identifiers:
            task = _resolve_task_by_identifier(identifier)
            if not task:
                errors.append({"task_identifier": identifier, "error": "Task not found"})
                continue

            if task.get("project_id") != project_id:
                errors.append(
                    {
                        "task_identifier": identifier,
                        "error": "Task does not belong to provided project_id",
                    }
                )
                continue

            actual_task_id = str(task["_id"])
            response = task_controller.update_task(
                json.dumps(normalized_updates), actual_task_id, modifier_id
            )

            status_code = response.get("statusCode", 200)
            if status_code >= 400:
                if isinstance(response.get("body"), str):
                    error_body = json.loads(response["body"])
                else:
                    error_body = response.get("body", {})
                errors.append(
                    {
                        "task_identifier": identifier,
                        "error": error_body.get("error", "Task update failed"),
                    }
                )
                continue

            if isinstance(response.get("body"), str):
                success_body = json.loads(response["body"])
            else:
                success_body = response.get("body", {})

            task_payload = success_body.get("task", {})
            updated_tasks.append(
                {
                    "task_identifier": identifier,
                    "task_id": str(task_payload.get("_id", actual_task_id)),
                    "ticket_id": task_payload.get("ticket_id", task.get("ticket_id")),
                    "updated_fields": sorted(list(normalized_updates.keys())),
                    "task": task_payload,
                }
            )

        return {
            "success": len(updated_tasks) > 0,
            "message": "Bulk task update completed",
            "project_id": project_id,
            "applied_updates": normalized_updates,
            "total_requested": len(task_identifiers),
            "updated_count": len(updated_tasks),
            "failed_count": len(errors),
            "updated_tasks": updated_tasks,
            "errors": errors,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed bulk task update: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# SYNCHRONOUS VERSIONS FOR LANGGRAPH TOOLS
# ─────────────────────────────────────────────────────────────────────────────


def agent_create_task_sync(
    requesting_user: str,
    title: str,
    project_id: str,
    user_id: str,
    description: str = "",
    assignee_email: Optional[str] = None,
    assignee_name: Optional[str] = None,
    priority: str = "Medium",
    status: str = "To Do",
    due_date: Optional[str] = None,
    issue_type: str = "task",
    labels: Optional[list] = None,
):
    """
    Synchronous version of agent_create_task for use in LangGraph tools.
    Creates task directly in database to avoid async/controller issues.
    """
    try:
        # Validate project exists and user has access
        project = db.projects.find_one(
            {
                "_id": ObjectId(project_id),
                "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
            }
        )

        if not project:
            raise Exception("Project not found or access denied")

        # Generate ticket ID
        project_prefix = "".join(
            [c.upper() for c in project.get("name", "TASK") if c.isalnum()]
        )[:4]
        task_count = db.tasks.count_documents({"project_id": project_id})
        ticket_id = f"{project_prefix}-{task_count + 1}"

        # Resolve assignee if provided
        assignee_data = {}
        if assignee_email:
            assignee = db.users.find_one({"email": assignee_email})
            if assignee:
                assignee_data = {
                    "assignee_email": assignee["email"],
                    "assignee_name": assignee.get("name", assignee_email),
                    "assignee_id": str(assignee["_id"]),
                }
            else:
                print(
                    f"⚠️ Assignee {assignee_email} not found, creating unassigned task"
                )
        elif assignee_name:
            assignee = db.users.find_one(
                {"name": {"$regex": f"^{assignee_name}$", "$options": "i"}}
            )
            if assignee:
                assignee_data = {
                    "assignee_email": assignee.get("email", ""),
                    "assignee_name": assignee.get("name", assignee_name),
                    "assignee_id": str(assignee["_id"]),
                }

        # Create task document
        task = {
            "title": title,
            "description": description,
            "project_id": project_id,
            "status": status,
            "priority": priority,
            "issue_type": issue_type,
            "ticket_id": ticket_id,
            "labels": labels or [],
            "created_by": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **assignee_data,
        }

        if due_date:
            task["due_date"] = due_date

        # Insert task
        result = db.tasks.insert_one(task)
        task["_id"] = str(result.inserted_id)

        # Update project task count
        db.projects.update_one(
            {"_id": ObjectId(project_id)}, {"$inc": {"task_count": 1}}
        )

        return {"success": True, "task": task, "ticket_id": ticket_id}

    except Exception as e:
        raise Exception(f"Failed to create task: {str(e)}")


def agent_assign_task_sync(
    requesting_user: str,
    task_id: str,
    assignee_identifier: str,
    user_id: str,
):
    """
    Synchronous version of agent_assign_task for use in LangGraph tools.
    Assigns task directly in database to avoid async/controller issues.
    """
    try:
        # Find task
        task = db.tasks.find_one({"_id": ObjectId(task_id)})

        if not task:
            raise Exception("Task not found")

        # Check user has access to project
        project = db.projects.find_one(
            {
                "_id": ObjectId(task["project_id"]),
                "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
            }
        )

        if not project:
            raise Exception("Access denied")

        # Resolve assignee
        assignee = db.users.find_one(
            {
                "$or": [
                    {"email": assignee_identifier},
                    {"name": {"$regex": f"^{assignee_identifier}$", "$options": "i"}},
                ]
            }
        )

        if not assignee:
            raise Exception(f"User '{assignee_identifier}' not found")

        # Update task
        db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {
                "$set": {
                    "assignee_email": assignee["email"],
                    "assignee_name": assignee.get("name", assignee["email"]),
                    "assignee_id": str(assignee["_id"]),
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        # Get updated task
        updated_task = db.tasks.find_one({"_id": ObjectId(task_id)})
        updated_task["_id"] = str(updated_task["_id"])

        return {"success": True, "task": updated_task}

    except Exception as e:
        raise Exception(f"Failed to assign task: {str(e)}")
