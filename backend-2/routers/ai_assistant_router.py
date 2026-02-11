"""
AI Assistant Router
Routes for ChatGPT-like AI interface using Azure AI Foundry
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user
from controllers import ai_assistant_controller


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
    request: CreateConversationRequest,
    current_user: str = Depends(get_current_user)
):
    """Create a new AI conversation"""
    return ai_assistant_controller.create_conversation(
        user_id=current_user,
        title=request.title
    )


@router.get("/conversations")
async def get_conversations(current_user: str = Depends(get_current_user)):
    """Get all conversations for current user"""
    return ai_assistant_controller.get_user_conversations(
        user_id=current_user
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all messages in a conversation"""
    return ai_assistant_controller.get_conversation_messages(conversation_id)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: str = Depends(get_current_user)
):
    """Send a message and get AI response"""
    return ai_assistant_controller.send_message(
        conversation_id=conversation_id,
        user_id=current_user,
        content=request.content,
        stream=request.stream
    )


@router.post("/conversations/{conversation_id}/generate-image")
async def generate_image(
    conversation_id: str,
    request: GenerateImageRequest,
    current_user: str = Depends(get_current_user)
):
    """Generate an image using FLUX-1.1-pro"""
    return ai_assistant_controller.generate_ai_image(
        conversation_id=conversation_id,
        user_id=current_user,
        prompt=request.prompt
    )


@router.post("/conversations/{conversation_id}/upload")
async def upload_file(
    conversation_id: str,
    file: UploadFile = File(...),
    message: Optional[str] = Form(None),
    current_user: str = Depends(get_current_user)
):
    """Upload a file to conversation"""
    return ai_assistant_controller.upload_file_to_conversation(
        conversation_id=conversation_id,
        user_id=current_user,
        file=file,
        message=message
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: str = Depends(get_current_user)
):
    """Delete a conversation"""
    return ai_assistant_controller.delete_conversation(
        conversation_id=conversation_id,
        user_id=current_user
    )


@router.patch("/conversations/{conversation_id}/title")
async def update_title(
    conversation_id: str,
    request: UpdateTitleRequest,
    current_user: str = Depends(get_current_user)
):
    """Update conversation title"""
    return ai_assistant_controller.update_conversation_title(
        conversation_id=conversation_id,
        user_id=current_user,
        title=request.title
    )


@router.get("/health")
async def health_check():
    """Health check for AI Assistant service"""
    return {
        "status": "healthy",
        "service": "AI Assistant",
        "models": {
            "chat": "GPT-5.2-chat (Azure OpenAI)",
            "image": "FLUX-1.1-pro (Azure AI Foundry)"
        }
    }
