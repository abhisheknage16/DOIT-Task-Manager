from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv(override=True)
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except Exception:  # pragma: no cover - graceful degradation if MCP isn't installed
    ClientSession = None  # type: ignore[assignment]
    StdioServerParameters = None  # type: ignore[assignment]
    stdio_client = None  # type: ignore[assignment]


MCP_SERVER_SCRIPTS: Dict[str, Path] = {
    "task": Path(__file__).resolve().parents[1] / "mcp_servers" / "task_mcp_server.py",
    "sprint": Path(__file__).resolve().parents[1]
    / "mcp_servers"
    / "sprint_mcp_server.py",
    "project": Path(__file__).resolve().parents[1]
    / "mcp_servers"
    / "project_mcp_server.py",
    "member": Path(__file__).resolve().parents[1]
    / "mcp_servers"
    / "member_mcp_server.py",
}

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _mcp_available() -> bool:
    return (
        ClientSession is not None
        and StdioServerParameters is not None
        and stdio_client is not None
    )


def get_mcp_runtime_diagnostics() -> Dict[str, Any]:
    return {
        "mcp_sdk_available": _mcp_available(),
        "python_executable": sys.executable,
        "backend_root": str(BACKEND_ROOT),
        "mcp_python_executable_override": os.getenv("MCP_PYTHON_EXECUTABLE"),
    }


def _build_server_params(script_path: Path):
    python_executable = os.getenv("MCP_PYTHON_EXECUTABLE") or sys.executable
    env = {**os.environ}
    env["PYTHONUNBUFFERED"] = "1"

    existing_pythonpath = env.get("PYTHONPATH", "")
    backend_root_str = str(BACKEND_ROOT)
    if existing_pythonpath:
        if backend_root_str not in existing_pythonpath.split(os.pathsep):
            env["PYTHONPATH"] = existing_pythonpath + os.pathsep + backend_root_str
    else:
        env["PYTHONPATH"] = backend_root_str

    return StdioServerParameters(
        command=python_executable,
        args=[str(script_path)],
        env=env,
    )


def _extract_text_from_tool_result(result: Any) -> Dict[str, Any]:
    """
    Extract BOTH structured and text output from MCP result.
    """
    if result is None:
        return {"text": "", "data": None}

    # Case 1: MCP structured content
    content = getattr(result, "content", None)
    if content:
        texts = []
        structured = []

        for item in content:
            # MCP text segment
            if hasattr(item, "text") and item.text:
                texts.append(item.text)

            # MCP structured JSON (VERY IMPORTANT)
            if hasattr(item, "data"):
                structured.append(item.data)

        return {
            "text": "\n".join(texts).strip(),
            "data": structured if structured else None,
        }

    # Case 2: raw string
    if isinstance(result, str):
        try:
            return {"text": result, "data": json.loads(result)}
        except:
            return {"text": result, "data": None}

    # Case 3: dict already
    if isinstance(result, dict):
        return {"text": json.dumps(result, indent=2), "data": result}

    return {"text": str(result), "data": None}


async def list_mcp_tools(server_name: str) -> Dict[str, Any]:
    """List tools exposed by a configured MCP server."""
    if not _mcp_available():
        return {
            "success": False,
            "error": (
                "MCP SDK is not available in the backend runtime. "
                "Install with: pip install 'mcp[cli]' and restart backend using the same Python environment."
            ),
            **get_mcp_runtime_diagnostics(),
        }

    script_path = MCP_SERVER_SCRIPTS.get(server_name)
    if not script_path or not script_path.exists():
        return {
            "success": False,
            "error": f"MCP server '{server_name}' is not configured.",
        }

    server_params = _build_server_params(script_path)

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_response = await session.list_tools()

                tools = getattr(tools_response, "tools", []) or []
                tool_names = [getattr(tool, "name", str(tool)) for tool in tools]

                return {
                    "success": True,
                    "server": server_name,
                    "tools": tool_names,
                }
    except Exception as exc:
        return {
            "success": False,
            "server": server_name,
            "error": str(exc),
        }


async def call_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call one MCP tool over stdio and normalize the response payload."""
    if not _mcp_available():
        return {
            "success": False,
            "server": server_name,
            "tool": tool_name,
            "error": (
                "MCP SDK is not available in the backend runtime. "
                "Install with: pip install 'mcp[cli]' and restart backend using the same Python environment."
            ),
            **get_mcp_runtime_diagnostics(),
        }

    script_path = MCP_SERVER_SCRIPTS.get(server_name)
    if not script_path or not script_path.exists():
        return {
            "success": False,
            "server": server_name,
            "tool": tool_name,
            "error": f"MCP server '{server_name}' is not configured.",
        }

    server_params = _build_server_params(script_path)

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                raw_result = await session.call_tool(tool_name, arguments or {})

                extracted = _extract_text_from_tool_result(raw_result)
                text_output = extracted["text"]
                structured_data = extracted["data"]
                parsed: Dict[str, Any] = {}

                # Prefer structured data
                if structured_data:
                    parsed = {
                        "success": True,
                        "data": structured_data,
                        "summary": text_output,
                    }

                else:
                    try:
                        maybe_json = json.loads(text_output) if text_output else {}
                        parsed = (
                            maybe_json
                            if isinstance(maybe_json, dict)
                            else {"data": maybe_json}
                        )
                    except Exception:
                        parsed = {"output": text_output}

                if "success" not in parsed:
                    parsed["success"] = True

                formatted_output = _format_mcp_result(parsed)

                return {
                    "success": True,
                    "server": server_name,
                    "tool": tool_name,
                    "result": parsed,
                    "formatted": formatted_output, 
                    "raw_text": text_output,
                }
    except Exception as exc:
        return {
            "success": False,
            "server": server_name,
            "tool": tool_name,
            "error": str(exc),
        }


def _format_mcp_result(result: Dict[str, Any]) -> str:
    """Convert structured MCP result into detailed human-readable output."""
    data = result.get("data")

    if not data:
        return result.get("summary") or result.get("output", "")

    # If list of items (MOST IMPORTANT CASE)
    if isinstance(data, list):
        lines = []
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                line = f"{i}. " + ", ".join(f"{k}: {v}" for k, v in item.items())
                lines.append(line)
            else:
                lines.append(f"{i}. {item}")
        return "\n".join(lines)

    # If dict
    if isinstance(data, dict):
        return "\n".join(f"{k}: {v}" for k, v in data.items())

    return str(data)


async def get_mcp_servers_health() -> Dict[str, Any]:
    """Check if all configured MCP servers are reachable and list their tools."""
    checks = await asyncio.gather(
        *(list_mcp_tools(name) for name in MCP_SERVER_SCRIPTS.keys())
    )

    healthy = all(check.get("success") for check in checks)
    return {
        "healthy": healthy,
        "servers": checks,
    }
