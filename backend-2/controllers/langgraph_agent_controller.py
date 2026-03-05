# backend-2/controllers/langgraph_agent_controller.py
"""
LangGraph AI Agent Controller
Stack: Azure OpenAI + LangGraph + LangChain Tools

Provides advanced agentic automation with multi-step reasoning,
tool orchestration, and state management.
"""

from fastapi import HTTPException
from datetime import datetime
from models.ai_conversation import AIConversation, AIMessage
from utils.langgraph_agent_utils import (
    send_message_to_langgraph_agent,
    clear_chat_history,
    get_chat_history,
    check_langgraph_agent_health,
)
from utils.langgraph_agent_tools import (
    get_all_langgraph_tools,
    set_tool_context,
)
from utils.ai_data_analyzer import analyze_user_data_for_ai
from utils.cache_utils import (
    get_cached_user_context,
    cache_user_context,
    clear_user_context_cache,
)
from models.user import User
import json


# ─── Conversation CRUD ─────────────────────────────────────────────────────────


def create_langgraph_conversation(user_id: str, title: str = "LangGraph AI Chat"):
    try:
        conversation_id = AIConversation.create(user_id, title)
        conversation = AIConversation.get_by_id(conversation_id)
        if conversation:
            conversation["_id"] = str(conversation["_id"])
        return {"success": True, "conversation": conversation}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def get_langgraph_conversations(user_id: str):
    try:
        conversations = AIConversation.get_user_conversations(user_id)
        for c in conversations:
            c["_id"] = str(c["_id"])
        return {"success": True, "conversations": conversations}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def get_langgraph_conversation_messages(conversation_id: str):
    try:
        messages = AIMessage.get_conversation_messages(conversation_id)
        for m in messages:
            m["_id"] = str(m["_id"])
        return {"success": True, "messages": messages}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def delete_langgraph_conversation(conversation_id: str, user_id: str):
    try:
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        clear_chat_history(conversation_id)
        clear_user_context_cache(user_id)
        AIConversation.delete(conversation_id)
        return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Core: send message ────────────────────────────────────────────────────────


def send_message_to_langgraph(
    conversation_id: str,
    user_id: str,
    content: str,
    include_user_context: bool = True,
):
    """
    Route a user message through LangGraph agent with tools.
    """
    print(f"\n🤖 [LangGraph Agent] Processing message for user {user_id}")
    print(f"   Conversation: {conversation_id}")
    print(f"   Content: {content[:80]}...")

    try:
        # ── Verify conversation ──────────────────────────────────────────────
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # ── Save user message ────────────────────────────────────────────────
        AIMessage.create(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )

        # ── Get user info for tool context ───────────────────────────────────
        user = User.find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_email = user.get("email")
        user_role = user.get("role", "member")

        # Set tool context
        set_tool_context(user_id, user_email, user_role)

        # ── Build user context ───────────────────────────────────────────────
        context = None
        if include_user_context:
            context = get_cached_user_context(user_id)

            if context is None:
                user_data = analyze_user_data_for_ai(user_id)
                if user_data:
                    stats = user_data.get("stats", {})
                    tasks = stats.get("tasks", {})
                    projects = stats.get("projects", {})
                    sprints = stats.get("sprints", {})
                    velocity = user_data.get("velocity", {})
                    blockers = user_data.get("blockers", {})

                    context = {
                        "user_name": user_data["user"]["name"],
                        "user_role": user_data["user"]["role"],
                        "tasks_total": tasks.get("total", 0),
                        "tasks_overdue": tasks.get("overdue", 0),
                        "tasks_due_soon": tasks.get("dueSoon", 0),
                        "tasks_done_week": tasks.get("completedWeek", 0),
                        "status_breakdown": tasks.get("statusBreakdown", {}),
                        "priority_breakdown": tasks.get("priorityBreakdown", {}),
                        "projects_total": projects.get("total", 0),
                        "sprints_active": sprints.get("active", 0),
                        "velocity_30d": velocity.get("completed_last_30_days", 0),
                        "blocked_tasks": blockers.get("blocked_tasks", 0),
                        "recent_tasks": [
                            {
                                "ticket": t.get("ticket_id"),
                                "title": t.get("title"),
                                "status": t.get("status"),
                                "due": t.get("dueDate"),
                            }
                            for t in user_data.get("recentTasks", [])[:8]
                        ],
                    }
                    cache_user_context(user_id, context, ttl=60)
                    print(f"   📊 Context: {tasks.get('total')} tasks [from DB]")
            else:
                print(f"   ⚡ Context cached: {context.get('tasks_total')} tasks")

        # ── Get tools ────────────────────────────────────────────────────────
        tools = get_all_langgraph_tools()

        # ── Call LangGraph agent ─────────────────────────────────────────────
        result = send_message_to_langgraph_agent(
            user_id=user_id,
            conversation_id=conversation_id,
            message=content,
            tools=tools,
            context=context,
        )

        if not result["success"]:
            err = result.get("error", "LangGraph agent call failed")
            print(f"   ❌ LangGraph agent error: {err}")
            ai_content = f"❌ LangGraph AI error: {err}"
        else:
            ai_content = result["response"]
            tool_info = (
                f" [Tools: {len(result.get('tool_calls', []))}]"
                if result.get("tool_calls")
                else ""
            )
            print(f"   ✅ LangGraph agent replied ({len(ai_content)} chars){tool_info}")

        # ── Save agent reply ─────────────────────────────────────────────────
        ai_message_id = AIMessage.create(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_content,
        )

        tokens = result.get("tokens", {})
        if tokens.get("total"):
            AIMessage.update_tokens(ai_message_id, tokens["total"])

        # Auto-title from first message
        if conversation.get("message_count", 0) <= 2:
            title = content[:50] + ("..." if len(content) > 50 else "")
            AIConversation.update_title(conversation_id, title)

        return {
            "success": True,
            "message": {
                "_id": str(ai_message_id),
                "role": "assistant",
                "content": ai_content,
                "created_at": datetime.utcnow().isoformat(),
                "tokens_used": tokens.get("total", 0),
            },
            "model": result.get("model"),
            "tool_calls": result.get("tool_calls", []),
            "tokens": tokens,
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ [LangGraph Agent] Unexpected error: {exc}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ─── History management ────────────────────────────────────────────────────────


def reset_langgraph_history(conversation_id: str):
    """Wipe the in-memory chat history for this conversation."""
    clear_chat_history(conversation_id)
    return {
        "success": True,
        "message": "LangGraph chat history cleared.",
    }


def get_langgraph_history(conversation_id: str):
    """Return the current in-memory chat history."""
    history = get_chat_history(conversation_id)
    return {"success": True, "history": history, "turns": len(history) // 2}


# ─── Health ────────────────────────────────────────────────────────────────────


def langgraph_agent_health_check():
    health = check_langgraph_agent_health()
    return {
        "service": "LangGraph AI (Azure OpenAI + LangChain Tools)",
        "healthy": health.get("healthy", False),
        "endpoint": health.get("endpoint"),
        "deployment": health.get("deployment"),
        "api_version": health.get("api_version"),
        "error": health.get("error"),
    }
