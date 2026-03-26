"""
AI Assistant Router - ENHANCED WITH INSIGHTS
Routes for ChatGPT-like AI interface using Azure AI Foundry
NOW with intelligent data-driven insights from MongoDB
"""

import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user
from controllers import ai_assistant_controller
from dotenv import load_dotenv

load_dotenv()


router = APIRouter()


# Request/Response Models
class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"


class SendMessageRequest(BaseModel):
    content: str
    stream: Optional[bool] = False


class GenerateImageRequest(BaseModel):
    prompt: str


class UpdateTitleRequest(BaseModel):
    title: str


# Routes
@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest, current_user: str = Depends(get_current_user)
):
    """Create a new AI conversation"""
    return ai_assistant_controller.create_conversation(
        user_id=current_user, title=request.title
    )


@router.get("/conversations")
async def get_conversations(current_user: str = Depends(get_current_user)):
    """Get all conversations for current user"""
    return ai_assistant_controller.get_user_conversations(user_id=current_user)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str, current_user: dict = Depends(get_current_user)
):
    """Get all messages in a conversation"""
    return ai_assistant_controller.get_conversation_messages(conversation_id)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: str = Depends(get_current_user),
):
    """
    Send a message and get AI response
    🆕 ENHANCED: Now includes intelligent insights from user's data
    """
    return ai_assistant_controller.send_message(
        conversation_id=conversation_id,
        user_id=current_user,
        content=request.content,
        stream=request.stream,
    )


@router.post("/conversations/{conversation_id}/generate-image")
async def generate_image(
    conversation_id: str,
    request: GenerateImageRequest,
    current_user: str = Depends(get_current_user),
):
    """Generate an image using FLUX-1.1-pro"""
    return ai_assistant_controller.generate_ai_image(
        conversation_id=conversation_id, user_id=current_user, prompt=request.prompt
    )


@router.post("/conversations/{conversation_id}/upload")
async def upload_file(
    conversation_id: str,
    file: UploadFile = File(...),
    message: Optional[str] = Form(None),
    current_user: str = Depends(get_current_user),
):
    """Upload a file to conversation"""
    return ai_assistant_controller.upload_file_to_conversation(
        conversation_id=conversation_id,
        user_id=current_user,
        file=file,
        message=message,
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str, current_user: str = Depends(get_current_user)
):
    """Delete a conversation"""
    return ai_assistant_controller.delete_conversation(
        conversation_id=conversation_id, user_id=current_user
    )


@router.patch("/conversations/{conversation_id}/title")
async def update_title(
    conversation_id: str,
    request: UpdateTitleRequest,
    current_user: str = Depends(get_current_user),
):
    """Update conversation title"""
    return ai_assistant_controller.update_conversation_title(
        conversation_id=conversation_id, user_id=current_user, title=request.title
    )


@router.get("/insights")
async def get_insights(current_user: str = Depends(get_current_user)):
    """
    🆕 Get intelligent insights based on user's data
    Returns key metrics, recommendations, and alerts based on MongoDB data

    Example response:
    {
        "success": true,
        "insights": [
            {
                "type": "critical",
                "icon": "🚨",
                "title": "3 Overdue Tasks",
                "description": "Immediate action required",
                "priority": 1
            }
        ],
        "summary": {
            "tasks": {...},
            "projects": {...},
            "velocity": {...}
        }
    }
    """
    return ai_assistant_controller.get_user_insights(current_user)


@router.get("/health")
async def health_check():
    """Health check for AI Assistant service"""
    chat_model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    image_model = os.getenv("AZURE_FLUX_MODEL", "FLUX-1.1-pro")

    return {
        "status": "healthy",
        "service": "AI Assistant",
        "models": {
            "chat": f"{chat_model} (Azure OpenAI)",
            "image": f"{image_model} (Azure AI Foundry)",
        },
        "features": [
            "💬 Intelligent conversations with data context",
            "📊 Real-time insights from MongoDB",
            "🎯 Personalized recommendations",
            "🖼️ Image generation (FLUX-1.1-pro)",
            "📎 File upload and analysis",
            "⚡ Fast response times",
        ],
    }
