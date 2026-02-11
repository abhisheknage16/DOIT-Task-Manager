"""
AI Assistant Controller
Handles ChatGPT-like AI interactions using Azure AI Foundry (GPT-5.2-chat + FLUX-1.1-pro)
"""
from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from models.ai_conversation import AIConversation, AIMessage
from utils.azure_ai_utils import (
    chat_completion,
    chat_completion_streaming,
    generate_image,
    get_context_with_system_prompt,
    truncate_context
)
from bson import ObjectId
import json
from typing import Optional, List
import os
from datetime import datetime
from utils.file_parser import extract_file_content, summarize_file_content


def create_conversation(user_id: str, title: str = "New Conversation"):
    """Create a new AI conversation"""
    try:
        conversation_id = AIConversation.create(user_id, title)
        conversation = AIConversation.get_by_id(conversation_id)
        
        if conversation:
            conversation["_id"] = str(conversation["_id"])
            return {
                "success": True,
                "conversation": conversation,
                "message": "Conversation created successfully"
            }
        
        raise HTTPException(status_code=500, detail="Failed to create conversation")
    
    except Exception as e:
        print(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def get_user_conversations(user_id: str):
    """Get all conversations for a user"""
    try:
        conversations = AIConversation.get_user_conversations(user_id)
        
        # Convert ObjectIds to strings
        for conv in conversations:
            conv["_id"] = str(conv["_id"])
        
        return {
            "success": True,
            "conversations": conversations
        }
    
    except Exception as e:
        print(f"Error fetching conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def get_conversation_messages(conversation_id: str):
    """Get all messages in a conversation"""
    try:
        messages = AIMessage.get_conversation_messages(conversation_id)
        
        # Convert ObjectIds to strings
        for msg in messages:
            msg["_id"] = str(msg["_id"])
        
        return {
            "success": True,
            "messages": messages
        }
    
    except Exception as e:
        print(f"Error fetching messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def send_message(conversation_id: str, user_id: str, content: str, stream: bool = False):
    """Send a message and get AI response"""
    try:
        print(f"\n🤖 Processing message for conversation {conversation_id}")
        print(f"   User: {user_id}, Content: {content[:50]}...")
        
        # Verify conversation exists and belongs to user
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        print(f"   ✅ Conversation verified")
        
        # Save user message
        user_message_id = AIMessage.create(
            conversation_id=conversation_id,
            role="user",
            content=content
        )
        print(f"   ✅ User message saved: {user_message_id}")
        
        # Get conversation history for context
        recent_messages = AIMessage.get_recent_context(conversation_id, limit=20)
        print(f"   📚 Loaded {len(recent_messages)} previous messages")
        
        # Prepare messages for API
        api_messages = get_context_with_system_prompt(recent_messages)
        print(f"   📝 Prepared {len(api_messages)} messages for API")
        
        # Truncate if needed
        api_messages = truncate_context(api_messages, max_tokens=8000)
        print(f"   ✂️ Truncated to {len(api_messages)} messages")
        
        # Handle streaming vs non-streaming
        if stream:
            return stream_ai_response(conversation_id, api_messages)
        else:
            print(f"   🚀 Calling Azure OpenAI...")
            # Get AI response (GPT-5.2-chat uses default temperature=1.0)
            response = chat_completion(
                messages=api_messages,
                max_tokens=2000
            )
            print(f"   ✅ Got AI response: {response['content'][:50]}...")
            
            # Save AI response
            ai_message_id = AIMessage.create(
                conversation_id=conversation_id,
                role="assistant",
                content=response["content"]
            )
            print(f"   ✅ AI response saved: {ai_message_id}")
            
            # Update token usage
            if "tokens" in response:
                AIMessage.update_tokens(ai_message_id, response["tokens"]["total"])
            
            # Update conversation title if it's the first message
            if conversation.get("message_count", 0) <= 2:
                # Auto-generate title from first user message
                title = content[:50] + ("..." if len(content) > 50 else "")
                AIConversation.update_title(conversation_id, title)
            
            return {
                "success": True,
                "message": {
                    "_id": str(ai_message_id),
                    "role": "assistant",
                    "content": response["content"],
                    "created_at": datetime.utcnow().isoformat(),
                    "tokens_used": response.get("tokens", {}).get("total", 0)
                },
                "tokens": response.get("tokens", {})
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in send_message: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def stream_ai_response(conversation_id: str, api_messages: List[dict]):
    """Stream AI response chunks"""
    async def generate():
        try:
            full_content = ""
            
            # Stream chunks
            for chunk in chat_completion_streaming(api_messages):
                full_content += chunk
                # Send chunk in SSE format
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # Save complete response to database
            ai_message_id = AIMessage.create(
                conversation_id=conversation_id,
                role="assistant",
                content=full_content
            )
            
            # Send completion message
            yield f"data: {json.dumps({'done': True, 'message_id': str(ai_message_id)})}\n\n"
        
        except Exception as e:
            print(f"Error in stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


def generate_ai_image(conversation_id: str, user_id: str, prompt: str):
    """Generate an image using FLUX-1.1-pro"""
    try:
        # Verify conversation
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Save user request
        user_message_id = AIMessage.create(
            conversation_id=conversation_id,
            role="user",
            content=f"Generate image: {prompt}"
        )
        
        # Generate image
        result = generate_image(prompt)
        
        if result.get("success"):
            # Save AI response with image
            ai_message_id = AIMessage.create(
                conversation_id=conversation_id,
                role="assistant",
                content=f"I've generated an image based on your prompt: '{prompt}'",
                image_url=result.get("image_url") or result.get("filepath")
            )
            
            return {
                "success": True,
                "message": {
                    "_id": str(ai_message_id),
                    "role": "assistant",
                    "content": f"Here's your generated image for: '{prompt}'",
                    "image_url": result.get("image_url") or result.get("filepath"),
                    "created_at": datetime.utcnow().isoformat()
                },
                "image": result
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Image generation failed: {result.get('error', 'Unknown error')}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def upload_file_to_conversation(
    conversation_id: str,
    user_id: str,
    file: UploadFile,
    message: Optional[str] = None
):
    """Upload a file and add it to conversation context"""
    try:
        print(f"\n📎 Processing file upload for conversation {conversation_id}")
        print(f"   File: {file.filename}, Type: {file.content_type}")
        
        # Verify conversation
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Create upload directory
        upload_dir = "uploads/ai_attachments"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(upload_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(file.file.read())
        
        print(f"   ✅ File saved: {filepath}")
        
        # Extract file content
        print(f"   📖 Extracting file content...")
        extraction_result = extract_file_content(filepath, file.content_type)
        
        if not extraction_result.get("success"):
            print(f"   ⚠️ Could not extract content: {extraction_result.get('error')}")
            # Save message without extracted content
            content = message or f"Uploaded file: {file.filename} (content extraction not supported)"
        else:
            print(f"   ✅ Content extracted: {extraction_result.get('content_type')}")
            # Include extracted content in message for AI context
            file_content = extraction_result.get("content", "")
            
            # Truncate if too long
            file_content = summarize_file_content(file_content, max_tokens=3000)
            
            # Create message with file content
            content = f"User uploaded file '{file.filename}'.\n\nFile Contents:\n{file_content}"
        
        # Create message with attachment and extracted content
        message_id = AIMessage.create(
            conversation_id=conversation_id,
            role="user",
            content=content,
            attachments=[{
                "filename": file.filename,
                "filepath": filepath,
                "content_type": file.content_type,
                "size": os.path.getsize(filepath),
                "extracted": extraction_result.get("success", False)
            }]
        )
        
        print(f"   ✅ Message created with file content: {message_id}")
        
        # Generate AI acknowledgment
        if extraction_result.get("success"):
            file_type = extraction_result.get("content_type", "file")
            ai_content = f"I've received and analyzed your {file_type} file '{file.filename}'. "
            
            # Add specific details based on file type
            if file_type == "csv":
                rows = extraction_result.get("rows", 0)
                columns = extraction_result.get("columns", 0)
                ai_content += f"It contains {rows} rows and {columns} columns. "
            elif file_type == "pdf":
                pages = extraction_result.get("pages", 0)
                ai_content += f"It has {pages} pages. "
            
            ai_content += "I can now answer questions about this file. What would you like to know?"
            
            # Save AI acknowledgment
            ai_message_id = AIMessage.create(
                conversation_id=conversation_id,
                role="assistant",
                content=ai_content
            )
            
            return {
                "success": True,
                "message": ai_content,
                "file": {
                    "filename": file.filename,
                    "filepath": filepath,
                    "url": f"/{filepath}",
                    "extracted": True,
                    "metadata": {
                        "type": file_type,
                        **{k: v for k, v in extraction_result.items() if k not in ['success', 'content', 'error']}
                    }
                },
                "message_id": str(message_id),
                "ai_message_id": str(ai_message_id)
            }
        else:
            return {
                "success": True,
                "message": f"File '{file.filename}' uploaded, but content extraction not supported for this file type.",
                "file": {
                    "filename": file.filename,
                    "filepath": filepath,
                    "url": f"/{filepath}",
                    "extracted": False
                },
                "message_id": str(message_id)
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading file: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def delete_conversation(conversation_id: str, user_id: str):
    """Delete a conversation and all its messages"""
    try:
        # Verify conversation
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Delete conversation and messages
        AIConversation.delete(conversation_id)
        
        return {
            "success": True,
            "message": "Conversation deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def update_conversation_title(conversation_id: str, user_id: str, title: str):
    """Update conversation title"""
    try:
        # Verify conversation
        conversation = AIConversation.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Update title
        AIConversation.update_title(conversation_id, title)
        
        return {
            "success": True,
            "message": "Title updated successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating title: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
