# backend-2/routers/langgraph_agent_router.py
"""
LangGraph AI Agent Router
Stack: Azure OpenAI + LangGraph + LangChain Tools

Base path: /api/langgraph-agent
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user
from controllers.langgraph_agent_controller import (
    create_langgraph_conversation,
    get_langgraph_conversations,
    get_langgraph_conversation_messages,
    delete_langgraph_conversation,
    send_message_to_langgraph,
    reset_langgraph_history,
    get_langgraph_history,
    langgraph_agent_health_check,
)

router = APIRouter()


# ─── Pydantic models ───────────────────────────────────────────────────────────


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "LangGraph AI Chat"


class SendMessageRequest(BaseModel):
    content: str
    include_user_context: Optional[bool] = True


# ─── Conversation CRUD ─────────────────────────────────────────────────────────


@router.post("/conversations")
def create_conversation(
    request: CreateConversationRequest,
    current_user: str = Depends(get_current_user),
):
    """Create a new LangGraph AI conversation."""
    return create_langgraph_conversation(user_id=current_user, title=request.title)


@router.get("/conversations")
def list_conversations(current_user: str = Depends(get_current_user)):
    """List all LangGraph AI conversations for the current user."""
    return get_langgraph_conversations(user_id=current_user)


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    """Get all messages in a conversation."""
    return get_langgraph_conversation_messages(conversation_id)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    """Delete a conversation and clear the chat history."""
    return delete_langgraph_conversation(conversation_id, current_user)


# ─── Core: send message ────────────────────────────────────────────────────────


@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: str = Depends(get_current_user),
):
    """
    Send a message to the LangGraph AI Agent.

    The agent has access to tools for:
    - Creating and managing tasks
    - Creating and managing sprints
    - Assigning tasks
    - Listing projects, tasks, and team members
    - And more!

    The agent uses multi-step reasoning to accomplish complex goals.
    """
    return send_message_to_langgraph(
        conversation_id=conversation_id,
        user_id=current_user,
        content=request.content,
        include_user_context=request.include_user_context,
    )


# ─── History management ────────────────────────────────────────────────────────


@router.post("/conversations/{conversation_id}/reset-history")
def reset_history(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    """Clear the in-memory chat history for this conversation."""
    return reset_langgraph_history(conversation_id=conversation_id)


@router.get("/conversations/{conversation_id}/history")
def get_history(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    """Return the current in-memory chat history (for debugging)."""
    return get_langgraph_history(conversation_id=conversation_id)


# ─── Health ────────────────────────────────────────────────────────────────────


@router.get("/health")
def health():
    """
    Check the LangGraph agent stack:
    - Azure OpenAI connectivity
    - LangGraph configuration
    """
    return langgraph_agent_health_check()
