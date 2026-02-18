# """
# Azure AI Foundry Agent Integration Utilities
# Connects to the MS Foundry AI Agent (asst_0uvId9Fz7NLJfxIwIzD0uN9b)
# Uses azure-ai-projects SDK with DefaultAzureCredential (Service Principal)
# """

# import os
# import time
# import json
# import logging
# from typing import Optional, Dict, Any
# from dotenv import load_dotenv

# load_dotenv()

# logger = logging.getLogger(__name__)

# # ─── Configuration ────────────────────────────────────────────────────────────
# AZURE_AI_PROJECT_CONNECTION = os.getenv("AZURE_AI_PROJECT_CONNECTION")
# AZURE_AGENT_ID = os.getenv("AZURE_AGENT_ID", "asst_0uvId9Fz7NLJfxIwIzD0uN9b")
# AZURE_AGENT_TIMEOUT = int(os.getenv("AZURE_AGENT_TIMEOUT", "60"))
# AGENT_THREAD_TTL = int(os.getenv("AGENT_THREAD_TTL", "86400"))  # 24 h

# # Service-principal creds (populated from env → picked up by DefaultAzureCredential)
# AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
# AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
# AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

# # ─── SDK initialisation ───────────────────────────────────────────────────────
# _agent_client = None  # AIProjectClient
# _agents_client = None  # client.agents handle


# def _parse_connection_string(conn: str) -> Dict[str, str]:
#     """
#     Parse Azure AI project connection string.
#     Format: <host>;<subscription_id>;<resource_group>;<project_name>
#     """
#     parts = [p.strip() for p in conn.split(";")]
#     if len(parts) != 4:
#         raise ValueError(
#             f"AZURE_AI_PROJECT_CONNECTION must have 4 semicolon-separated parts, got {len(parts)}"
#         )
#     return {
#         "endpoint": f"https://{parts[0]}",
#         "subscription_id": parts[1],
#         "resource_group": parts[2],
#         "project_name": parts[3],
#     }


# def get_agent_client():
#     """
#     Return (and lazily initialise) the Azure AI Project client.
#     Uses DefaultAzureCredential which automatically picks up
#     AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET from env.
#     """
#     global _agent_client, _agents_client

#     if _agent_client is not None:
#         return _agent_client, _agents_client

#     if not AZURE_AI_PROJECT_CONNECTION:
#         raise RuntimeError("AZURE_AI_PROJECT_CONNECTION is not set")

#     try:
#         from azure.ai.projects import AIProjectClient
#         from azure.identity import DefaultAzureCredential

#         parsed = _parse_connection_string(AZURE_AI_PROJECT_CONNECTION)

#         credential = DefaultAzureCredential()

#         _agent_client = AIProjectClient(
#             endpoint=parsed["endpoint"],
#             credential=credential,
#             # Some SDK versions also accept subscription_id / resource_group_name / project_name
#         )
#         _agents_client = _agent_client.agents

#         logger.info("✅ Azure AI Project client initialised")
#         print("✅ Azure AI Foundry Agent client ready")
#         return _agent_client, _agents_client

#     except ImportError as e:
#         raise RuntimeError(
#             "azure-ai-projects package not installed. "
#             "Run: pip install azure-ai-projects azure-identity --break-system-packages"
#         ) from e
#     except Exception as e:
#         logger.error(f"❌ Failed to init Azure AI client: {e}")
#         raise


# # ─── Thread cache (in-memory) ─────────────────────────────────────────────────
# # Maps user_id → {"thread_id": str, "created_at": float}
# _thread_cache: Dict[str, Dict[str, Any]] = {}


# def get_or_create_thread(user_id: str) -> str:
#     """
#     Return an existing active thread for the user, or create a new one.
#     Threads expire after AGENT_THREAD_TTL seconds.
#     """
#     _, agents = get_agent_client()

#     now = time.time()
#     cached = _thread_cache.get(user_id)

#     if cached and (now - cached["created_at"]) < AGENT_THREAD_TTL:
#         logger.debug(f"Reusing thread {cached['thread_id']} for user {user_id}")
#         return cached["thread_id"]

#     # Create fresh thread
#     thread = agents.create_thread()
#     thread_id = thread.id
#     _thread_cache[user_id] = {"thread_id": thread_id, "created_at": now}
#     logger.info(f"Created new agent thread {thread_id} for user {user_id}")
#     return thread_id


# def delete_thread(user_id: str) -> bool:
#     """Delete the cached thread for a user (start fresh conversation)."""
#     cached = _thread_cache.pop(user_id, None)
#     if not cached:
#         return False

#     try:
#         _, agents = get_agent_client()
#         agents.delete_thread(cached["thread_id"])
#         logger.info(f"Deleted thread {cached['thread_id']} for user {user_id}")
#         return True
#     except Exception as e:
#         logger.warning(f"Could not delete thread: {e}")
#         return False


# # ─── Core: send message and wait for reply ────────────────────────────────────


# def send_message_to_agent(
#     user_id: str,
#     message: str,
#     thread_id: Optional[str] = None,
#     context: Optional[Dict] = None,
# ) -> Dict[str, Any]:
#     """
#     Send a message to the Azure AI Foundry agent and wait for the response.

#     Args:
#         user_id:   ID of the DOIT user (used for thread management)
#         message:   The user's text message
#         thread_id: Optionally provide an existing thread ID
#         context:   Optional additional context dict (serialised into the message)

#     Returns:
#         {
#             "success": bool,
#             "response": str,          # agent text reply
#             "thread_id": str,
#             "run_id": str,
#             "tool_calls": list,       # any tool calls made
#             "tokens": dict            # usage if available
#         }
#     """
#     try:
#         _, agents = get_agent_client()

#         # ── Get / create thread ──────────────────────────────────────────
#         if not thread_id:
#             thread_id = get_or_create_thread(user_id)

#         # ── Optionally enrich message with context ───────────────────────
#         full_message = message
#         if context:
#             full_message = f"{message}\n\n[Context: {json.dumps(context, default=str)}]"

#         # ── Add user message to thread ───────────────────────────────────
#         agents.create_message(
#             thread_id=thread_id,
#             role="user",
#             content=full_message,
#         )

#         # ── Create and poll a run ────────────────────────────────────────
#         run = agents.create_and_process_run(
#             thread_id=thread_id,
#             assistant_id=AZURE_AGENT_ID,
#         )

#         # ── Handle terminal states ───────────────────────────────────────
#         if run.status == "failed":
#             err = getattr(run, "last_error", None)
#             err_msg = str(err) if err else "Run failed with unknown error"
#             logger.error(f"Agent run failed: {err_msg}")
#             return {
#                 "success": False,
#                 "error": err_msg,
#                 "thread_id": thread_id,
#                 "run_id": run.id,
#             }

#         # ── Collect assistant messages ───────────────────────────────────
#         messages = agents.list_messages(thread_id=thread_id)

#         response_text = ""
#         tool_calls_summary = []

#         # Messages are newest-first; grab the last assistant reply
#         for msg in messages:
#             if msg.role == "assistant":
#                 for block in msg.content:
#                     if hasattr(block, "text"):
#                         response_text = block.text.value
#                         break
#                 if response_text:
#                     break

#         # ── Token usage ──────────────────────────────────────────────────
#         tokens = {}
#         if hasattr(run, "usage") and run.usage:
#             tokens = {
#                 "prompt": getattr(run.usage, "prompt_tokens", 0),
#                 "completion": getattr(run.usage, "completion_tokens", 0),
#                 "total": getattr(run.usage, "total_tokens", 0),
#             }

#         return {
#             "success": True,
#             "response": response_text,
#             "thread_id": thread_id,
#             "run_id": run.id,
#             "run_status": run.status,
#             "tool_calls": tool_calls_summary,
#             "tokens": tokens,
#         }

#     except Exception as e:
#         logger.error(f"Error communicating with Azure agent: {e}", exc_info=True)
#         return {
#             "success": False,
#             "error": str(e),
#             "thread_id": thread_id or "",
#         }


# def get_thread_messages(thread_id: str) -> Dict[str, Any]:
#     """Retrieve all messages from an existing thread."""
#     try:
#         _, agents = get_agent_client()
#         raw = agents.list_messages(thread_id=thread_id)

#         messages = []
#         for msg in raw:
#             content_text = ""
#             for block in msg.content:
#                 if hasattr(block, "text"):
#                     content_text = block.text.value
#                     break
#             messages.append(
#                 {
#                     "id": msg.id,
#                     "role": msg.role,
#                     "content": content_text,
#                     "created_at": msg.created_at,
#                 }
#             )

#         return {"success": True, "messages": messages}

#     except Exception as e:
#         logger.error(f"Error fetching thread messages: {e}")
#         return {"success": False, "error": str(e)}


# def check_agent_health() -> Dict[str, Any]:
#     """Verify connectivity to the Azure AI Foundry agent."""
#     try:
#         _, agents = get_agent_client()
#         agent = agents.get_agent(AZURE_AGENT_ID)
#         return {
#             "healthy": True,
#             "agent_id": agent.id,
#             "agent_name": getattr(agent, "name", "unknown"),
#             "model": getattr(agent, "model", "unknown"),
#         }
#     except Exception as e:
#         return {"healthy": False, "error": str(e)}
"""
Azure AI Foundry Agent Integration Utilities
Connects to the MS Foundry AI Agent (asst_0uvId9Fz7NLJfxIwIzD0uN9b)

SDK: azure-ai-agents (standalone, not via azure-ai-projects)
Install: pip install azure-ai-agents azure-identity

AgentsClient is constructed directly with the project endpoint:
    AgentsClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())

The endpoint is of the form:
    https://<ai-services-account>.services.ai.azure.com/api/projects/<project-name>
Set as AZURE_AI_PROJECT_ENDPOINT in your .env file.
"""

import os
import time
import json
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv(
    "AZURE_AI_PROJECT_CONNECTION"
)
AZURE_AGENT_ID = os.getenv("AZURE_AGENT_ID", "asst_0uvId9Fz7NLJfxIwIzD0uN9b")
AZURE_AGENT_TIMEOUT = int(os.getenv("AZURE_AGENT_TIMEOUT", "60"))
AGENT_THREAD_TTL = int(os.getenv("AGENT_THREAD_TTL", "86400"))  # 24 h

# Service-principal creds (picked up automatically by DefaultAzureCredential)
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

# ─── SDK client (lazy singleton) ──────────────────────────────────────────────
_agents_client = None  # azure.ai.agents.AgentsClient


def get_agents_client():
    """
    Lazily initialise and return an AgentsClient.

    Uses the standalone azure-ai-agents package (v1.x).
    The client authenticates via DefaultAzureCredential which picks up
    AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET from the environment.
    """
    global _agents_client

    if _agents_client is not None:
        return _agents_client

    if not AZURE_AI_PROJECT_ENDPOINT:
        raise RuntimeError(
            "AZURE_AI_PROJECT_ENDPOINT is not set in your environment / .env file.\n"
            "It should look like:\n"
            "  https://<ai-services-account>.services.ai.azure.com/api/projects/<project-name>"
        )

    try:
        from azure.ai.agents import AgentsClient
        from azure.identity import DefaultAzureCredential

        _agents_client = AgentsClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(),
        )

        logger.info("✅ Azure AI Agents client initialised")
        print("✅ Azure AI Foundry AgentsClient ready")
        return _agents_client

    except ImportError as exc:
        raise RuntimeError(
            "azure-ai-agents package not installed.\n"
            "Run: pip install azure-ai-agents azure-identity"
        ) from exc
    except Exception as exc:
        logger.error(f"❌ Failed to init AgentsClient: {exc}")
        raise


# ─── Thread cache (in-memory, per process) ────────────────────────────────────
_thread_cache: Dict[str, Dict[str, Any]] = {}


def get_or_create_thread(user_id: str) -> str:
    client = get_agents_client()
    now = time.time()
    cached = _thread_cache.get(user_id)

    if cached and (now - cached["created_at"]) < AGENT_THREAD_TTL:
        logger.debug(f"Reusing thread {cached['thread_id']} for user {user_id}")
        return cached["thread_id"]

    thread = client.threads.create()
    thread_id = thread.id
    _thread_cache[user_id] = {"thread_id": thread_id, "created_at": now}
    logger.info(f"Created new agent thread {thread_id} for user {user_id}")
    return thread_id


def delete_thread(user_id: str) -> bool:
    cached = _thread_cache.pop(user_id, None)
    if not cached:
        return False
    try:
        client = get_agents_client()
        client.threads.delete(cached["thread_id"])
        logger.info(f"Deleted thread {cached['thread_id']} for user {user_id}")
        return True
    except Exception as exc:
        logger.warning(f"Could not delete thread on Azure: {exc}")
        return False


def send_message_to_agent(
    user_id: str,
    message: str,
    thread_id: Optional[str] = None,
    context: Optional[Dict] = None,
) -> Dict[str, Any]:
    client = get_agents_client()

    try:
        if not thread_id:
            thread_id = get_or_create_thread(user_id)

        full_message = message
        if context:
            full_message = f"{message}\n\n[Context: {json.dumps(context, default=str)}]"

        client.messages.create(
            thread_id=thread_id,
            role="user",
            content=full_message,
        )

        run = client.runs.create_and_process(
            thread_id=thread_id,
            agent_id=AZURE_AGENT_ID,
        )

        if run.status == "failed":
            err = getattr(run, "last_error", None)
            err_msg = str(err) if err else "Run failed with unknown error"
            logger.error(f"Agent run failed: {err_msg}")
            return {
                "success": False,
                "error": err_msg,
                "thread_id": thread_id,
                "run_id": run.id,
            }

        messages_page = client.messages.list(thread_id=thread_id)

        response_text = ""
        for msg in messages_page:
            if msg.role == "assistant":
                for block in msg.content:
                    if hasattr(block, "text"):
                        response_text = block.text.value
                        break
                if response_text:
                    break

        tokens = {}
        if hasattr(run, "usage") and run.usage:
            tokens = {
                "prompt": getattr(run.usage, "prompt_tokens", 0),
                "completion": getattr(run.usage, "completion_tokens", 0),
                "total": getattr(run.usage, "total_tokens", 0),
            }

        return {
            "success": True,
            "response": response_text,
            "thread_id": thread_id,
            "run_id": run.id,
            "run_status": run.status,
            "tool_calls": [],
            "tokens": tokens,
        }

    except Exception as exc:
        logger.error(f"Error communicating with Azure agent: {exc}", exc_info=True)
        return {"success": False, "error": str(exc), "thread_id": thread_id or ""}


def get_thread_messages(thread_id: str) -> Dict[str, Any]:
    try:
        client = get_agents_client()
        raw = client.messages.list(thread_id=thread_id)

        messages = []
        for msg in raw:
            content_text = ""
            for block in msg.content:
                if hasattr(block, "text"):
                    content_text = block.text.value
                    break
            messages.append(
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": content_text,
                    "created_at": msg.created_at,
                }
            )

        return {"success": True, "messages": messages}

    except Exception as exc:
        logger.error(f"Error fetching thread messages: {exc}")
        return {"success": False, "error": str(exc)}


def check_agent_health() -> Dict[str, Any]:
    try:
        client = get_agents_client()
        agent = client.get_agent(AZURE_AGENT_ID)
        return {
            "healthy": True,
            "agent_id": agent.id,
            "agent_name": getattr(agent, "name", "unknown"),
            "model": getattr(agent, "model", "unknown"),
        }
    except Exception as exc:
        return {"healthy": False, "error": str(exc)}
