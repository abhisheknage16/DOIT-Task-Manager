from __future__ import annotations

import json
import sys
import contextlib
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

with contextlib.redirect_stdout(sys.stderr):
    from controllers import sprint_controller
    from controllers.agent_sprint_controller import agent_create_sprint
    from database import db
    from utils.local_agent_automation import (
        find_sprint_by_name_or_id,
        find_task_by_title_or_id,
        resolve_project_id,
    )

mcp = FastMCP("doit-sprint-server")


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


def _run_silenced(func, *args, **kwargs):
    with contextlib.redirect_stdout(sys.stderr):
        return func(*args, **kwargs)


@mcp.tool()
def create_sprint(
    requesting_user_id: str,
    requesting_user_email: str,
    name: str,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    goal: str = "",
) -> str:
    """Create a sprint for a project (admin roles only as per RBAC)."""
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

        result = _run_silenced(
            agent_create_sprint,
            requesting_user=requesting_user_email,
            name=name,
            project_id=resolved_project_id,
            start_date=start_date or "",
            end_date=end_date or "",
            user_id=requesting_user_id,
            goal=goal,
        )

        return json.dumps(
            {
                "success": True,
                "action": "create_sprint",
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
def list_sprints(
    requesting_user_id: str,
    project_name: Optional[str] = None,
) -> str:
    """List sprints in a project, or across all projects visible to the user."""
    try:
        if project_name:
            project_id = resolve_project_id(requesting_user_id, project_name=project_name)
            if not project_id:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Project '{project_name}' not found.",
                    }
                )
            response = _run_silenced(
                sprint_controller.get_project_sprints, project_id, requesting_user_id
            )
            payload = _controller_payload(response)
            return json.dumps(payload, default=str)

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

        docs = list(db.sprints.find({"project_id": {"$in": project_ids}}).sort("created_at", -1))
        sprints = []
        for sprint in docs:
            sprint_id = str(sprint.get("_id"))
            sprints.append(
                {
                    "sprint_id": sprint_id,
                    "name": sprint.get("name"),
                    "project_id": sprint.get("project_id"),
                    "status": sprint.get("status", "planned"),
                    "start_date": sprint.get("start_date"),
                    "end_date": sprint.get("end_date"),
                    "goal": sprint.get("goal", ""),
                    "total_tasks": db.tasks.count_documents({"sprint_id": sprint_id}),
                    "completed_tasks": db.tasks.count_documents(
                        {"sprint_id": sprint_id, "status": "Done"}
                    ),
                }
            )

        return json.dumps({"success": True, "count": len(sprints), "sprints": sprints}, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def start_sprint(
    requesting_user_id: str,
    sprint_identifier: str,
    project_name: Optional[str] = None,
) -> str:
    """Start a sprint by sprint name or ID."""
    try:
        project_id = None
        if project_name:
            project_id = resolve_project_id(requesting_user_id, project_name=project_name)

        sprint = find_sprint_by_name_or_id(
            user_id=requesting_user_id,
            project_id=project_id,
            sprint_id=sprint_identifier,
            sprint_name=sprint_identifier,
        )
        if not sprint:
            return json.dumps({"success": False, "error": "Sprint not found."})

        payload = _controller_payload(
            _run_silenced(sprint_controller.start_sprint, sprint["_id"], requesting_user_id)
        )
        return json.dumps(payload, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def complete_sprint(
    requesting_user_id: str,
    sprint_identifier: str,
    project_name: Optional[str] = None,
) -> str:
    """Complete a sprint by sprint name or ID."""
    try:
        project_id = None
        if project_name:
            project_id = resolve_project_id(requesting_user_id, project_name=project_name)

        sprint = find_sprint_by_name_or_id(
            user_id=requesting_user_id,
            project_id=project_id,
            sprint_id=sprint_identifier,
            sprint_name=sprint_identifier,
        )
        if not sprint:
            return json.dumps({"success": False, "error": "Sprint not found."})

        payload = _controller_payload(
            _run_silenced(
                sprint_controller.complete_sprint, sprint["_id"], requesting_user_id
            )
        )
        return json.dumps(payload, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def add_ticket_to_sprint(
    requesting_user_id: str,
    task_identifier: str,
    sprint_identifier: str,
    project_name: Optional[str] = None,
) -> str:
    """Add a task/ticket into a sprint."""
    try:
        project_id = None
        if project_name:
            project_id = resolve_project_id(requesting_user_id, project_name=project_name)

        sprint = find_sprint_by_name_or_id(
            user_id=requesting_user_id,
            project_id=project_id,
            sprint_id=sprint_identifier,
            sprint_name=sprint_identifier,
        )
        if not sprint:
            return json.dumps({"success": False, "error": "Sprint not found."})

        task = find_task_by_title_or_id(
            user_id=requesting_user_id,
            task_id=task_identifier,
            task_title=task_identifier,
            ticket_id=task_identifier,
        )
        if not task:
            return json.dumps({"success": False, "error": "Task not found."})

        body = json.dumps({"task_id": task["_id"]})
        payload = _controller_payload(
            _run_silenced(
                sprint_controller.add_task_to_sprint,
                sprint["_id"],
                body,
                requesting_user_id,
            )
        )
        return json.dumps(payload, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def remove_ticket_from_sprint(
    requesting_user_id: str,
    task_identifier: str,
    sprint_identifier: str,
    project_name: Optional[str] = None,
) -> str:
    """Remove a task/ticket from a sprint."""
    try:
        project_id = None
        if project_name:
            project_id = resolve_project_id(requesting_user_id, project_name=project_name)

        sprint = find_sprint_by_name_or_id(
            user_id=requesting_user_id,
            project_id=project_id,
            sprint_id=sprint_identifier,
            sprint_name=sprint_identifier,
        )
        if not sprint:
            return json.dumps({"success": False, "error": "Sprint not found."})

        task = find_task_by_title_or_id(
            user_id=requesting_user_id,
            task_id=task_identifier,
            task_title=task_identifier,
            ticket_id=task_identifier,
        )
        if not task:
            return json.dumps({"success": False, "error": "Task not found."})

        payload = _controller_payload(
            _run_silenced(
                sprint_controller.remove_task_from_sprint,
                sprint["_id"],
                task["_id"],
                requesting_user_id,
            )
        )
        return json.dumps(payload, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
