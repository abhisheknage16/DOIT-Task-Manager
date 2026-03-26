from __future__ import annotations

import json
import sys
import contextlib
from pathlib import Path
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

with contextlib.redirect_stdout(sys.stderr):
    from controllers import member_controller
    from utils.local_agent_automation import find_user_by_email_or_name, resolve_project_id

mcp = FastMCP("doit-member-server")


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
def list_members(
    requesting_user_id: str,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    """List all members (including owner) in a project."""
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

        payload = _controller_payload(
            _run_silenced(
                member_controller.get_project_members,
                resolved_project_id,
                requesting_user_id,
            )
        )
        return json.dumps(payload, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def add_member(
    requesting_user_id: str,
    member_email: str,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    """Add a user to a project by email (owner-only as per RBAC)."""
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

        payload = _controller_payload(
            _run_silenced(
                member_controller.add_project_member,
                json.dumps({"email": member_email}),
                resolved_project_id,
                requesting_user_id,
            )
        )
        return json.dumps(payload, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def remove_member(
    requesting_user_id: str,
    member_identifier: str,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    """Remove a project member by email or name (owner-only as per RBAC)."""
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

        member = find_user_by_email_or_name(member_identifier)
        if not member:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Member '{member_identifier}' not found.",
                }
            )

        payload = _controller_payload(
            _run_silenced(
                member_controller.remove_project_member,
                resolved_project_id,
                member["_id"],
                requesting_user_id,
            )
        )
        return json.dumps(payload, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
