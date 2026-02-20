"""
Local Private AI Agent Utilities
Stack: Ollama (local LLM) + LlamaIndex (orchestration) + ChromaDB (vector store)

100% on-premise — no data leaves your infrastructure.

Install:
    pip install llama-index llama-index-llms-ollama llama-index-embeddings-ollama
               llama-index-vector-stores-chroma chromadb

Ollama: https://ollama.ai  →  ollama pull llama3
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL", "qwen2.5-coder:1.5b"
)  # or mistral, gemma2, etc.
OLLAMA_EMBED_MODEL = os.getenv(
    "OLLAMA_EMBED_MODEL", "nomic-embed-text"
)  # local embedding model
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")  # local disk path
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "doit_knowledge")
LOCAL_AGENT_TIMEOUT = int(os.getenv("LOCAL_AGENT_TIMEOUT", "120"))

# System prompt injected into every chat session
LOCAL_AGENT_SYSTEM_PROMPT = """You are DOIT Local AI — a private, on-premise AI assistant 
for the DOIT task management system. You have access to the user's real-time task and 
project data which will be provided as context in their messages.

Guidelines:
- Be concise, actionable and data-driven.
- When referencing tasks, always include the ticket ID.
- If asked to create or update tasks, explain clearly what should be done (you cannot 
  directly execute DB writes — that is handled by the DOIT backend).
- All data stays on-premise. You run entirely locally via Ollama.
- If you don't know something, say so — do not hallucinate.
"""

# ─── Lazy singletons ──────────────────────────────────────────────────────────
_llm = None  # Ollama LLM
_embed_model = None  # Ollama embedding model
_chroma_client = None  # ChromaDB client
_chroma_collection = None  # ChromaDB collection
_vector_store = None  # LlamaIndex ChromaVectorStore
_index = None  # LlamaIndex VectorStoreIndex


# ─── Client initialisation ────────────────────────────────────────────────────


def get_llm():
    """Return (and lazily init) the Ollama LLM via LlamaIndex."""
    global _llm
    if _llm is not None:
        return _llm
    try:
        from llama_index.llms.ollama import Ollama

        _llm = Ollama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            request_timeout=float(LOCAL_AGENT_TIMEOUT),
            system_prompt=LOCAL_AGENT_SYSTEM_PROMPT,
        )
        logger.info(f"✅ Ollama LLM ready: {OLLAMA_MODEL} @ {OLLAMA_BASE_URL}")
        return _llm
    except ImportError as exc:
        raise RuntimeError(
            "llama-index-llms-ollama not installed.\n"
            "Run: pip install llama-index-llms-ollama"
        ) from exc


def get_embed_model():
    """Return (and lazily init) the Ollama embedding model."""
    global _embed_model
    if _embed_model is not None:
        return _embed_model
    try:
        from llama_index.embeddings.ollama import OllamaEmbedding

        _embed_model = OllamaEmbedding(
            model_name=OLLAMA_EMBED_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
        logger.info(f"✅ Ollama embeddings ready: {OLLAMA_EMBED_MODEL}")
        return _embed_model
    except ImportError as exc:
        raise RuntimeError(
            "llama-index-embeddings-ollama not installed.\n"
            "Run: pip install llama-index-embeddings-ollama"
        ) from exc


def get_chroma_collection():
    """Return (and lazily init) the ChromaDB collection."""
    global _chroma_client, _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection
    try:
        import chromadb

        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _chroma_collection = _chroma_client.get_or_create_collection(CHROMA_COLLECTION)
        logger.info(f"✅ ChromaDB ready: {CHROMA_DB_PATH} / {CHROMA_COLLECTION}")
        return _chroma_collection
    except ImportError as exc:
        raise RuntimeError(
            "chromadb not installed.\nRun: pip install chromadb"
        ) from exc


def get_vector_index():
    """
    Return (and lazily init) the LlamaIndex VectorStoreIndex backed by ChromaDB.
    This is the RAG retrieval layer.
    """
    global _index, _vector_store
    if _index is not None:
        return _index
    try:
        import chromadb
        from llama_index.core import VectorStoreIndex, StorageContext, Settings
        from llama_index.vector_stores.chroma import ChromaVectorStore

        # Wire up LlamaIndex global settings
        Settings.llm = get_llm()
        Settings.embed_model = get_embed_model()

        chroma_col = get_chroma_collection()
        _vector_store = ChromaVectorStore(chroma_collection=chroma_col)
        storage_ctx = StorageContext.from_defaults(vector_store=_vector_store)

        _index = VectorStoreIndex.from_vector_store(
            vector_store=_vector_store,
            storage_context=storage_ctx,
        )
        logger.info("✅ LlamaIndex VectorStoreIndex ready")
        return _index
    except ImportError as exc:
        raise RuntimeError(
            "llama-index or llama-index-vector-stores-chroma not installed.\n"
            "Run: pip install llama-index llama-index-vector-stores-chroma"
        ) from exc


# ─── RAG: index user context into ChromaDB ────────────────────────────────────


def index_user_context(user_id: str, context: Dict[str, Any]) -> bool:
    """
    Embed and store the user's current DOIT context (tasks, projects, sprints)
    into ChromaDB so the RAG query engine can retrieve relevant chunks.

    Called before each message so the index always has fresh data.
    Returns False if RAG indexing fails, but this is non-fatal — the agent
    will still work without RAG.
    """
    try:
        from llama_index.core import (
            Document,
            VectorStoreIndex,
            StorageContext,
            Settings,
        )
        from llama_index.vector_stores.chroma import ChromaVectorStore
        import chromadb

        Settings.llm = get_llm()
        Settings.embed_model = get_embed_model()

        chroma_col = get_chroma_collection()

        # Build plain-text documents from the context dict
        docs: List[Document] = []

        # Summary document
        summary = (
            f"User: {context.get('user_name')} ({context.get('user_role')})\n"
            f"Tasks: {context.get('tasks_total')} total, "
            f"{context.get('tasks_overdue')} overdue, "
            f"{context.get('tasks_due_soon')} due soon, "
            f"{context.get('tasks_done_week')} completed this week\n"
            f"Projects: {context.get('projects_total')}\n"
            f"Active sprints: {context.get('sprints_active')}\n"
            f"Velocity (30d): {context.get('velocity_30d')} tasks\n"
            f"Blocked tasks: {context.get('blocked_tasks')}\n"
            f"Status breakdown: {context.get('status_breakdown')}\n"
            f"Priority breakdown: {context.get('priority_breakdown')}"
        )
        docs.append(
            Document(
                text=summary,
                metadata={
                    "user_id": user_id,
                    "type": "summary",
                    "ts": str(time.time()),
                },
            )
        )

        # Individual recent task documents
        for task in context.get("recent_tasks", []):
            task_text = (
                f"Task [{task.get('ticket')}]: {task.get('title')}\n"
                f"Status: {task.get('status')}  Due: {task.get('due')}"
            )
            docs.append(
                Document(
                    text=task_text,
                    metadata={
                        "user_id": user_id,
                        "type": "task",
                        "ticket": task.get("ticket", ""),
                    },
                )
            )

        # Delete stale entries for this user before re-indexing
        try:
            existing = chroma_col.get(where={"user_id": user_id})
            if existing and existing.get("ids"):
                chroma_col.delete(ids=existing["ids"])
        except Exception:
            pass  # Collection might be empty

        # Index fresh documents
        vector_store = ChromaVectorStore(chroma_collection=chroma_col)
        storage_ctx = StorageContext.from_defaults(vector_store=vector_store)
        VectorStoreIndex.from_documents(docs, storage_context=storage_ctx)

        # Refresh the singleton index
        global _index, _vector_store
        _vector_store = vector_store
        _index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_ctx,
        )

        logger.info(f"📚 Indexed {len(docs)} context docs for user {user_id}")
        return True

    except ImportError as exc:
        # ChromaDB dependency issue (Pydantic/Python compatibility)
        logger.warning(
            f"⚠️  RAG unavailable (ChromaDB import failed): {exc}. "
            "Agent will work without vector search. "
            "Fix: pip install --upgrade chromadb llama-index"
        )
        return False
    except Exception as exc:
        # Other runtime errors
        logger.warning(
            f"⚠️  RAG indexing failed (non-fatal): {type(exc).__name__}: {exc}. "
            "Agent will work without vector search."
        )
        return False


# ─── In-memory chat history (per user) ───────────────────────────────────────
# Maps user_id → list of {"role": str, "content": str}
_chat_histories: Dict[str, List[Dict[str, str]]] = {}

MAX_HISTORY = 20  # keep last N turns to avoid context overflow


def get_chat_history(user_id: str) -> List[Dict[str, str]]:
    return _chat_histories.get(user_id, [])


def append_to_history(user_id: str, role: str, content: str):
    history = _chat_histories.setdefault(user_id, [])
    history.append({"role": role, "content": content})
    # Trim to MAX_HISTORY turns (each turn = 2 entries)
    if len(history) > MAX_HISTORY * 2:
        _chat_histories[user_id] = history[-(MAX_HISTORY * 2) :]


def clear_chat_history(user_id: str):
    _chat_histories.pop(user_id, None)


# ─── Core: send a message to the local agent ──────────────────────────────────


def send_message_to_local_agent(
    user_id: str,
    message: str,
    context: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Route a user message through:
      1. (Optional) RAG retrieval from ChromaDB for relevant context chunks
      2. Ollama LLM chat with full conversation history

    Returns:
        {
            "success":   bool,
            "response":  str,
            "model":     str,
            "rag_used":  bool,
            "tokens":    dict,
        }
    """
    try:
        llm = get_llm()

        # ── Index fresh user context into ChromaDB ──────────────────────────
        rag_used = False
        rag_context_text = ""
        if context:
            indexed = index_user_context(user_id, context)
            if indexed:
                # RAG: retrieve top-3 relevant chunks for this query
                try:
                    index = get_vector_index()
                    query_engine = index.as_query_engine(
                        llm=llm,
                        similarity_top_k=3,
                    )
                    rag_result = query_engine.query(message)
                    rag_context_text = str(rag_result)
                    rag_used = True
                    logger.debug(f"RAG retrieved {len(rag_context_text)} chars")
                except Exception as rag_exc:
                    logger.warning(f"RAG retrieval failed (non-fatal): {rag_exc}")

        # ── Build prompt with history + context ─────────────────────────────
        history = get_chat_history(user_id)

        # Combine: RAG chunks + raw context summary → injected as system context
        context_block = ""
        if rag_context_text:
            context_block += f"\n\n[Retrieved Context]\n{rag_context_text}"
        if context and not rag_context_text:
            # Fallback: just serialise the raw context dict
            import json

            context_block += (
                f"\n\n[User Data]\n{json.dumps(context, default=str, indent=2)}"
            )

        augmented_message = message + context_block if context_block else message

        # ── LlamaIndex chat with Ollama ──────────────────────────────────────
        from llama_index.core.llms import ChatMessage, MessageRole

        chat_messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=LOCAL_AGENT_SYSTEM_PROMPT)
        ]

        # Inject history
        for turn in history:
            role = MessageRole.USER if turn["role"] == "user" else MessageRole.ASSISTANT
            chat_messages.append(ChatMessage(role=role, content=turn["content"]))

        # Current user message (with context appended)
        chat_messages.append(
            ChatMessage(role=MessageRole.USER, content=augmented_message)
        )

        response = llm.chat(chat_messages)
        response_text = str(response.message.content).strip()

        # ── Update history (store original message, not augmented) ───────────
        append_to_history(user_id, "user", message)
        append_to_history(user_id, "assistant", response_text)

        # ── Token estimates (Ollama doesn't always return usage) ─────────────
        tokens = {}
        raw = getattr(response, "raw", None)
        if raw and isinstance(raw, dict):
            tokens = {
                "prompt": raw.get("prompt_eval_count", 0),
                "completion": raw.get("eval_count", 0),
                "total": raw.get("prompt_eval_count", 0) + raw.get("eval_count", 0),
            }

        return {
            "success": True,
            "response": response_text,
            "model": OLLAMA_MODEL,
            "rag_used": rag_used,
            "tokens": tokens,
        }

    except Exception as exc:
        logger.error(f"Local agent error: {exc}", exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "model": OLLAMA_MODEL,
        }


# ─── Health check ─────────────────────────────────────────────────────────────


def check_local_agent_health() -> Dict[str, Any]:
    """Verify Ollama is reachable and the model is available."""
    import urllib.request

    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5) as r:
            import json as _json

            data = _json.loads(r.read())
            models = [m["name"] for m in data.get("models", [])]
            model_ok = any(OLLAMA_MODEL in m for m in models)
            return {
                "healthy": model_ok,
                "ollama_url": OLLAMA_BASE_URL,
                "model": OLLAMA_MODEL,
                "model_available": model_ok,
                "available_models": models,
                "chroma_path": CHROMA_DB_PATH,
                "error": None
                if model_ok
                else f"Model '{OLLAMA_MODEL}' not pulled yet. Run: ollama pull {OLLAMA_MODEL}",
            }
    except Exception as exc:
        return {
            "healthy": False,
            "ollama_url": OLLAMA_BASE_URL,
            "model": OLLAMA_MODEL,
            "error": f"Ollama not reachable: {exc}. Is Ollama running?",
        }
