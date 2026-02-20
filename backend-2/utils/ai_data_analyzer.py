"""
AI Data Analyzer for Azure AI Foundry Assistant
Provides intelligent data analysis and insights based on user's MongoDB data
Similar to Gemini chat but using Azure AI Foundry
"""

from datetime import datetime, timedelta, timezone
from bson import ObjectId
from database import db


def analyze_user_data_for_ai(user_id: str) -> dict:
    """
    Comprehensive user data analysis for AI Assistant context
    Returns structured data that AI can use to provide intelligent insights

    This is similar to analyze_user_data in chat_controller but optimized
    for AI Assistant's conversation context
    """
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None

        # Get all projects where user is owner or member
        user_projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )

        project_ids = [str(p["_id"]) for p in user_projects]

        # 🚀 OPTIMIZATION: Exclude large arrays (activities, attachments, links)
        # This reduces data transfer by 60-70% for typical tasks
        task_projection = {
            "activities": 0,
            "attachments": 0,
            "links": 0,
        }

        # Fetch relevant collections with field projections
        my_tasks = list(db.tasks.find({"assignee_id": user_id}, task_projection))
        all_tasks = list(db.tasks.find({"project_id": {"$in": project_ids}}, task_projection))
        sprints = list(db.sprints.find({"project_id": {"$in": project_ids}}))

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Helper functions
        def format_date(dt):
            if not dt:
                return None
            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                except:
                    return dt
            return dt.strftime("%Y-%m-%d")

        def days_ago(dt):
            if not dt:
                return None
            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                except:
                    return None
            if isinstance(dt, datetime):
                return (now - dt).days
            return None

        # Task Statistics
        task_stats = {
            "total": len(my_tasks),
            "by_status": {},
            "by_priority": {},
            "overdue_count": 0,
            "due_soon_count": 0,
            "completed_this_week": 0,
            "completed_this_month": 0,
        }

        for task in my_tasks:
            status = task.get("status", "To Do")
            priority = task.get("priority", "Medium")

            task_stats["by_status"][status] = task_stats["by_status"].get(status, 0) + 1
            task_stats["by_priority"][priority] = (
                task_stats["by_priority"].get(priority, 0) + 1
            )

            due = task.get("due_date")
            if due and status not in ["Done", "Closed"]:
                due_dt = None
                if isinstance(due, str):
                    try:
                        due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
                    except:
                        pass
                elif isinstance(due, datetime):
                    due_dt = due

                if due_dt:
                    if due_dt < now:
                        task_stats["overdue_count"] += 1
                    elif due_dt < now + timedelta(days=7):
                        task_stats["due_soon_count"] += 1

            completed = task.get("updated_at")
            if status in ["Done", "Closed"] and isinstance(completed, datetime):
                if completed > now - timedelta(days=7):
                    task_stats["completed_this_week"] += 1
                if completed > now - timedelta(days=30):
                    task_stats["completed_this_month"] += 1

        # Team & Collaboration
        team_stats = {}
        for proj in user_projects:
            owner_id = proj.get("user_id")
            members = proj.get("members", [])
            member_ids = [m.get("user_id") for m in members if m.get("user_id")]

            team_stats[str(proj["_id"])] = {
                "name": proj.get("name", "Unnamed Project"),
                "owner_id": owner_id,
                "total_members": len(set(member_ids))
                + (1 if owner_id and owner_id not in member_ids else 0),
                "members_list": member_ids[:8],
            }

        # Unique collaborators
        all_assignees = {t["assignee_id"] for t in all_tasks if t.get("assignee_id")}
        total_collaborators = len(all_assignees - {user_id})

        # Workload distribution
        assignee_workload = {}
        for task in all_tasks:
            assignee = task.get("assignee_id")
            if assignee:
                assignee_workload[assignee] = assignee_workload.get(assignee, 0) + 1

        top_assignees = sorted(
            assignee_workload.items(), key=lambda x: x[1], reverse=True
        )[:5]

        # Blocked / Blocker tasks
        blocked_count = 0
        blocking_count = 0
        for task in all_tasks:
            links = task.get("links", [])
            if any(l.get("type") == "blocked-by" for l in links):
                blocked_count += 1
            if any(l.get("type") == "blocks" for l in links):
                blocking_count += 1

        # Velocity (last 30 days)
        completed_last_30d = sum(
            1
            for t in all_tasks
            if t.get("status") in ["Done", "Closed"]
            and t.get("updated_at")
            and days_ago(t["updated_at"]) is not None
            and days_ago(t["updated_at"]) <= 30
        )

        # Recent tasks with more context
        recent_tasks = []
        for task in sorted(
            my_tasks, key=lambda x: x.get("updated_at", datetime.min), reverse=True
        )[:10]:
            recent_tasks.append(
                {
                    "ticket_id": task.get("ticket_id", ""),
                    "title": task.get("title", "Untitled"),
                    "status": task.get("status", "To Do"),
                    "priority": task.get("priority", "Medium"),
                    "dueDate": format_date(task.get("due_date")),
                    "projectId": task.get("project_id"),
                    "issue_type": task.get("issue_type", "task"),
                    "labels": task.get("labels", []),
                }
            )

        # Top projects with more details
        top_projects = []
        for p in user_projects[:8]:
            project_tasks = [
                t for t in all_tasks if t.get("project_id") == str(p["_id"])
            ]
            completed = len(
                [t for t in project_tasks if t.get("status") in ["Done", "Closed"]]
            )

            top_projects.append(
                {
                    "name": p.get("name", "Unnamed Project"),
                    "id": str(p["_id"]),
                    "taskCount": len(project_tasks),
                    "completedCount": completed,
                    "progress": round(
                        (completed / len(project_tasks) * 100) if project_tasks else 0,
                        1,
                    ),
                }
            )

        # Sprint insights
        sprint_insights = {
            "total": len(sprints),
            "active": sum(1 for s in sprints if s.get("status") == "active"),
            "completed": sum(1 for s in sprints if s.get("status") == "completed"),
            "planned": sum(1 for s in sprints if s.get("status") == "planned"),
        }

        # Active sprint details
        active_sprint = None
        for s in sprints:
            if s.get("status") == "active":
                sprint_tasks = [
                    t for t in all_tasks if t.get("sprint_id") == str(s["_id"])
                ]
                active_sprint = {
                    "name": s.get("name"),
                    "goal": s.get("goal", ""),
                    "start_date": format_date(s.get("start_date")),
                    "end_date": format_date(s.get("end_date")),
                    "total_tasks": len(sprint_tasks),
                    "completed_tasks": len(
                        [t for t in sprint_tasks if t.get("status") == "Done"]
                    ),
                }
                break

        return {
            "user": {
                "name": user.get("name", "User"),
                "email": user.get("email"),
                "role": user.get("role", "Member"),
            },
            "team": {
                "total_collaborators": total_collaborators,
                "projects_team_info": team_stats,
            },
            "workload_distribution": {
                "total_tasks_in_projects": len(all_tasks),
                "top_assignees": [
                    {"user_id": uid, "task_count": count}
                    for uid, count in top_assignees
                ],
            },
            "blockers": {
                "blocked_tasks": blocked_count,
                "blocking_tasks": blocking_count,
            },
            "velocity": {
                "completed_last_30_days": completed_last_30d,
                "avg_per_week": round(completed_last_30d / 4.3, 1)
                if completed_last_30d > 0
                else 0,
            },
            "stats": {
                "tasks": {
                    "total": task_stats["total"],
                    "overdue": task_stats["overdue_count"],
                    "dueSoon": task_stats["due_soon_count"],
                    "completedWeek": task_stats["completed_this_week"],
                    "completedMonth": task_stats["completed_this_month"],
                    "statusBreakdown": task_stats["by_status"],
                    "priorityBreakdown": task_stats["by_priority"],
                },
                "projects": {
                    "total": len(user_projects),
                    "owned": sum(
                        1 for p in user_projects if p.get("user_id") == user_id
                    ),
                    "memberOf": sum(
                        1 for p in user_projects if p.get("user_id") != user_id
                    ),
                    "withTasks": sum(
                        1
                        for p in user_projects
                        if any(t["project_id"] == str(p["_id"]) for t in all_tasks)
                    ),
                },
                "sprints": sprint_insights,
            },
            "recentTasks": recent_tasks,
            "topProjects": top_projects,
            "activeSprint": active_sprint,
        }

    except Exception as e:
        print(f"Error analyzing user data for AI: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def build_ai_system_prompt(user_data: dict) -> str:
    """
    Build comprehensive system prompt with user's data context
    This helps AI provide personalized, data-driven insights
    """
    if not user_data: 
        return """You are DOIT AI Assistant, a helpful and intelligent AI integrated into the DOIT project management system.

You help users with:
- Answering questions about project management
- Providing general assistance with any queries
- Generating images when requested

Be concise, helpful, and professional."""

    tasks = user_data["stats"]["tasks"]
    projects = user_data["stats"]["projects"]
    sprints = user_data["stats"]["sprints"]
    user_info = user_data["user"]

    prompt = f"""You are DOIT AI Assistant, an intelligent AI integrated into the DOIT project management system. You have access to the user's complete project and task data to provide personalized insights and recommendations.

## USER PROFILE
- **Name:** {user_info["name"]}
- **Role:** {user_info["role"]}
- **Email:** {user_info["email"]}

## TASK ANALYTICS
- **Total Tasks Assigned:** {tasks["total"]}
- **Status Distribution:** Done: {tasks["statusBreakdown"].get("Done", 0)}, In Progress: {tasks["statusBreakdown"].get("In Progress", 0)}, To Do: {tasks["statusBreakdown"].get("To Do", 0)}, Closed: {tasks["statusBreakdown"].get("Closed", 0)}
- **Priority Distribution:** High: {tasks["priorityBreakdown"].get("High", 0)}, Medium: {tasks["priorityBreakdown"].get("Medium", 0)}, Low: {tasks["priorityBreakdown"].get("Low", 0)}
- **Critical Metrics:**
  - Overdue Tasks: {tasks["overdue"]}
  - Due Within 7 Days: {tasks["dueSoon"]}
  - Completed This Week: {tasks["completedWeek"]}
  - Completed This Month: {tasks["completedMonth"]}

## PROJECT OVERVIEW
- **Total Projects:** {projects["total"]}
- **Owned Projects:** {projects["owned"]}
- **Member In:** {projects["memberOf"]}
- **Active Projects:** {projects["withTasks"]}

## SPRINT STATUS
- **Total Sprints:** {sprints["total"]}
- **Active Sprints:** {sprints["active"]}
- **Completed Sprints:** {sprints["completed"]}
- **Planned Sprints:** {sprints["planned"]}

## TEAM COLLABORATION
- **Total Collaborators:** {user_data["team"]["total_collaborators"]}
- **Blocked Tasks:** {user_data["blockers"]["blocked_tasks"]}
- **Blocking Tasks:** {user_data["blockers"]["blocking_tasks"]}

## VELOCITY METRICS
- **Completed Last 30 Days:** {user_data["velocity"]["completed_last_30_days"]}
- **Average Per Week:** {user_data["velocity"]["avg_per_week"]}

## RECENT ACTIVITY (Last 10 Tasks)
{format_recent_tasks(user_data["recentTasks"])}

## TOP PROJECTS
{format_top_projects(user_data["topProjects"])}
"""

    if user_data.get("activeSprint"):
        sprint = user_data["activeSprint"]
        prompt += f"""
## ACTIVE SPRINT
- **Name:** {sprint["name"]}
- **Goal:** {sprint["goal"]}
- **Duration:** {sprint["start_date"]} to {sprint["end_date"]}
- **Progress:** {sprint["completed_tasks"]}/{sprint["total_tasks"]} tasks completed
"""

    prompt += """
## RESPONSE GUIDELINES
1. **Be Data-Driven:** Reference actual metrics, task names, and project details
2. **Provide Actionable Insights:** Give concrete recommendations based on their data
3. **Celebrate Progress:** Acknowledge completed tasks and achievements with genuine enthusiasm
4. **Flag Risks:** Highlight overdue tasks, bottlenecks, or concerning patterns proactively
5. **Suggest Optimizations:** Recommend priority adjustments, sprint planning improvements
6. **Use Context:** Understand the user's complete workload when answering questions
7. **Be Concise:** Keep responses focused and valuable (2-4 paragraphs typically)
8. **Personalize:** Address the user by name and acknowledge their specific situation
9. **Visual Aids:** Use emojis strategically (📊 📈 ⚠️ ✅ 🚀) for clarity
10. **Image Generation:** When asked to generate images, acknowledge and describe what you're creating

## CAPABILITIES
- Answer questions about projects, tasks, sprints with specific data
- Provide productivity insights and recommendations
- Generate images using FLUX-1.1-pro when requested
- Analyze trends and patterns in their work
- Suggest task prioritization and time management strategies
- Help with project planning and sprint organization
## TASK AUTOMATION CAPABILITIES

You can execute task management commands on behalf of the user. When the user asks you to perform actions, you can:

**Available Commands:**

1. **Create Task:**
   - "Create a task titled 'X' in Project Y"
   - "Make a high priority bug for Z, assign to user@example.com"
   - Extracts: title, project, priority, assignee, description, labels, due date

2. **Assign Task:**
   - "Assign task ABC-123 to John"
   - "Give the login bug task to sarah@example.com"

3. **Update Task:**
   - "Change status of task ABC-123 to In Progress"
   - "Update the priority of X to High"
   - "Mark task Y as Done"

4. **Create Sprint:** (Admin only)
   - "Create a sprint called Sprint 23 for Project Beta from 2026-03-01 to 2026-03-14"

5. **List Tasks:**
   - "Show me all my tasks"
   - "List overdue tasks"
   - "What are my high priority tasks?"

6. **List Projects:**
   - "Show my projects"
   - "List all projects I'm part of"

**Command Detection:**
When you detect a request to perform an action (create, assign, update, list), acknowledge the command and execute it. The system will automatically handle the execution and provide results.

**Example Interactions:**

User: "Create a high priority task for fixing the login bug in Project Alpha, assign it to john@example.com"
Assistant: "I'll create that task for you right away!"
[System executes command]
Assistant: "✅ Task 'Fix login bug' created successfully in Project Alpha and assigned to john@example.com!"

User: "Show me all my overdue tasks"
Assistant: "Let me fetch your overdue tasks..."
[System executes command]
Assistant: "You have 3 overdue tasks:
- [ABC-001] Fix API endpoint - High priority
- [ABC-002] Update documentation - Medium priority
- [ABC-003] Review PR #45 - Low priority"

Remember: Always acknowledge commands and provide clear feedback on execution results.

You have complete visibility into their task ecosystem. Use this to provide holistic, intelligent assistance that considers their entire workload and helps them be more productive.
"""

    return prompt


def format_recent_tasks(tasks):
    """Format recent tasks for AI prompt"""
    if not tasks:
        return "No recent tasks"

    formatted = []
    for task in tasks:
        due = task.get("dueDate", "No due date")
        ticket = task.get("ticket_id", "")
        labels = ", ".join(task.get("labels", [])) if task.get("labels") else "none"

        formatted.append(
            f"- [{ticket}] {task['title']} ({task['status']}) - Priority: {task['priority']} - Due: {due} - Labels: {labels}"
        )

    return "\n".join(formatted)


def format_top_projects(projects):
    """Format top projects for AI prompt"""
    if not projects:
        return "No projects"

    formatted = []
    for proj in projects:
        progress = proj.get("progress", 0)
        formatted.append(
            f"- {proj['name']} - {proj['taskCount']} tasks ({proj['completedCount']} done, {progress}% complete)"
        )

    return "\n".join(formatted)


def extract_insights_from_data(user_data: dict) -> list:
    """
    Extract key insights and alerts from user data
    Returns list of insight objects for highlighting in UI
    """
    if not user_data:
        return []

    insights = []
    tasks = user_data["stats"]["tasks"]
    projects = user_data["stats"]["projects"]
    velocity = user_data["velocity"]

    # Critical: Overdue tasks
    # if tasks["overdue"] > 0:
    #     insights.append(
    #         {
    #             "type": "critical",
    #             "icon": "🚨",
    #             "title": f"{tasks['overdue']} Overdue Task(s)",
    #             "description": "Immediate action required to address overdue items",
    #             "priority": 1,
    #         }
    #     )

    # Warning: Due soon
    # if tasks["dueSoon"] > 0:
    #     insights.append(
    #         {
    #             "type": "warning",
    #             "icon": "⏰",
    #             "title": f"{tasks['dueSoon']} Task(s) Due This Week",
    #             "description": "Plan your time wisely for upcoming deadlines",
    #             "priority": 2,
    #         }
    #     )

    # Positive: Great weekly performance
    # if tasks["completedWeek"] >= 5:
    #     insights.append(
    #         {
    #             "type": "success",
    #             "icon": "🌟",
    #             "title": "Excellent Weekly Performance!",
    #             "description": f"You've completed {tasks['completedWeek']} tasks this week",
    #             "priority": 3,
    #         }
    #     )

    # Info: High workload
    high_priority = tasks["priorityBreakdown"].get("High", 0)
    # if high_priority > 5:
    #     insights.append(
    #         {
    #             "type": "info",
    #             "icon": "📊",
    #             "title": f"{high_priority} High Priority Tasks",
    #             "description": "Consider reviewing priorities and deadlines",
    #             "priority": 4,
    #         }
    #     )

    # Blocked tasks warning
    # if user_data["blockers"]["blocked_tasks"] > 0:
    #     insights.append(
    #         {
    #             "type": "warning",
    #             "icon": "🚧",
    #             "title": f"{user_data['blockers']['blocked_tasks']} Blocked Task(s)",
    #             "description": "Tasks waiting on dependencies - review blockers",
    #             "priority": 3,
    #         }
    #     )

    # Velocity insight
    # if velocity["completed_last_30_days"] > 0:
    #     avg = velocity["avg_per_week"]
    #     insights.append(
    #         {
    #             "type": "info",
    #             "icon": "📈",
    #             "title": f"Velocity: {avg} tasks/week",
    #             "description": f"Completed {velocity['completed_last_30_days']} tasks in last 30 days",
    #             "priority": 5,
    #         }
    #     )

    # Active sprint status
    # if user_data.get("activeSprint"):
    #     sprint = user_data["activeSprint"]
    #     progress = round(
    #         (sprint["completed_tasks"] / sprint["total_tasks"] * 100)
    #         if sprint["total_tasks"] > 0
    #         else 0,
    #         1,
    #     )

    #     insights.append(
    #         {
    #             "type": "info",
    #             "icon": "🏃",
    #             "title": f"Active Sprint: {sprint['name']}",
    #             "description": f"{progress}% complete ({sprint['completed_tasks']}/{sprint['total_tasks']} tasks)",
    #             "priority": 2,
    #         }
    #     )

    # Sort by priority
    insights.sort(key=lambda x: x["priority"])

    return insights
