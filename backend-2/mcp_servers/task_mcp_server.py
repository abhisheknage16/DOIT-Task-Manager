from __future__ import annotations

import json
import sys
import contextlib
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP

# Ensure backend root is importable when launched via stdio subprocess.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

with contextlib.redirect_stdout(sys.stderr):
    from controllers import task_controller
    from controllers.agent_task_controller import agent_assign_task, agent_create_task
    from database import db
    from utils.local_agent_automation import find_task_by_title_or_id, resolve_project_id

mcp = FastMCP("doit-task-server")


def _controller_payload(response: Dict[str, Any]) -> Dict[str, Any]:
    status = response.get("status", response.get("statusCode", 500))
    body = response.get("body", {})

    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            body = {"raw": body}

    return {
        "success": 200 <= status < 300,
        "status": status,
        **body,
    }


def _normalize_priority(priority: Optional[str]) -> str:
    if not priority:
        return "Medium"

    value = priority.strip().lower()
    if value == "critical":
        return "High"

    allowed = {"low": "Low", "medium": "Medium", "high": "High"}
    return allowed.get(value, "Medium")


def _run_silenced(func, *args, **kwargs):
    with contextlib.redirect_stdout(sys.stderr):
        return func(*args, **kwargs)


@mcp.tool()
def list_tasks(
    requesting_user_id: str,
    project_name: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 25,
) -> str:
    """List tasks user can access, with optional project/status/priority filters."""
    try:
        query: Dict[str, Any] = {}

        if project_name:
            project_id = resolve_project_id(requesting_user_id, project_name=project_name)
            if not project_id:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Project '{project_name}' not found for this user.",
                    }
                )
            query["project_id"] = project_id
        else:
            projects = list(
                db.projects.find(
                    {
                        "$or": [
                            {"user_id": requesting_user_id},
                            {"members.user_id": requesting_user_id},
                        ]
                    }
                )
            )
            project_ids = [str(project["_id"]) for project in projects]
            query["project_id"] = {"$in": project_ids}

        if status:
            query["status"] = status
        if priority:
            query["priority"] = priority

        docs = list(db.tasks.find(query).sort("created_at", -1).limit(max(1, min(limit, 100))))

        tasks = []
        for task in docs:
            tasks.append(
                {
                    "task_id": str(task.get("_id")),
                    "ticket_id": task.get("ticket_id"),
                    "title": task.get("title"),
                    "project_id": task.get("project_id"),
                    "status": task.get("status"),
                    "priority": task.get("priority"),
                    "assignee_name": task.get("assignee_name"),
                    "assignee_email": task.get("assignee_email"),
                    "sprint_id": task.get("sprint_id"),
                    "due_date": task.get("due_date"),
                }
            )

        return json.dumps(
            {
                "success": True,
                "count": len(tasks),
                "tasks": tasks,
            },
            default=str,
        )
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def create_ticket(
    requesting_user_id: str,
    requesting_user_email: str,
    title: str,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
    description: str = "",
    priority: str = "Medium",
    issue_type: str = "task",
    due_date: Optional[str] = None,
    assignee_email: Optional[str] = None,
    assignee_name: Optional[str] = None,
    labels: Optional[list[str]] = None,
) -> str:
    """Create a task/ticket using RBAC-aware task controller flow."""
    try:
        resolved_project_id = resolve_project_id(
            requesting_user_id,
            project_id=project_id,
            project_name=project_name,
        )
        if not resolved_project_id:
            return json.dumps(
                {
                    "success": False,
                    "error": "Could not resolve project. Provide a valid project_name or project_id.",
                }
            )

        kwargs: Dict[str, Any] = {
            "description": description,
            "priority": _normalize_priority(priority),
            "issue_type": (issue_type or "task").lower(),
        }

        if due_date:
            kwargs["due_date"] = due_date
        if labels:
            kwargs["labels"] = labels

        result = _run_silenced(
            agent_create_task,
            requesting_user=requesting_user_email,
            title=title,
            project_id=resolved_project_id,
            user_id=requesting_user_id,
            assignee_email=assignee_email,
            assignee_name=assignee_name,
            **kwargs,
        )

        return json.dumps(
            {
                "success": True,
                "action": "create_ticket",
                "project_id": resolved_project_id,
                "result": result,
            },
            default=str,
        )
    except HTTPException as exc:
        return json.dumps(
            {
                "success": False,
                "status": exc.status_code,
                "error": exc.detail,
            }
        )
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def assign_ticket(
    requesting_user_id: str,
    requesting_user_email: str,
    task_identifier: str,
    assignee_identifier: str,
) -> str:
    """Assign a task by ticket ID, task ID, or task title."""
    try:
        task = find_task_by_title_or_id(
            user_id=requesting_user_id,
            task_id=task_identifier,
            task_title=task_identifier,
            ticket_id=task_identifier,
        )
        if not task:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Task '{task_identifier}' not found.",
                }
            )

        result = _run_silenced(
            agent_assign_task,
            requesting_user=requesting_user_email,
            task_id=task.get("ticket_id") or task["_id"],
            assignee_identifier=assignee_identifier,
            user_id=requesting_user_id,
        )

        return json.dumps(
            {
                "success": True,
                "action": "assign_ticket",
                "result": result,
            },
            default=str,
        )
    except HTTPException as exc:
        return json.dumps(
            {
                "success": False,
                "status": exc.status_code,
                "error": exc.detail,
            }
        )
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def update_ticket_status(
    requesting_user_id: str,
    task_identifier: str,
    new_status: str,
    comment: Optional[str] = None,
) -> str:
    """Update a task status (e.g., To Do, In Progress, Done, Closed)."""
    try:
        task = find_task_by_title_or_id(
            user_id=requesting_user_id,
            task_id=task_identifier,
            task_title=task_identifier,
            ticket_id=task_identifier,
        )
        if not task:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Task '{task_identifier}' not found.",
                }
            )

        body = {"status": new_status}
        if comment:
            body["comment"] = comment

        response = _run_silenced(
            task_controller.update_task,
            json.dumps(body),
            task["_id"],
            requesting_user_id,
        )

        return json.dumps(_controller_payload(response), default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
