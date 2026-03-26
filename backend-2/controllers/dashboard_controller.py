# """
# Dashboard Controller - Analytics and Reports
# """

# import json
# from datetime import datetime, timedelta, timezone
# from bson import ObjectId
# from utils.auth_utils import verify_token
# from database import db


# def serialize_datetime(obj):
#     """Convert datetime objects to ISO format strings"""
#     if isinstance(obj, datetime):
#         return obj.isoformat()
#     return obj


# def convert_dates_to_strings(data):
#     """Recursively convert all datetime objects in a data structure to strings"""
#     if isinstance(data, dict):
#         return {key: convert_dates_to_strings(value) for key, value in data.items()}
#     elif isinstance(data, list):
#         return [convert_dates_to_strings(item) for item in data]
#     elif isinstance(data, datetime):
#         return data.isoformat()
#     else:
#         return data


# def get_dashboard_analytics(user_id):
#     """
#     Get comprehensive dashboard analytics for the logged-in user
#     Returns: task stats, project stats, upcoming deadlines, recent activity
#     OPTIMIZED: Uses MongoDB aggregation and efficient queries
#     """
#     try:
#         # Verify authentication
#         if not user_id:
#             return {
#                 "success": False,
#                 "status": 401,
#                 "headers": [("Content-Type", "application/json")],
#                 "body": json.dumps(
#                     {"success": False, "error": "Authentication required"}
#                 ),
#             }

#         from models.user import User

#         user = User.find_by_id(user_id)
#         if not user:
#             return {
#                 "success": False,
#                 "status": 404,
#                 "headers": [("Content-Type", "application/json")],
#                 "body": json.dumps({"success": False, "error": "User not found"}),
#             }

#         user_role = user.get("role")

#         # Get user's projects (owned or member of)
#         projects_collection = db["projects"]
#         tasks_collection = db["tasks"]

#         # ⚡ OPTIMIZED: Find projects where user is owner or member
#         user_projects = list(
#             projects_collection.find(
#                 {
#                     "$or": [
#                         {"user_id": user_id},
#                         {"members": {"$elemMatch": {"user_id": user_id}}},
#                     ]
#                 },
#                 {"_id": 1, "name": 1, "status": 1, "user_id": 1},
#             )
#         )  # Only fetch needed fields

#         project_ids = [p["_id"] for p in user_projects]
#         project_ids_str = [str(pid) for pid in project_ids]

#         print(f"[DASHBOARD] Found {len(user_projects)} projects")

#         # ⚡ OPTIMIZED: Use aggregation for task statistics
#         # Get tasks assigned to user using aggregation pipeline
#         my_tasks_pipeline = [
#             {"$match": {"assignee_id": user_id}},
#             {
#                 "$project": {
#                     "_id": 1,
#                     "status": 1,
#                     "priority": 1,
#                     "due_date": 1,
#                     "project_id": 1,
#                     "title": 1,
#                     "updated_at": 1,
#                 }
#             },
#         ]

#         my_tasks = list(tasks_collection.aggregate(my_tasks_pipeline))

#         print(f"[DASHBOARD] Found {len(my_tasks)} tasks assigned to user")

#         # Calculate task statistics efficiently
#         now = datetime.now(timezone.utc)
#         overdue_count = 0
#         pending_count = 0
#         in_progress_count = 0
#         done_count = 0
#         closed_count = 0

#         for task in my_tasks:
#             status = task.get("status")
#             if status == "In Progress":
#                 in_progress_count += 1
#             elif status == "Done":
#                 done_count += 1
#             elif status == "Closed":
#                 closed_count += 1

#             # Count as pending if not done/closed
#             if status not in ["Done", "Closed"]:
#                 pending_count += 1

#                 # Check if overdue
#                 if task.get("due_date"):
#                     due_date = task.get("due_date")
#                     if isinstance(due_date, str):
#                         try:
#                             due_date = datetime.fromisoformat(
#                                 due_date.replace("Z", "+00:00")
#                             )
#                         except:
#                             continue
#                     if due_date < now:
#                         overdue_count += 1

#         task_stats = {
#             "total": len(my_tasks),
#             "pending": pending_count,
#             "in_progress": in_progress_count,
#             "done": done_count,
#             "closed": closed_count,
#             "overdue": overdue_count,
#         }

#         # Calculate project statistics
#         owned_count = sum(1 for p in user_projects if p.get("user_id") == user_id)
#         member_count = len(user_projects) - owned_count
#         active_count = sum(1 for p in user_projects if p.get("status") == "Active")
#         completed_count = sum(
#             1 for p in user_projects if p.get("status") == "Completed"
#         )

#         project_stats = {
#             "total": len(user_projects),
#             "owned": owned_count,
#             "member_of": member_count,
#             "active": active_count,
#             "completed": completed_count,
#         }

#         # Calculate task distribution by priority (only non-completed tasks)
#         priority_distribution = {"High": 0, "Medium": 0, "Low": 0}
#         for task in my_tasks:
#             if task.get("status") not in ["Done", "Closed"]:
#                 priority = task.get("priority", "Low")
#                 if priority in priority_distribution:
#                     priority_distribution[priority] += 1

#         # Calculate task distribution by status
#         status_distribution = {"To Do": 0, "In Progress": 0, "Done": 0, "Closed": 0}
#         for task in my_tasks:
#             status = task.get("status", "To Do")
#             if status in status_distribution:
#                 status_distribution[status] += 1

#         # Get upcoming deadlines (next 7 days) - limit to 15 tasks
#         end_of_week = now + timedelta(days=7)
#         upcoming_deadlines = []

#         # Create a map for quick project lookup
#         project_map = {str(p["_id"]): p.get("name", "Unknown") for p in user_projects}

#         for task in my_tasks:
#             if task.get("status") not in ["Done", "Closed"] and task.get("due_date"):
#                 due_date = task.get("due_date")
#                 if isinstance(due_date, str):
#                     try:
#                         due_date = datetime.fromisoformat(
#                             due_date.replace("Z", "+00:00")
#                         )
#                     except:
#                         continue

#                 if due_date <= end_of_week:
#                     project_name = project_map.get(
#                         str(task.get("project_id")), "Unknown"
#                     )
#                     due_date_str = (
#                         due_date.isoformat()
#                         if isinstance(due_date, datetime)
#                         else str(due_date)
#                     )

#                     upcoming_deadlines.append(
#                         {
#                             "task_id": str(task["_id"]),
#                             "title": task.get("title", ""),
#                             "due_date": due_date_str,
#                             "priority": task.get("priority", "Low"),
#                             "status": task.get("status", "To Do"),
#                             "project_id": str(task.get("project_id", "")),
#                             "project_name": project_name,
#                             "days_until": (due_date - now).days,
#                         }
#                     )

#         # Sort by due date and limit to 15
#         upcoming_deadlines.sort(key=lambda x: x["due_date"])
#         upcoming_deadlines = upcoming_deadlines[:15]

#         # ⚡ OPTIMIZED: Get project progress using aggregation
#         project_progress = []

#         if project_ids_str:
#             # Use aggregation to count tasks per project efficiently
#             progress_pipeline = [
#                 {"$match": {"project_id": {"$in": project_ids_str}}},
#                 {
#                     "$group": {
#                         "_id": "$project_id",
#                         "total": {"$sum": 1},
#                         "closed": {
#                             "$sum": {"$cond": [{"$eq": ["$status", "Closed"]}, 1, 0]}
#                         },
#                     }
#                 },
#             ]

#             progress_results = list(tasks_collection.aggregate(progress_pipeline))

#             # Build progress data
#             for result in progress_results:
#                 project_id = result["_id"]
#                 total = result["total"]
#                 closed = result["closed"]

#                 project_name = project_map.get(project_id, "Unknown")

#                 if total > 0:
#                     progress_percentage = (closed / total) * 100
#                 else:
#                     progress_percentage = 0

#                 project_progress.append(
#                     {
#                         "project_id": project_id,
#                         "project_name": project_name,
#                         "total_tasks": total,
#                         "completed_tasks": closed,
#                         "progress_percentage": round(progress_percentage, 1),
#                     }
#                 )

#         # Sort by progress percentage
#         project_progress.sort(key=lambda x: x["progress_percentage"], reverse=True)
#         project_progress = project_progress[:10]  # Top 10 projects

#         print(
#             f"[DASHBOARD] Project progress calculated for {len(project_progress)} projects"
#         )

#         # Get recent activity (last 10 activities) - already have my_tasks sorted
#         recent_activities = []
#         sorted_tasks = sorted(
#             my_tasks, key=lambda x: x.get("updated_at", ""), reverse=True
#         )[:10]

#         for task in sorted_tasks:
#             project_name = project_map.get(str(task.get("project_id")), "Unknown")

#             updated_at = task.get("updated_at", "")
#             if isinstance(updated_at, datetime):
#                 updated_at = updated_at.isoformat()

#             recent_activities.append(
#                 {
#                     "task_id": str(task["_id"]),
#                     "title": task.get("title", ""),
#                     "status": task.get("status", ""),
#                     "priority": task.get("priority", ""),
#                     "project_name": project_name,
#                     "project_id": str(task.get("project_id", "")),
#                     "updated_at": updated_at,
#                 }
#             )

#         # Prepare response
#         analytics = {
#             "task_stats": task_stats,
#             "project_stats": project_stats,
#             "priority_distribution": priority_distribution,
#             "status_distribution": status_distribution,
#             "upcoming_deadlines": upcoming_deadlines,
#             "project_progress": project_progress,
#             "recent_activities": recent_activities,
#         }

#         response_data = {"success": True, "analytics": analytics}

#         print(f"[DASHBOARD] Analytics generated successfully")

#         return {
#             "success": True,
#             "status": 200,
#             "headers": [("Content-Type", "application/json")],
#             "body": json.dumps(response_data),
#         }

#     except Exception as e:
#         print(f"Error in get_dashboard_analytics: {str(e)}")
#         import traceback

#         traceback.print_exc()
#         return {
#             "success": False,
#             "status": 500,
#             "headers": [("Content-Type", "application/json")],
#             "body": json.dumps(
#                 {
#                     "success": False,
#                     "error": f"Failed to fetch dashboard analytics: {str(e)}",
#                 }
#             ),
#         }


# def get_downloadable_report(user_id):
#     """
#     Get detailed report data for download (CSV/PDF)
#     Returns comprehensive data about user's tasks and projects
#     OPTIMIZED: Uses efficient queries and minimal data loading
#     """
#     try:
#         # Verify authentication
#         if not user_id:
#             return {
#                 "success": False,
#                 "status": 401,
#                 "headers": [("Content-Type", "application/json")],
#                 "body": json.dumps(
#                     {"success": False, "error": "Authentication required"}
#                 ),
#             }

#         from models.user import User

#         user = User.find_by_id(user_id)
#         if not user:
#             return {
#                 "success": False,
#                 "status": 404,
#                 "headers": [("Content-Type", "application/json")],
#                 "body": json.dumps({"success": False, "error": "User not found"}),
#             }

#         # Get user's projects and tasks
#         projects_collection = db["projects"]
#         tasks_collection = db["tasks"]

#         # ⚡ OPTIMIZED: Find projects with only necessary fields
#         user_projects = list(
#             projects_collection.find(
#                 {
#                     "$or": [
#                         {"user_id": user_id},
#                         {"members": {"$elemMatch": {"user_id": user_id}}},
#                     ]
#                 },
#                 {
#                     "_id": 1,
#                     "name": 1,
#                     "description": 1,
#                     "status": 1,
#                     "created_at": 1,
#                     "user_id": 1,
#                 },
#             )
#         )

#         project_ids = [p["_id"] for p in user_projects]
#         project_ids_str = [str(pid) for pid in project_ids]

#         # ⚡ OPTIMIZED: Get task counts using aggregation instead of fetching all tasks
#         # Count all project tasks
#         if project_ids_str:
#             project_task_counts_pipeline = [
#                 {"$match": {"project_id": {"$in": project_ids_str}}},
#                 {
#                     "$group": {
#                         "_id": "$project_id",
#                         "total": {"$sum": 1},
#                         "completed": {
#                             "$sum": {
#                                 "$cond": [
#                                     {"$in": ["$status", ["Done", "Closed"]]},
#                                     1,
#                                     0,
#                                 ]
#                             }
#                         },
#                     }
#                 },
#             ]
#             project_task_counts = {
#                 r["_id"]: {"total": r["total"], "completed": r["completed"]}
#                 for r in tasks_collection.aggregate(project_task_counts_pipeline)
#             }
#         else:
#             project_task_counts = {}

#         # Get tasks assigned to user only
#         my_tasks = list(
#             tasks_collection.find(
#                 {"assignee_id": user_id},
#                 {
#                     "_id": 1,
#                     "ticket_id": 1,
#                     "title": 1,
#                     "description": 1,
#                     "status": 1,
#                     "priority": 1,
#                     "due_date": 1,
#                     "project_id": 1,
#                     "created_at": 1,
#                     "updated_at": 1,
#                 },
#             )
#         )

#         # Count task stats
#         pending_count = sum(
#             1 for t in my_tasks if t.get("status") not in ["Done", "Closed"]
#         )
#         completed_count = len(my_tasks) - pending_count

#         # Prepare detailed report data
#         report_data = {
#             "generated_at": datetime.now().isoformat(),
#             "user_info": {
#                 "user_id": user_id,
#                 "name": user.get("name", ""),
#                 "email": user.get("email", ""),
#                 "role": user.get("role", ""),
#             },
#             "projects": [],
#             "my_tasks": [],
#             "summary": {
#                 "total_projects": len(user_projects),
#                 "total_tasks": len(my_tasks),
#                 "pending_tasks": pending_count,
#                 "completed_tasks": completed_count,
#             },
#         }

#         # Create project map for quick lookup
#         project_map = {str(p["_id"]): p.get("name", "") for p in user_projects}

#         # Add project details
#         for project in user_projects:
#             project_id_str = str(project["_id"])
#             counts = project_task_counts.get(
#                 project_id_str, {"total": 0, "completed": 0}
#             )

#             # Convert datetime to string
#             created_at = project.get("created_at", "")
#             if isinstance(created_at, datetime):
#                 created_at = created_at.isoformat()

#             report_data["projects"].append(
#                 {
#                     "project_id": project_id_str,
#                     "name": project.get("name", ""),
#                     "description": project.get("description", ""),
#                     "status": project.get("status", ""),
#                     "created_at": created_at,
#                     "total_tasks": counts["total"],
#                     "completed_tasks": counts["completed"],
#                 }
#             )

#         # Add task details
#         for task in my_tasks:
#             # Convert datetime fields to strings
#             created_at = task.get("created_at", "")
#             if isinstance(created_at, datetime):
#                 created_at = created_at.isoformat()

#             updated_at = task.get("updated_at", "")
#             if isinstance(updated_at, datetime):
#                 updated_at = updated_at.isoformat()

#             due_date = task.get("due_date", "")
#             if isinstance(due_date, datetime):
#                 due_date = due_date.isoformat()

#             project_name = project_map.get(str(task.get("project_id")), "")

#             report_data["my_tasks"].append(
#                 {
#                     "task_id": str(task["_id"]),
#                     "ticket_id": task.get("ticket_id", ""),
#                     "title": task.get("title", ""),
#                     "description": task.get("description", ""),
#                     "status": task.get("status", ""),
#                     "priority": task.get("priority", ""),
#                     "due_date": due_date,
#                     "project_name": project_name,
#                     "created_at": created_at,
#                     "updated_at": updated_at,
#                 }
#             )

#         response_data = {"success": True, "report": report_data}

#         return {
#             "success": True,
#             "status": 200,
#             "headers": [("Content-Type", "application/json")],
#             "body": json.dumps(response_data),
#         }

#     except Exception as e:
#         print(f"Error in get_downloadable_report: {str(e)}")
#         import traceback

#         traceback.print_exc()
#         return {
#             "success": False,
#             "status": 500,
#             "headers": [("Content-Type", "application/json")],
#             "body": json.dumps(
#                 {"success": False, "error": f"Failed to generate report: {str(e)}"}
#             ),
#         }
"""
Dashboard Controller - Analytics and Reports (FIXED: Timezone Safe)
"""

import json
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from utils.auth_utils import verify_token
from database import db


# ✅ NEW: Central datetime normalizer
def normalize_datetime(dt):
    """
    Ensure datetime is timezone-aware (UTC)
    Handles:
    - naive datetime (Mongo)
    - ISO string
    - already aware datetime
    """
    if not dt:
        return None

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except:
            return None

    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    return None


def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def convert_dates_to_strings(data):
    """
    Recursively convert:
    - datetime → ISO string
    - ObjectId → string
    """
    if isinstance(data, dict):
        return {key: convert_dates_to_strings(value) for key, value in data.items()}

    elif isinstance(data, list):
        return [convert_dates_to_strings(item) for item in data]

    elif isinstance(data, datetime):
        return data.isoformat()

    elif isinstance(data, ObjectId):
        return str(data)

    else:
        return data


# =========================================
# 🔹 DASHBOARD ANALYTICS
# =========================================
def get_dashboard_analytics(user_id):
    try:
        if not user_id:
            return {
                "success": False,
                "status": 401,
                "headers": [("Content-Type", "application/json")],
                "body": json.dumps({"success": False, "error": "Authentication required"}),
            }

        from models.user import User

        user = User.find_by_id(user_id)
        if not user:
            return {
                "success": False,
                "status": 404,
                "headers": [("Content-Type", "application/json")],
                "body": json.dumps({"success": False, "error": "User not found"}),
            }

        projects_collection = db["projects"]
        tasks_collection = db["tasks"]

        user_projects = list(
            projects_collection.find(
                {
                    "$or": [
                        {"user_id": user_id},
                        {"members": {"$elemMatch": {"user_id": user_id}}},
                    ]
                },
                {"_id": 1, "name": 1, "status": 1, "user_id": 1},
            )
        )

        project_ids = [p["_id"] for p in user_projects]
        project_ids_str = [str(pid) for pid in project_ids]

        print(f"[DASHBOARD] Found {len(user_projects)} projects")

        my_tasks = list(
            tasks_collection.aggregate(
                [
                    {"$match": {"assignee_id": user_id}},
                    {
                        "$project": {
                            "_id": 1,
                            "status": 1,
                            "priority": 1,
                            "due_date": 1,
                            "project_id": 1,
                            "title": 1,
                            "updated_at": 1,
                        }
                    },
                ]
            )
        )

        print(f"[DASHBOARD] Found {len(my_tasks)} tasks assigned to user")

        # ✅ ALWAYS UTC AWARE
        now = datetime.now(timezone.utc)

        overdue_count = 0
        pending_count = 0
        in_progress_count = 0
        done_count = 0
        closed_count = 0

        for task in my_tasks:
            status = task.get("status")

            if status == "In Progress":
                in_progress_count += 1
            elif status == "Done":
                done_count += 1
            elif status == "Closed":
                closed_count += 1

            if status not in ["Done", "Closed"]:
                pending_count += 1

                due_date = normalize_datetime(task.get("due_date"))

                if due_date and due_date < now:
                    overdue_count += 1

        task_stats = {
            "total": len(my_tasks),
            "pending": pending_count,
            "in_progress": in_progress_count,
            "done": done_count,
            "closed": closed_count,
            "overdue": overdue_count,
        }

        owned_count = sum(1 for p in user_projects if p.get("user_id") == user_id)
        member_count = len(user_projects) - owned_count
        active_count = sum(1 for p in user_projects if p.get("status") == "Active")
        completed_count = sum(
            1 for p in user_projects if p.get("status") == "Completed"
        )

        project_stats = {
            "total": len(user_projects),
            "owned": owned_count,
            "member_of": member_count,
            "active": active_count,
            "completed": completed_count,
        }

        priority_distribution = {"High": 0, "Medium": 0, "Low": 0}
        status_distribution = {"To Do": 0, "In Progress": 0, "Done": 0, "Closed": 0}

        for task in my_tasks:
            status = task.get("status", "To Do")

            if status not in ["Done", "Closed"]:
                priority = task.get("priority", "Low")
                if priority in priority_distribution:
                    priority_distribution[priority] += 1

            if status in status_distribution:
                status_distribution[status] += 1

        # ✅ Upcoming deadlines
        end_of_week = now + timedelta(days=7)
        upcoming_deadlines = []
        # =========================================
        # 🔥 PROJECT PROGRESS (FIXED)
        # =========================================
        project_progress = []

        # Use ObjectId list (NOT string)
        if project_ids:
            progress_pipeline = [
                {
                    "$match": {
                        "$or": [
                            {"project_id": {"$in": project_ids}},  # ObjectId match
                            {"project_id": {"$in": [str(pid) for pid in project_ids]}},  # fallback if stored as string
                        ]
                    }
                },
                {
                    "$group": {
                        "_id": "$project_id",
                        "total": {"$sum": 1},
                        "closed": {
                            "$sum": {"$cond": [{"$eq": ["$status", "Closed"]}, 1, 0]}
                        },
                    }
                },
            ]

            progress_results = list(tasks_collection.aggregate(progress_pipeline))

            # ⚠️ IMPORTANT: fix project_map for ObjectId
            project_map_obj = {p["_id"]: p.get("name", "Unknown") for p in user_projects}

            for result in progress_results:
                pid = result["_id"]

                # normalize for lookup
                if isinstance(pid, str):
                    try:
                        pid_lookup = ObjectId(pid)
                    except:
                        pid_lookup = pid
                else:
                    pid_lookup = pid

                total = result["total"]
                closed = result["closed"]

                progress_percentage = (closed / total * 100) if total > 0 else 0

                project_progress.append(
                    {
                        "project_id": str(pid),
                        "project_name": project_map_obj.get(pid_lookup, "Unknown"),
                        "total_tasks": total,
                        "completed_tasks": closed,
                        "progress_percentage": round(progress_percentage, 1),
                    }
                )

        # Sort and limit
        project_progress.sort(key=lambda x: x["progress_percentage"], reverse=True)
        project_progress = project_progress[:10]

        print(f"[DASHBOARD] Project progress calculated: {len(project_progress)}")

        project_map = {str(p["_id"]): p.get("name", "Unknown") for p in user_projects}

        for task in my_tasks:
            if task.get("status") in ["Done", "Closed"]:
                continue

            due_date = normalize_datetime(task.get("due_date"))
            if not due_date:
                continue

            if due_date <= end_of_week:
                upcoming_deadlines.append(
                    {
                        "task_id": str(task["_id"]),
                        "title": task.get("title", ""),
                        "due_date": due_date.isoformat(),
                        "priority": task.get("priority", "Low"),
                        "status": task.get("status", "To Do"),
                        "project_id": str(task.get("project_id", "")),
                        "project_name": project_map.get(
                            str(task.get("project_id")), "Unknown"
                        ),
                        "days_until": (due_date - now).days,
                        "_due_date_obj": due_date,  # for sorting
                    }
                )

        # ✅ Correct sorting
        upcoming_deadlines.sort(key=lambda x: x["_due_date_obj"])
        upcoming_deadlines = upcoming_deadlines[:15]

        # remove temp field
        for t in upcoming_deadlines:
            t.pop("_due_date_obj", None)

        # ✅ Recent activity
        recent_activities = []

        sorted_tasks = sorted(
            my_tasks,
            key=lambda x: normalize_datetime(x.get("updated_at")) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )[:10]

        for task in sorted_tasks:
            updated_at = normalize_datetime(task.get("updated_at"))

            recent_activities.append(
                {
                    "task_id": str(task["_id"]),
                    "title": task.get("title", ""),
                    "status": task.get("status", ""),
                    "priority": task.get("priority", ""),
                    "project_name": project_map.get(
                        str(task.get("project_id")), "Unknown"
                    ),
                    "project_id": str(task.get("project_id", "")),
                    "updated_at": updated_at.isoformat() if updated_at else "",
                }
            )

        analytics = {
            "task_stats": task_stats,
            "project_stats": project_stats,
            "priority_distribution": priority_distribution,
            "status_distribution": status_distribution,
            "upcoming_deadlines": upcoming_deadlines,
            "project_progress":project_progress,
            "recent_activities": recent_activities,
        }

        return {
            "success": True,
            "status": 200,
            "headers": [("Content-Type", "application/json")],
            "body": json.dumps({"success": True, "analytics": analytics}),
        }

    except Exception as e:
        print(f"Error in get_dashboard_analytics: {str(e)}")
        import traceback

        traceback.print_exc()

        return {
            "success": False,
            "status": 500,
            "headers": [("Content-Type", "application/json")],
            "body": json.dumps(
                {
                    "success": False,
                    "error": f"Failed to fetch dashboard analytics: {str(e)}",
                }
            ),
        }


# =========================================
# 🔹 DOWNLOADABLE REPORT (FIXED)
# =========================================
def get_downloadable_report(user_id):
    try:
        if not user_id:
            return {
                "success": False,
                "status": 401,
                "headers": [("Content-Type", "application/json")],
                "body": json.dumps({"success": False, "error": "Authentication required"}),
            }

        from models.user import User

        user = User.find_by_id(user_id)
        if not user:
            return {
                "success": False,
                "status": 404,
                "headers": [("Content-Type", "application/json")],
                "body": json.dumps({"success": False, "error": "User not found"}),
            }

        projects_collection = db["projects"]
        tasks_collection = db["tasks"]

        user_projects = list(
            projects_collection.find(
                {
                    "$or": [
                        {"user_id": user_id},
                        {"members": {"$elemMatch": {"user_id": user_id}}},
                    ]
                }
            )
        )

        my_tasks = list(tasks_collection.find({"assignee_id": user_id}))

        report_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "projects": convert_dates_to_strings(user_projects),
            "my_tasks": convert_dates_to_strings(my_tasks),
        }

        return {
            "success": True,
            "status": 200,
            "headers": [("Content-Type", "application/json")],
            "body": json.dumps({"success": True, "report": report_data}),
        }

    except Exception as e:
        print(f"Error in get_downloadable_report: {str(e)}")
        import traceback

        traceback.print_exc()

        return {
            "success": False,
            "status": 500,
            "headers": [("Content-Type", "application/json")],
            "body": json.dumps(
                {"success": False, "error": f"Failed to generate report: {str(e)}"}
            ),
        }