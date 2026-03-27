<p align="center">
  <img src="frontend/src/doit.png" alt="DOIT Logo" width="120" />
</p>

<h1 align="center">DOIT — AI-Powered Task Management System</h1>

<p align="center">
  A full-stack, Jira-style project management platform supercharged with <strong>6 AI agents</strong>, real-time collaboration, voice chat, document intelligence, and advanced analytics.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-19.x-61DAFB?logo=react&logoColor=white" alt="React" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white" alt="MongoDB" />
  <img src="https://img.shields.io/badge/Azure_AI-Foundry-0078D4?logo=microsoftazure&logoColor=white" alt="Azure AI" />
  <img src="https://img.shields.io/badge/LangGraph-LangChain-1C3C3C?logo=langchain&logoColor=white" alt="LangGraph" />
  <img src="https://img.shields.io/badge/WebSocket-Real--time-010101?logo=socketdotio&logoColor=white" alt="WebSocket" />
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [AI Agents Architecture](#-ai-agents-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Documentation](#-api-documentation)
- [Screenshots](#-screenshots)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🚀 Overview

**DOIT** is an enterprise-grade task management system that combines traditional project management capabilities (projects, sprints, Kanban boards, calendars) with cutting-edge AI-powered automation. It features **6 distinct AI agents** that can autonomously create tasks, review code, analyze documents, and interact through natural language — including voice.

---

## ✨ Key Features

### 📁 Project Management
- Create and manage multiple projects with role-based access control (Super Admin, Admin, Member)
- Project-level dashboards with analytics and progress tracking
- Team member invitation and management via email

### 🏃 Sprint Management
- Create, plan, and track sprints with start/end dates and goals
- Sprint backlog management — add/remove tasks from sprints
- Burndown charts, velocity tracking, and sprint progress monitoring

### 📝 Task Management
- **Kanban Board** — Drag-and-drop task visualization (To Do → In Progress → Done)
- **Calendar View** — Deadline-based task scheduling with React Big Calendar
- Task assignment, prioritization (Low/Medium/High/Critical), and status tracking
- Issue types: Task, Bug, Story, Epic
- Labels, attachments, linked tasks, and comment threads
- Auto-generated ticket IDs (e.g., `PROJ-001`)

### 💬 Real-Time Team Chat (WebSocket)
- Channel-based messaging per project
- Instant message delivery with WebSocket
- File attachments (images, PDFs, documents)
- Emoji reactions and reply threads with context preview
- Message editing and deletion
- Online/offline connection status indicator

### 🤖 AI-Powered Chatbot (Gemini / Azure OpenAI)
- Context-aware project management assistant
- Intent detection: risk analysis, sprint status, workload check, assignment suggestions
- Persona modes: Friendly, Professional, Direct
- Floating chat widget accessible from any page

### 🎨 DOIT-AI Assistant (GPT-4o + FLUX-1.1-pro)
- Multi-modal AI assistant with text + image generation
- Agent selection panel: Azure Foundry, LangGraph, Local (Ollama), MCP
- Conversation management with history persistence
- Smart context injection with user's project data

### 📊 Data Visualization & Analytics
- Interactive chart builder with Chart.js and Recharts
- Dataset upload (CSV, Excel) with automatic analysis
- Custom visualization gallery with export (PNG, PDF, Excel)
- AI-powered data analysis with GPT insights

### 📄 Document Intelligence
- Upload documents (PDF, DOCX, PPTX, CSV, Excel, images) for AI analysis
- **Azure Document Intelligence** for OCR, table extraction, and form field parsing
- **Docling** fallback for PPTX, TXT, and URL parsing
- KPI extraction, insight generation, and branded PDF report export (ReportLab)

### 🔍 AI Code Review
- GitHub PR-based code review with AI analysis
- Security scanning with Bandit (Python linter)
- Quality metrics, code smell detection, and best-practice suggestions
- Background processing via Celery + Redis
- GitHub webhook support for automatic PR reviews

### 🎙️ Voice Chat
- Full voice pipeline: **Azure Whisper STT → AI Agent → Azure TTS**
- Multiple voice personas (Friendly, Professional, Direct, Assistant)
- Audio recording from browser → transcription → AI response → speech synthesis
- Seamless integration with Azure AI Foundry Agent

### 👤 User Management & Authentication
- **Dual auth**: Traditional JWT + Clerk SSO integration
- Profile management with personal info, education, and certificates
- Session management with device tracking and tab-level security
- Role-based access: Super Admin, Admin, Member
- Password change with validation

### 📈 System Dashboard (Super Admin)
- System-wide metrics: total users, projects, tasks, sprints
- User activity monitoring and growth analytics
- Export reports as PDF/Excel with branded formatting

---

## 🧠 AI Agents Architecture

DOIT integrates **6 distinct AI agents**, each with specialized capabilities:

| # | Agent | Stack | Capabilities |
|---|-------|-------|-------------|
| 1 | **Azure AI Foundry Agent** | Azure AI Agent Service | Task automation, project queries, member management via OpenAPI function calling |
| 2 | **LangGraph Agent** | Azure OpenAI + LangGraph + LangChain Tools | Multi-step reasoning, task/sprint CRUD, team queries with tool calling |
| 3 | **Local Private Agent** | Ollama + LlamaIndex + ChromaDB | 100% on-premise RAG agent — no data leaves your infrastructure |
| 4 | **MCP Agent** | Model Context Protocol + Groq | Connects to 4 MCP servers (Task, Sprint, Project, Member) for structured automation |
| 5 | **AI Chatbot** | Google Gemini / Azure OpenAI | Context-aware PM assistant with intent detection and persona modes |
| 6 | **Document Intelligence** | Azure Document Intelligence + GPT-4.1-mini | OCR, table extraction, KPI analysis, PDF report generation |

### Foundry Agents (Azure AI Agent Service)

Located in `Foundry_Agents/`, these are pre-built agents deployed on Azure:

| Agent | Purpose |
|-------|---------|
| **Agent905 — Main Orchestrator** | Coordinates other agents for complex workflows |
| **Agent777 — Git/PR Code Reviewer** | Reviews GitHub PRs for code quality and security |
| **Agent749 — Data Analyzer** | Analyzes uploaded datasets and generates insights |
| **Agent422 — Weather Forecaster** | Weather forecasting capabilities |
| **Data Visualizer Agent** | Generates charts and visualizations from data |
| **Email Agent** | Handles email-based notifications and automation |

---

## 🛠️ Tech Stack

### Frontend
| Technology | Purpose |
|-----------|---------|
| **React 19** | UI framework |
| **React Router 7** | Client-side routing |
| **Clerk** | SSO authentication |
| **@dnd-kit** | Drag-and-drop Kanban board |
| **React Big Calendar** | Calendar view for tasks |
| **Recharts + Chart.js** | Data visualization and charts |
| **Lucide React + React Icons** | Icon libraries |
| **Axios** | HTTP client with caching interceptor |
| **React Toastify** | Toast notifications |
| **ExcelJS / jsPDF** | Export to Excel and PDF |
| **@tanstack/react-query** | Server state management |
| **html2canvas** | Screenshot and export utilities |
| **WebSocket (custom hooks)** | Real-time Kanban and Team Chat |

### Backend
| Technology | Purpose |
|-----------|---------|
| **FastAPI** | High-performance async API framework |
| **MongoDB Atlas** | Cloud-hosted NoSQL database |
| **PyMongo** | MongoDB driver |
| **JWT + Passlib** | Authentication and password hashing |
| **WebSocket** | Real-time bidirectional communication |
| **Celery + Redis** | Background task processing (code reviews) |
| **Pydantic v2** | Request/response validation |
| **Azure OpenAI (GPT-4o, GPT-4.1-mini)** | AI language models |
| **Azure Whisper** | Speech-to-text transcription |
| **Azure TTS** | Text-to-speech synthesis |
| **Azure Document Intelligence** | OCR and document parsing |
| **Azure AI Agent Service** | Foundry Agent hosting |
| **LangChain + LangGraph** | AI agent framework with tool calling |
| **Ollama + LlamaIndex + ChromaDB** | Local RAG agent stack |
| **MCP (Model Context Protocol)** | Structured AI agent communication |
| **Bandit** | Python security scanning |
| **GitPython** | Git repository operations |
| **ReportLab** | PDF report generation |
| **Pandas** | Data analysis and CSV/Excel processing |

---

## 📂 Project Structure

```
DOIT---A-Task-Management-System/
│
├── 📁 backend-2/                    # FastAPI Backend
│   ├── main.py                      # App entry point, router registration, lifespan events
│   ├── config.py                    # Environment configuration (MongoDB, JWT)
│   ├── database.py                  # MongoDB collections and connections
│   ├── schemas.py                   # Pydantic request/response models
│   ├── dependencies.py              # Auth dependencies (get_current_user, require_admin)
│   ├── celery_app.py                # Celery worker configuration (Redis broker)
│   ├── document_intelligence.py     # Azure DI + Docling + GPT analysis engine
│   ├── init_agent.py                # Azure AI Agent service account setup
│   ├── init_db.py                   # Database initialization (super admin, channels)
│   │
│   ├── 📁 routers/                  # API route definitions (24 routers)
│   │   ├── auth_router.py           # Login, register, Clerk sync, sessions
│   │   ├── project_router.py        # Project CRUD
│   │   ├── task_router.py           # Task CRUD, labels, attachments, comments
│   │   ├── sprint_router.py         # Sprint CRUD, task assignment
│   │   ├── member_router.py         # Project member management
│   │   ├── dashboard_router.py      # Project dashboard analytics
│   │   ├── system_dashboard_router.py # System-wide admin dashboard
│   │   ├── profile_router.py        # User profile management
│   │   ├── user_router.py           # User listing and role management
│   │   ├── chat_router.py           # AI chatbot conversations
│   │   ├── team_chat_router.py      # WebSocket team chat
│   │   ├── data_viz_router.py       # Data visualization and datasets
│   │   ├── ai_assistant_router.py   # DOIT-AI assistant (GPT-4o + FLUX)
│   │   ├── azure_agent_router.py    # Azure AI Foundry Agent
│   │   ├── langgraph_agent_router.py # LangGraph AI Agent
│   │   ├── local_agent_router.py    # Local Ollama Agent
│   │   ├── mcp_agent_router.py      # MCP Agent
│   │   ├── code_review_router.py    # AI code review + GitHub webhook
│   │   ├── voice_chat_router.py     # Voice chat pipeline
│   │   ├── document_intelligence_router.py # Document analysis
│   │   ├── agent_automation_router.py      # Agent task automation
│   │   ├── agent_data_router.py            # Agent data endpoints
│   │   └── local_agent_router.py           # Local agent endpoints
│   │
│   ├── 📁 controllers/              # Business logic (23 controllers)
│   │   ├── auth_controller.py       # Authentication logic
│   │   ├── project_controller.py    # Project operations
│   │   ├── task_controller.py       # Task operations + ticket ID generation
│   │   ├── sprint_controller.py     # Sprint lifecycle management
│   │   ├── chat_controller.py       # AI chat with intent detection
│   │   ├── team_chat_controller.py  # Team chat message handling
│   │   ├── dashboard_controller.py  # Analytics computation
│   │   ├── data_viz_controller.py   # Chart generation and dataset management
│   │   ├── ai_assistant_controller.py # Multi-modal AI assistant
│   │   ├── azure_agent_controller.py  # Foundry Agent integration
│   │   ├── langgraph_agent_controller.py # LangGraph agent logic
│   │   ├── local_agent_controller.py    # Ollama + RAG agent
│   │   ├── mcp_agent_controller.py      # MCP agent orchestration
│   │   ├── code_review_controller.py    # Code review analysis
│   │   └── git_controller.py            # GitHub API integration
│   │
│   ├── 📁 models/                   # MongoDB document models
│   │   ├── user.py                  # User model
│   │   ├── project.py               # Project model with members
│   │   ├── task.py                  # Task model with full metadata
│   │   ├── sprint.py                # Sprint model with task references
│   │   ├── profile.py               # Extended user profile
│   │   ├── code_review.py           # Code review records
│   │   ├── git_activity.py          # GitHub activity tracking
│   │   └── ai_conversation.py       # AI chat conversation storage
│   │
│   ├── 📁 middleware/               # Request middleware
│   │   ├── agent_auth.py            # Agent service token authentication
│   │   └── role_middleware.py        # Role-based access control
│   │
│   ├── 📁 utils/                    # Utility modules (22 utilities)
│   │   ├── auth_utils.py            # JWT token management, session tracking
│   │   ├── azure_ai_utils.py        # Azure OpenAI client wrapper
│   │   ├── azure_agent_utils.py     # Foundry Agent communication
│   │   ├── azure_speech_utils.py    # Whisper STT + TTS utilities
│   │   ├── ai_code_reviewer.py      # AI-powered code analysis
│   │   ├── ai_data_analyzer.py      # User data context builder for AI
│   │   ├── langgraph_agent_utils.py # LangGraph agent configuration
│   │   ├── langgraph_agent_tools.py # 20+ LangChain tools for agent
│   │   ├── langgraph_agent_automation.py # Agent automation workflows
│   │   ├── local_agent_utils.py     # Ollama + ChromaDB RAG setup
│   │   ├── local_agent_automation.py # Local agent automation
│   │   ├── mcp_client_utils.py      # MCP protocol client
│   │   ├── github_utils.py          # GitHub API helper functions
│   │   ├── code_scanners.py         # Bandit security scanner integration
│   │   ├── file_parser.py           # PDF and DOCX text extraction
│   │   ├── cache_utils.py           # Response caching
│   │   ├── websocket_manager.py     # WebSocket connection manager
│   │   ├── label_utils.py           # Task label processing
│   │   ├── ticket_utils.py          # Auto ticket ID generation
│   │   └── validators.py            # Input validation helpers
│   │
│   ├── 📁 mcp_servers/              # Model Context Protocol servers
│   │   ├── task_mcp_server.py       # Task operations MCP server
│   │   ├── sprint_mcp_server.py     # Sprint operations MCP server
│   │   ├── project_mcp_server.py    # Project operations MCP server
│   │   └── member_mcp_server.py     # Member operations MCP server
│   │
│   ├── 📁 tasks/                    # Celery background tasks
│   │   └── code_review_tasks.py     # Async PR analysis tasks
│   │
│   └── 📁 uploads/                  # File upload storage
│       ├── chat_attachments/
│       ├── ai_images/
│       └── ai_attachments/
│
├── 📁 frontend/                     # React Frontend
│   ├── package.json                 # Dependencies and scripts
│   ├── 📁 public/                   # Static assets
│   └── 📁 src/
│       ├── App.js                   # Main app with routing and auth
│       ├── App.css                  # Global styles (dark/light theme)
│       ├── index.js                 # Entry point with Clerk provider
│       │
│       ├── 📁 components/           # Reusable UI components
│       │   ├── Calendar/            # Calendar view for task deadlines
│       │   ├── Charts/              # Chart components (bar, pie, line)
│       │   ├── Chat/                # AI chatbot widget
│       │   ├── CodeReview/          # Code review interface
│       │   ├── DataVizualization/   # Data viz builder and gallery
│       │   ├── Input/               # Custom input components
│       │   ├── Kanban/              # Drag-and-drop Kanban board
│       │   ├── Loader/              # Loading animations
│       │   ├── Profile/             # Profile display components
│       │   ├── Projects/            # Project cards and lists
│       │   ├── Sprints/             # Sprint board and planning
│       │   ├── Tasks/               # Task cards and detail views
│       │   └── TeamChat/            # Real-time team chat
│       │
│       ├── 📁 pages/                # Page-level components
│       │   ├── AIAssistant/         # DOIT-AI multi-agent assistant
│       │   ├── About/               # About DOIT page
│       │   ├── Auth/                # Login/Register with Clerk
│       │   ├── Dashboard/           # Project dashboard
│       │   ├── MyTasks/             # Personal task view
│       │   ├── Profile/             # Profile management
│       │   ├── Projects/            # Projects listing
│       │   ├── Sprints/             # Sprint management
│       │   ├── SuperAdminDashboard/ # Super admin overview
│       │   ├── SystemDashboard/     # System metrics dashboard
│       │   ├── Tasks/               # Task board (Kanban + Calendar)
│       │   └── Users/               # User management
│       │
│       ├── 📁 services/             # API service layers
│       │   ├── api.js               # Core API client (41KB)
│       │   ├── sprintAPI.js         # Sprint API endpoints
│       │   ├── foundryAgentAPI.js   # Azure Foundry Agent API
│       │   ├── langgraphAgentAPI.js # LangGraph Agent API
│       │   ├── localAgentAPI.js     # Local Ollama Agent API
│       │   ├── mcpAgentAPI.js       # MCP Agent API
│       │   └── agentAPI.js          # Agent automation API
│       │
│       ├── 📁 context/              # React Context providers
│       │   └── AuthContext.js       # Authentication state management
│       │
│       └── 📁 utils/                # Frontend utilities
│           ├── exportUtils.js       # PDF/Excel export functions
│           ├── systemExportUtils.js  # System dashboard exports
│           ├── requestCache.js      # API request caching
│           ├── useWebSocket.js      # WebSocket hook for team chat
│           └── useKanbanWebSocket.js # WebSocket hook for Kanban
│
├── 📁 Foundry_Agents/               # Azure AI Foundry Agent configs
│   ├── Agent905-Main-Orchestrator/
│   ├── Agent777-Git-repo-PRs-code-reviewing-agent/
│   ├── Agent749-Data-analyzing-agent/
│   ├── Agent422-Weather-Forecasting-agent/
│   ├── Data_Visualizer_agent/
│   └── Email_Agent/
│
├── 📁 .github/workflows/            # CI/CD pipelines
│   ├── main_DOIT-py-backend.yml
│   └── main_doit-backend.yml
│
├── .gitignore
├── .env                              # Environment variables (not committed)
└── README.md
```

---

## 🏁 Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **MongoDB Atlas** account (or local MongoDB instance)
- **Redis** (for Celery background tasks)
- **Azure** account (for AI services — optional for basic features)

### Backend Setup

```bash
# Navigate to backend
cd backend-2

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials (see Environment Variables section)

# Initialize Agent service account (optional)
python init_agent.py

# Start the server
python main.py
```

The API server will start at `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env
# Edit .env with your Clerk keys and API URL

# Start development server
npm start
```

The frontend will start at `http://localhost:3000`

### Start Celery Worker (for Code Reviews)

```bash
cd backend-2
celery -A celery_app worker --loglevel=info -Q code_review
```

---

## 🔐 Environment Variables

### Backend (`backend-2/.env`)

```env
# ── Database ────────────────────────────────────
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/taskdb
JWT_SECRET=your-secret-key

# ── Azure OpenAI ────────────────────────────────
AZURE_OPENAI_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# ── Azure AI Foundry Agent ──────────────────────
AZURE_AI_PROJECT_CONNECTION_STRING=your-connection-string
AZURE_AGENT_ID=your-agent-id

# ── Azure Document Intelligence ─────────────────
DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-di.cognitiveservices.azure.com/
DOCUMENT_INTELLIGENCE_KEY=your-key

# ── Azure Whisper STT ───────────────────────────
WHISPER_ENDPOINT=your-whisper-endpoint
WHISPER_API_KEY=your-whisper-key

# ── Azure TTS ───────────────────────────────────
TTS_ENDPOINT=your-tts-endpoint
TTS_API_KEY=your-tts-key

# ── Groq (for MCP Agent) ───────────────────────
GROQ_API_KEY=your-groq-key

# ── GitHub Integration ──────────────────────────
GITHUB_TOKEN=your-github-pat

# ── Redis (Celery) ──────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Agent Service Account ──────────────────────
AGENT_SERVICE_TOKEN=auto-generated
AGENT_SERVICE_USER_ID=auto-generated
```

### Frontend (`frontend/.env`)

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_CLERK_PUBLISHABLE_KEY=your-clerk-publishable-key
```

---

## 📖 API Documentation

Once the backend is running, interactive API docs are available at:

| Resource | URL |
|----------|-----|
| **Swagger UI** | `http://localhost:8000/docs` |
| **ReDoc** | `http://localhost:8000/redoc` |

### Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | Login with email/password |
| `GET` | `/api/projects` | List user's projects |
| `POST` | `/api/tasks` | Create a new task |
| `GET` | `/api/tasks/project/{id}` | Get tasks by project |
| `POST` | `/api/sprints/{project_id}` | Create a sprint |
| `POST` | `/api/chat/ask` | AI chatbot query |
| `POST` | `/api/foundry-agent/chat` | Azure Foundry Agent |
| `POST` | `/api/langgraph-agent/conversations/{id}/messages` | LangGraph Agent |
| `POST` | `/api/local-agent/conversations/{id}/messages` | Local Ollama Agent |
| `POST` | `/api/mcp-agent/conversations/{id}/messages` | MCP Agent |
| `POST` | `/api/code-review/create` | Create AI code review |
| `POST` | `/api/voice-chat/voice/chat` | Voice chat pipeline |
| `POST` | `/api/document-intelligence/analyze` | Analyze document |
| `POST` | `/api/document-intelligence/export-pdf` | Export insight report |
| `WS` | `/api/team-chat/ws/{channel_id}` | Team chat WebSocket |

---

## 🖼️ Screenshots

> Coming soon — screenshots of Dashboard, Kanban Board, AI Assistant, Team Chat, and Analytics.

---

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

---

## 📄 License

This project is proprietary. All rights reserved.

---

<p align="center">
  Built with ❤️ by the DOIT Team
</p>
