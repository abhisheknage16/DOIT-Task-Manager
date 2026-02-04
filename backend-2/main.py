# from fastapi import FastAPI, Request, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from fastapi.staticfiles import StaticFiles
# from contextlib import asynccontextmanager
# import uvicorn
# import traceback
# from pathlib import Path

# from routers import (
#     auth_router, project_router, task_router, sprint_router,
#     dashboard_router, profile_router, user_router, chat_router,
#     member_router, system_dashboard_router, team_chat_router
# )
# from init_db import initialize_super_admin, initialize_default_channels

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Startup and shutdown events"""
#     # Startup
#     print("="*50)
#     print("Initializing database...")
#     initialize_super_admin()
#     initialize_default_channels()
#     print("Database initialized successfully!")
#     print("="*50)
#     yield
#     # Shutdown (cleanup if needed)
#     print("Shutting down...")

# app = FastAPI(
#     title="Task Management System API",
#     description="Complete task management system with projects, sprints, and AI chat",
#     version="1.0.0",
#     lifespan=lifespan
# )

# # CORS middleware - VERY IMPORTANT for frontend communication
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],  # Add your frontend URLs
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
#     expose_headers=["*"]
# )

# # Include routers
# app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(project_router, prefix="/api/projects", tags=["Projects"])
# app.include_router(member_router, prefix="/api/projects", tags=["Members"])
# app.include_router(task_router, prefix="/api/tasks", tags=["Tasks"])
# app.include_router(sprint_router, prefix="/api", tags=["Sprints"])
# app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
# app.include_router(system_dashboard_router, prefix="/api/dashboard", tags=["System Dashboard"])
# app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
# app.include_router(user_router, prefix="/api/users", tags=["Users"])
# app.include_router(chat_router, prefix="/api/chat", tags=["AI Chat"])
# app.include_router(team_chat_router, prefix="/api/team-chat", tags=["Team Chat"])

# # Serve static files for chat attachments
# uploads_dir = Path("uploads")
# uploads_dir.mkdir(exist_ok=True)
# (uploads_dir / "chat_attachments").mkdir(exist_ok=True)
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# @app.get("/")
# async def root():
#     return {"message": "Task Management System API - Running", "status": "OK"}

# @app.get("/health")
# async def health_check():
#     return {"status": "healthy", "service": "task-management-api", "version": "1.0.0"}

# # Global exception handler with detailed logging
# @app.exception_handler(HTTPException)
# async def http_exception_handler(request: Request, exc: HTTPException):
#     print(f"[ERROR] HTTP {exc.status_code}: {exc.detail}")
#     print(f"[ERROR] Path: {request.method} {request.url.path}")
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={"error": exc.detail, "success": False}
#     )

# @app.exception_handler(Exception)
# async def general_exception_handler(request: Request, exc: Exception):
#     print(f"[ERROR] Unhandled exception on {request.method} {request.url.path}")
#     print(f"[ERROR] Exception: {str(exc)}")
#     traceback.print_exc()
#     return JSONResponse(
#         status_code=500,
#         content={
#             "error": f"Internal server error: {str(exc)}",
#             "success": False,
#             "path": str(request.url.path)
#         }
#     )

# # Middleware to log all requests (helpful for debugging)
# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     print(f"[REQUEST] {request.method} {request.url.path}")
#     response = await call_next(request)
#     print(f"[RESPONSE] {request.method} {request.url.path} - Status: {response.status_code}")
#     return response

# if __name__ == "__main__":
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,
#         log_level="info"
#     )

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import traceback
from pathlib import Path

from routers import (
    auth_router, project_router, task_router, sprint_router,
    dashboard_router, profile_router, user_router, chat_router,
    member_router, system_dashboard_router, team_chat_router,
    data_viz_router  # ← ADD THIS IMPORT
)
from init_db import initialize_super_admin, initialize_default_channels

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("="*50)
    print("Initializing database...")
    initialize_super_admin()
    initialize_default_channels()
    print("Database initialized successfully!")
    print("="*50)
    yield
    # Shutdown (cleanup if needed)
    print("Shutting down...")

app = FastAPI(
    title="Task Management System API",
    description="Complete task management system with projects, sprints, AI chat, and data visualization",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - VERY IMPORTANT for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(project_router, prefix="/api/projects", tags=["Projects"])
app.include_router(member_router, prefix="/api/projects", tags=["Members"])
app.include_router(task_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(sprint_router, prefix="/api", tags=["Sprints"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(system_dashboard_router, prefix="/api/dashboard", tags=["System Dashboard"])
app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
app.include_router(user_router, prefix="/api/users", tags=["Users"])
app.include_router(chat_router, prefix="/api/chat", tags=["AI Chat"])
app.include_router(team_chat_router, prefix="/api/team-chat", tags=["Team Chat"])
app.include_router(data_viz_router, prefix="/api/data-viz", tags=["Data Visualization"])  # ← ADD THIS LINE

# Serve static files for chat attachments
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
(uploads_dir / "chat_attachments").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    return {"message": "Task Management System API - Running", "status": "OK"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "task-management-api",
        "version": "1.0.0",
        "features": [
            "Authentication",
            "Projects & Tasks",
            "Sprints",
            "AI Chat",
            "Team Chat",
            "Data Visualization"  # ← NEW FEATURE
        ]
    }

# Global exception handler with detailed logging
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    print(f"[ERROR] HTTP {exc.status_code}: {exc.detail}")
    print(f"[ERROR] Path: {request.method} {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "success": False}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] Unhandled exception on {request.method} {request.url.path}")
    print(f"[ERROR] Exception: {str(exc)}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "error": f"Internal server error: {str(exc)}",
            "success": False,
            "path": str(request.url.path)
        }
    )

# Middleware to log all requests (helpful for debugging)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[REQUEST] {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"[RESPONSE] {request.method} {request.url.path} - Status: {response.status_code}")
    return response

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Task Management System API")
    print("="*60)
    print("📊 Features:")
    print("  ✓ Authentication & Authorization")
    print("  ✓ Project & Task Management")
    print("  ✓ Sprint Planning")
    print("  ✓ AI-Powered Chatbot")
    print("  ✓ Team Collaboration Chat")
    print("  ✓ Data Visualization & Analytics")  # ← NEW
    print("="*60)
    print("🌐 Server starting on http://0.0.0.0:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("📋 ReDoc: http://localhost:8000/redoc")
    print("="*60 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )