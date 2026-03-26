# """
# Azure Speech Services Integration
# - Whisper STT (Speech-to-Text): Convert audio to text
# - TTS (Text-to-Speech): Convert text to speech audio
# """
# import os
# import requests
# from typing import BinaryIO, Optional
# from dotenv import load_dotenv

# load_dotenv()

# # Azure Whisper Configuration
# WHISPER_ENDPOINT = os.getenv("WHISPER_ENDPOINT")
# WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")

# # Azure TTS Configuration
# TTS_ENDPOINT = os.getenv("TTS_ENDPOINT")
# TTS_API_KEY = os.getenv("TTS_API_KEY")

# # Debug: Print loaded values
# print("🔍 Azure Speech Configuration:")
# print(f"  WHISPER_ENDPOINT: {WHISPER_ENDPOINT}")
# print(f"  WHISPER_KEY: {'✅ Loaded' if WHISPER_API_KEY else '❌ Missing'}")
# print(f"  TTS_ENDPOINT: {TTS_ENDPOINT}")
# print(f"  TTS_KEY: {'✅ Loaded' if TTS_API_KEY else '❌ Missing'}")


# def transcribe_audio(audio_file: BinaryIO, language: str = "en") -> dict:
#     """
#     Transcribe audio using Azure Whisper

#     Args:
#         audio_file: Audio file object (webm, mp3, wav, etc.)
#         language: Language code (default: "en")

#     Returns:
#         dict with transcription text and metadata
#     """
#     if not WHISPER_ENDPOINT or not WHISPER_API_KEY:
#         raise Exception("Azure Whisper credentials not configured. Check WHISPER_ENDPOINT and WHISPER_API_KEY.")

#     try:
#         # Prepare multipart/form-data request
#         files = {
#             'file': audio_file
#         }

#         headers = {
#             'api-key': WHISPER_API_KEY
#         }

#         # Optional: Add language parameter if endpoint supports it
#         # For translation endpoint, it translates to English
#         # For transcription endpoint, use language parameter

#         response = requests.post(
#             WHISPER_ENDPOINT,
#             headers=headers,
#             files=files,
#             timeout=30
#         )

#         if response.status_code == 200:
#             data = response.json()
#             print(f"✅ Whisper transcription successful: {data.get('text', '')[:100]}...")
#             return {
#                 "success": True,
#                 "text": data.get("text", ""),
#                 "language": data.get("language"),
#                 "duration": data.get("duration"),
#             }
#         else:
#             print(f"❌ Whisper API error: {response.status_code} - {response.text}")
#             return {
#                 "success": False,
#                 "error": f"Whisper API returned status {response.status_code}",
#                 "details": response.text
#             }

#     except Exception as e:
#         print(f"❌ Whisper transcription error: {e}")
#         return {
#             "success": False,
#             "error": str(e)
#         }


# def text_to_speech(
#     text: str,
#     voice: str = "en-US-AvaMultilingualNeural",
#     speed: float = 1.0,
#     output_format: str = "mp3"
# ) -> dict:
#     """
#     Convert text to speech using Azure TTS

#     Args:
#         text: Text to convert to speech
#         voice: Voice name (default: Ava Multilingual Neural)
#         speed: Speech rate (0.5 to 2.0, default: 1.0)
#         output_format: Audio format (mp3, wav, ogg, default: mp3)

#     Returns:
#         dict with audio bytes and metadata
#     """
#     if not TTS_ENDPOINT or not TTS_API_KEY:
#         raise Exception("Azure TTS credentials not configured. Check TTS_ENDPOINT and TTS_API_KEY.")

#     try:
#         headers = {
#             'api-key': TTS_API_KEY,
#             'Content-Type': 'application/json'
#         }

#         # Build request payload
#         payload = {
#             "input": text,
#             "voice": voice,
#             "response_format": output_format,
#             "speed": speed
#         }

#         response = requests.post(
#             TTS_ENDPOINT,
#             headers=headers,
#             json=payload,
#             timeout=30
#         )

#         if response.status_code == 200:
#             audio_bytes = response.content
#             print(f"✅ TTS synthesis successful: {len(audio_bytes)} bytes")
#             return {
#                 "success": True,
#                 "audio": audio_bytes,
#                 "format": output_format,
#                 "size": len(audio_bytes)
#             }
#         else:
#             print(f"❌ TTS API error: {response.status_code} - {response.text}")
#             return {
#                 "success": False,
#                 "error": f"TTS API returned status {response.status_code}",
#                 "details": response.text
#             }

#     except Exception as e:
#         print(f"❌ TTS synthesis error: {e}")
#         return {
#             "success": False,
#             "error": str(e)
#         }


# # Voice presets for different use cases
# VOICE_PRESETS = {
#     "friendly": {
#         "voice": "en-US-AvaMultilingualNeural",
#         "speed": 1.05,
#         "description": "Warm, friendly female voice"
#     },
#     "professional": {
#         "voice": "en-US-AndrewMultilingualNeural",
#         "speed": 1.0,
#         "description": "Professional male voice"
#     },
#     "direct": {
#         "voice": "en-US-BrianMultilingualNeural",
#         "speed": 1.1,
#         "description": "Direct, clear male voice"
#     },
#     "assistant": {
#         "voice": "en-US-EmmaMultilingualNeural",
#         "speed": 1.0,
#         "description": "Clear, helpful female voice"
#     }
# }


# def get_voice_config(persona: str = "friendly") -> dict:
#     """Get voice configuration for a persona"""
#     return VOICE_PRESETS.get(persona, VOICE_PRESETS["friendly"])
"""
Azure Speech Services Integration - FIXED VERSION
- Whisper STT (Speech-to-Text): Convert audio to text
- TTS (Text-to-Speech): Convert text to speech audio

FIX: Proper MIME type handling and file pointer management for Azure Whisper API
"""

import os
import requests
from typing import BinaryIO, Optional
from dotenv import load_dotenv

load_dotenv(override=True)

# Azure Whisper Configuration
WHISPER_ENDPOINT = os.getenv("WHISPER_ENDPOINT")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")

# Azure TTS Configuration
TTS_ENDPOINT = os.getenv("TTS_ENDPOINT")
TTS_API_KEY = os.getenv("TTS_API_KEY")

# Debug: Print loaded values
print("🔍 Azure Speech Configuration:")
print(f"  WHISPER_ENDPOINT: {WHISPER_ENDPOINT}")
print(f"  WHISPER_KEY: {'✅ Loaded' if WHISPER_API_KEY else '❌ Missing'}")
print(f"  TTS_ENDPOINT: {TTS_ENDPOINT}")
print(f"  TTS_KEY: {'✅ Loaded' if TTS_API_KEY else '❌ Missing'}")


def transcribe_audio(audio_file: BinaryIO, language: str = "en") -> dict:
    """
    Transcribe audio using Azure Whisper

    Args:
        audio_file: Audio file object (webm, mp3, wav, etc.)
        language: Language code (default: "en")

    Returns:
        dict with transcription text and metadata
    """
    if not WHISPER_ENDPOINT or not WHISPER_API_KEY:
        raise Exception(
            "Azure Whisper credentials not configured. Check WHISPER_ENDPOINT and WHISPER_API_KEY."
        )

    try:
        # Resolve filename and MIME type so Whisper can detect the audio format.
        # Without a proper filename/content-type, the API returns a 400 "Unrecognized file format" error.
        filename = getattr(audio_file, "name", None) or "audio.webm"

        MIME_MAP = {
            "webm": "audio/webm",
            "mp3": "audio/mpeg",
            "mp4": "audio/mp4",
            "mpeg": "audio/mpeg",
            "mpga": "audio/mpeg",
            "m4a": "audio/mp4",
            "wav": "audio/wav",
            "flac": "audio/flac",
            "ogg": "audio/ogg",
            "oga": "audio/ogg",
        }
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
        content_type = MIME_MAP.get(ext, f"audio/{ext}")

        # CRITICAL FIX: Reset file pointer to beginning
        # If the file was already read (e.g., during size check), we need to reset it
        if hasattr(audio_file, "seek"):
            audio_file.seek(0)

        # Pass (filename, file_object, content_type) tuple — required by Whisper
        files = {"file": (filename, audio_file, content_type)}

        headers = {"api-key": WHISPER_API_KEY}

        print(
            f"🎤 Sending to Whisper: filename={filename}, content_type={content_type}, size={len(audio_file.read() if hasattr(audio_file, 'read') else b'')} bytes"
        )

        # CRITICAL: Reset again after size check
        if hasattr(audio_file, "seek"):
            audio_file.seek(0)

        # Optional: Add language parameter if endpoint supports it
        # For translation endpoint, it translates to English
        # For transcription endpoint, use language parameter

        response = requests.post(
            WHISPER_ENDPOINT, headers=headers, files=files, timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print(
                f"✅ Whisper transcription successful: {data.get('text', '')[:100]}..."
            )
            return {
                "success": True,
                "text": data.get("text", ""),
                "language": data.get("language"),
                "duration": data.get("duration"),
            }
        else:
            print(f"❌ Whisper API error: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": f"Whisper API returned status {response.status_code}",
                "details": response.text,
            }

    except Exception as e:
        print(f"❌ Whisper transcription error: {e}")
        return {"success": False, "error": str(e)}


def text_to_speech(
    text: str,
    voice: str = "en-US-AvaMultilingualNeural",
    speed: float = 1.0,
    output_format: str = "mp3",
) -> dict:
    """
    Convert text to speech using Azure TTS

    Args:
        text: Text to convert to speech
        voice: Voice name (default: Ava Multilingual Neural)
        speed: Speech rate (0.5 to 2.0, default: 1.0)
        output_format: Audio format (mp3, wav, ogg, default: mp3)

    Returns:
        dict with audio bytes and metadata
    """
    if not TTS_ENDPOINT or not TTS_API_KEY:
        raise Exception(
            "Azure TTS credentials not configured. Check TTS_ENDPOINT and TTS_API_KEY."
        )

    try:
        headers = {"api-key": TTS_API_KEY, "Content-Type": "application/json"}

        # Build request payload
        payload = {
            "input": text,
            "voice": voice,
            "response_format": output_format,
            "speed": speed,
        }

        response = requests.post(
            TTS_ENDPOINT, headers=headers, json=payload, timeout=30
        )

        if response.status_code == 200:
            audio_bytes = response.content
            print(f"✅ TTS synthesis successful: {len(audio_bytes)} bytes")
            return {
                "success": True,
                "audio": audio_bytes,
                "format": output_format,
                "size": len(audio_bytes),
            }
        else:
            print(f"❌ TTS API error: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": f"TTS API returned status {response.status_code}",
                "details": response.text,
            }

    except Exception as e:
        print(f"❌ TTS synthesis error: {e}")
        return {"success": False, "error": str(e)}


# Voice presets for different use cases
VOICE_PRESETS = {
    "friendly": {
        "voice": "en-US-AvaMultilingualNeural",
        "speed": 1.05,
        "description": "Warm, friendly female voice",
    },
    "professional": {
        "voice": "en-US-AndrewMultilingualNeural",
        "speed": 1.0,
        "description": "Professional male voice",
    },
    "direct": {
        "voice": "en-US-BrianMultilingualNeural",
        "speed": 1.1,
        "description": "Direct, clear male voice",
    },
    "assistant": {
        "voice": "en-US-EmmaMultilingualNeural",
        "speed": 1.0,
        "description": "Clear, helpful female voice",
    },
}


def get_voice_config(persona: str = "friendly") -> dict:
    """Get voice configuration for a persona"""
    return VOICE_PRESETS.get(persona, VOICE_PRESETS["friendly"])
