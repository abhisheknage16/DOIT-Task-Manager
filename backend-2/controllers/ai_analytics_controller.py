"""
AI User Analytics Controller
Provides GPT-powered insights and FLUX visualizations on user task/project data
"""

import json
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from database import db
from utils.azure_ai_utils import chat_completion_gpt4_mini, generate_image


def get_user_analytics_data(user_id: str) -> dict:
    """
    Aggregate comprehensive user performance analytics from MongoDB.
    Returns structured data for charts and AI analysis.
    """
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return {"success": False, "error": "User not found"}

        user_projects = list(
            db.projects.find(
                {"$or": [{"user_id": user_id}, {"members.user_id": user_id}]}
            )
        )
        project_ids = [str(p["_id"]) for p in user_projects]

        my_tasks = list(
            db.tasks.find({"assignee_id": user_id}, {"activities": 0, "attachments": 0})
        )

        all_project_tasks = list(
            db.tasks.find(
                {"project_id": {"$in": project_ids}},
                {
                    "title": 1,
                    "status": 1,
                    "priority": 1,
                    "assignee_id": 1,
                    "due_date": 1,
                    "issue_type": 1,
                    "sprint_id": 1,
                    "updated_at": 1,
                    "project_id": 1,
                },
            )
        )

        sprints = list(db.sprints.find({"project_id": {"$in": project_ids}}))

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # ── Status / priority / issue type distributions ───────────────────
        status_dist = {}
        priority_dist = {}
        issue_type_dist = {}
        overdue_tasks = []
        due_soon_tasks = []

        for task in my_tasks:
            status = task.get("status", "To Do")
            priority = task.get("priority", "Medium")
            issue_type = task.get("issue_type", "task")

            status_dist[status] = status_dist.get(status, 0) + 1
            priority_dist[priority] = priority_dist.get(priority, 0) + 1
            issue_type_dist[issue_type] = issue_type_dist.get(issue_type, 0) + 1

            if status not in ["Done", "Closed"]:
                due = task.get("due_date")
                if due:
                    due_dt = None
                    if isinstance(due, datetime):
                        due_dt = due
                    elif isinstance(due, str):
                        try:
                            due_dt = datetime.fromisoformat(
                                due.replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                        except Exception:
                            pass
                    if due_dt:
                        days_diff = (due_dt - now).days
                        if days_diff < 0:
                            overdue_tasks.append(
                                {
                                    "ticket_id": task.get("ticket_id", ""),
                                    "title": task.get("title", ""),
                                    "priority": priority,
                                    "days_overdue": abs(days_diff),
                                }
                            )
                        elif days_diff <= 7:
                            due_soon_tasks.append(
                                {
                                    "ticket_id": task.get("ticket_id", ""),
                                    "title": task.get("title", ""),
                                    "priority": priority,
                                    "days_remaining": days_diff,
                                }
                            )

        # ── Project progress ───────────────────────────────────────────────
        project_progress = []
        for proj in user_projects:
            proj_id = str(proj["_id"])
            proj_tasks = [
                t for t in all_project_tasks if t.get("project_id") == proj_id
            ]
            total = len(proj_tasks)
            completed = sum(
                1 for t in proj_tasks if t.get("status") in ["Done", "Closed"]
            )
            in_progress = sum(1 for t in proj_tasks if t.get("status") == "In Progress")
            project_progress.append(
                {
                    "name": proj.get("name", "Unknown")[:20],
                    "total": total,
                    "completed": completed,
                    "in_progress": in_progress,
                    "todo": max(0, total - completed - in_progress),
                    "progress_pct": round(
                        (completed / total * 100) if total > 0 else 0, 1
                    ),
                }
            )

        # ── Sprint velocity (last 8 completed sprints) ─────────────────────
        completed_sprints = sorted(
            [s for s in sprints if s.get("status") == "completed"],
            key=lambda x: x.get("completed_at") or datetime.min,
        )[-8:]

        sprint_velocity = []
        for sprint in completed_sprints:
            sprint_tasks = [
                t for t in all_project_tasks if t.get("sprint_id") == str(sprint["_id"])
            ]
            done = sum(1 for t in sprint_tasks if t.get("status") in ["Done", "Closed"])
            sprint_velocity.append(
                {
                    "sprint": sprint.get("name", "Sprint")[:15],
                    "completed": done,
                    "total": len(sprint_tasks),
                }
            )

        # ── 8-week completion history ──────────────────────────────────────
        weekly_completion = []
        for week_offset in range(7, -1, -1):
            week_start = now - timedelta(days=(week_offset + 1) * 7)
            week_end = now - timedelta(days=week_offset * 7)
            completed_in_week = sum(
                1
                for t in my_tasks
                if t.get("status") in ["Done", "Closed"]
                and isinstance(t.get("updated_at"), datetime)
                and week_start <= t["updated_at"] <= week_end
            )
            weekly_completion.append(
                {
                    "week": f"W-{week_offset}" if week_offset > 0 else "This wk",
                    "completed": completed_in_week,
                }
            )

        # ── Day-of-week activity heatmap ───────────────────────────────────
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_activity = {d: 0 for d in days}
        for task in my_tasks:
            updated = task.get("updated_at")
            if isinstance(updated, datetime):
                day_name = days[updated.weekday()]
                day_activity[day_name] += 1
        day_activity_list = [{"day": d, "activity": day_activity[d]} for d in days]

        # ── Team workload ──────────────────────────────────────────────────
        assignee_counts = {}
        for task in all_project_tasks:
            if task.get("status") not in ["Done", "Closed"]:
                aid = task.get("assignee_id")
                if aid:
                    assignee_counts[aid] = assignee_counts.get(aid, 0) + 1

        team_workload = []
        for aid, count in sorted(assignee_counts.items(), key=lambda x: -x[1])[:6]:
            try:
                u = (
                    db.users.find_one({"_id": ObjectId(aid)}, {"name": 1})
                    if len(aid) == 24
                    else None
                )
            except Exception:
                u = None
            team_workload.append(
                {
                    "name": (u.get("name", "User")[:12] if u else "Unknown"),
                    "tasks": count,
                    "is_me": aid == user_id,
                }
            )

        total_tasks = len(my_tasks)
        completed_tasks = sum(
            1 for t in my_tasks if t.get("status") in ["Done", "Closed"]
        )
        active_sprints = sum(1 for s in sprints if s.get("status") == "active")

        return {
            "success": True,
            "user": {
                "name": user.get("name", "User"),
                "email": user.get("email"),
                "role": user.get("role", "member"),
            },
            "summary": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "completion_rate": round(
                    (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1
                ),
                "overdue_count": len(overdue_tasks),
                "due_soon_count": len(due_soon_tasks),
                "total_projects": len(user_projects),
                "active_sprints": active_sprints,
            },
            "charts": {
                "status_distribution": [
                    {"name": k, "value": v} for k, v in status_dist.items()
                ],
                "priority_distribution": [
                    {"name": k, "value": v} for k, v in priority_dist.items()
                ],
                "issue_type_distribution": [
                    {"name": k, "value": v} for k, v in issue_type_dist.items()
                ],
                "project_progress": project_progress[:8],
                "sprint_velocity": sprint_velocity,
                "weekly_completion": weekly_completion,
                "day_activity": day_activity_list,
                "team_workload": team_workload,
            },
            "alerts": {"overdue": overdue_tasks[:10], "due_soon": due_soon_tasks[:10]},
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def generate_ai_analytics_insight(user_id: str, question: str = None) -> dict:
    """
    Use GPT-4.1-mini profile to generate personalized performance insights from user data.
    """
    try:
        analytics = get_user_analytics_data(user_id)
        if not analytics.get("success"):
            return {"success": False, "error": analytics.get("error")}

        summary = analytics["summary"]
        charts = analytics["charts"]
        user_info = analytics["user"]

        context = f"""
User: {user_info["name"]} ({user_info["role"]})

PERFORMANCE SUMMARY:
- Total Tasks: {summary["total_tasks"]}
- Completed: {summary["completed_tasks"]} ({summary["completion_rate"]}%)
- Overdue: {summary["overdue_count"]}
- Due Soon (7 days): {summary["due_soon_count"]}
- Projects: {summary["total_projects"]}
- Active Sprints: {summary["active_sprints"]}

TASK STATUS: {json.dumps({d["name"]: d["value"] for d in charts["status_distribution"]})}
PRIORITY BREAKDOWN: {json.dumps({d["name"]: d["value"] for d in charts["priority_distribution"]})}
ISSUE TYPES: {json.dumps({d["name"]: d["value"] for d in charts["issue_type_distribution"]})}

PROJECT PROGRESS (top 5):
{chr(10).join([f"- {p['name']}: {p['progress_pct']}% ({p['completed']}/{p['total']} tasks)" for p in charts["project_progress"][:5]])}

SPRINT VELOCITY (recent):
{chr(10).join([f"- {s['sprint']}: {s['completed']} completed" for s in charts["sprint_velocity"][-4:]])}

WEEKLY COMPLETION (last 8 weeks):
{chr(10).join([f"- {w['week']}: {w['completed']} tasks" for w in charts["weekly_completion"]])}

ALERTS:
- Overdue: {[t["ticket_id"] + " " + t["title"][:30] for t in analytics["alerts"]["overdue"][:5]]}
- Due soon: {[t["ticket_id"] + " " + t["title"][:30] for t in analytics["alerts"]["due_soon"][:5]]}
"""

        user_prompt = (
            question
            if question
            else (
                "Analyze this user's task management performance and provide:\n"
                "1. **Performance Assessment** — Overall productivity summary with specific numbers\n"
                "2. **Key Strengths** — What's going well based on the data\n"
                "3. **Risk Areas** — Immediate concerns (overdue tasks, bottlenecks)\n"
                "4. **Actionable Recommendations** — 3-4 specific, concrete next steps\n"
                "5. **Productivity Score** — Rate 1-10 with brief justification\n\n"
                "Be data-driven, specific, and actionable. Reference actual numbers."
            )
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert productivity analyst and project management coach. "
                    "Analyze user performance data and provide insightful, actionable recommendations. "
                    "Use markdown formatting with headers and bullet points. Be specific with numbers."
                ),
            },
            {
                "role": "user",
                "content": f"Here is the performance data:\n\n{context}\n\n{user_prompt}",
            },
        ]

        response = chat_completion_gpt4_mini(messages, max_tokens=1500)
        return {
            "success": True,
            "insight": response["content"],
            "tokens": response.get("tokens", {}),
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def generate_ai_visualization_image(
    user_id: str, viz_type: str = "performance"
) -> dict:
    """
    Use FLUX model to generate artistic infographic visualizations of user data.
    """
    try:
        analytics = get_user_analytics_data(user_id)
        if not analytics.get("success"):
            return {"success": False, "error": analytics.get("error")}

        summary = analytics["summary"]
        completion_rate = summary["completion_rate"]
        total = summary["total_tasks"]
        completed = summary["completed_tasks"]
        projects = len(analytics["charts"]["project_progress"])

        prompts = {
            "performance": (
                f"Professional data visualization dashboard infographic for a software developer. "
                f"Minimalist tech aesthetic with dark navy background. "
                f"Shows {completion_rate}% task completion rate as a glowing circular progress ring in electric blue. "
                f"Clean geometric charts: bar graphs in cyan and emerald showing {completed} completed out of {total} total tasks. "
                f"Small decorative data points, subtle grid lines, professional typography. "
                f"Corporate tech design, visual data art, ultra sharp, 8k quality."
            ),
            "network": (
                f"Abstract network visualization of project connections. "
                f"Dark background with {projects} glowing nodes in different colors "
                f"(blues, greens, purples) connected by luminous energy lines. "
                f"Central node larger, constellation-like pattern, cyberpunk aesthetic, "
                f"ultra high quality digital art render, no text."
            ),
            "velocity": (
                f"Artistic sprint velocity and productivity chart visualization. "
                f"Dark background with smooth flowing area chart gradient from deep blue to cyan. "
                f"Shows upward productivity trend with glowing data points. "
                f"Minimalist axes, abstract yet data-like, professional analytics aesthetic, "
                f"subtle particle effects, sharp clean lines, 4k quality."
            ),
        }

        prompt = prompts.get(viz_type, prompts["performance"])
        result = generate_image(prompt, save_to_file=True)

        if result.get("success"):
            return {
                "success": True,
                "image_url": result.get("image_url"),
                "viz_type": viz_type,
            }
        return {
            "success": False,
            "error": result.get("error", "Image generation failed"),
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}
