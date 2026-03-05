"""
LangGraph AI Agent Utilities
Stack: Azure OpenAI + LangGraph + LangChain

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
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

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
_llm = None  # Azure OpenAI LLM
_checkpointer = None  # LangGraph memory checkpointer
_agents = {}  # Cache of agents per user


# ─── Client initialization ────────────────────────────────────────────────────


def get_llm():
    """Return (and lazily init) the Azure OpenAI LLM."""
    global _llm
    if _llm is not None:
        return _llm

    try:
        # FIXED: Remove temperature parameter or set to 1 (default)
        # Some Azure OpenAI models don't support custom temperature values
        _llm = AzureChatOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            azure_deployment=AZURE_OPENAI_DEPLOYMENT,
            api_version=AZURE_OPENAI_API_VERSION,
            # temperature=1,  # Use default temperature (comment out or set to 1)
            timeout=LANGGRAPH_AGENT_TIMEOUT,
        )
        logger.info(f"✅ Azure OpenAI LLM ready: {AZURE_OPENAI_DEPLOYMENT}")
        return _llm
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize Azure OpenAI: {exc}") from exc


def get_checkpointer():
    """Return (and lazily init) the LangGraph memory checkpointer."""
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    _checkpointer = MemorySaver()
    logger.info("✅ LangGraph MemorySaver ready")
    return _checkpointer


# ─── In-memory chat history (per conversation) ────────────────────────────────
_chat_histories: Dict[str, List[Dict[str, str]]] = {}

MAX_HISTORY = 20  # keep last N turns


def get_chat_history(conversation_id: str) -> List[Dict[str, str]]:
    return _chat_histories.get(conversation_id, [])


def append_to_history(conversation_id: str, role: str, content: str):
    history = _chat_histories.setdefault(conversation_id, [])
    history.append({"role": role, "content": content})
    # Trim to MAX_HISTORY turns
    if len(history) > MAX_HISTORY * 2:
        _chat_histories[conversation_id] = history[-(MAX_HISTORY * 2) :]


def clear_chat_history(conversation_id: str):
    _chat_histories.pop(conversation_id, None)


# ─── Core: send message to LangGraph agent ───────────────────────────────────


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

        # ── Build context-enriched system prompt ─────────────────────────────
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

        # ── Create or retrieve agent for this conversation ───────────────────
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

        # ── Invoke agent with message ────────────────────────────────────────
        config = {"configurable": {"thread_id": conversation_id}}

        result = agent.invoke(
            {"messages": [HumanMessage(content=message)]}, config=config
        )

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

        # ── Update history ───────────────────────────────────────────────────
        append_to_history(conversation_id, "user", message)
        append_to_history(conversation_id, "assistant", response_text)

        # ── Token estimation (if available) ──────────────────────────────────
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
            "model": AZURE_OPENAI_DEPLOYMENT,
            "tool_calls": tool_calls,
            "tokens": tokens,
        }

    except Exception as exc:
        logger.error(f"LangGraph agent error: {exc}", exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "model": AZURE_OPENAI_DEPLOYMENT,
        }


# ─── Health check ─────────────────────────────────────────────────────────────


def check_langgraph_agent_health() -> Dict[str, Any]:
    """Verify Azure OpenAI is reachable and configured."""
    try:
        llm = get_llm()
        # Test with a simple message
        response = llm.invoke("Hello")

        return {
            "healthy": True,
            "endpoint": AZURE_OPENAI_ENDPOINT,
            "deployment": AZURE_OPENAI_DEPLOYMENT,
            "api_version": AZURE_OPENAI_API_VERSION,
            "error": None,
        }
    except Exception as exc:
        return {
            "healthy": False,
            "endpoint": AZURE_OPENAI_ENDPOINT,
            "deployment": AZURE_OPENAI_DEPLOYMENT,
            "error": f"Azure OpenAI not reachable: {exc}",
        }
