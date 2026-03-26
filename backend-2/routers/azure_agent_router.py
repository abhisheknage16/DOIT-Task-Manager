# """
# Azure AI Foundry Agent Router
# Endpoints for chatting with the MS Foundry AI Agent (asst_0uvId9Fz7NLJfxIwIzD0uN9b)

# Base path: /api/foundry-agent
# """
import uuid, os, csv, io
from fastapi import UploadFile, File
import shutil, uuid, os
from fastapi import HTTPException
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user
from controllers.azure_agent_controller import (
    create_agent_conversation,
    get_agent_conversations,
    get_agent_conversation_messages,
    delete_agent_conversation,
    send_message_to_foundry_agent,
    reset_agent_thread,
    get_foundry_thread_messages,
    agent_health_check,
)

router = APIRouter()
# # ─── Pydantic request models ───────────────────────────────────────────────────


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "Agent Chat"


class SendMessageRequest(BaseModel):
    content: str
    include_user_context: Optional[bool] = True


# ─── Conversation CRUD ─────────────────────────────────────────────────────────


@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    current_user: str = Depends(get_current_user),
):
    """Create a new Foundry Agent conversation."""
    return create_agent_conversation(user_id=current_user, title=request.title)


@router.get("/conversations")
async def list_conversations(current_user: str = Depends(get_current_user)):
    """List all Foundry Agent conversations for the current user."""
    return get_agent_conversations(user_id=current_user)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    """Get all messages in a conversation."""
    return get_agent_conversation_messages(conversation_id)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: str = Depends(get_current_user),
):
    """Delete a conversation and reset the underlying Foundry thread."""
    return delete_agent_conversation(conversation_id, current_user)


# ─── Core: send message ────────────────────────────────────────────────────────


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: str = Depends(get_current_user),
):
    """
    Send a message to the Azure AI Foundry Agent and get a response.

    The agent has access to:
    - Its own configured tools (from Azure AI Foundry portal)
    - Live DOIT user context (tasks, projects, sprints) injected automatically
    - Full multi-turn conversation history via Foundry threads
    """
    return send_message_to_foundry_agent(
        conversation_id=conversation_id,
        user_id=current_user,
        content=request.content,
        include_user_context=request.include_user_context,
    )


# ─── Thread management ─────────────────────────────────────────────────────────


@router.post("/reset-thread")
async def reset_thread(current_user: str = Depends(get_current_user)):
    """
    Reset the Foundry conversation thread for the current user.
    The next message will start a completely new conversation with the agent.
    """
    return reset_agent_thread(user_id=current_user)


@router.get("/thread-messages")
async def get_thread_messages_raw(current_user: str = Depends(get_current_user)):
    """
    Fetch raw messages directly from the Azure AI Foundry thread.
    Useful for debugging or syncing state.
    """
    return get_foundry_thread_messages(user_id=current_user)


# ─── Health ────────────────────────────────────────────────────────────────────


@router.get("/health")
async def health():
    """Check connectivity to the Azure AI Foundry Agent."""
    return agent_health_check()


# Add to azure_agent_router.py


@router.post("/conversations/{conversation_id}/upload")
async def upload_file_to_conversation(
    conversation_id: str,
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
):
    allowed_types = {
        "application/pdf",
        "text/csv",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }

    content_type = file.content_type or ""
    filename = file.filename or "uploaded_file"

    if content_type not in allowed_types and not filename.endswith(
        (".csv", ".txt", ".xlsx", ".pdf", ".docx")
    ):
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: PDF, CSV, Excel, Word, TXT",
        )

    # Read raw bytes
    raw_bytes = await file.read()

    # ── Extract readable content based on file type ──────────────────────
    extracted_content = ""

    # CSV / plain text — read directly
    if filename.endswith(".csv") or content_type in ("text/csv", "text/plain"):
        try:
            text = raw_bytes.decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(text))
            rows = list(reader)
            if rows:
                # Send headers + first 100 rows to stay within token limits
                headers = rows[0]
                data_rows = rows[1:101]
                extracted_content = (
                    f"**Columns ({len(headers)}):** {', '.join(headers)}\n\n"
                )
                extracted_content += (
                    f"**Total rows (preview up to 100):** {len(data_rows)}\n\n"
                )
                extracted_content += "**Data:**\n"
                extracted_content += " | ".join(headers) + "\n"
                extracted_content += " | ".join(["---"] * len(headers)) + "\n"
                for row in data_rows:
                    extracted_content += " | ".join(str(cell) for cell in row) + "\n"
        except Exception as e:
            extracted_content = f"Could not parse CSV: {str(e)}"

    # Excel — use openpyxl
    elif filename.endswith(".xlsx"):
        try:
            import openpyxl

            wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if rows:
                headers = [str(h) if h is not None else "" for h in rows[0]]
                extracted_content = f"**Sheet:** {ws.title}\n"
                extracted_content += (
                    f"**Columns ({len(headers)}):** {', '.join(headers)}\n\n"
                )
                extracted_content += "**Data (first 100 rows):**\n"
                extracted_content += " | ".join(headers) + "\n"
                extracted_content += " | ".join(["---"] * len(headers)) + "\n"
                for row in rows[1:101]:
                    extracted_content += (
                        " | ".join(str(c) if c is not None else "" for c in row) + "\n"
                    )
        except ImportError:
            extracted_content = "openpyxl not installed. Run: pip install openpyxl"
        except Exception as e:
            extracted_content = f"Could not parse Excel file: {str(e)}"

    # PDF — use PyPDF2 or pdfplumber
    elif filename.endswith(".pdf"):
        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                pages_text = []
                for i, page in enumerate(pdf.pages[:10]):  # First 10 pages
                    text = page.extract_text()
                    if text:
                        pages_text.append(f"[Page {i + 1}]\n{text}")
                extracted_content = "\n\n".join(pages_text)
        except ImportError:
            try:
                import PyPDF2

                reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
                pages_text = []
                for i, page in enumerate(reader.pages[:10]):
                    pages_text.append(f"[Page {i + 1}]\n{page.extract_text()}")
                extracted_content = "\n\n".join(pages_text)
            except ImportError:
                extracted_content = (
                    "PDF parsing library not installed. Run: pip install pdfplumber"
                )
        except Exception as e:
            extracted_content = f"Could not parse PDF: {str(e)}"

    # Word DOCX
    elif filename.endswith(".docx"):
        try:
            from docx import Document

            doc = Document(io.BytesIO(raw_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            extracted_content = "\n".join(paragraphs[:200])  # First 200 paragraphs
        except ImportError:
            extracted_content = (
                "python-docx not installed. Run: pip install python-docx"
            )
        except Exception as e:
            extracted_content = f"Could not parse Word document: {str(e)}"

    else:
        extracted_content = raw_bytes.decode("utf-8", errors="replace")[:5000]

    # ── Build agent message with actual file content ──────────────────────
    analysis_prompt = (
        f"The user has uploaded a file: **{filename}**\n\n"
        f"Here is the extracted content:\n\n"
        f"{extracted_content}\n\n"
        f"Please analyze this data thoroughly. Provide:\n"
        f"1. A structured summary of what the file contains\n"
        f"2. Key statistics or patterns you observe\n"
        f"3. Business insights from the data\n"
        f"4. Any anomalies or items that stand out\n"
        f"Then ask if the user would like a detailed report exported."
    )

    result = send_message_to_foundry_agent(
        conversation_id=conversation_id,
        user_id=current_user,
        content=analysis_prompt,
        include_user_context=True,
    )

    return {
        "success": True,
        "file_name": filename,
        "rows_extracted": extracted_content.count("\n"),
        "analysis_triggered": True,
        "agent_response": result.get("message", {}),
    }
