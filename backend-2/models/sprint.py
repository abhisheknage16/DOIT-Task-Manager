"""
Sprint Model
Handles sprint data and operations in MongoDB
"""

from database import sprints
from bson import ObjectId
from datetime import datetime, timezone


class Sprint:
    @staticmethod
    def create(sprint_data):
        """Create a new sprint with all required fields"""
        sprint = {
            "name": sprint_data.get("name"),
            "goal": sprint_data.get("goal", ""),
            "project_id": sprint_data.get("project_id"),
            "start_date": sprint_data.get(
                "start_date"
            ),  # ISO format date string (YYYY-MM-DD)
            "end_date": sprint_data.get(
                "end_date"
            ),  # ISO format date string (YYYY-MM-DD)
            "status": sprint_data.get(
                "status", "planned"
            ),  # planned, active, completed
            "created_by": sprint_data.get("created_by"),  # User ID of creator
            "completed_at": None,  # Timestamp when sprint was completed
            "total_tasks_snapshot": 0,  # Total tasks when completed
            "completed_tasks_snapshot": 0,  # Completed tasks when completed
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }

        result = sprints.insert_one(sprint)
        sprint["_id"] = result.inserted_id
        return sprint

    @staticmethod
    def find_by_id(sprint_id):
        """Find sprint by ID with safe field handling"""
        try:
            sprint = sprints.find_one({"_id": ObjectId(sprint_id)})

            # Ensure all expected fields exist (for backward compatibility)
            if sprint:
                sprint.setdefault("completed_at", None)
                sprint.setdefault("total_tasks_snapshot", 0)
                sprint.setdefault("completed_tasks_snapshot", 0)
                sprint.setdefault("goal", "")
                sprint.setdefault("start_date", None)
                sprint.setdefault("end_date", None)
                sprint.setdefault("status", "planned")

            return sprint
        except Exception as e:
            print(f"Error finding sprint: {e}")
            return None

    @staticmethod
    def find_by_project(project_id):
        """Get all sprints for a project with safe field handling"""
        sprint_list = list(
            sprints.find({"project_id": project_id}).sort("created_at", -1)
        )

        # Ensure all expected fields exist for each sprint
        for sprint in sprint_list:
            sprint.setdefault("completed_at", None)
            sprint.setdefault("total_tasks_snapshot", 0)
            sprint.setdefault("completed_tasks_snapshot", 0)
            sprint.setdefault("goal", "")
            sprint.setdefault("start_date", None)
            sprint.setdefault("end_date", None)
            sprint.setdefault("status", "planned")

        return sprint_list

    @staticmethod
    def find_active_by_project(project_id):
        """Get active sprint for a project"""
        sprint = sprints.find_one({"project_id": project_id, "status": "active"})

        # Ensure all expected fields exist
        if sprint:
            sprint.setdefault("completed_at", None)
            sprint.setdefault("total_tasks_snapshot", 0)
            sprint.setdefault("completed_tasks_snapshot", 0)
            sprint.setdefault("goal", "")
            sprint.setdefault("start_date", None)
            sprint.setdefault("end_date", None)

        return sprint

    @staticmethod
    def find_by_name(project_id, sprint_name):
        """Find sprint by name within a project (case-insensitive)"""
        sprint = sprints.find_one(
            {
                "project_id": project_id,
                "name": {"$regex": f"^{sprint_name}$", "$options": "i"},
            }
        )

        # Ensure all expected fields exist
        if sprint:
            sprint.setdefault("completed_at", None)
            sprint.setdefault("total_tasks_snapshot", 0)
            sprint.setdefault("completed_tasks_snapshot", 0)
            sprint.setdefault("goal", "")
            sprint.setdefault("start_date", None)
            sprint.setdefault("end_date", None)
            sprint.setdefault("status", "planned")

        return sprint

    @staticmethod
    def update(sprint_id, update_data):
        """Update sprint details"""
        update_data["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

        result = sprints.update_one({"_id": ObjectId(sprint_id)}, {"$set": update_data})

        return result.modified_count > 0

    @staticmethod
    def delete(sprint_id):
        """Delete a sprint and unlink tasks"""
        # First, remove sprint_id from all associated tasks
        from database import db

        db.tasks.update_many(
            {"sprint_id": str(sprint_id)}, {"$unset": {"sprint_id": ""}}
        )

        # Then delete the sprint
        result = sprints.delete_one({"_id": ObjectId(sprint_id)})
        return result.deleted_count > 0

    @staticmethod
    def delete_by_project(project_id):
        """Delete all sprints for a project"""
        # First, unlink all tasks from these sprints
        from database import db

        sprint_ids = [str(s["_id"]) for s in sprints.find({"project_id": project_id})]

        if sprint_ids:
            db.tasks.update_many(
                {"sprint_id": {"$in": sprint_ids}}, {"$unset": {"sprint_id": ""}}
            )

        # Then delete all sprints
        result = sprints.delete_many({"project_id": project_id})
        return result.deleted_count

    @staticmethod
    def start_sprint(sprint_id):
        """Start a sprint - make it active"""
        # First, check if there's already an active sprint in this project
        sprint = Sprint.find_by_id(sprint_id)
        if not sprint:
            return False

        # Set any other active sprints in this project to planned
        sprints.update_many(
            {
                "project_id": sprint["project_id"],
                "status": "active",
                "_id": {"$ne": ObjectId(sprint_id)},
            },
            {"$set": {"status": "planned"}},
        )

        # Activate this sprint
        update_data = {
            "status": "active",
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }

        result = sprints.update_one({"_id": ObjectId(sprint_id)}, {"$set": update_data})

        return result.modified_count > 0

    @staticmethod
    def complete_sprint(sprint_id, total_tasks=0, completed_tasks=0):
        """Complete a sprint and snapshot task counts"""
        update_data = {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "total_tasks_snapshot": total_tasks,
            "completed_tasks_snapshot": completed_tasks,
        }

        result = sprints.update_one({"_id": ObjectId(sprint_id)}, {"$set": update_data})

        return result.modified_count > 0

    @staticmethod
    def get_sprint_stats(sprint_id):
        """Get statistics for a sprint"""
        from database import db

        # Count tasks in this sprint
        total_tasks = db.tasks.count_documents({"sprint_id": str(sprint_id)})
        completed_tasks = db.tasks.count_documents(
            {"sprint_id": str(sprint_id), "status": "Done"}
        )
        in_progress_tasks = db.tasks.count_documents(
            {"sprint_id": str(sprint_id), "status": "In Progress"}
        )
        todo_tasks = db.tasks.count_documents(
            {"sprint_id": str(sprint_id), "status": "To Do"}
        )

        # Calculate completion percentage - handle division by zero
        completion_percentage = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "todo_tasks": todo_tasks,
            "completion_percentage": round(completion_percentage, 1),
        }

    @staticmethod
    def add_task_to_sprint(sprint_id, task_id):
        """Add a task to a sprint"""
        from database import db

        result = db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {
                "$set": {
                    "sprint_id": str(sprint_id),
                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                }
            },
        )

        return result.modified_count > 0

    @staticmethod
    def remove_task_from_sprint(task_id):
        """Remove a task from its sprint"""
        from database import db

        result = db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {
                "$unset": {"sprint_id": ""},
                "$set": {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None)},
            },
        )

        return result.modified_count > 0

    @staticmethod
    def get_sprint_tasks(sprint_id):
        """Get all tasks in a sprint"""
        from database import db

        tasks = list(
            db.tasks.find({"sprint_id": str(sprint_id)}).sort("created_at", -1)
        )
        return tasks

    @staticmethod
    def migrate_add_missing_fields():
        """
        Migration helper: Add missing fields to existing sprints
        Run this once to update old sprints
        """
        result = sprints.update_many(
            {"completed_at": {"$exists": False}},
            {
                "$set": {
                    "completed_at": None,
                    "total_tasks_snapshot": 0,
                    "completed_tasks_snapshot": 0,
                }
            },
        )

        print(f"✅ Migrated {result.modified_count} sprints (added missing fields)")

        # Also ensure start_date and end_date exist
        result2 = sprints.update_many(
            {"start_date": {"$exists": False}},
            {"$set": {"start_date": None, "end_date": None}},
        )

        print(f"✅ Migrated {result2.modified_count} sprints (added date fields)")

        # Ensure goal exists
        result3 = sprints.update_many(
            {"goal": {"$exists": False}}, {"$set": {"goal": ""}}
        )

        print(f"✅ Migrated {result3.modified_count} sprints (added goal field)")

        return result.modified_count + result2.modified_count + result3.modified_count
