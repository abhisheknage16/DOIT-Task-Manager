"""
Local Private AI Agent Router
Stack: Ollama + LlamaIndex + ChromaDB — fully on-premise

Base path: /api/local-agent
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user
from controllers.local_agent_controller import (
    create_local_conversation,
    get_local_conversations,
    get_local_conversation_messages,
    delete_local_conversation,
    send_message_to_local,
    reset_local_history,
    get_local_history,
    local_agent_health_check,
)

router = APIRouter()


# ─── Pydantic models ───────────────────────────────────────────────────────────


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "Local AI Chat"


class SendMessageRequest(BaseModel):
    content: str
    include_user_context: Optional[bool] = True


# ─── Conversation CRUD ─────────────────────────────────────────────────────────


@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    current_user: str = Depends(get_current_user),
):
    """Create a new Local AI conversation."""
    return create_local_conversation(user_id=current_user, title=request.title)


@router.get("/conversations")
async def list_conversations(current_user: str = Depends(get_current_user)):
    """List all Local AI conversations for the current user."""
    return get_local_conversations(user_id=current_user)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    """Get all messages in a conversation."""
    return get_local_conversation_messages(conversation_id)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    """Delete a conversation and clear the local chat history."""
    return delete_local_conversation(conversation_id, current_user)


# ─── Core: send message ────────────────────────────────────────────────────────


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: str = Depends(get_current_user),
):
    """
    Send a message to the Local AI Agent (Ollama + RAG via LlamaIndex + ChromaDB).

    - Runs 100% on-premise — no data leaves your infrastructure
    - User's DOIT context is embedded into ChromaDB and retrieved via RAG
    - Full multi-turn history maintained in-memory per user
    """
    return send_message_to_local(
        conversation_id=conversation_id,
        user_id=current_user,
        content=request.content,
        include_user_context=request.include_user_context,
    )


# ─── History management ────────────────────────────────────────────────────────


@router.post("/reset-history")
async def reset_history(current_user: str = Depends(get_current_user)):
    """
    Clear the in-memory chat history for the current user.
    The next message will start a fresh conversation with no prior context.
    """
    return reset_local_history(user_id=current_user)


@router.get("/history")
async def get_history(current_user: str = Depends(get_current_user)):
    """Return the current in-memory chat history (useful for debugging)."""
    return get_local_history(user_id=current_user)


# ─── Health ────────────────────────────────────────────────────────────────────


@router.get("/health")
async def health():
    """
    Check the local agent stack:
    - Ollama reachability and model availability
    - ChromaDB path
    """
    return local_agent_health_check()
