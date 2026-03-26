from __future__ import annotations

import json
import sys
import contextlib
from pathlib import Path
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

with contextlib.redirect_stdout(sys.stderr):
    from controllers import project_controller

mcp = FastMCP("doit-project-server")


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
def list_projects(requesting_user_id: str) -> str:
    """List all projects visible to the authenticated user."""
    try:
        payload = _controller_payload(
            _run_silenced(project_controller.get_user_projects, requesting_user_id)
        )
        return json.dumps(payload, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def create_project(
    requesting_user_id: str,
    name: str,
    description: str = "",
) -> str:
    """Create a project (admin/super-admin as enforced by controller RBAC)."""
    try:
        body = json.dumps({"name": name, "description": description})
        payload = _controller_payload(
            _run_silenced(project_controller.create_project, body, requesting_user_id)
        )
        return json.dumps(payload, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
