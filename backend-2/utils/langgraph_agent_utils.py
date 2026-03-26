"""
LangGraph AI Agent Utilities
Stack: Azure OpenAI/Groq + LangGraph + LangChain
Provides advanced agentic automation with:
- Multi-step reasoning
- Tool orchestration
- State management
- Memory across conversations
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from openai import NotFoundError
from langchain_openai import AzureChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
LANGGRAPH_LLM_PROVIDER = os.getenv("LANGGRAPH_LLM_PROVIDER", "auto").strip().lower()

# Azure OpenAI configuration (preferred by default)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
AZURE_OPENAI_API_VERSION_FALLBACKS = [
    v.strip()
    for v in os.getenv(
        "AZURE_OPENAI_API_VERSION_FALLBACKS", "2024-12-01-preview,2024-10-21"
    ).split(",")
    if v.strip()
]

# Groq configuration (optional fallback)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
# Optional comma-separated fallback list.
# Example: GROQ_FALLBACK_MODELS=qwen/qwen3-32b,llama-3.1-8b-instant
GROQ_FALLBACK_MODELS = os.getenv(
    "GROQ_FALLBACK_MODELS", "qwen/qwen3-32b,llama-3.1-8b-instant"
)

LANGGRAPH_AGENT_TIMEOUT = int(os.getenv("LANGGRAPH_AGENT_TIMEOUT", "120"))

# System prompt for the LangGraph agent
LANGGRAPH_AGENT_SYSTEM_PROMPT = """You are a powerful AI assistant for the DOIT task management system with comprehensive automation capabilities.

You have access to advanced tools for:

**Task Management:**
- Create single or multiple tasks with full details (title, description, priority, assignee, due date, labels)
- List, filter, update, and delete tasks
- Bulk update multiple tasks at once
- Assign and reassign tasks to team members

**Sprint Management:**
- Create sprints with flexible date options
- Add individual or bulk tasks to sprints
- List and track sprint progress
- Auto-calculate sprint dates from duration

**Project Management:**
- Create new projects
- Add/remove team members
- View project details and member lists
- Track project progress

**Analytics & Reporting:**
- Generate project analytics (status breakdown, completion rates)
- View user workload summaries
- Track overdue tasks across projects
- Get insights on team productivity

**Profile Management:**
- Update user profile information
- Manage personal details

**Key Capabilities:**
1. **Multi-step workflows**: Chain multiple actions together
2. **Intelligent filtering**: Find tasks/sprints by various criteria
3. **Bulk operations**: Update many items at once
4. **Smart suggestions**: Recommend actions based on context
5. **Proactive alerts**: Identify overdue tasks and blockers

**When responding:**
- Be action-oriented and execute tasks when requested
- Provide clear summaries of what was done
- Suggest next steps or related actions
- Use ticket IDs for precise task references
- Be concise but informative

Remember: You can see the user's current tasks, projects, and team context. Use this information to provide personalized, context-aware assistance."""

# ─── Lazy singletons ──────────────────────────────────────────────────────────
_llm = None  # Active LLM client
_llm_provider = None  # Active provider name
_llm_model = None  # Active model/deployment name
_llm_api_version = None  # Active Azure API version (if provider=azure)
_checkpointer = None  # LangGraph memory checkpointer
_agents = {}  # Cache of agents per user

# ─── Client initialization ──────────────────────────────────────────────────


def _get_provider_order() -> List[str]:
    provider = LANGGRAPH_LLM_PROVIDER
    if provider in {"azure", "groq"}:
        return [provider]

    # auto mode: prefer Azure first to match the rest of the backend stack,
    # then fall back to Groq when Azure credentials are absent or invalid.
    return ["azure", "groq"]


def _normalize_azure_chat_endpoint(endpoint_raw: Optional[str]):
    """
    Accept either:
    1) Azure resource endpoint: https://<resource>.openai.azure.com/
    2) Full chat-completions URL:
       https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=...

    Returns: (base_endpoint, deployment_from_url, api_version_from_url)
    """
    if not endpoint_raw:
        return None, None, None

    parsed = urlparse(endpoint_raw)
    if not parsed.scheme or not parsed.netloc:
        return endpoint_raw, None, None

    base_endpoint = f"{parsed.scheme}://{parsed.netloc}"
    deployment_from_url = None
    api_version_from_url = None

    path = parsed.path or ""
    marker = "/openai/deployments/"
    if marker in path:
        deployment_part = path.split(marker, 1)[1]
        deployment_from_url = (
            deployment_part.split("/", 1)[0] if deployment_part else None
        )

    query = parse_qs(parsed.query)
    api_versions = query.get("api-version", [])
    if api_versions:
        api_version_from_url = api_versions[0]

    return base_endpoint, deployment_from_url, api_version_from_url


def _azure_api_version_candidates(preferred: Optional[str] = None) -> List[str]:
    _, _, api_version_from_url = _normalize_azure_chat_endpoint(AZURE_OPENAI_ENDPOINT)
    candidates = [
        preferred or AZURE_OPENAI_API_VERSION,
        api_version_from_url,
        *AZURE_OPENAI_API_VERSION_FALLBACKS,
        "2024-12-01-preview",
        "2024-10-21",
    ]
    unique = []
    for version in candidates:
        if version and version not in unique:
            unique.append(version)
    return unique


def _build_azure_llm(api_version: Optional[str] = None) -> AzureChatOpenAI:
    endpoint_base, deployment_from_url, api_version_from_url = _normalize_azure_chat_endpoint(
        AZURE_OPENAI_ENDPOINT
    )
    deployment = AZURE_OPENAI_DEPLOYMENT or deployment_from_url
    effective_api_version = api_version or AZURE_OPENAI_API_VERSION or api_version_from_url

    if not endpoint_base or not AZURE_OPENAI_KEY or not deployment:
        raise RuntimeError(
            "Missing Azure OpenAI configuration (AZURE_OPENAI_ENDPOINT, "
            "AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT)"
        )

    return AzureChatOpenAI(
        azure_endpoint=endpoint_base,
        api_key=AZURE_OPENAI_KEY,
        azure_deployment=deployment,
        openai_api_version=effective_api_version,
        request_timeout=LANGGRAPH_AGENT_TIMEOUT,
        temperature=0,
    )


def _build_azure_runtime_info(api_version: Optional[str] = None):
    endpoint_base, deployment_from_url, api_version_from_url = _normalize_azure_chat_endpoint(
        AZURE_OPENAI_ENDPOINT
    )
    return {
        "endpoint": endpoint_base,
        "deployment": AZURE_OPENAI_DEPLOYMENT or deployment_from_url,
        "api_version": api_version or AZURE_OPENAI_API_VERSION or api_version_from_url,
    }


def _try_rotate_azure_api_version() -> bool:
    """Rotate to next Azure API version candidate and rebuild LLM; returns True if switched."""
    global _llm, _llm_api_version, _llm_model, _llm_provider, _agents

    versions = _azure_api_version_candidates(preferred=_llm_api_version)
    if not versions:
        return False

    start_idx = 0
    if _llm_api_version in versions:
        start_idx = versions.index(_llm_api_version) + 1

    for idx in range(start_idx, len(versions)):
        candidate = versions[idx]
        try:
            _llm = _build_azure_llm(api_version=candidate)
            _llm_provider = "azure"
            info = _build_azure_runtime_info(api_version=candidate)
            _llm_model = info.get("deployment")
            _llm_api_version = candidate
            # Existing cached agents hold old model objects; clear to force rebind.
            _agents.clear()
            logger.warning(
                "LangGraph Azure retry: switched api-version to %s for deployment=%s endpoint=%s",
                candidate,
                _llm_model,
                info.get("endpoint"),
            )
            return True
        except Exception as exc:
            logger.warning("LangGraph Azure api-version %s init failed: %s", candidate, exc)

    return False


def _build_groq_llm() -> ChatGroq:
    if not GROQ_API_KEY:
        raise RuntimeError("Missing GROQ_API_KEY in environment")

    candidates: List[str] = [GROQ_MODEL]
    if GROQ_FALLBACK_MODELS.strip():
        candidates.extend([m.strip() for m in GROQ_FALLBACK_MODELS.split(",") if m.strip()])

    for model_name in candidates:
        if model_name:
            return ChatGroq(
                api_key=GROQ_API_KEY,
                model=model_name,
                timeout=LANGGRAPH_AGENT_TIMEOUT,
            )

    raise RuntimeError("No Groq model candidates configured")


def get_llm():
    """Return (and lazily init) the chat LLM (Azure preferred, Groq fallback)."""
    global _llm, _llm_provider, _llm_model, _llm_api_version
    if _llm is not None:
        return _llm

    try:
        errors: List[str] = []
        for provider in _get_provider_order():
            try:
                if provider == "azure":
                    preferred_version = _azure_api_version_candidates()[0]
                    _llm = _build_azure_llm(api_version=preferred_version)
                    _llm_provider = "azure"
                    info = _build_azure_runtime_info(api_version=preferred_version)
                    _llm_model = info.get("deployment")
                    _llm_api_version = info.get("api_version")
                    logger.info(
                        "✅ LangGraph LLM ready: provider=azure deployment=%s api_version=%s endpoint=%s",
                        _llm_model,
                        _llm_api_version,
                        info.get("endpoint"),
                    )
                else:
                    _llm = _build_groq_llm()
                    _llm_provider = "groq"
                    _llm_model = GROQ_MODEL
                    _llm_api_version = None
                    logger.info(
                        f"✅ LangGraph LLM ready: provider=groq model={_llm_model}"
                    )
                return _llm
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                logger.warning(f"LangGraph provider init failed ({provider}): {exc}")

        raise RuntimeError("Unable to initialize any LangGraph provider. " + " | ".join(errors))
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize LangGraph LLM: {exc}") from exc


def get_checkpointer():
    """Return (and lazily init) the LangGraph memory checkpointer."""
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    _checkpointer = MemorySaver()
    logger.info("✅ LangGraph MemorySaver ready")
    return _checkpointer


# ─── In-memory chat history (per conversation) ──────────────────────────────
_chat_histories: Dict[str, List[Dict[str, str]]] = {}
MAX_HISTORY = 20  # keep last N turns


def get_chat_history(conversation_id: str) -> List[Dict[str, str]]:
    """Get chat history for a conversation."""
    return _chat_histories.get(conversation_id, [])


def append_to_history(conversation_id: str, role: str, content: str):
    """Append a message to conversation history."""
    history = _chat_histories.setdefault(conversation_id, [])
    history.append({"role": role, "content": content})

    # Trim to MAX_HISTORY turns
    if len(history) > MAX_HISTORY * 2:
        _chat_histories[conversation_id] = history[-(MAX_HISTORY * 2) :]


def clear_chat_history(conversation_id: str):
    """Clear chat history for a conversation."""
    _chat_histories.pop(conversation_id, None)


# ─── Core: send message to LangGraph agent ─────────────────────────────────


def send_message_to_langgraph_agent(
    user_id: str,
    conversation_id: str,
    message: str,
    tools: List[Any],
    context: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Route a user message through LangGraph agent with tools.

    Args:
        user_id: User identifier
        conversation_id: Conversation identifier for memory
        message: User's message
        tools: List of LangChain tools available to the agent
        context: Optional user context (tasks, projects, etc.)

    Returns:
        {
            "success": bool,
            "response": str,
            "model": str,
            "tool_calls": list,
            "tokens": dict,
        }
    """
    try:
        llm = get_llm()
        checkpointer = get_checkpointer()

        # ── Build context-enriched system prompt ───────────────────────────
        system_prompt = LANGGRAPH_AGENT_SYSTEM_PROMPT

        if context:
            context_summary = f"""

Current User Context:
- User: {context.get("user_name")} ({context.get("user_role")})
- Tasks: {context.get("tasks_total")} total, {context.get("tasks_overdue")} overdue, {context.get("tasks_due_soon")} due soon
- Projects: {context.get("projects_total")}
- Active Sprints: {context.get("sprints_active")}
- Completed this week: {context.get("tasks_done_week")}

Recent Tasks:
"""
            for task in context.get("recent_tasks", [])[:5]:
                context_summary += f"- [{task.get('ticket')}] {task.get('title')} ({task.get('status')})\n"

            system_prompt += context_summary

        # ── Create or retrieve agent for this conversation ─────────────────
        agent_key = f"{user_id}_{conversation_id}"

        if agent_key not in _agents:
            agent = create_react_agent(
                model=llm,
                tools=tools,
                checkpointer=checkpointer,
                prompt=system_prompt,
            )
            _agents[agent_key] = agent
            logger.info(f"✅ Created new LangGraph agent for {agent_key}")
        else:
            agent = _agents[agent_key]

        # ── Invoke agent with message ──────────────────────────────────────
        config = {"configurable": {"thread_id": conversation_id}}

        invoke_payload = {"messages": [HumanMessage(content=message)]}
        try:
            result = agent.invoke(invoke_payload, config=config)
        except NotFoundError as exc:
            # Azure OpenAI often returns 404 when api-version or deployment mapping is wrong.
            if _llm_provider == "azure" and _try_rotate_azure_api_version():
                logger.warning("LangGraph Azure 404 recovered via api-version fallback retry")
                llm = get_llm()
                agent = create_react_agent(
                    model=llm,
                    tools=tools,
                    checkpointer=checkpointer,
                    prompt=system_prompt,
                )
                _agents[agent_key] = agent
                result = agent.invoke(invoke_payload, config=config)
            else:
                raise exc

        # Extract response
        messages = result.get("messages", [])
        if not messages:
            raise ValueError("No response from agent")

        last_message = messages[-1]
        response_text = (
            last_message.content
            if hasattr(last_message, "content")
            else str(last_message)
        )

        # Extract tool calls information
        tool_calls = []
        for msg in messages:
            if (
                hasattr(msg, "additional_kwargs")
                and "tool_calls" in msg.additional_kwargs
            ):
                for tc in msg.additional_kwargs["tool_calls"]:
                    tool_calls.append(
                        {
                            "name": tc.get("function", {}).get("name"),
                            "args": tc.get("function", {}).get("arguments"),
                        }
                    )

        # ── Update history ─────────────────────────────────────────────────
        append_to_history(conversation_id, "user", message)
        append_to_history(conversation_id, "assistant", response_text)

        # ── Token estimation (if available) ────────────────────────────────
        tokens = {}
        if hasattr(last_message, "usage_metadata"):
            usage = last_message.usage_metadata
            tokens = {
                "prompt": usage.get("input_tokens", 0),
                "completion": usage.get("output_tokens", 0),
                "total": usage.get("total_tokens", 0),
            }

        return {
            "success": True,
            "response": response_text,
            "model": _llm_model,
            "provider": _llm_provider,
            "tool_calls": tool_calls,
            "tokens": tokens,
        }

    except Exception as exc:
        logger.error(f"LangGraph agent error: {exc}", exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "model": _llm_model or AZURE_OPENAI_DEPLOYMENT or GROQ_MODEL,
            "provider": _llm_provider,
        }


# ─── Health check ───────────────────────────────────────────────────────────


def check_langgraph_agent_health() -> Dict[str, Any]:
    """Return quick, non-blocking config health for LangGraph provider."""
    try:
        # Ensure provider is initialized, but do not make network calls here.
        get_llm()

        if _llm_provider == "azure":
            info = _build_azure_runtime_info(api_version=_llm_api_version)
            endpoint = info.get("endpoint")
            deployment = _llm_model or info.get("deployment")
            api_version = _llm_api_version or info.get("api_version")
        else:
            endpoint = None
            deployment = _llm_model or GROQ_MODEL
            api_version = None

        return {
            "healthy": True,
            "provider": _llm_provider,
            "model": _llm_model,
            "endpoint": endpoint,
            "deployment": deployment,
            "api_version": api_version,
            "connectivity_checked": False,
            "error": None,
        }

    except Exception as exc:
        return {
            "healthy": False,
            "provider": _llm_provider,
            "model": _llm_model or AZURE_OPENAI_DEPLOYMENT or GROQ_MODEL,
            "endpoint": _build_azure_runtime_info(api_version=_llm_api_version).get("endpoint") if LANGGRAPH_LLM_PROVIDER != "groq" else None,
            "deployment": AZURE_OPENAI_DEPLOYMENT if LANGGRAPH_LLM_PROVIDER != "groq" else GROQ_MODEL,
            "api_version": (_llm_api_version or _build_azure_runtime_info().get("api_version")) if LANGGRAPH_LLM_PROVIDER != "groq" else None,
            "connectivity_checked": False,
            "error": f"LangGraph provider config invalid: {exc}",
        }
