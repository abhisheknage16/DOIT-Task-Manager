"""
Agent Task Controller
Simplified interface for AI Agent to create and manage tasks
"""

from fastapi import HTTPException
from controllers import task_controller
from models.user import User
from models.project import Project
import json


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
                status_code=404,
                detail=f"User with email '{requesting_user}' not found"
            )
        
        # Step 2: Check if user has permission to create tasks (Admin or Member)
        user_role = actual_user.get("role", "").lower()
        if user_role not in ["admin", "member"]:
            raise HTTPException(
                status_code=403,
                detail=f"Only Admin and Member users can create tasks. Your role is '{actual_user.get('role')}'"
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
            from database import db

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


def agent_assign_task(requesting_user: str, task_id: str, assignee_identifier: str, user_id: str):
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
                status_code=404,
                detail=f"User with email '{requesting_user}' not found"
            )
        
        # Step 2: Check permission (Admin or Member)
        user_role = actual_user.get("role", "").lower()
        if user_role not in ["admin", "member"]:
            raise HTTPException(
                status_code=403,
                detail=f"Only Admin and Member users can assign tasks. Your role is '{actual_user.get('role')}'"
            )
        
        modifier_id = str(actual_user["_id"])
    
        # Try email first
        assignee = User.find_by_email(assignee_identifier)

        # Try name if email fails
        if not assignee:
            from database import db

            assignee = db.users.find_one(
                {"name": {"$regex": f"^{assignee_identifier}$", "$options": "i"}}
            )

        if not assignee:
            raise HTTPException(
                status_code=404, detail=f"User '{assignee_identifier}' not found"
            )

        assignee_id = str(assignee["_id"])

        # Resolve task_id - could be ticket_id (FTP-005) or MongoDB _id
        from models.task import Task
        task = Task.find_by_ticket_id(task_id) if task_id.startswith(('FTP-', 'SLS-', 'TMP-', 'TST-', 'NP-')) else Task.find_by_id(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task '{task_id}' not found"
            )
        
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

