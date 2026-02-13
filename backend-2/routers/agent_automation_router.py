"""
Agent Automation Router
Provides simplified endpoints for Azure AI Agent to create and assign tasks
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from middleware.agent_auth import verify_agent_token
from controllers.agent_task_controller import agent_create_task, agent_assign_task
import json

router = APIRouter(prefix="/api/agent/automation", tags=["Agent Automation"])


class CreateTaskRequest(BaseModel):
    requesting_user: EmailStr  # Email of user making the request
    title: str
    project_id: str
    description: Optional[str] = ""
    assignee_email: Optional[EmailStr] = None
    assignee_name: Optional[str] = None
    priority: Optional[str] = "Medium"
    status: Optional[str] = "To Do"
    due_date: Optional[str] = None
    issue_type: Optional[str] = "task"
    labels: Optional[List[str]] = []


class AssignTaskRequest(BaseModel):
    requesting_user: EmailStr  # Email of user making the request
    assignee_identifier: str  # Email or name


@router.post("/tasks")
async def create_task_automation(
    request: CreateTaskRequest, agent_user_id: str = Depends(verify_agent_token)
):
    """
    Create a task with automatic assignee resolution and RBAC validation

    Requires:
    - requesting_user: Email of the user making this request (for permission check)
    - title, project_id: Required task fields

    Agent can provide either:
    - assignee_email: "john@example.com"
    - assignee_name: "John Doe"

    The system will automatically find and assign the user
    
    Permissions: Admin or Member can create tasks
    """
    return agent_create_task(
        requesting_user=request.requesting_user,
        title=request.title,
        project_id=request.project_id,
        user_id=agent_user_id,
        description=request.description,
        assignee_email=request.assignee_email,
        assignee_name=request.assignee_name,
        priority=request.priority,
        status=request.status,
        due_date=request.due_date,
        issue_type=request.issue_type,
        labels=request.labels,
    )


@router.put("/tasks/{task_id}/assign")
async def assign_task_automation(
    task_id: str,
    request: AssignTaskRequest,
    agent_user_id: str = Depends(verify_agent_token),
):
    """
    Assign a task to a user by email or name with RBAC validation

    Requires:
    - requesting_user: Email of the user making this request
    - assignee_identifier: Email or name of user to assign to

    Example: {"requesting_user": "admin@example.com", "assignee_identifier": "john@example.com"}
    Example: {"requesting_user": "member@example.com", "assignee_identifier": "John Doe"}
    
    Permissions: Admin or Member can assign tasks
    """
    return agent_assign_task(
        requesting_user=request.requesting_user,
        task_id=task_id,
        assignee_identifier=request.assignee_identifier,
        user_id=agent_user_id,
    )


@router.get("/projects/{project_id}/assignable-users")
async def get_assignable_users(
    project_id: str, agent_user_id: str = Depends(verify_agent_token)
):
    """
    Get list of users who can be assigned tasks in a project
    """
    from controllers.member_controller import get_project_members

    response = get_project_members(project_id, agent_user_id)

    if isinstance(response.get("body"), str):
        return json.loads(response["body"])
    return response.get("body", {})

