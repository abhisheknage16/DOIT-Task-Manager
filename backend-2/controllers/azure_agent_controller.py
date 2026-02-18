"""
Azure AI Foundry Agent Controller
Integrates the MS Foundry AI Agent into DOIT's existing AI Assistant flow.

Key differences vs. ai_assistant_controller.py (GPT-5.2 direct calls):
- Uses the pre-configured Foundry Agent (asst_0uvId9Fz7NLJfxIwIzD0uN9b)
- The Agent has its own system instructions, tools and knowledge configured in Foundry
- We pass user context as additional message content
- Threads are managed per-user for multi-turn conversations
"""

from fastapi import HTTPException
from datetime import datetime
from models.ai_conversation import AIConversation, AIMessage
from models.user import User
from utils.azure_agent_utils import (
    send_message_to_agent,
    get_or_create_thread,
    delete_thread,
    get_thread_messages,
    check_agent_health,
    _thread_cache,
)
from utils.ai_data_analyzer import analyze_user_data_for_ai
import json


# ─── Conversation helpers (reuse DOIT's AIConversation model) ─────────────────


def create_agent_conversation(user_id: str, title: str = "Agent Chat"):
    """Create a new conversation record (same model as AI Assistant)."""
    try:
        conversation_id = AIConversation.create(user_id, title)
        conversation = AIConversation.get_by_id(conversation_id)
        if conversation:
            conversation["_id"] = str(conversation["_id"])
        return {"success": True, "conversation": conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_agent_conversations(user_id: str):
    """List all agent conversations for a user."""
    try:
        conversations = AIConversation.get_user_conversations(user_id)
        for c in conversations:
            c["_id"] = str(c["_id"])
        return {"success": True, "conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_agent_conversation_messages(conversation_id: str):
    """Get all stored messages for a conversation."""
    try:
        messages = AIMessage.get_conversation_messages(conversation_id)
        for m in messages:
            m["_id"] = str(m["_id"])
        return {"success": True, "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def delete_agent_conversation(conversation_id: str, user_id: str):
    """Delete conversation record and reset the Foundry thread."""
    try:
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Reset Foundry thread so the agent starts fresh
        delete_thread(user_id)

        AIConversation.delete(conversation_id)
        return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Main: send message to Foundry agent ──────────────────────────────────────


def send_message_to_foundry_agent(
    conversation_id: str,
    user_id: str,
    content: str,
    include_user_context: bool = True,
):
    """
    Send a user message to the Azure AI Foundry Agent and persist
    both the user message and the agent reply in DOIT's conversation store.

    Args:
        conversation_id:     DOIT conversation record ID
        user_id:             Authenticated user's ID
        content:             User's message text
        include_user_context: Whether to enrich the message with live MongoDB data
    """
    print(f"\n🤖 [Foundry Agent] Processing message for user {user_id}")
    print(f"   Conversation: {conversation_id}")
    print(f"   Content: {content[:80]}...")

    try:
        # ── Verify conversation ──────────────────────────────────────────
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # ── Save user message ────────────────────────────────────────────
        AIMessage.create(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )

        # ── Optionally build user context ────────────────────────────────
        context = None
        if include_user_context:
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
                        for t in user_data.get("recentTasks", [])[:5]
                    ],
                }
                print(
                    f"   📊 Enriched with context: {tasks.get('total')} tasks, "
                    f"{tasks.get('overdue')} overdue"
                )

        # ── Get / create Foundry thread for this user ────────────────────
        thread_id = get_or_create_thread(user_id)
        print(f"   🧵 Thread: {thread_id}")

        # ── Call the Foundry agent ───────────────────────────────────────
        result = send_message_to_agent(
            user_id=user_id,
            message=content,
            thread_id=thread_id,
            context=context,
        )

        if not result["success"]:
            err = result.get("error", "Agent call failed")
            print(f"   ❌ Agent error: {err}")
            ai_content = (
                f"❌ I encountered an issue processing your request: {err}\n\n"
                "Please try again or contact support if the problem persists."
            )
        else:
            ai_content = result["response"]
            print(f"   ✅ Agent replied ({len(ai_content)} chars)")

        # ── Save agent reply ─────────────────────────────────────────────
        ai_message_id = AIMessage.create(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_content,
        )

        # Update token usage if available
        tokens = result.get("tokens", {})
        if tokens.get("total"):
            AIMessage.update_tokens(ai_message_id, tokens["total"])

        # Auto-title the conversation from first message
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
            "thread_id": result.get("thread_id"),
            "run_id": result.get("run_id"),
            "tokens": tokens,
            "agent_id": "asst_0uvId9Fz7NLJfxIwIzD0uN9b",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [Foundry Agent] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─── Thread management endpoints ──────────────────────────────────────────────


def reset_agent_thread(user_id: str):
    """Clear the cached Foundry thread so the next message starts fresh."""
    deleted = delete_thread(user_id)
    return {
        "success": True,
        "message": "Thread reset. Next message will start a new conversation.",
        "had_thread": deleted,
    }


def get_foundry_thread_messages(user_id: str):
    """Retrieve raw messages directly from the Foundry thread."""
    cached = _thread_cache.get(user_id)
    if not cached:
        return {"success": True, "messages": [], "thread_id": None}

    result = get_thread_messages(cached["thread_id"])
    result["thread_id"] = cached["thread_id"]
    return result


def agent_health_check():
    """Check connectivity to the Azure AI Foundry agent."""
    health = check_agent_health()
    return {
        "service": "Azure AI Foundry Agent",
        "agent_id": "asst_0uvId9Fz7NLJfxIwIzD0uN9b",
        "healthy": health.get("healthy", False),
        "agent_name": health.get("agent_name", "unknown"),
        "model": health.get("model", "unknown"),
        "error": health.get("error"),
    }
