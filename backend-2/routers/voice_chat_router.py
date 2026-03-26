# """
# voice_chat_router.py
# Voice Chat Interface with Azure Whisper STT + GPT-4o-mini + Azure TTS

# Flow:
# 1. Frontend sends audio file (webm/mp3/wav)
# 2. Backend transcribes with Azure Whisper
# 3. GPT-4o-mini generates response (streaming)
# 4. Azure TTS converts response to audio
# 5. Stream audio back to frontend
# """

# from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
# from fastapi.responses import StreamingResponse
# from controllers import chat_controller
# from dependencies import get_current_user
# from utils.azure_speech_utils import transcribe_audio, text_to_speech, get_voice_config
# from utils.azure_ai_utils import chat_completion_streaming
# from utils.ai_data_analyzer import analyze_user_data_for_ai, build_ai_system_prompt
# import json
# import io
# import asyncio

# router = APIRouter()


# @router.post("/voice/transcribe")
# async def transcribe_voice(
#     audio: UploadFile = File(...),
#     user_id: str = Depends(get_current_user)
# ):
#     """
#     Transcribe audio file using Azure Whisper
    
#     Accepts: webm, mp3, wav, m4a, ogg
#     Returns: { text, language, duration }
#     """
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")
    
#     try:
#         # Read audio file
#         audio_bytes = await audio.read()
#         audio_file = io.BytesIO(audio_bytes)
#         audio_file.name = audio.filename or "audio.webm"
        
#         print(f"🎤 [Whisper] Transcribing audio: {audio.filename} ({len(audio_bytes)} bytes)")
        
#         # Transcribe with Azure Whisper
#         result = transcribe_audio(audio_file)
        
#         if not result.get("success"):
#             raise HTTPException(
#                 status_code=500,
#                 detail=result.get("error", "Transcription failed")
#             )
        
#         return {
#             "success": True,
#             "text": result.get("text", ""),
#             "language": result.get("language"),
#             "duration": result.get("duration"),
#         }
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"❌ [Whisper] Error: {e}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# @router.post("/voice/chat")
# async def voice_chat(
#     audio: UploadFile = File(...),
#     persona: str = "friendly",
#     conversation_history: str = "[]",  # JSON string
#     user_id: str = Depends(get_current_user)
# ):
#     """
#     Complete voice chat flow:
#     1. Transcribe audio with Whisper
#     2. Generate response with GPT-4o-mini (streaming)
#     3. Convert response to speech with TTS
#     4. Stream audio back
    
#     Returns: Audio stream (MP3)
#     """
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")
    
#     try:
#         # ── 1. Transcribe audio ────────────────────────────────────────
#         audio_bytes = await audio.read()
#         audio_file = io.BytesIO(audio_bytes)
#         audio_file.name = audio.filename or "audio.webm"
        
#         print(f"🎤 [Voice Chat] Step 1: Transcribing audio ({len(audio_bytes)} bytes)")
        
#         transcription = transcribe_audio(audio_file)
#         if not transcription.get("success"):
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"Transcription failed: {transcription.get('error')}"
#             )
        
#         user_message = transcription.get("text", "").strip()
#         if not user_message:
#             raise HTTPException(status_code=400, detail="No speech detected")
        
#         print(f"✅ Transcribed: '{user_message[:100]}...'")
        
#         # ── 2. Generate AI response ────────────────────────────────────
#         print(f"🤖 [Voice Chat] Step 2: Generating AI response")
        
#         # Parse conversation history
#         try:
#             history = json.loads(conversation_history)
#         except:
#             history = []
        
#         # Detect intent and gather context (from existing chat_controller logic)
#         intent = chat_controller.detect_intent(user_message)
#         is_pm_query = intent in [
#             "risk_analysis", "assignment_suggestion", "team_inquiry",
#             "sprint_status", "workload_check", "blocker_analysis",
#             "velocity_check", "recommendation", "project_inquiry"
#         ]
        
#         # Get context
#         if is_pm_query:
#             sprint_name = None
#             project_name = None
#             if intent == "sprint_status":
#                 sprint_name = chat_controller.extract_sprint_name(user_message)
#             if intent == "project_inquiry":
#                 project_name = chat_controller.extract_project_name(user_message)
            
#             context = chat_controller.gather_pm_context(
#                 user_id, None, intent,
#                 sprint_name=sprint_name,
#                 project_name=project_name
#             )
#             system_prompt = chat_controller.build_pm_system_prompt(persona, context)
#         else:
#             user_data = analyze_user_data_for_ai(user_id)
#             system_prompt = build_ai_system_prompt(user_data)
#             context = user_data
        
#         # Build messages
#         from utils.azure_ai_utils import get_context_with_system_prompt, truncate_context
        
#         prior_messages = chat_controller.build_messages(history, user_message)
#         messages = get_context_with_system_prompt(
#             prior_messages[:-1],
#             system_prompt=system_prompt
#         )
#         messages.append({"role": "user", "content": user_message})
#         messages = truncate_context(messages, max_tokens=8000)
        
#         # Stream GPT response and collect full text
#         full_response = ""
#         for chunk in chat_completion_streaming(messages, max_tokens=1500):
#             full_response += chunk
        
#         print(f"✅ AI Response: '{full_response[:100]}...'")
        
#         # ── 3. Convert to speech ───────────────────────────────────────
#         print(f"🔊 [Voice Chat] Step 3: Converting to speech")
        
#         voice_config = get_voice_config(persona)
#         tts_result = text_to_speech(
#             full_response,
#             voice=voice_config["voice"],
#             speed=voice_config["speed"],
#             output_format="mp3"
#         )
        
#         if not tts_result.get("success"):
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"TTS failed: {tts_result.get('error')}"
#             )
        
#         audio_bytes = tts_result.get("audio")
#         print(f"✅ Audio generated: {len(audio_bytes)} bytes")
        
#         # ── 4. Return audio stream ─────────────────────────────────────
#         return StreamingResponse(
#             io.BytesIO(audio_bytes),
#             media_type="audio/mpeg",
#             headers={
#                 "X-Transcript": user_message,  # Include transcript in header
#                 "X-Response-Text": full_response[:500],  # Truncated response text
#                 "Content-Disposition": "inline; filename=response.mp3"
#             }
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"❌ [Voice Chat] Error: {e}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Voice chat failed: {str(e)}")


# @router.post("/voice/synthesize")
# async def synthesize_speech(
#     text: str,
#     persona: str = "friendly",
#     user_id: str = Depends(get_current_user)
# ):
#     """
#     Convert text to speech using Azure TTS
    
#     Body: { "text": "...", "persona": "friendly" }
#     Returns: Audio stream (MP3)
#     """
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")
    
#     if not text or not text.strip():
#         raise HTTPException(status_code=400, detail="Text is required")
    
#     try:
#         voice_config = get_voice_config(persona)
#         result = text_to_speech(
#             text,
#             voice=voice_config["voice"],
#             speed=voice_config["speed"],
#             output_format="mp3"
#         )
        
#         if not result.get("success"):
#             raise HTTPException(
#                 status_code=500,
#                 detail=result.get("error", "TTS failed")
#             )
        
#         audio_bytes = result.get("audio")
        
#         return StreamingResponse(
#             io.BytesIO(audio_bytes),
#             media_type="audio/mpeg",
#             headers={
#                 "Content-Disposition": "inline; filename=speech.mp3"
#             }
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"❌ [TTS] Error: {e}")
#         raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


# @router.get("/voice/health")
# async def voice_health(user_id: str = Depends(get_current_user)):
#     """Check Azure Speech services health"""
#     try:
#         from utils.azure_speech_utils import WHISPER_ENDPOINT, WHISPER_API_KEY, TTS_ENDPOINT, TTS_API_KEY
        
#         return {
#             "success": True,
#             "services": {
#                 "whisper": {
#                     "configured": bool(WHISPER_ENDPOINT and WHISPER_API_KEY),
#                     "endpoint": WHISPER_ENDPOINT[:50] + "..." if WHISPER_ENDPOINT else None
#                 },
#                 "tts": {
#                     "configured": bool(TTS_ENDPOINT and TTS_API_KEY),
#                     "endpoint": TTS_ENDPOINT[:50] + "..." if TTS_ENDPOINT else None
#                 }
#             },
#             "voice_presets": list(get_voice_config.__globals__['VOICE_PRESETS'].keys())
#         }
#     except Exception as e:
#         return {
#             "success": False,
#             "error": str(e)
#         }

"""
voice_chat_router.py
────────────────────
DOIT Voice Chat — Full Pipeline
  Audio (MediaRecorder) → Azure Whisper STT → Azure AI Foundry Agent → Azure TTS → Audio

Endpoints
---------
POST /api/voice-chat/voice/chat        — Full round-trip (audio in → audio out)
POST /api/voice-chat/voice/transcribe  — Whisper STT only
POST /api/voice-chat/voice/synthesize  — Azure TTS only
GET  /api/voice-chat/voice/health      — Service status
"""

import os
import json
import tempfile
import logging
import httpx
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# ── Auth dependency (mirrors the rest of the app) ─────────────────────────────
try:
    from dependencies import get_current_user
except ImportError:
    async def get_current_user(request=None):
        return "dev-user"

# ── Azure config ──────────────────────────────────────────────────────────────
WHISPER_ENDPOINT  = os.getenv("WHISPER_ENDPOINT")      # full URL with ?api-version=…
WHISPER_API_KEY   = os.getenv("WHISPER_API_KEY") or os.getenv("AZURE_OPENAI_KEY")

TTS_ENDPOINT      = os.getenv("TTS_ENDPOINT")          # full URL with ?api-version=…
TTS_API_KEY       = os.getenv("TTS_API_KEY") or os.getenv("AZURE_OPENAI_KEY")

# Azure AI Foundry Agent (reuse from azure_agent_utils)
try:
    from utils.azure_agent_utils import send_message_to_agent, get_or_create_thread
    FOUNDRY_AVAILABLE = True
    logger.info("✅ Azure AI Foundry Agent utils imported")
except Exception as exc:
    FOUNDRY_AVAILABLE = False
    logger.warning(f"⚠️  Azure AI Foundry Agent utils not available: {exc}")

# ── Voice personas → TTS voice mapping ───────────────────────────────────────
PERSONA_VOICES = {
    "friendly":     "alloy",
    "professional": "onyx",
    "direct":       "echo",
    "assistant":    "nova",
}

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Azure Whisper STT
# ═══════════════════════════════════════════════════════════════════════════════

def _normalise_audio_filename(filename: str, content_type: str = "") -> tuple[str, str]:
    """
    Return (safe_filename, mime_type).

    MediaRecorder in Chrome sends filename='blob' with no extension.
    We derive the extension from content_type when the filename has none.
    """
    mime_map = {
        ".webm": "audio/webm",
        ".mp4":  "audio/mp4",
        ".m4a":  "audio/mp4",
        ".mp3":  "audio/mpeg",
        ".wav":  "audio/wav",
        ".ogg":  "audio/ogg",
    }
    ct_ext_map = {
        "audio/webm": (".webm", "audio/webm"),
        "audio/mp4":  (".mp4",  "audio/mp4"),
        "audio/mpeg": (".mp3",  "audio/mpeg"),
        "audio/wav":  (".wav",  "audio/wav"),
        "audio/ogg":  (".ogg",  "audio/ogg"),
        "video/webm": (".webm", "audio/webm"),  # some browsers report video/webm
    }

    ext = Path(filename).suffix.lower()

    if ext in mime_map:
        # filename already has a valid extension
        return filename, mime_map[ext]

    # No usable extension — derive from content_type
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in ct_ext_map:
        new_ext, mime = ct_ext_map[ct]
        return f"audio{new_ext}", mime

    # Fallback: assume webm (most common from Chrome MediaRecorder)
    logger.warning(f"Unknown audio format: filename={filename!r}, content_type={content_type!r} — defaulting to webm")
    return "audio.webm", "audio/webm"


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm", content_type: str = "") -> dict:
    """
    Send audio bytes to Azure Whisper and return transcription result.
    Uses the WHISPER_ENDPOINT from .env (already includes deployment + api-version).
    """
    if not WHISPER_ENDPOINT or not WHISPER_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Whisper endpoint/key not configured (WHISPER_ENDPOINT, WHISPER_API_KEY)"
        )

    safe_filename, mime = _normalise_audio_filename(filename, content_type)
    logger.info(f"🎤 Transcribing {len(audio_bytes)} bytes | file={safe_filename} | mime={mime}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            WHISPER_ENDPOINT,
            headers={"api-key": WHISPER_API_KEY},
            files={"file": (safe_filename, audio_bytes, mime)},
            data={"response_format": "json"},
        )

    if resp.status_code != 200:
        logger.error(f"Whisper error {resp.status_code}: {resp.text[:300]}")
        raise HTTPException(
            status_code=502,
            detail=f"Whisper transcription failed: HTTP {resp.status_code}"
        )

    result = resp.json()
    transcript = result.get("text", "").strip()
    logger.info(f"✅ Transcript: {transcript[:80]}…")
    return {
        "text": transcript,
        "language": result.get("language", "en"),
        "duration": result.get("duration"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Azure AI Foundry Agent
# ═══════════════════════════════════════════════════════════════════════════════

async def query_foundry_agent(user_id: str, transcript: str, conversation_history: list) -> str:
    """
    Send transcript to Azure AI Foundry Agent and return the text reply.
    Falls back to a simple echo if the agent is unavailable.
    """
    if not FOUNDRY_AVAILABLE:
        return (
            "I'm sorry, the AI agent is currently unavailable. "
            "Please check that the Azure AI Foundry Agent is configured correctly."
        )

    # Build context string from recent conversation history
    context = None
    if conversation_history:
        recent = conversation_history[-6:]  # last 3 turns
        context = {
            "conversation_history": recent,
            "interface": "voice",
            "instruction": (
                "You are a voice assistant. Keep replies concise (2-4 sentences). "
                "No markdown, no bullet points — plain spoken language only."
            ),
        }

    logger.info(f"🤖 Querying Foundry Agent for user {user_id}: {transcript[:60]}…")

    result = send_message_to_agent(
        user_id=user_id,
        message=transcript,
        context=context,
    )

    if not result.get("success"):
        err = result.get("error", "Unknown agent error")
        logger.error(f"Agent error: {err}")
        raise HTTPException(status_code=502, detail=f"Agent error: {err}")

    response_text = result.get("response", "").strip()
    logger.info(f"✅ Agent reply: {response_text[:80]}…")
    return response_text


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Azure TTS
# ═══════════════════════════════════════════════════════════════════════════════

async def synthesize_speech(text: str, voice: str = "alloy") -> bytes:
    """
    Send text to Azure TTS and return raw MP3 audio bytes.
    Uses the TTS_ENDPOINT from .env (already includes deployment + api-version).
    """
    if not TTS_ENDPOINT or not TTS_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="TTS endpoint/key not configured (TTS_ENDPOINT, TTS_API_KEY)"
        )

    payload = {
        "model": "tts",
        "input": text,
        "voice": voice,
        "response_format": "mp3",
    }

    logger.info(f"🔊 Synthesizing {len(text)} chars with voice '{voice}'")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            TTS_ENDPOINT,
            headers={
                "api-key": TTS_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code != 200:
        logger.error(f"TTS error {resp.status_code}: {resp.text[:300]}")
        raise HTTPException(
            status_code=502,
            detail=f"TTS synthesis failed: HTTP {resp.status_code}"
        )

    audio_bytes = resp.content
    logger.info(f"✅ TTS produced {len(audio_bytes)} bytes of audio")
    return audio_bytes


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT: Full voice round-trip
# POST /api/voice-chat/voice/chat
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/voice/chat")
async def voice_chat(
    audio: UploadFile = File(..., description="Audio recording (webm / mp4 / wav)"),
    persona: str = Form("friendly"),
    conversation_history: str = Form("[]"),
    user_id: str = Depends(get_current_user),
):
    """
    Full voice pipeline:
      1. Azure Whisper — transcribe user audio
      2. Azure AI Foundry Agent — generate reply
      3. Azure TTS — synthesize reply to audio
    Returns: audio/mpeg stream with X-Transcript and X-Response-Text headers.
    """
    # ── 1. Read uploaded audio ────────────────────────────────────────────────
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    filename     = audio.filename or "audio.webm"
    content_type = audio.content_type or ""
    logger.info(f"🎙️ Voice chat — user={user_id}, file={filename!r}, content_type={content_type!r}, size={len(audio_bytes)} bytes")

    # ── 2. Parse conversation history ─────────────────────────────────────────
    try:
        history: list = json.loads(conversation_history)
    except Exception:
        history = []

    # ── 3. Whisper STT ────────────────────────────────────────────────────────
    stt_result   = await transcribe_audio(audio_bytes, filename, content_type)
    transcript   = stt_result["text"]

    if not transcript:
        raise HTTPException(status_code=422, detail="No speech detected in audio")

    # ── 4. Azure AI Foundry Agent ─────────────────────────────────────────────
    response_text = await query_foundry_agent(user_id, transcript, history)

    # ── 5. Azure TTS ──────────────────────────────────────────────────────────
    voice      = PERSONA_VOICES.get(persona, "alloy")
    audio_out  = await synthesize_speech(response_text, voice)

    # ── 6. Stream audio back with metadata headers ────────────────────────────
    safe_transcript    = transcript.replace("\n", " ")[:500]
    safe_response_text = response_text.replace("\n", " ")[:1000]

    return StreamingResponse(
        iter([audio_out]),
        media_type="audio/mpeg",
        headers={
            "X-Transcript":      safe_transcript,
            "X-Response-Text":   safe_response_text,
            "Cache-Control":     "no-cache",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT: Whisper STT only
# POST /api/voice-chat/voice/transcribe
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/voice/transcribe")
async def transcribe_only(
    audio: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """Transcribe audio using Azure Whisper only (no agent, no TTS)."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    result = await transcribe_audio(audio_bytes, audio.filename or "audio.webm", audio.content_type or "")
    return JSONResponse(content={"success": True, **result})


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT: Azure TTS only
# POST /api/voice-chat/voice/synthesize
# ═══════════════════════════════════════════════════════════════════════════════

class SynthesizeRequest(BaseModel):
    text: str
    persona: str = "friendly"

@router.post("/voice/synthesize")
async def synthesize_only(
    body: SynthesizeRequest,
    user_id: str = Depends(get_current_user),
):
    """Convert text to speech via Azure TTS only."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    voice     = PERSONA_VOICES.get(body.persona, "alloy")
    audio_out = await synthesize_speech(body.text, voice)

    return StreamingResponse(
        iter([audio_out]),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT: Health check
# GET /api/voice-chat/voice/health
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/voice/health")
async def voice_health():
    """Check availability of each voice-pipeline service."""
    status = {
        "pipeline": "Whisper → Azure AI Foundry Agent → TTS",
        "whisper": {
            "configured": bool(WHISPER_ENDPOINT and WHISPER_API_KEY),
            "endpoint":   (WHISPER_ENDPOINT or "")[:60] + "…" if WHISPER_ENDPOINT else None,
        },
        "foundry_agent": {
            "available": FOUNDRY_AVAILABLE,
        },
        "tts": {
            "configured": bool(TTS_ENDPOINT and TTS_API_KEY),
            "endpoint":   (TTS_ENDPOINT or "")[:60] + "…" if TTS_ENDPOINT else None,
        },
        "voice_presets": list(PERSONA_VOICES.keys()),
    }

    all_ok = (
        status["whisper"]["configured"]
        and status["foundry_agent"]["available"]
        and status["tts"]["configured"]
    )
    status["healthy"] = all_ok

    return JSONResponse(content=status, status_code=200 if all_ok else 503)