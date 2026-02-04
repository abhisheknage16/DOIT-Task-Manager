from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from schemas import (
    TaskCreate, TaskUpdate, AddLabelRequest, AddAttachmentRequest,
    RemoveAttachmentRequest, AddLinkRequest, RemoveLinkRequest, AddCommentRequest
)
from controllers import task_controller, git_controller
from dependencies import get_current_user
from utils.router_helpers import handle_controller_response
from utils.websocket_manager import manager
from utils.auth_utils import verify_token_for_websocket
import json

router = APIRouter()

# WebSocket endpoint for real-time Kanban board updates
@router.websocket("/ws/project/{project_id}")
async def kanban_websocket(websocket: WebSocket, project_id: str, token: str):
    """WebSocket for real-time Kanban board collaboration"""
    # Verify token
    user_id = verify_token_for_websocket(token)
    if not user_id:
        await websocket.close(code=1008)  # Policy violation
        return
    
    # Verify project access
    from models.project import Project
    if not Project.is_member(project_id, user_id):
        await websocket.close(code=1008)
        return
    
    # Connect to project's Kanban channel
    channel_id = f"kanban_{project_id}"
    await manager.connect(websocket, channel_id, user_id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection",
            "channel_id": channel_id,
            "project_id": project_id,
            "message": "Connected to Kanban board"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_json()
            
            # Handle heartbeat
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        manager.disconnect(channel_id, user_id)
    except Exception as e:
        print(f"[KANBAN WS] Error: {str(e)}")
        manager.disconnect(channel_id, user_id)

@router.post("")
async def create_task(data: TaskCreate, user_id: str = Depends(get_current_user)):
    """Create new task"""
    body = json.dumps(data.model_dump())
    response = task_controller.create_task(body, user_id)
    return handle_controller_response(response)

@router.get("/my")
async def get_my_tasks(user_id: str = Depends(get_current_user)):
    """Get tasks assigned to me"""
    response = task_controller.get_my_tasks(user_id)
    return handle_controller_response(response)

@router.get("/pending-approval")
async def get_pending_approval(user_id: str = Depends(get_current_user)):
    """Get all pending approval tasks"""
    response = task_controller.get_all_pending_approval_tasks(user_id)
    return handle_controller_response(response)

@router.get("/closed")
async def get_closed_tasks(user_id: str = Depends(get_current_user)):
    """Get all closed tasks"""
    response = task_controller.get_all_closed_tasks(user_id)
    return handle_controller_response(response)

@router.get("/project/{project_id}")
async def get_project_tasks(project_id: str, user_id: str = Depends(get_current_user)):
    """Get all tasks for a project"""
    response = task_controller.get_project_tasks(project_id, user_id)
    return handle_controller_response(response)

@router.get("/{task_id}")
async def get_task(task_id: str, user_id: str = Depends(get_current_user)):
    """Get task by ID"""
    response = task_controller.get_task_by_id(task_id, user_id)
    return handle_controller_response(response)

@router.put("/{task_id}")
async def update_task(task_id: str, data: TaskUpdate, user_id: str = Depends(get_current_user)):
    """Update task - CRITICAL for Kanban drag-drop"""
    body = json.dumps(data.model_dump())
    response = task_controller.update_task(body, task_id, user_id)
    return handle_controller_response(response)

@router.delete("/{task_id}")
async def delete_task(task_id: str, user_id: str = Depends(get_current_user)):
    """Delete task"""
    response = task_controller.delete_task(task_id, user_id)
    return handle_controller_response(response)

# Labels
@router.post("/{task_id}/labels")
async def add_label(task_id: str, data: AddLabelRequest, user_id: str = Depends(get_current_user)):
    """Add label to task"""
    body = json.dumps(data.model_dump())
    response = task_controller.add_label_to_task(task_id, body, user_id)
    return handle_controller_response(response)

@router.delete("/{task_id}/labels/{label}")
async def remove_label(task_id: str, label: str, user_id: str = Depends(get_current_user)):
    """Remove label from task"""
    response = task_controller.remove_label_from_task(task_id, label, user_id)
    return handle_controller_response(response)

@router.get("/labels/{project_id}")
async def get_project_labels(project_id: str, user_id: str = Depends(get_current_user)):
    """Get all labels for project"""
    response = task_controller.get_project_labels(project_id, user_id)
    return handle_controller_response(response)

# Attachments
@router.post("/{task_id}/attachments")
async def add_attachment(task_id: str, data: AddAttachmentRequest, user_id: str = Depends(get_current_user)):
    """Add attachment to task"""
    body = json.dumps(data.model_dump())
    response = task_controller.add_attachment_to_task(task_id, body, user_id)
    return handle_controller_response(response)

@router.delete("/{task_id}/attachments")
async def remove_attachment(task_id: str, data: RemoveAttachmentRequest, user_id: str = Depends(get_current_user)):
    """Remove attachment from task"""
    body = json.dumps(data.model_dump())
    response = task_controller.remove_attachment_from_task(task_id, body, user_id)
    return handle_controller_response(response)

# Links
@router.post("/{task_id}/links")
async def add_link(task_id: str, data: AddLinkRequest, user_id: str = Depends(get_current_user)):
    """Add link to another task"""
    body = json.dumps(data.model_dump())
    response = task_controller.add_link_to_task(task_id, body, user_id)
    return handle_controller_response(response)

@router.delete("/{task_id}/links")
async def remove_link(task_id: str, data: RemoveLinkRequest, user_id: str = Depends(get_current_user)):
    """Remove link from task"""
    body = json.dumps(data.model_dump())
    response = task_controller.remove_link_from_task(task_id, body, user_id)
    return handle_controller_response(response)

# Approval
@router.post("/{task_id}/approve")
async def approve_task(task_id: str, user_id: str = Depends(get_current_user)):
    """Approve and close task"""
    response = task_controller.approve_task(task_id, user_id)
    return handle_controller_response(response)

# Comments
@router.post("/{task_id}/comments")
async def add_comment(task_id: str, data: AddCommentRequest, user_id: str = Depends(get_current_user)):
    """Add comment to task"""
    body = json.dumps(data.model_dump())
    response = task_controller.add_task_comment(task_id, body, user_id)
    return handle_controller_response(response)

# Git Activity
@router.get("/git-activity/{task_id}")
async def get_git_activity(task_id: str, user_id: str = Depends(get_current_user)):
    """Get GitHub activity for a task (branches, commits, PRs)"""
    response = git_controller.get_task_git_activity(task_id, user_id)
    return handle_controller_response(response)