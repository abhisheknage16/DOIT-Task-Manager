"""
Agent Data Access Router
Provides real-time MongoDB data access for Azure AI Agent
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from database import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["Agent Data Access"])


@router.get("/projects")
async def get_all_projects_for_agent():
    """
    Get all projects data for AI agent
    Returns simplified project information from MongoDB
    """
    try:
        projects = list(db.projects.find({}, {
            "_id": 0,
            "project_id": 1,
            "name": 1,
            "description": 1,
            "status": 1,
            "owner": 1,
            "owner_name": 1,
            "members": 1,
            "created_at": 1,
            "updated_at": 1,
            "progress_percentage": 1,
            "total_tasks": 1,
            "completed_tasks": 1
        }).limit(100))
        
        # Convert datetime objects to strings
        for project in projects:
            if project.get("created_at"):
                project["created_at"] = str(project["created_at"])
            if project.get("updated_at"):
                project["updated_at"] = str(project["updated_at"])
        
        return {
            "success": True,
            "count": len(projects),
            "projects": projects
        }
    except Exception as e:
        logger.error(f"Error fetching projects for agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")


@router.get("/tasks")
async def get_all_tasks_for_agent(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 100
):
    """
    Get tasks data for AI agent with optional filters
    
    Parameters:
    - project_id: Filter by specific project
    - status: Filter by status (To Do, In Progress, Dev Complete, Testing, Done)
    - priority: Filter by priority (Critical, High, Medium, Low)
    - assigned_to: Filter by assigned user ID
    - limit: Maximum number of results (default 100)
    """
    try:
        query = {}
        if project_id:
            query["project_id"] = project_id
        if status:
            query["status"] = status
        if priority:
            query["priority"] = priority
        if assigned_to:
            query["assigned_to"] = assigned_to
            
        tasks = list(db.tasks.find(query, {
            "_id": 0,
            "task_id": 1,
            "title": 1,
            "description": 1,
            "status": 1,
            "priority": 1,
            "assigned_to": 1,
            "assigned_to_name": 1,
            "project_id": 1,
            "project_name": 1,
            "ticket_id": 1,
            "issue_type": 1,
            "labels": 1,
            "created_at": 1,
            "updated_at": 1,
            "due_date": 1,
            "sprint_id": 1
        }).limit(limit))
        
        # Convert datetime objects to strings
        for task in tasks:
            if task.get("created_at"):
                task["created_at"] = str(task["created_at"])
            if task.get("updated_at"):
                task["updated_at"] = str(task["updated_at"])
            if task.get("due_date"):
                task["due_date"] = str(task["due_date"])
        
        return {
            "success": True,
            "count": len(tasks),
            "filters_applied": {
                "project_id": project_id,
                "status": status,
                "priority": priority,
                "assigned_to": assigned_to
            },
            "tasks": tasks
        }
    except Exception as e:
        logger.error(f"Error fetching tasks for agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching tasks: {str(e)}")


@router.get("/users")
async def get_all_users_for_agent():
    """
    Get users data for AI agent (excluding sensitive information)
    Returns user information without passwords, tokens, etc.
    """
    try:
        users = list(db.users.find({}, {
            "_id": 0,
            "user_id": 1,
            "name": 1,
            "email": 1,
            "role": 1,
            "organization": 1,
            "department": 1,
            "job_title": 1,
            "created_at": 1,
            "is_active": 1
            # Explicitly exclude: password, token_version, github_token, clerk_id
        }).limit(200))
        
        # Convert datetime objects to strings
        for user in users:
            if user.get("created_at"):
                user["created_at"] = str(user["created_at"])
        
        return {
            "success": True,
            "count": len(users),
            "users": users
        }
    except Exception as e:
        logger.error(f"Error fetching users for agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


@router.get("/sprints")
async def get_sprints_for_agent(
    project_id: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Get sprint data for AI agent
    
    Parameters:
    - project_id: Filter by specific project
    - status: Filter by status (Planning, Active, Completed)
    """
    try:
        query = {}
        if project_id:
            query["project_id"] = project_id
        if status:
            query["status"] = status
            
        sprints = list(db.sprints.find(query, {
            "_id": 0,
            "sprint_id": 1,
            "name": 1,
            "project_id": 1,
            "project_name": 1,
            "start_date": 1,
            "end_date": 1,
            "status": 1,
            "goal": 1,
            "tasks": 1,
            "total_tasks": 1,
            "completed_tasks": 1,
            "created_at": 1
        }).limit(100))
        
        # Convert datetime objects to strings
        for sprint in sprints:
            if sprint.get("created_at"):
                sprint["created_at"] = str(sprint["created_at"])
            if sprint.get("start_date"):
                sprint["start_date"] = str(sprint["start_date"])
            if sprint.get("end_date"):
                sprint["end_date"] = str(sprint["end_date"])
        
        return {
            "success": True,
            "count": len(sprints),
            "filters_applied": {
                "project_id": project_id,
                "status": status
            },
            "sprints": sprints
        }
    except Exception as e:
        logger.error(f"Error fetching sprints for agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching sprints: {str(e)}")


@router.get("/statistics")
async def get_project_statistics():
    """
    Get aggregated statistics for AI agent
    Provides overview of all projects, tasks, users, and their distributions
    """
    try:
        stats = {
            "total_projects": db.projects.count_documents({}),
            "total_tasks": db.tasks.count_documents({}),
            "total_users": db.users.count_documents({}),
            "total_sprints": db.sprints.count_documents({}),
            "tasks_by_status": {},
            "tasks_by_priority": {},
            "users_by_role": {},
            "projects_by_status": {}
        }
        
        # Task status distribution
        for status in ["To Do", "In Progress", "Dev Complete", "Testing", "Done"]:
            count = db.tasks.count_documents({"status": status})
            stats["tasks_by_status"][status] = count
        
        # Task priority distribution
        for priority in ["Critical", "High", "Medium", "Low"]:
            count = db.tasks.count_documents({"priority": priority})
            stats["tasks_by_priority"][priority] = count
        
        # Users by role
        for role in ["super-admin", "admin", "manager", "member", "viewer"]:
            count = db.users.count_documents({"role": role})
            stats["users_by_role"][role] = count
        
        # Projects by status
        for status in ["Active", "On Hold", "Completed"]:
            count = db.projects.count_documents({"status": status})
            stats["projects_by_status"][status] = count
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": str(datetime.utcnow())
        }
    except Exception as e:
        logger.error(f"Error fetching statistics for agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


@router.get("/task/{task_id}")
async def get_task_details(task_id: str):
    """
    Get detailed information about a specific task
    
    Parameters:
    - task_id: The unique task identifier
    """
    try:
        task = db.tasks.find_one({"task_id": task_id}, {"_id": 0})
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
        
        # Convert datetime objects to strings
        if task.get("created_at"):
            task["created_at"] = str(task["created_at"])
        if task.get("updated_at"):
            task["updated_at"] = str(task["updated_at"])
        if task.get("due_date"):
            task["due_date"] = str(task["due_date"])
        
        return {
            "success": True,
            "task": task
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching task details for agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching task: {str(e)}")


@router.get("/project/{project_id}")
async def get_project_details(project_id: str):
    """
    Get detailed information about a specific project
    
    Parameters:
    - project_id: The unique project identifier
    """
    try:
        project = db.projects.find_one({"project_id": project_id}, {"_id": 0})
        
        if not project:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
        
        # Convert datetime objects to strings
        if project.get("created_at"):
            project["created_at"] = str(project["created_at"])
        if project.get("updated_at"):
            project["updated_at"] = str(project["updated_at"])
        
        return {
            "success": True,
            "project": project
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project details for agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching project: {str(e)}")


@router.get("/health")
async def agent_api_health_check():
    """
    Health check endpoint for agent API
    """
    try:
        # Test database connection
        db.users.find_one()
        
        return {
            "status": "healthy",
            "service": "Agent Data API",
            "database": "connected",
            "timestamp": str(datetime.utcnow())
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "Agent Data API",
            "database": "disconnected",
            "error": str(e),
            "timestamp": str(datetime.utcnow())
        }
