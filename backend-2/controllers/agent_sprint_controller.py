# """
# Agent Sprint Controller
# Handles sprint creation with RBAC validation for Azure AI Agent
# """

# import json
# from fastapi import HTTPException
# from models.user import User
# from models.project import Project
# from controllers import sprint_controller


# def agent_create_sprint(
#     requesting_user: str,
#     name: str,
#     project_id: str,
#     start_date: str,
#     end_date: str,
#     user_id: str,
#     goal: str = "",
#     status: str = "Planning",
# ):
#     """
#     Create sprint with RBAC validation

#     Args:
#         requesting_user: Email of the actual user making this request
#         name: Sprint name
#         project_id: Target project ID
#         start_date: Sprint start date (ISO format)
#         end_date: Sprint end date (ISO format)
#         user_id: Service account user ID (from agent auth)
#         goal: Sprint goal (optional)
#         status: Sprint status (optional, default "Planning")
#     """
#     try:
#         # Step 1: Validate requesting user
#         actual_user = User.find_by_email(requesting_user)
#         if not actual_user:
#             raise HTTPException(
#                 status_code=404, detail=f"User with email '{requesting_user}' not found"
#             )

#         # Step 2: Check permission - ONLY Admin can create sprints
#         user_role = actual_user.get("role", "").lower()
#         if user_role != "admin":
#             raise HTTPException(
#                 status_code=403,
#                 detail=f"Only Admin users can create sprints. Your role is '{actual_user.get('role')}'",
#             )

#         # Step 3: Verify project exists
#         project = Project.find_by_id(project_id)
#         if not project:
#             raise HTTPException(
#                 status_code=404, detail=f"Project with ID '{project_id}' not found"
#             )

#         # Step 4: Build sprint data
#         sprint_data = {
#             "name": name,
#             "goal": goal,
#             "start_date": start_date,
#             "end_date": end_date,
#             "status": status,
#         }

#         # Step 5: Call existing sprint controller with actual user's ID
#         creator_id = str(actual_user["_id"])
#         body = json.dumps(sprint_data)

#         response = sprint_controller.create_sprint(body, project_id, creator_id)

#         # Step 6: Check if response contains an error status code
#         status_code = response.get("statusCode", 200)
#         if status_code >= 400:
#             # Parse error message
#             if isinstance(response.get("body"), str):
#                 error_body = json.loads(response["body"])
#             else:
#                 error_body = response.get("body", {})

#             error_message = error_body.get("error", "Sprint creation failed")
#             raise HTTPException(status_code=status_code, detail=error_message)

#         # Step 7: Parse successful response
#         if isinstance(response.get("body"), str):
#             result = json.loads(response["body"])
#         else:
#             result = response.get("body", {})

#         return result

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Sprint creation error: {str(e)}")


# def agent_create_sprint_sync(
#     requesting_user: str,
#     name: str,
#     project_id: str,
#     user_id: str,
#     start_date: Optional[str] = None,
#     end_date: Optional[str] = None,
#     goal: str = "",
# ):
#     """
#     Synchronous version of agent_create_sprint for use in LangGraph tools.
#     """
#     from controllers import sprint_controller
#     import json

#     sprint_data = {
#         "name": name,
#         "goal": goal,
#         "status": "planned",
#     }

#     if start_date:
#         sprint_data["start_date"] = start_date
#     if end_date:
#         sprint_data["end_date"] = end_date

#     body = json.dumps(sprint_data)
#     response = sprint_controller.create_sprint(body, project_id, user_id)

#     if response.get("statusCode", 200) >= 400:
#         error_body = (
#             json.loads(response["body"])
#             if isinstance(response["body"], str)
#             else response["body"]
#         )
#         raise Exception(error_body.get("error", "Failed to create sprint"))

#     result = (
#         json.loads(response["body"])
#         if isinstance(response["body"], str)
#         else response["body"]
#     )
#     return result
# backend-2/controllers/agent_sprint_controller.py
"""
Agent Sprint Controller
Handles sprint creation with RBAC validation for Azure AI Agent
"""

import json
from typing import Optional, List
from datetime import datetime, timedelta
import re
from fastapi import HTTPException
from models.user import User
from models.project import Project
from models.task import Task
from controllers import sprint_controller
from database import db
from bson import ObjectId


def _normalize_agent_sprint_dates(start_date: str, end_date: str) -> tuple[str, str]:
    """
    Always anchor agent-created sprints to today's date.

    If incoming dates contain a valid positive duration, preserve that duration.
    Otherwise, default sprint length to 14 days.
    """
    today = datetime.utcnow().date()
    duration_days = 14

    try:
        requested_start = datetime.fromisoformat(start_date).date()
        requested_end = datetime.fromisoformat(end_date).date()
        requested_duration = (requested_end - requested_start).days

        if requested_duration > 0:
            duration_days = requested_duration
    except Exception:
        # Keep safe default when incoming dates are missing/invalid.
        pass

    normalized_start = today
    normalized_end = today + timedelta(days=duration_days)

    return normalized_start.isoformat(), normalized_end.isoformat()


def agent_create_sprint(
    requesting_user: str,
    name: str,
    project_id: str,
    start_date: str,
    end_date: str,
    user_id: str,
    goal: str = "",
    status: str = "Planning",
):
    """
    Create sprint with RBAC validation

    Args:
        requesting_user: Email of the actual user making this request
        name: Sprint name
        project_id: Target project ID
        start_date: Sprint start date (ISO format)
        end_date: Sprint end date (ISO format)
        user_id: Service account user ID (from agent auth)
        goal: Sprint goal (optional)
        status: Sprint status (optional, default "Planning")
    """
    try:
        # Step 1: Validate requesting user
        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        # Step 2: Check permission - Admin and Super-Admin can create sprints
        user_role = actual_user.get("role", "").lower()
        if user_role not in ["admin", "super-admin"]:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only Admin and Super-Admin users can create sprints. "
                    f"Your role is '{actual_user.get('role')}'"
                ),
            )

        # Step 3: Verify project exists
        project = Project.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project with ID '{project_id}' not found"
            )

        # Step 4: Normalize dates for agent-created sprints.
        normalized_start_date, normalized_end_date = _normalize_agent_sprint_dates(
            start_date, end_date
        )

        # Step 5: Build sprint data
        sprint_data = {
            "name": name,
            "goal": goal,
            "start_date": normalized_start_date,
            "end_date": normalized_end_date,
            "status": status,
        }

        # Step 6: Call existing sprint controller with actual user's ID
        creator_id = str(actual_user["_id"])
        body = json.dumps(sprint_data)

        response = sprint_controller.create_sprint(body, project_id, creator_id)

        # Step 7: Check if response contains an error status code
        status_code = response.get("statusCode", 200)
        if status_code >= 400:
            # Parse error message
            if isinstance(response.get("body"), str):
                error_body = json.loads(response["body"])
            else:
                error_body = response.get("body", {})

            error_message = error_body.get("error", "Sprint creation failed")
            raise HTTPException(status_code=status_code, detail=error_message)

        # Step 8: Parse successful response
        if isinstance(response.get("body"), str):
            result = json.loads(response["body"])
        else:
            result = response.get("body", {})

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sprint creation error: {str(e)}")


def agent_start_sprint(
    requesting_user: str,
    project_id: str,
    user_id: str,
    sprint_id: Optional[str] = None,
    sprint_name: Optional[str] = None,
):
    """
    Start a sprint with RBAC + project membership validation.

    The caller can provide either sprint_id (preferred) or sprint_name.
    """
    try:
        if not sprint_id and not sprint_name:
            raise HTTPException(
                status_code=400,
                detail="Provide either sprint_id or sprint_name to start a sprint",
            )

        # Validate requesting user from context email.
        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        actual_user_id = str(actual_user["_id"])

        # Validate project exists.
        project = Project.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project with ID '{project_id}' not found"
            )

        # Validate project membership.
        if not Project.is_member(project_id, actual_user_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied. Requesting user is not a member of this project.",
            )

        # Resolve sprint from id or name.
        sprint = None
        if sprint_id:
            sprint = db.sprints.find_one({"_id": ObjectId(sprint_id), "project_id": project_id})
        elif sprint_name:
            sprint = db.sprints.find_one(
                {
                    "project_id": project_id,
                    "name": {"$regex": f"^{sprint_name}$", "$options": "i"},
                }
            )

        if not sprint:
            identifier = sprint_id if sprint_id else sprint_name
            raise HTTPException(
                status_code=404,
                detail=f"Sprint '{identifier}' not found in project '{project_id}'",
            )

        sprint_id_resolved = str(sprint["_id"])

        # Start sprint via existing controller logic.
        response = sprint_controller.start_sprint(sprint_id_resolved, actual_user_id)

        status_code = response.get("statusCode", 200)
        if status_code >= 400:
            if isinstance(response.get("body"), str):
                error_body = json.loads(response["body"])
            else:
                error_body = response.get("body", {})

            error_message = error_body.get("error", "Failed to start sprint")
            raise HTTPException(status_code=status_code, detail=error_message)

        if isinstance(response.get("body"), str):
            result = json.loads(response["body"])
        else:
            result = response.get("body", {})

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sprint start error: {str(e)}")


def agent_complete_sprint(
    requesting_user: str,
    project_id: str,
    user_id: str,
    sprint_id: Optional[str] = None,
    sprint_name: Optional[str] = None,
):
    """
    Complete a sprint with RBAC + project membership validation.

    The caller can provide either sprint_id (preferred) or sprint_name.
    """
    try:
        if not sprint_id and not sprint_name:
            raise HTTPException(
                status_code=400,
                detail="Provide either sprint_id or sprint_name to complete a sprint",
            )

        # Validate requesting user from context email.
        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        actual_user_id = str(actual_user["_id"])

        # Validate project exists.
        project = Project.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project with ID '{project_id}' not found"
            )

        # Validate project membership.
        if not Project.is_member(project_id, actual_user_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied. Requesting user is not a member of this project.",
            )

        # Resolve sprint from id or name.
        sprint = None
        if sprint_id:
            sprint = db.sprints.find_one({"_id": ObjectId(sprint_id), "project_id": project_id})
        elif sprint_name:
            sprint = db.sprints.find_one(
                {
                    "project_id": project_id,
                    "name": {"$regex": f"^{sprint_name}$", "$options": "i"},
                }
            )

        if not sprint:
            identifier = sprint_id if sprint_id else sprint_name
            raise HTTPException(
                status_code=404,
                detail=f"Sprint '{identifier}' not found in project '{project_id}'",
            )

        sprint_id_resolved = str(sprint["_id"])

        # Complete sprint via existing controller logic.
        response = sprint_controller.complete_sprint(sprint_id_resolved, actual_user_id)

        status_code = response.get("statusCode", 200)
        if status_code >= 400:
            if isinstance(response.get("body"), str):
                error_body = json.loads(response["body"])
            else:
                error_body = response.get("body", {})

            error_message = error_body.get("error", "Failed to complete sprint")
            raise HTTPException(status_code=status_code, detail=error_message)

        if isinstance(response.get("body"), str):
            result = json.loads(response["body"])
        else:
            result = response.get("body", {})

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sprint completion error: {str(e)}")


def agent_add_task_to_sprint(
    requesting_user: str,
    project_id: str,
    task_identifier: str,
    user_id: str,
    sprint_id: Optional[str] = None,
    sprint_name: Optional[str] = None,
):
    """
    Add a task to sprint using either sprint_id or sprint_name.

    Task identifier accepts ticket ID (AA-009) or Mongo _id.
    """
    try:
        if not sprint_id and not sprint_name:
            raise HTTPException(
                status_code=400,
                detail="Provide either sprint_id or sprint_name to add a task to sprint",
            )

        if not task_identifier or not str(task_identifier).strip():
            raise HTTPException(status_code=400, detail="task_identifier is required")

        # Validate requesting user from context email.
        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        actual_user_id = str(actual_user["_id"])

        # Validate project exists.
        project = Project.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project with ID '{project_id}' not found"
            )

        # Validate project membership.
        if not Project.is_member(project_id, actual_user_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied. Requesting user is not a member of this project.",
            )

        # Resolve sprint from id or name.
        sprint = None
        if sprint_id:
            sprint = db.sprints.find_one(
                {"_id": ObjectId(sprint_id), "project_id": project_id}
            )
        elif sprint_name:
            sprint = db.sprints.find_one(
                {
                    "project_id": project_id,
                    "name": {"$regex": f"^{re.escape(sprint_name)}$", "$options": "i"},
                }
            )

        if not sprint:
            identifier = sprint_id if sprint_id else sprint_name
            raise HTTPException(
                status_code=404,
                detail=f"Sprint '{identifier}' not found in project '{project_id}'",
            )

        sprint_id_resolved = str(sprint["_id"])

        # Resolve task by Mongo _id or ticket ID.
        raw_task_identifier = str(task_identifier).strip()
        is_object_id_like = bool(re.fullmatch(r"[0-9a-fA-F]{24}", raw_task_identifier))

        if is_object_id_like:
            task = Task.find_by_id(raw_task_identifier) or Task.find_by_ticket_id(
                raw_task_identifier
            )
        else:
            task = Task.find_by_ticket_id(raw_task_identifier) or Task.find_by_id(
                raw_task_identifier
            )

        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task '{raw_task_identifier}' not found",
            )

        if task.get("project_id") != project_id:
            raise HTTPException(
                status_code=400,
                detail="Task must belong to the same project as the sprint",
            )

        task_id_resolved = str(task["_id"])

        # Delegate to existing sprint controller logic.
        response = sprint_controller.add_task_to_sprint(
            sprint_id_resolved,
            json.dumps({"task_id": task_id_resolved}),
            actual_user_id,
        )

        status_code = response.get("statusCode", 200)
        if status_code >= 400:
            if isinstance(response.get("body"), str):
                error_body = json.loads(response["body"])
            else:
                error_body = response.get("body", {})

            error_message = error_body.get("error", "Failed to add task to sprint")
            raise HTTPException(status_code=status_code, detail=error_message)

        if isinstance(response.get("body"), str):
            result = json.loads(response["body"])
        else:
            result = response.get("body", {})

        result.update(
            {
                "project_id": project_id,
                "sprint_id": sprint_id_resolved,
                "sprint_name": sprint.get("name"),
                "task_id": task_id_resolved,
                "ticket_id": task.get("ticket_id"),
            }
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Add task to sprint error: {str(e)}")


def agent_bulk_add_tasks_to_sprint(
    requesting_user: str,
    project_id: str,
    task_identifiers: List[str],
    user_id: str,
    sprint_id: Optional[str] = None,
    sprint_name: Optional[str] = None,
):
    """
    Add multiple tasks to a sprint in one request.

    - Supports task identifiers as ticket IDs (AA-009) or Mongo _id values.
    - Resolves sprint by sprint_id (preferred) or sprint_name.
    - Returns per-task success and error details.
    """
    try:
        if not sprint_id and not sprint_name:
            raise HTTPException(
                status_code=400,
                detail="Provide either sprint_id or sprint_name to add tasks to sprint",
            )

        if not task_identifiers:
            raise HTTPException(
                status_code=400,
                detail="task_identifiers must include at least one task identifier",
            )

        # Validate requesting user from context email.
        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        actual_user_id = str(actual_user["_id"])

        # Validate project exists.
        project = Project.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project with ID '{project_id}' not found"
            )

        # Validate project membership.
        if not Project.is_member(project_id, actual_user_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied. Requesting user is not a member of this project.",
            )

        # Resolve sprint from id or name.
        sprint = None
        if sprint_id:
            sprint = db.sprints.find_one(
                {"_id": ObjectId(sprint_id), "project_id": project_id}
            )
        elif sprint_name:
            sprint = db.sprints.find_one(
                {
                    "project_id": project_id,
                    "name": {"$regex": f"^{re.escape(sprint_name)}$", "$options": "i"},
                }
            )

        if not sprint:
            identifier = sprint_id if sprint_id else sprint_name
            raise HTTPException(
                status_code=404,
                detail=f"Sprint '{identifier}' not found in project '{project_id}'",
            )

        sprint_id_resolved = str(sprint["_id"])

        updated_tasks = []
        errors = []

        for raw_identifier in task_identifiers:
            task_identifier = str(raw_identifier or "").strip()
            if not task_identifier:
                errors.append(
                    {
                        "task_identifier": raw_identifier,
                        "error": "Task identifier is empty",
                    }
                )
                continue

            is_object_id_like = bool(
                re.fullmatch(r"[0-9a-fA-F]{24}", task_identifier)
            )

            if is_object_id_like:
                task = Task.find_by_id(task_identifier) or Task.find_by_ticket_id(
                    task_identifier
                )
            else:
                task = Task.find_by_ticket_id(task_identifier) or Task.find_by_id(
                    task_identifier
                )

            if not task:
                errors.append(
                    {"task_identifier": task_identifier, "error": "Task not found"}
                )
                continue

            if task.get("project_id") != project_id:
                errors.append(
                    {
                        "task_identifier": task_identifier,
                        "error": "Task does not belong to provided project_id",
                    }
                )
                continue

            task_id_resolved = str(task["_id"])

            response = sprint_controller.add_task_to_sprint(
                sprint_id_resolved,
                json.dumps({"task_id": task_id_resolved}),
                actual_user_id,
            )

            status_code = response.get("statusCode", 200)
            if status_code >= 400:
                if isinstance(response.get("body"), str):
                    error_body = json.loads(response["body"])
                else:
                    error_body = response.get("body", {})

                errors.append(
                    {
                        "task_identifier": task_identifier,
                        "error": error_body.get("error", "Failed to add task to sprint"),
                    }
                )
                continue

            updated_tasks.append(
                {
                    "task_identifier": task_identifier,
                    "task_id": task_id_resolved,
                    "ticket_id": task.get("ticket_id"),
                    "sprint_id": sprint_id_resolved,
                    "sprint_name": sprint.get("name"),
                }
            )

        return {
            "success": len(updated_tasks) > 0,
            "message": "Bulk add tasks to sprint completed",
            "project_id": project_id,
            "sprint_id": sprint_id_resolved,
            "sprint_name": sprint.get("name"),
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
            status_code=500, detail=f"Bulk add tasks to sprint error: {str(e)}"
        )


def agent_remove_task_from_sprint(
    requesting_user: str,
    project_id: str,
    task_identifier: str,
    user_id: str,
    sprint_id: Optional[str] = None,
    sprint_name: Optional[str] = None,
):
    """
    Remove a task from sprint using either sprint_id or sprint_name.

    Task identifier accepts ticket ID (AA-010) or Mongo _id.
    """
    try:
        if not sprint_id and not sprint_name:
            raise HTTPException(
                status_code=400,
                detail="Provide either sprint_id or sprint_name to remove a task from sprint",
            )

        if not task_identifier or not str(task_identifier).strip():
            raise HTTPException(status_code=400, detail="task_identifier is required")

        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        actual_user_id = str(actual_user["_id"])

        project = Project.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project with ID '{project_id}' not found"
            )

        if not Project.is_member(project_id, actual_user_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied. Requesting user is not a member of this project.",
            )

        sprint = None
        if sprint_id:
            sprint = db.sprints.find_one(
                {"_id": ObjectId(sprint_id), "project_id": project_id}
            )
        elif sprint_name:
            sprint = db.sprints.find_one(
                {
                    "project_id": project_id,
                    "name": {"$regex": f"^{re.escape(sprint_name)}$", "$options": "i"},
                }
            )

        if not sprint:
            identifier = sprint_id if sprint_id else sprint_name
            raise HTTPException(
                status_code=404,
                detail=f"Sprint '{identifier}' not found in project '{project_id}'",
            )

        sprint_id_resolved = str(sprint["_id"])

        raw_task_identifier = str(task_identifier).strip()
        is_object_id_like = bool(re.fullmatch(r"[0-9a-fA-F]{24}", raw_task_identifier))

        if is_object_id_like:
            task = Task.find_by_id(raw_task_identifier) or Task.find_by_ticket_id(
                raw_task_identifier
            )
        else:
            task = Task.find_by_ticket_id(raw_task_identifier) or Task.find_by_id(
                raw_task_identifier
            )

        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task '{raw_task_identifier}' not found",
            )

        if task.get("project_id") != project_id:
            raise HTTPException(
                status_code=400,
                detail="Task must belong to the same project as the sprint",
            )

        task_id_resolved = str(task["_id"])

        response = sprint_controller.remove_task_from_sprint(
            sprint_id_resolved,
            task_id_resolved,
            actual_user_id,
        )

        status_code = response.get("statusCode", 200)
        if status_code >= 400:
            if isinstance(response.get("body"), str):
                error_body = json.loads(response["body"])
            else:
                error_body = response.get("body", {})

            error_message = error_body.get("error", "Failed to remove task from sprint")
            raise HTTPException(status_code=status_code, detail=error_message)

        if isinstance(response.get("body"), str):
            result = json.loads(response["body"])
        else:
            result = response.get("body", {})

        result.update(
            {
                "project_id": project_id,
                "sprint_id": sprint_id_resolved,
                "sprint_name": sprint.get("name"),
                "task_id": task_id_resolved,
                "ticket_id": task.get("ticket_id"),
            }
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remove task from sprint error: {str(e)}")


def agent_bulk_remove_tasks_from_sprint(
    requesting_user: str,
    project_id: str,
    task_identifiers: List[str],
    user_id: str,
    sprint_id: Optional[str] = None,
    sprint_name: Optional[str] = None,
):
    """
    Remove multiple tasks from a sprint in one request.

    - Supports task identifiers as ticket IDs (AA-010) or Mongo _id values.
    - Resolves sprint by sprint_id (preferred) or sprint_name.
    - Returns per-task success and error details.
    """
    try:
        if not sprint_id and not sprint_name:
            raise HTTPException(
                status_code=400,
                detail="Provide either sprint_id or sprint_name to remove tasks from sprint",
            )

        if not task_identifiers:
            raise HTTPException(
                status_code=400,
                detail="task_identifiers must include at least one task identifier",
            )

        actual_user = User.find_by_email(requesting_user)
        if not actual_user:
            raise HTTPException(
                status_code=404, detail=f"User with email '{requesting_user}' not found"
            )

        actual_user_id = str(actual_user["_id"])

        project = Project.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project with ID '{project_id}' not found"
            )

        if not Project.is_member(project_id, actual_user_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied. Requesting user is not a member of this project.",
            )

        sprint = None
        if sprint_id:
            sprint = db.sprints.find_one(
                {"_id": ObjectId(sprint_id), "project_id": project_id}
            )
        elif sprint_name:
            sprint = db.sprints.find_one(
                {
                    "project_id": project_id,
                    "name": {"$regex": f"^{re.escape(sprint_name)}$", "$options": "i"},
                }
            )

        if not sprint:
            identifier = sprint_id if sprint_id else sprint_name
            raise HTTPException(
                status_code=404,
                detail=f"Sprint '{identifier}' not found in project '{project_id}'",
            )

        sprint_id_resolved = str(sprint["_id"])

        removed_tasks = []
        errors = []

        for raw_identifier in task_identifiers:
            task_identifier = str(raw_identifier or "").strip()
            if not task_identifier:
                errors.append(
                    {
                        "task_identifier": raw_identifier,
                        "error": "Task identifier is empty",
                    }
                )
                continue

            is_object_id_like = bool(
                re.fullmatch(r"[0-9a-fA-F]{24}", task_identifier)
            )

            if is_object_id_like:
                task = Task.find_by_id(task_identifier) or Task.find_by_ticket_id(
                    task_identifier
                )
            else:
                task = Task.find_by_ticket_id(task_identifier) or Task.find_by_id(
                    task_identifier
                )

            if not task:
                errors.append(
                    {"task_identifier": task_identifier, "error": "Task not found"}
                )
                continue

            if task.get("project_id") != project_id:
                errors.append(
                    {
                        "task_identifier": task_identifier,
                        "error": "Task does not belong to provided project_id",
                    }
                )
                continue

            task_id_resolved = str(task["_id"])

            response = sprint_controller.remove_task_from_sprint(
                sprint_id_resolved,
                task_id_resolved,
                actual_user_id,
            )

            status_code = response.get("statusCode", 200)
            if status_code >= 400:
                if isinstance(response.get("body"), str):
                    error_body = json.loads(response["body"])
                else:
                    error_body = response.get("body", {})

                errors.append(
                    {
                        "task_identifier": task_identifier,
                        "error": error_body.get(
                            "error", "Failed to remove task from sprint"
                        ),
                    }
                )
                continue

            removed_tasks.append(
                {
                    "task_identifier": task_identifier,
                    "task_id": task_id_resolved,
                    "ticket_id": task.get("ticket_id"),
                    "sprint_id": sprint_id_resolved,
                    "sprint_name": sprint.get("name"),
                }
            )

        return {
            "success": len(removed_tasks) > 0,
            "message": "Bulk remove tasks from sprint completed",
            "project_id": project_id,
            "sprint_id": sprint_id_resolved,
            "sprint_name": sprint.get("name"),
            "total_requested": len(task_identifiers),
            "removed_count": len(removed_tasks),
            "failed_count": len(errors),
            "removed_tasks": removed_tasks,
            "errors": errors,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Bulk remove tasks from sprint error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# SYNCHRONOUS VERSION FOR LANGGRAPH TOOLS
# ─────────────────────────────────────────────────────────────────────────────
# backend-2/controllers/agent_sprint_controller.py


def agent_create_sprint_sync(
    requesting_user: str,
    name: str,
    project_id: str,
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    goal: str = "",
):
    """
    Synchronous version of agent_create_sprint for use in LangGraph tools.
    Creates sprint directly in database to avoid async/controller issues.
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

        # Create sprint document with ALL expected fields
        sprint = {
            "name": name,
            "goal": goal,
            "project_id": project_id,
            "status": "planned",
            "created_by": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None,  # Add this field
            "tasks": [],
        }

        if start_date:
            sprint["start_date"] = start_date
        else:
            sprint["start_date"] = None

        if end_date:
            sprint["end_date"] = end_date
        else:
            sprint["end_date"] = None

        # Insert sprint
        result = db.sprints.insert_one(sprint)
        sprint["_id"] = str(result.inserted_id)

        return {"success": True, "sprint": sprint}

    except Exception as e:
        raise Exception(f"Failed to create sprint: {str(e)}")
