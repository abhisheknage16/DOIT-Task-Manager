"""
Local Private AI Agent Controller
Stack: Ollama (local LLM) + LlamaIndex + ChromaDB

Mirrors azure_agent_controller.py — same conversation model,
same context enrichment, same response shape.
"""

from fastapi import HTTPException
from datetime import datetime
from models.ai_conversation import AIConversation, AIMessage
from utils.local_agent_utils import (
    send_message_to_local_agent,
    clear_chat_history,
    get_chat_history,
    check_local_agent_health,
    OLLAMA_MODEL,
    CHROMA_DB_PATH,
)
from utils.ai_data_analyzer import analyze_user_data_for_ai


# ─── Conversation CRUD (reuse DOIT AIConversation model) ──────────────────────


def create_local_conversation(user_id: str, title: str = "Local AI Chat"):
    try:
        conversation_id = AIConversation.create(user_id, title)
        conversation = AIConversation.get_by_id(conversation_id)
        if conversation:
            conversation["_id"] = str(conversation["_id"])
        return {"success": True, "conversation": conversation}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def get_local_conversations(user_id: str):
    try:
        conversations = AIConversation.get_user_conversations(user_id)
        for c in conversations:
            c["_id"] = str(c["_id"])
        return {"success": True, "conversations": conversations}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def get_local_conversation_messages(conversation_id: str):
    try:
        messages = AIMessage.get_conversation_messages(conversation_id)
        for m in messages:
            m["_id"] = str(m["_id"])
        return {"success": True, "messages": messages}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def delete_local_conversation(conversation_id: str, user_id: str):
    try:
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Clear in-memory chat history so the next conversation starts clean
        clear_chat_history(user_id)
        AIConversation.delete(conversation_id)
        return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Core: send message ────────────────────────────────────────────────────────


def send_message_to_local(
    conversation_id: str,
    user_id: str,
    content: str,
    include_user_context: bool = True,
):
    """
    Route a user message through Ollama + LlamaIndex + ChromaDB (RAG)
    and persist both the user message and the local agent reply.
    """
    print(f"\n🦙 [Local Agent] Processing message for user {user_id}")
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

        # ── Build user context (identical shape to Foundry controller) ───────
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
                        for t in user_data.get("recentTasks", [])[:8]
                    ],
                }
                print(
                    f"   📊 Context: {tasks.get('total')} tasks, "
                    f"{tasks.get('overdue')} overdue"
                )

        # ── Call local agent (Ollama + RAG) ──────────────────────────────────
        result = send_message_to_local_agent(
            user_id=user_id,
            message=content,
            context=context,
        )

        if not result["success"]:
            err = result.get("error", "Local agent call failed")
            print(f"   ❌ Local agent error: {err}")
            ai_content = (
                f"❌ Local AI error: {err}\n\n"
                "Make sure Ollama is running (`ollama serve`) and the model is pulled "
                f"(`ollama pull {OLLAMA_MODEL}`)."
            )
        else:
            ai_content = result["response"]
            rag_label = " [+RAG]" if result.get("rag_used") else ""
            print(f"   ✅ Local agent replied ({len(ai_content)} chars){rag_label}")

        # ── Save agent reply ──────────────────────────────────────────────────
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
            "model": result.get("model", OLLAMA_MODEL),
            "rag_used": result.get("rag_used", False),
            "tokens": tokens,
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ [Local Agent] Unexpected error: {exc}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ─── History management ────────────────────────────────────────────────────────


def reset_local_history(user_id: str):
    """Wipe the in-memory chat history for this user."""
    clear_chat_history(user_id)
    return {
        "success": True,
        "message": "Local chat history cleared. Next message starts fresh.",
    }


def get_local_history(user_id: str):
    """Return the current in-memory chat history (for debugging)."""
    history = get_chat_history(user_id)
    return {"success": True, "history": history, "turns": len(history) // 2}


# ─── Health ────────────────────────────────────────────────────────────────────


def local_agent_health_check():
    health = check_local_agent_health()
    return {
        "service": "Local AI (Ollama + LlamaIndex + ChromaDB)",
        "healthy": health.get("healthy", False),
        "ollama_url": health.get("ollama_url"),
        "model": health.get("model"),
        "model_available": health.get("model_available", False),
        "available_models": health.get("available_models", []),
        "chroma_path": CHROMA_DB_PATH,
        "error": health.get("error"),
    }
