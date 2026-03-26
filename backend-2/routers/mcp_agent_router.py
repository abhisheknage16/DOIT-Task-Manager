"""
MCP Agent Router
Base path: /api/mcp-agent
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from controllers.mcp_agent_controller import (
    create_mcp_conversation,
    delete_mcp_conversation,
    get_mcp_conversation_messages,
    get_mcp_conversations,
    mcp_agent_health_check,
    send_message_to_mcp,
)
from dependencies import get_current_user

router = APIRouter()


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "MCP Chat"


class SendMessageRequest(BaseModel):
    content: str


@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    current_user: str = Depends(get_current_user),
):
    return create_mcp_conversation(user_id=current_user, title=request.title)


@router.get("/conversations")
async def list_conversations(current_user: str = Depends(get_current_user)):
    return get_mcp_conversations(user_id=current_user)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    return get_mcp_conversation_messages(conversation_id)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    return delete_mcp_conversation(conversation_id, current_user)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: str = Depends(get_current_user),
):
    return await send_message_to_mcp(
        conversation_id=conversation_id,
        user_id=current_user,
        content=request.content,
    )


@router.get("/health")
async def health():
    return await mcp_agent_health_check()
