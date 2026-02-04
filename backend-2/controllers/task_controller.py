import json
import asyncio
from models.task import Task
from models.project import Project
from models.user import User
from utils.response import success_response, error_response, datetime_to_iso
from utils.validators import validate_required_fields
from utils.ticket_utils import generate_ticket_id
from utils.label_utils import validate_label, normalize_label
from utils.websocket_manager import manager
from bson import ObjectId
from datetime import datetime, timezone

def create_task(body_str, user_id):
    """Create a new task - requires authentication"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    try:
        data = json.loads(body_str)
    except:
        return error_response("Invalid JSON", 400)
    
    # Validate required fields
    required = ["title", "project_id"]
    validation_error = validate_required_fields(data, required)
    if validation_error:
        return error_response(validation_error, 400)
    
    # Validate title length
    if len(data["title"].strip()) < 3:
        return error_response("Task title must be at least 3 characters", 400)
    
    project_id = data["project_id"]
    
    # Check if project exists
    project = Project.find_by_id(project_id)
    if not project:
        return error_response("Project not found", 404)
    
    # Check if user is member or owner
    if not Project.is_member(project_id, user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    # Validate priority
    valid_priorities = ["Low", "Medium", "High"]
    priority = data.get("priority", "Medium")
    if priority not in valid_priorities:
        return error_response(f"Priority must be one of: {', '.join(valid_priorities)}", 400)
    
    # Validate issue type
    valid_issue_types = ["task", "bug", "story", "epic"]
    issue_type = data.get("issue_type", "task").lower()
    if issue_type not in valid_issue_types:
        return error_response(f"Issue type must be one of: {', '.join(valid_issue_types)}", 400)
    
    # Validate status
    valid_statuses = ["To Do", "In Progress", "Testing", "Dev Complete", "Done"]
    status = data.get("status", "To Do")
    if status not in valid_statuses:
        return error_response(f"Status must be one of: {', '.join(valid_statuses)}", 400)
    
    # Validate assignee if provided
    assignee_id = data.get("assignee_id")
    assignee_name = "Unassigned"
    assignee_email = ""
    
    if assignee_id:
        # Check if assignee is a project member
        if not Project.is_member(project_id, assignee_id):
            return error_response("Assignee must be a project member", 400)
        
        # Get assignee info
        assignee = User.find_by_id(assignee_id)
        if assignee:
            # Check if creator is member trying to assign to admin
            creator = User.find_by_id(user_id)
            creator_role = creator.get("role", "member") if creator else "member"
            assignee_role = assignee.get("role", "member")
            
            # Members cannot assign tasks to admin or super-admin users
            if creator_role == "member" and assignee_role in ["admin", "super-admin"]:
                return error_response("Members cannot assign tasks to admin or super-admin users", 403)
            
            assignee_name = assignee["name"]
            assignee_email = assignee["email"]
    
    # Generate unique ticket ID
    try:
        ticket_id = generate_ticket_id(project_id, issue_type)
    except Exception as e:
        return error_response(f"Failed to generate ticket ID: {str(e)}", 500)
    
    # Validate and normalize labels
    labels = data.get("labels", [])
    if labels:
        if not isinstance(labels, list):
            return error_response("Labels must be an array", 400)
        
        normalized_labels = []
        for label in labels:
            if not isinstance(label, str):
                return error_response("Each label must be a string", 400)
            
            is_valid, error_msg = validate_label(label)
            if not is_valid:
                return error_response(f"Invalid label '{label}': {error_msg}", 400)
            
            normalized_labels.append(normalize_label(label))
        
        # Remove duplicates
        labels = list(set(normalized_labels))
    
    # Create task
    task_data = {
        "ticket_id": ticket_id,
        "issue_type": issue_type,
        "title": data["title"].strip(),
        "description": data.get("description", "").strip(),
        "project_id": project_id,
        "priority": priority,
        "status": status,
        "assignee_id": assignee_id,
        "assignee_name": assignee_name,
        "assignee_email": assignee_email,
        "due_date": data.get("due_date"),
        "labels": labels,
        "created_by": user_id
    }
    
    task = Task.create(task_data)
    
    # Convert ObjectId and datetime to strings
    task["_id"] = str(task["_id"])
    task["created_at"] = datetime_to_iso(task["created_at"])
    task["updated_at"] = datetime_to_iso(task["updated_at"])
    
    # Broadcast task creation to Kanban board
    asyncio.create_task(manager.broadcast_to_channel({
        "type": "task_created",
        "task": task,
        "user_name": User.find_by_id(user_id).get("name", "Unknown") if User.find_by_id(user_id) else "Unknown"
    }, f"kanban_{project_id}"))
    
    return success_response({
        "message": "Task created successfully",
        "task": task
    }, 201)


def get_project_tasks(project_id, user_id):
    """Get all tasks for a project"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    # Check if project exists
    project = Project.find_by_id(project_id)
    if not project:
        return error_response("Project not found", 404)
    
    # Check if user is member or owner
    if not Project.is_member(project_id, user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    tasks_list = Task.find_by_project(project_id)
    
    # Batch fetch sprints and users to avoid N+1 queries
    from database import db
    from models.sprint import Sprint
    
    # Collect unique sprint IDs and creator IDs
    sprint_ids = list(set([task["sprint_id"] for task in tasks_list if task.get("sprint_id")]))
    creator_ids = list(set([task["created_by"] for task in tasks_list if task.get("created_by")]))
    
    # Batch fetch sprints
    sprint_map = {}
    if sprint_ids:
        sprints = list(db.sprints.find({"_id": {"$in": [ObjectId(sid) for sid in sprint_ids]}}))
        sprint_map = {str(s["_id"]): s["name"] for s in sprints}
    
    # Batch fetch users
    user_map = {}
    if creator_ids:
        users = list(db.users.find({"_id": {"$in": [ObjectId(uid) for uid in creator_ids]}}))
        user_map = {str(u["_id"]): {"name": u.get("name", "Unknown"), "email": u.get("email", "")} for u in users}
    
    # Convert ObjectId and datetime to strings, add creator details
    for task in tasks_list:
        task["_id"] = str(task["_id"])
        task["created_at"] = datetime_to_iso(task["created_at"])
        task["updated_at"] = datetime_to_iso(task["updated_at"])
        # Convert moved_to_backlog_at if present
        if "moved_to_backlog_at" in task and task["moved_to_backlog_at"]:
            task["moved_to_backlog_at"] = datetime_to_iso(task["moved_to_backlog_at"])
        
        # Add sprint name from batch-fetched data
        if task.get("sprint_id"):
            task["sprint_name"] = sprint_map.get(task["sprint_id"], "")
        
        # Add creator details from batch-fetched data
        if task.get("created_by"):
            creator = user_map.get(task["created_by"])
            if creator:
                task["created_by_name"] = creator["name"]
                task["created_by_email"] = creator["email"]
            else:
                task["created_by_name"] = "Unknown"
                task["created_by_email"] = ""
        else:
            task["created_by_name"] = "Unknown"
            task["created_by_email"] = ""
    
    return success_response({
        "tasks": tasks_list,
        "count": len(tasks_list)
    })


def get_task_by_id(task_id, user_id):
    """Get a specific task by ID"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    task = Task.find_by_id(task_id)
    
    if not task:
        return error_response("Task not found", 404)
    
    # Check if user is member of the project
    if not Project.is_member(task["project_id"], user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    # Add sprint name if task is in a sprint
    if task.get("sprint_id"):
        from models.sprint import Sprint
        sprint = Sprint.find_by_id(task["sprint_id"])
        if sprint:
            task["sprint_name"] = sprint["name"]
    
    # Add creator details
    from database import db
    if task.get("created_by"):
        creator = db.users.find_one({"_id": ObjectId(task["created_by"])})
        if creator:
            task["created_by_name"] = creator.get("name", "Unknown")
            task["created_by_email"] = creator.get("email", "")
        else:
            task["created_by_name"] = "Unknown"
            task["created_by_email"] = ""
    else:
        task["created_by_name"] = "Unknown"
        task["created_by_email"] = ""
    
    # Add assignee details
    if task.get("assignee_id"):
        assignee = db.users.find_one({"_id": ObjectId(task["assignee_id"])})
        if assignee:
            task["assignee_name"] = assignee.get("name", "Unassigned")
            task["assignee_email"] = assignee.get("email", "")
        else:
            task["assignee_name"] = "Unassigned"
            task["assignee_email"] = ""
    else:
        task["assignee_name"] = "Unassigned"
        task["assignee_email"] = ""
    
    # Convert ObjectId and datetime to strings
    task["_id"] = str(task["_id"])
    task["created_at"] = datetime_to_iso(task["created_at"])
    task["updated_at"] = datetime_to_iso(task["updated_at"])
    # Convert moved_to_backlog_at if present
    if "moved_to_backlog_at" in task and task["moved_to_backlog_at"]:
        task["moved_to_backlog_at"] = datetime_to_iso(task["moved_to_backlog_at"])
    
    return success_response({"task": task})


def update_task(body_str, task_id, user_id):
    """Update a task"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    try:
        data = json.loads(body_str)
    except:
        return error_response("Invalid JSON", 400)
    
    # Check if task exists
    task = Task.find_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Check if user is member of the project
    if not Project.is_member(task["project_id"], user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    # Prepare update data
    update_data = {}
    
    if "title" in data:
        if data["title"] is not None and data["title"].strip():  # Only update if non-empty
            if len(data["title"].strip()) < 3:
                return error_response("Task title must be at least 3 characters", 400)
            update_data["title"] = data["title"].strip()
        elif data["title"] is not None and not data["title"].strip():
            # If empty string is explicitly sent, reject it
            return error_response("Task title cannot be empty", 400)
    
    if "description" in data:
        # Description can be empty, but only update if provided
        if data["description"] is not None:
            update_data["description"] = data["description"].strip() if data["description"] else ""
    
    if "priority" in data and data["priority"]:  # Only validate if priority is not None/empty
        valid_priorities = ["Low", "Medium", "High"]
        if data["priority"] not in valid_priorities:
            return error_response(f"Priority must be one of: {', '.join(valid_priorities)}", 400)
        update_data["priority"] = data["priority"]
    
    if "status" in data:
        valid_statuses = ["To Do", "In Progress", "Testing", "Dev Complete", "Done", "Closed"]
        if data["status"] not in valid_statuses:
            return error_response(f"Status must be one of: {', '.join(valid_statuses)}", 400)
        
        # If task is being marked as Done or Closed, remove from backlog
        if data["status"] in ["Done", "Closed"]:
            update_data["in_backlog"] = False
            update_data["moved_to_backlog_at"] = None
        
        # Only project owner can set status to "Closed"
        if data["status"] == "Closed":
            project = Project.find_by_id(task["project_id"])
            if not project:
                return error_response("Project not found", 404)
            
            if project["user_id"] != user_id:
                return error_response("Only project owner can close tasks", 403)
            
            # Add approval metadata
            current_user = User.find_by_id(user_id)
            update_data["approved_by"] = user_id
            update_data["approved_by_name"] = current_user["name"] if current_user else "Unknown"
            update_data["approved_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        
        # Comment is optional for status changes (allows Kanban drag-drop)
        # If comment is provided, it will be logged in activity
        update_data["status"] = data["status"]
    
    if "assignee_id" in data:
        assignee_id = data["assignee_id"]
        if assignee_id:
            # Check if assignee is a project member
            if not Project.is_member(task["project_id"], assignee_id):
                return error_response("Assignee must be a project member", 400)
            
            # Get assignee info
            assignee = User.find_by_id(assignee_id)
            if assignee:
                update_data["assignee_id"] = assignee_id
                update_data["assignee_name"] = assignee["name"]
                update_data["assignee_email"] = assignee["email"]
        else:
            # Unassign
            update_data["assignee_id"] = None
            update_data["assignee_name"] = "Unassigned"
            update_data["assignee_email"] = ""
    
    if "due_date" in data and data["due_date"]:
        update_data["due_date"] = data["due_date"]
    
    if "issue_type" in data and data["issue_type"]:
        valid_issue_types = ["bug", "task", "story", "epic"]
        if data["issue_type"] not in valid_issue_types:
            return error_response(f"Issue type must be one of: {', '.join(valid_issue_types)}", 400)
        update_data["issue_type"] = data["issue_type"]
    
    if "labels" in data and data["labels"] is not None:
        # Validate labels if provided
        labels = data["labels"]
        if not isinstance(labels, list):
            return error_response("Labels must be a list", 400)
        update_data["labels"] = labels
    
    if not update_data and not data.get("comment"):
        return error_response("No valid fields to update", 400)
    
    # Get user info for activity log
    current_user = User.find_by_id(user_id)
    user_name = current_user["name"] if current_user else "Unknown"
    
    # Update task
    success = Task.update(task_id, update_data)
    
    if success:
        # Add activity log for status change with comment
        if "status" in data:
            old_status = task.get("status", "To Do")
            # Only log if status actually changed
            if old_status != data["status"]:
                activity_data = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "action": "status_change",
                    "comment": data.get("comment", ""),
                    "old_value": old_status,
                    "new_value": data["status"]
                }
                Task.add_activity(task_id, activity_data)
        # Add activity log for comment only (no status change)
        elif data.get("comment", "").strip():
            activity_data = {
                "user_id": user_id,
                "user_name": user_name,
                "action": "comment",
                "comment": data.get("comment", "").strip(),
                "old_value": None,
                "new_value": None
            }
            Task.add_activity(task_id, activity_data)
        
        updated_task = Task.find_by_id(task_id)
        updated_task["_id"] = str(updated_task["_id"])
        updated_task["created_at"] = datetime_to_iso(updated_task["created_at"])
        updated_task["updated_at"] = datetime_to_iso(updated_task["updated_at"])
        # Convert moved_to_backlog_at if present
        if "moved_to_backlog_at" in updated_task and updated_task["moved_to_backlog_at"]:
            updated_task["moved_to_backlog_at"] = datetime_to_iso(updated_task["moved_to_backlog_at"])
        
        # Broadcast task update to Kanban board
        asyncio.create_task(manager.broadcast_to_channel({
            "type": "task_updated",
            "task": updated_task,
            "updated_fields": list(update_data.keys()),
            "user_id": user_id,
            "user_name": user_name,
            "old_status": task.get("status") if "status" in update_data else None
        }, f"kanban_{task['project_id']}"))
        
        return success_response({
            "message": "Task updated successfully",
            "task": updated_task
        })
    else:
        return error_response("Failed to update task", 500)


def delete_task(task_id, user_id):
    """Delete a task"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    # Check if task exists
    task = Task.find_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Check if user is member of the project
    if not Project.is_member(task["project_id"], user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    project_id = task["project_id"]
    
    # Delete task
    success = Task.delete(task_id)
    
    if success:
        # Broadcast task deletion to Kanban board
        user = User.find_by_id(user_id)
        asyncio.create_task(manager.broadcast_to_channel({
            "type": "task_deleted",
            "task_id": task_id,
            "user_name": user.get("name", "Unknown") if user else "Unknown"
        }, f"kanban_{project_id}"))
        
        return success_response({
            "message": "Task deleted successfully"
        })
    else:
        return error_response("Failed to delete task", 500)


def get_my_tasks(user_id):
    """Get all tasks assigned to the logged-in user with project and owner details"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    tasks_list = Task.find_by_assignee(user_id)
    
    # Enrich tasks with project name and owner name
    from database import db
    for task in tasks_list:
        task["_id"] = str(task["_id"])
        task["created_at"] = datetime_to_iso(task["created_at"])
        task["updated_at"] = datetime_to_iso(task["updated_at"])
        # Convert moved_to_backlog_at if present
        if "moved_to_backlog_at" in task and task["moved_to_backlog_at"]:
            task["moved_to_backlog_at"] = datetime_to_iso(task["moved_to_backlog_at"])
        
        # Get project details
        project = db.projects.find_one({"_id": ObjectId(task["project_id"])})
        if project:
            task["project_name"] = project.get("name", "Unknown Project")
            
            # Get owner details
            owner = db.users.find_one({"_id": ObjectId(project["user_id"])})
            if owner:
                task["created_by_name"] = owner.get("name", "Unknown")
                task["created_by_email"] = owner.get("email", "")
    
    return success_response({
        "tasks": tasks_list,
        "count": len(tasks_list)
    })


def add_label_to_task(task_id, body_str, user_id):
    """Add a label to a task"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    try:
        data = json.loads(body_str)
    except:
        return error_response("Invalid JSON", 400)
    
    # Validate required fields
    if "label" not in data:
        return error_response("Label is required", 400)
    
    label = data["label"]
    
    # Validate label
    is_valid, error_msg = validate_label(label)
    if not is_valid:
        return error_response(f"Invalid label: {error_msg}", 400)
    
    # Normalize label
    label = normalize_label(label)
    
    # Check if task exists
    task = Task.find_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Check if user is member of the project
    if not Project.is_member(task["project_id"], user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    # Get user info for activity log
    current_user = User.find_by_id(user_id)
    user_name = current_user["name"] if current_user else "Unknown"
    
    # Add label
    success = Task.add_label(task_id, label)
    
    if success:
        # Add activity log for label addition
        activity_data = {
            "user_id": user_id,
            "user_name": user_name,
            "action": "label_add",
            "label": label,
            "old_value": None,
            "new_value": label
        }
        Task.add_activity(task_id, activity_data)
        
        return success_response({
            "message": "Label added successfully",
            "label": label
        })
    else:
        return success_response({
            "message": "Label already exists on this task",
            "label": label
        })


def remove_label_from_task(task_id, label, user_id):
    """Remove a label from a task"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    # Normalize label
    label = normalize_label(label)
    
    # Check if task exists
    task = Task.find_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Check if user is member of the project
    if not Project.is_member(task["project_id"], user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    # Get user info for activity log
    current_user = User.find_by_id(user_id)
    user_name = current_user["name"] if current_user else "Unknown"
    
    # Remove label
    success = Task.remove_label(task_id, label)
    
    if success:
        # Add activity log for label removal
        activity_data = {
            "user_id": user_id,
            "user_name": user_name,
            "action": "label_remove",
            "label": label,
            "old_value": label,
            "new_value": None
        }
        Task.add_activity(task_id, activity_data)
        
        return success_response({
            "message": "Label removed successfully",
            "label": label
        })
    else:
        return error_response("Label not found on this task", 404)


def get_project_labels(project_id, user_id):
    """Get all unique labels used in a project"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    # Check if project exists
    project = Project.find_by_id(project_id)
    if not project:
        return error_response("Project not found", 404)
    
    # Check if user is member or owner
    if not Project.is_member(project_id, user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    # Get all tasks for project
    tasks_list = Task.find_by_project(project_id)
    
    # Collect all unique labels
    labels = set()
    for task in tasks_list:
        if "labels" in task and task["labels"]:
            labels.update(task["labels"])
    
    return success_response({
        "labels": sorted(list(labels))
    })

def add_attachment_to_task(task_id, body_str, user_id):
    """Add an attachment (URL or base64 document) to a task"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    try:
        data = json.loads(body_str)
    except:
        return error_response("Invalid JSON", 400)
    
    # Validate required fields
    required = ["name", "url"]
    validation_error = validate_required_fields(data, required)
    if validation_error:
        return error_response(validation_error, 400)
    
    # Validate URL format (allow http/https URLs or base64 data URLs)
    url = data["url"]
    is_base64 = url.startswith("data:")
    is_http_url = url.startswith(("http://", "https://"))
    
    if not is_base64 and not is_http_url:
        return error_response("URL must start with http://, https://, or be a base64 data URL", 400)
    
    # Validate base64 size (max 10MB)
    if is_base64:
        # Rough estimate: base64 is ~1.37x original size
        estimated_size = len(url) * 0.75  # Convert back to approximate original size
        max_size = 10 * 1024 * 1024  # 10MB
        if estimated_size > max_size:
            return error_response("File size exceeds 10MB limit", 400)
    
    # Validate name length
    name = data["name"].strip()
    if len(name) < 1 or len(name) > 100:
        return error_response("Attachment name must be 1-100 characters", 400)
    
    # Check if task exists
    task = Task.find_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Check if user is member of the project
    if not Project.is_member(task["project_id"], user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    # Get user info
    user = User.find_by_id(user_id)
    if not user:
        return error_response("User not found", 404)
    
    # Add attachment with optional file metadata
    attachment_data = {
        "name": name,
        "url": url,
        "added_by": user_id,
        "added_by_name": user["name"]
    }
    
    # Add file metadata if present (for documents)
    if "fileName" in data:
        attachment_data["fileName"] = data["fileName"]
    if "fileType" in data:
        attachment_data["fileType"] = data["fileType"]
    if "fileSize" in data:
        attachment_data["fileSize"] = data["fileSize"]
    
    success, attachment = Task.add_attachment(task_id, attachment_data)
    
    if success:
        # Add activity log for attachment addition
        attachment_type = "link" if url.startswith(("http://", "https://")) else "document"
        activity_data = {
            "user_id": user_id,
            "user_name": user["name"],
            "action": "attachment_add",
            "attachment_name": name,
            "attachment_type": attachment_type,
            "old_value": None,
            "new_value": name
        }
        Task.add_activity(task_id, activity_data)
        
        return success_response({
            "message": "Attachment added successfully",
            "attachment": attachment
        })
    else:
        return error_response("Failed to add attachment", 500)


def remove_attachment_from_task(task_id, body_str, user_id):
    """Remove an attachment from a task"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    try:
        data = json.loads(body_str)
    except:
        return error_response("Invalid JSON", 400)
    
    # Validate required fields
    if "url" not in data:
        return error_response("URL is required", 400)
    
    url = data["url"]
    
    # Check if task exists
    task = Task.find_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Check if user is member of the project
    if not Project.is_member(task["project_id"], user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    # Find attachment name before removing
    attachment_name = "Unknown"
    if "attachments" in task:
        for att in task["attachments"]:
            if att.get("url") == url:
                attachment_name = att.get("name", "Unknown")
                break
    
    # Get user info for activity log
    current_user = User.find_by_id(user_id)
    user_name = current_user["name"] if current_user else "Unknown"
    
    # Remove attachment
    success = Task.remove_attachment(task_id, url)
    
    if success:
        # Add activity log for attachment removal
        activity_data = {
            "user_id": user_id,
            "user_name": user_name,
            "action": "attachment_remove",
            "attachment_name": attachment_name,
            "old_value": attachment_name,
            "new_value": None
        }
        Task.add_activity(task_id, activity_data)
        
        return success_response({
            "message": "Attachment removed successfully"
        })
    else:
        return error_response("Attachment not found on this task", 404)


def add_link_to_task(task_id, body_str, user_id):
    """Add a link to another task"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    try:
        data = json.loads(body_str)
    except:
        return error_response("Invalid JSON", 400)
    
    # Accept either linked_task_id (MongoDB _id) or linked_ticket_id (TMS-001, etc.)
    linked_task_id = data.get("linked_task_id")
    linked_ticket_id = data.get("linked_ticket_id")
    link_type = data.get("type")
    
    if not link_type:
        return error_response("Missing required field: type", 400)
    
    if not linked_task_id and not linked_ticket_id:
        return error_response("Missing required field: linked_task_id or linked_ticket_id", 400)
    
    # Validate link type
    valid_link_types = ["blocks", "blocked-by", "relates-to", "duplicates"]
    if link_type not in valid_link_types:
        return error_response(f"Link type must be one of: {', '.join(valid_link_types)}", 400)
    
    # Check if source task exists
    task = Task.find_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Find linked task by ticket_id or task_id
    linked_task = None
    if linked_ticket_id:
        # Search by ticket_id (e.g., TMS-001)
        linked_task = Task.find_by_ticket_id(linked_ticket_id)
        if not linked_task:
            return error_response(f"Task with ticket ID '{linked_ticket_id}' not found", 404)
        linked_task_id = str(linked_task["_id"])
    else:
        # Search by MongoDB _id
        linked_task = Task.find_by_id(linked_task_id)
        if not linked_task:
            return error_response("Linked task not found", 404)
    
    # Check if user is member of both projects
    if not Project.is_member(task["project_id"], user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    if not Project.is_member(linked_task["project_id"], user_id):
        return error_response("Access denied. You are not a member of the linked task's project.", 403)
    
    # Prevent self-linking
    if task_id == linked_task_id:
        return error_response("Cannot link a task to itself", 400)
    
    # Check if link already exists
    if "links" in task:
        for link in task["links"]:
            if link["linked_task_id"] == linked_task_id and link["type"] == link_type:
                return error_response("This link already exists", 400)
    
    # Add link
    link_data = {
        "type": link_type,
        "linked_task_id": linked_task_id,
        "linked_ticket_id": linked_task.get("ticket_id", "")
    }
    
    success, link = Task.add_link(task_id, link_data)
    
    if success:
        # Log activity for link addition
        user = User.find_by_id(user_id)
        if user:
            activity = {
                "action": "link_add",
                "user_name": user.get("name", "Unknown"),
                "link_type": link_type,
                "linked_ticket_id": linked_task.get("ticket_id", ""),
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            }
            Task.add_activity(task_id, activity)
        
        # Create reverse link automatically for bidirectional relationships
        reverse_link_map = {
            "blocks": "blocked-by",
            "blocked-by": "blocks",
            "relates-to": "relates-to",
            "duplicates": "duplicated-by"
        }
        
        if link_type in reverse_link_map:
            reverse_link_type = reverse_link_map[link_type]
            reverse_link_data = {
                "type": reverse_link_type,
                "linked_task_id": task_id,
                "linked_ticket_id": task.get("ticket_id", "")
            }
            # Add reverse link (ignore if it fails)
            Task.add_link(linked_task_id, reverse_link_data)
        
        return success_response({
            "message": "Link added successfully",
            "link": link
        })
    else:
        return error_response("Failed to add link", 500)


def remove_link_from_task(task_id, body_str, user_id):
    """Remove a link from a task"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    try:
        data = json.loads(body_str)
    except:
        return error_response("Invalid JSON", 400)
    
    # Validate required fields
    required = ["linked_task_id", "type"]
    validation_error = validate_required_fields(data, required)
    if validation_error:
        return error_response(validation_error, 400)
    
    linked_task_id = data["linked_task_id"]
    link_type = data["type"]
    
    # Check if task exists
    task = Task.find_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Check if user is member of the project
    if not Project.is_member(task["project_id"], user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    # Remove link
    success = Task.remove_link(task_id, linked_task_id, link_type)
    
    if success:
        # Log activity for link removal
        user = User.find_by_id(user_id)
        if user:
            activity = {
                "action": "link_remove",
                "user_name": user.get("name", "Unknown"),
                "link_type": link_type,
                "linked_ticket_id": linked_task_id,
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            }
            Task.add_activity(task_id, activity)
        
        # Remove reverse link automatically
        reverse_link_map = {
            "blocks": "blocked-by",
            "blocked-by": "blocks",
            "relates-to": "relates-to",
            "duplicates": "duplicated-by"
        }
        
        if link_type in reverse_link_map:
            reverse_link_type = reverse_link_map[link_type]
            # Find the linked task by ticket_id to get its _id
            linked_task = Task.find_by_ticket_id(linked_task_id)
            if linked_task:
                # Remove reverse link (ignore if it fails)
                Task.remove_link(linked_task["_id"], task["ticket_id"], reverse_link_type)
        
        return success_response({
            "message": "Link removed successfully"
        })
    else:
        return error_response("Link not found or failed to remove", 404)


def approve_task(task_id, user_id):
    """Approve and close a Done task - only project owner can approve"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    # Check if task exists
    task = Task.find_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Get project and verify user is the owner
    project = Project.find_by_id(task["project_id"])
    if not project:
        return error_response("Project not found", 404)
    
    if project["user_id"] != user_id:
        return error_response("Only project owner can approve and close tasks", 403)
    
    # Check if task is in Done status
    if task.get("status") != "Done":
        return error_response("Only tasks with 'Done' status can be approved", 400)
    
    # Get user info for approval metadata
    current_user = User.find_by_id(user_id)
    user_name = current_user["name"] if current_user else "Unknown"
    
    # Update task to Closed status with approval metadata
    update_data = {
        "status": "Closed",
        "approved_by": user_id,
        "approved_by_name": user_name,
        "approved_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "closed_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),  # Add closed_at as well
        "in_backlog": False,
        "moved_to_backlog_at": None
    }
    
    success = Task.update(task_id, update_data)
    
    if success:
        # Add activity log for approval
        activity_data = {
            "user_id": user_id,
            "user_name": user_name,
            "action": "approved",
            "comment": "Task approved and closed",
            "old_value": "Done",
            "new_value": "Closed"
        }
        Task.add_activity(task_id, activity_data)
        
        # Get updated task and convert for JSON serialization
        updated_task = Task.find_by_id(task_id)
        if updated_task:
            updated_task["_id"] = str(updated_task["_id"])
            # Convert project_id if present
            if "project_id" in updated_task:
                updated_task["project_id"] = str(updated_task["project_id"])
            # Convert datetime fields (datetime_to_iso handles strings)
            for field in ["created_at", "updated_at", "due_date", "approved_at"]:
                if field in updated_task and updated_task[field]:
                    updated_task[field] = datetime_to_iso(updated_task[field])
        
        return success_response({
            "message": "Task approved and closed successfully",
            "task": updated_task
        })
    else:
        return error_response("Failed to approve task", 500)


def get_done_tasks_for_approval(project_id, user_id):
    """Get all Done tasks awaiting approval - only for project owner"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    # Get project and verify user is the owner
    project = Project.find_by_id(project_id)
    if not project:
        return error_response("Project not found", 404)
    
    if project["user_id"] != user_id:
        return error_response("Only project owner can view tasks awaiting approval", 403)
    
    # Get all tasks with Done status for this project
    from database import tasks
    done_tasks_cursor = tasks.find({
        "project_id": project_id,
        "status": "Done"
    }).sort("updated_at", -1)
    
    # Convert ObjectId and datetime to JSON-serializable formats
    done_tasks = []
    for task in done_tasks_cursor:
        task["_id"] = str(task["_id"])
        # Convert project_id if present
        if "project_id" in task:
            task["project_id"] = str(task["project_id"])
        # Convert datetime fields (datetime_to_iso handles strings)
        for field in ["created_at", "updated_at", "due_date"]:
            if field in task and task[field]:
                task[field] = datetime_to_iso(task[field])
        done_tasks.append(task)
    
    return success_response({
        "tasks": done_tasks,
        "count": len(done_tasks)
    })


def get_all_pending_approval_tasks(user_id):
    """
    Get all tasks pending approval across all projects
    - For admins: Tasks with 'Done' status from projects they own
    - For members: Tasks with 'Done' status that are assigned to them
    """
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    from database import db
    
    # Get user info
    user = User.find_by_id(user_id)
    if not user:
        return error_response("User not found", 404)
    
    user_role = user.get("role", "member")
    
    pending_tasks = []
    
    if user_role in ["admin", "super-admin"]:
        # Admin: Get all Done tasks from projects they own
        owned_projects = list(db.projects.find(
            {"user_id": user_id},  # user_id is stored as string in projects
            {"_id": 1, "name": 1}
        ))
        
        project_ids = [str(p["_id"]) for p in owned_projects]  # Convert to string
        project_names = {str(p["_id"]): p["name"] for p in owned_projects}
        
        # Get all Done tasks from owned projects (project_id is stored as string in tasks)
        tasks_cursor = db.tasks.find({
            "project_id": {"$in": project_ids},
            "status": "Done"
        }).sort("updated_at", -1)
        
        for task in tasks_cursor:
            task["_id"] = str(task["_id"])
            task["project_id"] = str(task["project_id"])
            task["project_name"] = project_names.get(task["project_id"], "Unknown")
            task["can_approve"] = True  # Admin can approve
            
            # Convert ALL datetime fields to ISO format
            for field in ["created_at", "updated_at", "due_date", "approved_at", "closed_at"]:
                if field in task and task[field]:
                    task[field] = datetime_to_iso(task[field])
            
            # Get assignee name if available
            if task.get("assignee_id"):
                assignee = User.find_by_id(task["assignee_id"])
                task["assignee_name"] = assignee["name"] if assignee else "Unknown"
            
            pending_tasks.append(task)
    
    else:
        # Member: Get Done tasks assigned to them
        tasks_cursor = db.tasks.find({
            "assignee_id": user_id,
            "status": "Done"
        }).sort("updated_at", -1)
        
        for task in tasks_cursor:
            task["_id"] = str(task["_id"])
            task["project_id"] = str(task["project_id"])
            
            # Get project name
            project = Project.find_by_id(task["project_id"])
            task["project_name"] = project["name"] if project else "Unknown"
            task["can_approve"] = False  # Member cannot approve
            
            # Convert ALL datetime fields to ISO format
            for field in ["created_at", "updated_at", "due_date", "approved_at", "closed_at"]:
                if field in task and task[field]:
                    task[field] = datetime_to_iso(task[field])
            
            task["assignee_name"] = user["name"]
            
            pending_tasks.append(task)
    
    return success_response({
        "tasks": pending_tasks,
        "count": len(pending_tasks),
        "user_role": user_role
    })


def get_all_closed_tasks(user_id):
    """
    Get all closed (approved) tasks
    - For admins: Closed tasks from projects they own
    - For members: Closed tasks assigned to them
    """
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    from database import db
    
    # Get user info
    user = User.find_by_id(user_id)
    if not user:
        return error_response("User not found", 404)
    
    user_role = user.get("role", "member")
    
    closed_tasks = []
    
    if user_role in ["admin", "super-admin"]:
        # Admin: Get all Closed tasks from projects they own
        owned_projects = list(db.projects.find(
            {"user_id": user_id},  # user_id is stored as string in projects
            {"_id": 1, "name": 1}
        ))
        
        project_ids = [str(p["_id"]) for p in owned_projects]  # Convert to string
        project_names = {str(p["_id"]): p["name"] for p in owned_projects}
        
        # Get all Closed tasks from owned projects (project_id is stored as string in tasks)
        tasks_cursor = db.tasks.find({
            "project_id": {"$in": project_ids},
            "status": "Closed"
        }).sort("closed_at", -1)
        
        for task in tasks_cursor:
            task["_id"] = str(task["_id"])
            task["project_id"] = str(task["project_id"])
            task["project_name"] = project_names.get(task["project_id"], "Unknown")
            
            # Convert ALL datetime fields to ISO format (including sprint-related fields)
            for field in ["created_at", "updated_at", "due_date", "closed_at", "approved_at", "moved_to_backlog_at", "moved_to_sprint_at", "removed_from_sprint_at"]:
                if field in task and task[field]:
                    task[field] = datetime_to_iso(task[field])
            
            # Get assignee name if available
            if task.get("assignee_id"):
                assignee = User.find_by_id(task["assignee_id"])
                task["assignee_name"] = assignee["name"] if assignee else "Unknown"
            
            # Get approver name
            if task.get("approved_by"):
                approver = User.find_by_id(task["approved_by"])
                task["approved_by_name"] = approver["name"] if approver else "Unknown"
            
            closed_tasks.append(task)
    
    else:
        # Member: Get Closed tasks assigned to them
        tasks_cursor = db.tasks.find({
            "assignee_id": user_id,
            "status": "Closed"
        }).sort("closed_at", -1)
        
        for task in tasks_cursor:
            task["_id"] = str(task["_id"])
            task["project_id"] = str(task["project_id"])
            
            # Get project name
            project = Project.find_by_id(task["project_id"])
            task["project_name"] = project["name"] if project else "Unknown"
            
            # Convert ALL datetime fields to ISO format (including sprint-related fields)
            for field in ["created_at", "updated_at", "due_date", "closed_at", "approved_at", "moved_to_backlog_at", "moved_to_sprint_at", "removed_from_sprint_at"]:
                if field in task and task[field]:
                    task[field] = datetime_to_iso(task[field])
            
            task["assignee_name"] = user["name"]
            
            # Get approver name
            if task.get("approved_by"):
                approver = User.find_by_id(task["approved_by"])
                task["approved_by_name"] = approver["name"] if approver else "Unknown"
            
            closed_tasks.append(task)
    
    return success_response({
        "tasks": closed_tasks,
        "count": len(closed_tasks),
        "user_role": user_role
    })

# Add this to task_controller.py (at the end or appropriate place)

def add_task_comment(task_id, body_str, user_id):
    """Add a comment to a task"""
    if not user_id:
        return error_response("Unauthorized. Please login.", 401)
    
    try:
        data = json.loads(body_str)
    except:
        return error_response("Invalid JSON", 400)
    
    # Validate required fields
    required = ["comment"]
    validation_error = validate_required_fields(data, required)
    if validation_error:
        return error_response(validation_error, 400)
    
    comment = data["comment"].strip()
    if len(comment) < 1:
        return error_response("Comment cannot be empty", 400)
    
    # Check if task exists
    task = Task.find_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Check if user is member of the project
    if not Project.is_member(task["project_id"], user_id):
        return error_response("Access denied. You are not a member of this project.", 403)
    
    # Get user info for activity log
    current_user = User.find_by_id(user_id)
    user_name = current_user["name"] if current_user else "Unknown"
    
    # Add activity log for comment
    activity_data = {
        "user_id": user_id,
        "user_name": user_name,
        "action": "comment",
        "comment": comment,
        "old_value": None,
        "new_value": None
    }
    Task.add_activity(task_id, activity_data)
    
    return success_response({
        "message": "Comment added successfully"
    }, 201)
