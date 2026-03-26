import json
from models.task import Task
from models.project import Project
from models.git_activity import GitBranch, GitCommit, GitPullRequest
from utils.response import success_response, error_response
from utils.github_utils import extract_ticket_id, decrypt_token, calculate_time_ago
from datetime import datetime, timezone

def github_webhook(body_str, headers_dict):
    """
    Handle GitHub webhook events
    
    Events handled:
    - create: Branch created
    - push: Commits pushed
    - pull_request: PR opened/closed/merged
    """
    try:
        payload = json.loads(body_str)
    except:
        return error_response("Invalid JSON", 400)
    
    # Get event type from headers
    event_type = headers_dict.get("X-GitHub-Event", headers_dict.get("x-github-event"))
    
    if not event_type:
        return error_response("Missing X-GitHub-Event header", 400)
    
    print(f"Received GitHub webhook: {event_type}")
    
    # Get repository info
    repo_full_name = payload.get("repository", {}).get("full_name")
    repo_url = payload.get("repository", {}).get("html_url")
    
    # Find project by repo URL
    project = Project.find_by_repo_url(repo_url)
    if not project:
        print(f"No project found for repo: {repo_url}")
        return success_response({"message": "Repository not tracked"})
    
    project_id = str(project["_id"])
    
    # Handle different event types
    if event_type == "create" and payload.get("ref_type") == "branch":
        handle_branch_created(payload, project_id)
    
    elif event_type == "push":
        handle_push_event(payload, project_id)
    
    elif event_type == "pull_request":
        handle_pull_request_event(payload, project_id)
    
    elif event_type == "delete" and payload.get("ref_type") == "branch":
        handle_branch_deleted(payload, project_id)
    
    return success_response({"message": "Webhook processed successfully"})

def handle_branch_created(payload, project_id):
    """Handle branch creation event"""
    branch_name = payload.get("ref")
    repo_url = payload.get("repository", {}).get("html_url")
    
    # Extract ticket ID from branch name
    ticket_id = extract_ticket_id(branch_name)
    if not ticket_id:
        print(f"No ticket ID found in branch: {branch_name}")
        return
    
    # Find task by ticket ID
    task = Task.find_by_ticket_id(ticket_id)
    if not task:
        print(f"No task found for ticket: {ticket_id}")
        return
    
    # Create branch record
    GitBranch.create({
        "task_id": str(task["_id"]),
        "project_id": project_id,
        "branch_name": branch_name,
        "repo_url": repo_url,
        "status": "active"
    })
    
    print(f"Branch created: {branch_name} for task {ticket_id}")

def handle_push_event(payload, project_id):
    """Handle push event with commits"""
    commits = payload.get("commits", [])
    branch_name = payload.get("ref", "").replace("refs/heads/", "")
    
    for commit in commits:
        message = commit.get("message", "")
        ticket_id = extract_ticket_id(message)
        
        if not ticket_id:
            # Also check branch name
            ticket_id = extract_ticket_id(branch_name)
        
        if not ticket_id:
            continue
        
        # Find task
        task = Task.find_by_ticket_id(ticket_id)
        if not task:
            continue
        
        # Create commit record
        GitCommit.create({
            "task_id": str(task["_id"]),
            "project_id": project_id,
            "commit_sha": commit.get("id"),
            "message": message,
            "author": commit.get("author", {}).get("name", "Unknown"),
            "author_email": commit.get("author", {}).get("email", ""),
            "branch_name": branch_name,
            "timestamp": commit.get("timestamp")
        })
        
        print(f"Commit logged: {commit.get('id')[:7]} for task {ticket_id}")

def handle_pull_request_event(payload, project_id):
    """Handle pull request event"""
    action = payload.get("action")  # opened, closed, reopened, etc.
    pr = payload.get("pull_request", {})
    
    branch_name = pr.get("head", {}).get("ref")
    pr_title = pr.get("title", "")
    
    # Extract ticket ID from branch or title
    ticket_id = extract_ticket_id(branch_name) or extract_ticket_id(pr_title)
    
    if not ticket_id:
        print(f"No ticket ID found in PR: {pr_title}")
        return
    
    # Find task
    task = Task.find_by_ticket_id(ticket_id)
    if not task:
        print(f"No task found for ticket: {ticket_id}")
        return
    
    # Determine status
    status = "open"
    merged_at = None
    closed_at = None
    
    if pr.get("merged"):
        status = "merged"
        merged_at = pr.get("merged_at")
    elif pr.get("state") == "closed":
        status = "closed"
        closed_at = pr.get("closed_at")
    
    # Create or update PR record
    GitPullRequest.update_or_create({
        "task_id": str(task["_id"]),
        "project_id": project_id,
        "pr_number": pr.get("number"),
        "title": pr_title,
        "branch_name": branch_name,
        "status": status,
        "author": pr.get("user", {}).get("login", "Unknown"),
        "created_at_github": pr.get("created_at"),
        "merged_at": merged_at,
        "closed_at": closed_at
    })
    
    print(f"PR {action}: #{pr.get('number')} for task {ticket_id}")

def handle_branch_deleted(payload, project_id):
    """Handle branch deletion event"""
    branch_name = payload.get("ref")
    
    # Update branch status to deleted
    GitBranch.update_status(branch_name, project_id, "deleted")
    print(f"Branch deleted: {branch_name}")

def get_task_git_activity(task_id, user_id):
    """Get Git activity for a specific task - fetches from GitHub API in real-time"""
    if not user_id:
        return error_response("Unauthorized", 401)
    
    # Get task
    task = Task.find_by_identifier(task_id)
    if not task:
        return error_response("Task not found", 404)
    
    # Get project to access GitHub repo info
    project = Project.find_by_id(task.get("project_id"))
    if not project:
        return error_response("Project not found", 404)
    
    # Check if project has GitHub integration
    git_repo_url = project.get("git_repo_url", "")
    git_access_token = project.get("git_access_token", "")
    
    if not git_repo_url:
        # No GitHub repo linked, return empty activity
        return success_response({
            "branches_count": 0,
            "commits_count": 0,
            "pull_requests_count": 0,
            "branches": [],
            "commits": [],
            "pull_requests": []
        })
    
    # Get token (decrypt if stored, or use default)
    from utils.github_utils import (
        decrypt_token, get_branches, search_commits, 
        search_pull_requests, calculate_time_ago
    )
    import os
    
    token = decrypt_token(git_access_token) if git_access_token else os.getenv("GITHUB_TOKEN")
    
    print(f"[GIT] Using token from: {'project (encrypted)' if git_access_token else 'environment variable'}")
    print(f"[GIT] Token exists: {bool(token)}")
    print(f"[GIT] Token preview: {token[:15] if token else 'NONE'}...")
    
    if not token:
        return error_response("GitHub token not configured", 400)
    
    # Get task ticket ID
    ticket_id = task.get("ticket_id")
    if not ticket_id:
        return success_response({
            "branches_count": 0,
            "commits_count": 0,
            "pull_requests_count": 0,
            "branches": [],
            "commits": [],
            "pull_requests": []
        })
    
    # Fetch data from GitHub API
    try:
        print(f"[GIT] Fetching GitHub activity for ticket: {ticket_id}")
        print(f"[GIT] Repo URL: {git_repo_url}")
        print(f"[GIT] Token exists: {bool(token)}")
        
        # Use ThreadPoolExecutor to fetch all data in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        start_time = time.time()
        branches = []
        commits = []
        pull_requests = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all three API calls simultaneously
            future_branches = executor.submit(get_branches, git_repo_url, token, ticket_id)
            future_commits = executor.submit(search_commits, git_repo_url, token, ticket_id)
            future_prs = executor.submit(search_pull_requests, git_repo_url, token, ticket_id)
            
            # Collect results as they complete
            branches = future_branches.result()
            commits = future_commits.result()
            pull_requests = future_prs.result()
        
        elapsed_time = time.time() - start_time
        print(f"[GIT] Parallel fetch completed in {elapsed_time:.2f}s")
        print(f"[GIT] Branches found: {len(branches)}")
        print(f"[GIT] Commits found: {len(commits)}")
        print(f"[GIT] Pull requests found: {len(pull_requests)}")
        
        # Format pull requests
        formatted_prs = []
        for pr in pull_requests:
            merged_at = pr.get("merged_at")
            closed_at = pr.get("closed_at")
            created_at = pr.get("created_at")
            
            status = "open"
            if pr.get("merged"):
                status = "merged"
            elif pr.get("state") == "closed":
                status = "closed"
            
            pr_data = {
                "pr_number": pr.get("number"),
                "title": pr.get("title"),
                "status": status,
                "author": pr.get("user", {}).get("login", "Unknown"),
                "created_at": created_at,
                "merged_at": merged_at,
                "time_ago": calculate_time_ago(merged_at or closed_at or created_at)
            }
            formatted_prs.append(pr_data)
        
        # Format commits
        formatted_commits = []
        for commit in commits:
            commit_data = commit.get("commit", {})
            formatted_commits.append({
                "sha": commit.get("sha", "")[:7],
                "message": commit_data.get("message", ""),
                "author": commit_data.get("author", {}).get("name", "Unknown"),
                "timestamp": commit_data.get("author", {}).get("date"),
                "time_ago": calculate_time_ago(commit_data.get("author", {}).get("date"))
            })
        
        # Format branches
        formatted_branches = [{"name": b.get("name"), "status": "active"} for b in branches]
        
        return success_response({
            "branches_count": len(branches),
            "commits_count": len(commits),
            "pull_requests_count": len(pull_requests),
            "branches": formatted_branches,
            "commits": formatted_commits,
            "pull_requests": formatted_prs
        })
    
    except Exception as e:
        print(f"Error fetching Git activity: {e}")
        import traceback
        traceback.print_exc()
        # Return empty activity if API call fails
        return success_response({
            "branches_count": 0,
            "commits_count": 0,
            "pull_requests_count": 0,
            "branches": [],
            "commits": [],
            "pull_requests": []
        })
