"""
Azure AI Foundry Agent Router
Endpoints for chatting with the MS Foundry AI Agent (asst_0uvId9Fz7NLJfxIwIzD0uN9b)

Base path: /api/foundry-agent
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user
from controllers.azure_agent_controller import (
    create_agent_conversation,
    get_agent_conversations,
    get_agent_conversation_messages,
    delete_agent_conversation,
    send_message_to_foundry_agent,
    reset_agent_thread,
    get_foundry_thread_messages,
    agent_health_check,
)

router = APIRouter()


# ─── Pydantic request models ───────────────────────────────────────────────────


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "Agent Chat"


class SendMessageRequest(BaseModel):
    content: str
    include_user_context: Optional[bool] = True


# ─── Conversation CRUD ─────────────────────────────────────────────────────────


@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    current_user: str = Depends(get_current_user),
):
    """Create a new Foundry Agent conversation."""
    return create_agent_conversation(user_id=current_user, title=request.title)


@router.get("/conversations")
async def list_conversations(current_user: str = Depends(get_current_user)):
    """List all Foundry Agent conversations for the current user."""
    return get_agent_conversations(user_id=current_user)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    """Get all messages in a conversation."""
    return get_agent_conversation_messages(conversation_id)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    """Delete a conversation and reset the underlying Foundry thread."""
    return delete_agent_conversation(conversation_id, current_user)


# ─── Core: send message ────────────────────────────────────────────────────────


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: str = Depends(get_current_user),
):
    """
    Send a message to the Azure AI Foundry Agent and get a response.

    The agent has access to:
    - Its own configured tools (from Azure AI Foundry portal)
    - Live DOIT user context (tasks, projects, sprints) injected automatically
    - Full multi-turn conversation history via Foundry threads
    """
    return send_message_to_foundry_agent(
        conversation_id=conversation_id,
        user_id=current_user,
        content=request.content,
        include_user_context=request.include_user_context,
    )


# ─── Thread management ─────────────────────────────────────────────────────────


@router.post("/reset-thread")
async def reset_thread(current_user: str = Depends(get_current_user)):
    """
    Reset the Foundry conversation thread for the current user.
    The next message will start a completely new conversation with the agent.
    """
    return reset_agent_thread(user_id=current_user)


@router.get("/thread-messages")
async def get_thread_messages_raw(current_user: str = Depends(get_current_user)):
    """
    Fetch raw messages directly from the Azure AI Foundry thread.
    Useful for debugging or syncing state.
    """
    return get_foundry_thread_messages(user_id=current_user)


# ─── Health ────────────────────────────────────────────────────────────────────


@router.get("/health")
async def health():
    """Check connectivity to the Azure AI Foundry Agent."""
    return agent_health_check()
