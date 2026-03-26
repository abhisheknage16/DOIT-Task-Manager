"""
Azure AI Foundry Integration Utilities
For Azure OpenAI chat and FLUX-1.1-pro image generation
"""
from openai import AzureOpenAI, NotFoundError
import requests
import base64
from typing import List, Dict, Optional, Tuple
import os
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs

# Load environment variables
load_dotenv(override=True)

# Azure OpenAI chat configuration (env-driven)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-09-01")
AZURE_OPENAI_API_VERSION_FALLBACKS = [
    v.strip()
    for v in os.getenv(
        "AZURE_OPENAI_API_VERSION_FALLBACKS",
        "2024-12-01-preview,2024-10-21"
    ).split(",")
    if v.strip()
]

# Dedicated GPT-4.1-mini profile (used by Data-Viz Insights / Global Insights flows)
AZURE_OPENAI_ENDPOINT_GPT_4_MINI = os.getenv("AZURE_OPENAI_ENDPOINT_GPT_4_mini") or os.getenv("AZURE_OPENAI_ENDPOINT_GPT_4_MINI")
AZURE_OPENAI_API_VERSION_GPT_4_MINI = os.getenv("AZURE_OPENAI_API_VERSION_GPT_4_mini") or os.getenv("AZURE_OPENAI_API_VERSION_GPT_4_MINI")
AZURE_OPENAI_DEPLOYMENT_GPT_4_MINI = os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT_4_mini") or os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT_4_MINI")

# Azure AI FLUX Configuration for image generation
AZURE_FLUX_ENDPOINT = os.getenv("AZURE_FLUX_ENDPOINT")
AZURE_FLUX_KEY = os.getenv("AZURE_FLUX_KEY")
AZURE_FLUX_MODEL = os.getenv("AZURE_FLUX_MODEL")

# Debug: Print loaded values (remove after testing)
print("🔍 Azure AI Configuration:")
print(f"  ENDPOINT: {AZURE_OPENAI_ENDPOINT}")
print(f"  DEPLOYMENT: {AZURE_OPENAI_DEPLOYMENT}")
print(f"  API_VERSION: {AZURE_OPENAI_API_VERSION}")
print(f"  KEY: {'✅ Loaded' if AZURE_OPENAI_KEY else '❌ Missing'}")


def _create_azure_client(api_version: str) -> AzureOpenAI:
    return AzureOpenAI(
        api_version=api_version,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
    )


def _normalize_azure_chat_endpoint(endpoint_raw: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Accept either:
    1) Azure resource endpoint: https://<resource>.openai.azure.com/
    2) Full chat completions URL:
       https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=...

    Returns: (base_endpoint, deployment_from_url, api_version_from_url)
    """
    if not endpoint_raw:
        return None, None, None

    parsed = urlparse(endpoint_raw)
    if not parsed.scheme or not parsed.netloc:
        return endpoint_raw, None, None

    base_endpoint = f"{parsed.scheme}://{parsed.netloc}"
    deployment_from_url = None
    api_version_from_url = None

    path = parsed.path or ""
    marker = "/openai/deployments/"
    if marker in path:
        deployment_part = path.split(marker, 1)[1]
        deployment_from_url = deployment_part.split("/", 1)[0] if deployment_part else None

    query = parse_qs(parsed.query)
    api_versions = query.get("api-version", [])
    if api_versions:
        api_version_from_url = api_versions[0]

    return base_endpoint, deployment_from_url, api_version_from_url


def get_gpt4_mini_chat_config() -> Dict[str, Optional[str]]:
    endpoint_raw = AZURE_OPENAI_ENDPOINT_GPT_4_MINI or AZURE_OPENAI_ENDPOINT
    endpoint_base, deployment_from_url, api_version_from_url = _normalize_azure_chat_endpoint(endpoint_raw)

    deployment = AZURE_OPENAI_DEPLOYMENT_GPT_4_MINI or deployment_from_url or AZURE_OPENAI_DEPLOYMENT
    api_version = AZURE_OPENAI_API_VERSION_GPT_4_MINI or api_version_from_url or AZURE_OPENAI_API_VERSION

    return {
        "endpoint_raw": endpoint_raw,
        "endpoint": endpoint_base,
        "deployment": deployment,
        "api_version": api_version,
        "key_loaded": bool(AZURE_OPENAI_KEY),
    }


def _api_version_candidates() -> List[str]:
    candidates = [AZURE_OPENAI_API_VERSION, *AZURE_OPENAI_API_VERSION_FALLBACKS]
    unique = []
    for version in candidates:
        if version and version not in unique:
            unique.append(version)
    return unique


def _chat_completions_create(request_kwargs: Dict):
    """Create chat completion with automatic api-version fallback on 404."""
    global azure_client, AZURE_OPENAI_API_VERSION

    if azure_client is None:
        raise Exception("Azure OpenAI client not initialized. Check environment variables.")

    try:
        return azure_client.chat.completions.create(**request_kwargs)
    except NotFoundError as original_error:
        tried_versions = [AZURE_OPENAI_API_VERSION]

        for api_version in _api_version_candidates():
            if api_version == AZURE_OPENAI_API_VERSION:
                continue

            tried_versions.append(api_version)

            try:
                trial_client = _create_azure_client(api_version)
                response = trial_client.chat.completions.create(**request_kwargs)

                azure_client = trial_client
                AZURE_OPENAI_API_VERSION = api_version
                print(f"⚠️ Azure 404 recovered by switching API version to: {api_version}")
                return response
            except NotFoundError:
                continue

        deployment = request_kwargs.get("model", "<unknown>")
        raise Exception(
            "Azure OpenAI returned 404 (Resource not found). "
            f"Deployment '{deployment}' was not reachable at endpoint '{AZURE_OPENAI_ENDPOINT}'. "
            "Verify that AZURE_OPENAI_DEPLOYMENT is the Azure deployment name (not just model name), "
            "the deployment exists in this exact Azure OpenAI resource, and API version is supported. "
            f"API versions tried: {', '.join(tried_versions)}"
        ) from original_error


# Initialize Azure OpenAI client (for text chat)
try:
    azure_client = _create_azure_client(AZURE_OPENAI_API_VERSION)
    print("✅ Azure OpenAI client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Azure OpenAI client: {e}")
    azure_client = None


def chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: int = 2000,
    temperature: float = 1.0,
    stream: bool = False,
) -> Dict:
    """
    Send a chat completion request to the Azure OpenAI deployment from environment.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        max_tokens: Maximum tokens in response
        temperature: Creativity level
        stream: Whether to stream the response

    Returns:
        Response dict with content and token usage
    """
    try:
        if azure_client is None:
            raise Exception(
                "Azure OpenAI client not initialized. Check environment variables."
            )

        print(f"📤 Sending request to Azure with {len(messages)} messages...")
        
        request_kwargs = {
            "model": AZURE_OPENAI_DEPLOYMENT,
            "messages": messages,
            "stream": stream,
        }

        # Use standard chat-completions token limit parameter for broad model compatibility.
        request_kwargs["max_tokens"] = max_tokens

        response = _chat_completions_create(request_kwargs)
        
        if stream:
            return response  # Return generator for streaming

        print(f"📥 Received response: {response.choices[0].message.content[:100]}...")

        # Non-streaming response
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "tokens": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens,
            },
            "finish_reason": response.choices[0].finish_reason,
        }

    except Exception as e:
        print(f"❌ Error in chat_completion: {str(e)}")
        print(f"   Message count: {len(messages)}")
        raise


def chat_completion_gpt4_mini(
    messages: List[Dict[str, str]],
    max_tokens: int = 2000,
    temperature: float = 1.0,
    stream: bool = False,
) -> Dict:
    """
    Chat completion that uses the dedicated GPT-4.1-mini profile from .env.
    Falls back to default profile values when dedicated vars are not set.
    """
    try:
        cfg = get_gpt4_mini_chat_config()
        endpoint = cfg.get("endpoint")
        deployment = cfg.get("deployment")
        preferred_api_version = cfg.get("api_version")

        if not endpoint:
            raise Exception("Azure endpoint is not configured for GPT-4.1-mini profile")
        if not deployment:
            raise Exception("Azure deployment is not configured for GPT-4.1-mini profile")
        if not AZURE_OPENAI_KEY:
            raise Exception("AZURE_OPENAI_KEY is missing")

        version_candidates = [preferred_api_version, AZURE_OPENAI_API_VERSION, "2024-12-01-preview", "2024-10-21"]
        unique_versions = []
        for version in version_candidates:
            if version and version not in unique_versions:
                unique_versions.append(version)

        last_error = None
        for api_version in unique_versions:
            try:
                client = AzureOpenAI(
                    api_version=api_version,
                    azure_endpoint=endpoint,
                    api_key=AZURE_OPENAI_KEY,
                )

                response = client.chat.completions.create(
                    model=deployment,
                    messages=messages,
                    max_tokens=max_tokens,
                    stream=stream,
                )

                if stream:
                    return response

                if api_version != preferred_api_version:
                    print(f"⚠️ GPT-4.1-mini call recovered with API version: {api_version}")

                return {
                    "content": response.choices[0].message.content,
                    "model": response.model,
                    "tokens": {
                        "prompt": response.usage.prompt_tokens,
                        "completion": response.usage.completion_tokens,
                        "total": response.usage.total_tokens,
                    },
                    "finish_reason": response.choices[0].finish_reason,
                }
            except NotFoundError as e:
                last_error = e
                continue
            except Exception as e:
                last_error = e
                continue

        raise Exception(
            "Failed to call GPT-4.1-mini profile. "
            f"Endpoint='{endpoint}', Deployment='{deployment}', API versions tried={unique_versions}. "
            f"Last error: {last_error}"
        )
    except Exception as e:
        print(f"❌ Error in chat_completion_gpt4_mini: {str(e)}")
        raise


def chat_completion_gpt4_mini(
    messages: List[Dict[str, str]],
    max_tokens: int = 2000,
    temperature: float = 1.0,
    stream: bool = False,
) -> Dict:
    """
    Chat completion that uses the dedicated GPT-4.1-mini profile from .env.
    Falls back to default profile values when dedicated vars are not set.
    """
    try:
        cfg = get_gpt4_mini_chat_config()
        endpoint = cfg.get("endpoint")
        deployment = cfg.get("deployment")
        preferred_api_version = cfg.get("api_version")

        if not endpoint:
            raise Exception("Azure endpoint is not configured for GPT-4.1-mini profile")
        if not deployment:
            raise Exception(
                "Azure deployment is not configured for GPT-4.1-mini profile"
            )
        if not AZURE_OPENAI_KEY:
            raise Exception("AZURE_OPENAI_KEY is missing")

        version_candidates = [
            preferred_api_version,
            AZURE_OPENAI_API_VERSION,
            "2024-12-01-preview",
            "2024-10-21",
        ]
        unique_versions = []
        for version in version_candidates:
            if version and version not in unique_versions:
                unique_versions.append(version)

        last_error = None
        for api_version in unique_versions:
            try:
                client = AzureOpenAI(
                    api_version=api_version,
                    azure_endpoint=endpoint,
                    api_key=AZURE_OPENAI_KEY,
                )

                response = client.chat.completions.create(
                    model=deployment,
                    messages=messages,
                    max_tokens=max_tokens,
                    stream=stream,
                )

                if stream:
                    return response

                if api_version != preferred_api_version:
                    print(
                        f"⚠️ GPT-4.1-mini call recovered with API version: {api_version}"
                    )

                return {
                    "content": response.choices[0].message.content,
                    "model": response.model,
                    "tokens": {
                        "prompt": response.usage.prompt_tokens,
                        "completion": response.usage.completion_tokens,
                        "total": response.usage.total_tokens,
                    },
                    "finish_reason": response.choices[0].finish_reason,
                }
            except NotFoundError as e:
                last_error = e
                continue
            except Exception as e:
                last_error = e
                continue

        raise Exception(
            "Failed to call GPT-4.1-mini profile. "
            f"Endpoint='{endpoint}', Deployment='{deployment}', API versions tried={unique_versions}. "
            f"Last error: {last_error}"
        )
    except Exception as e:
        print(f"❌ Error in chat_completion_gpt4_mini: {str(e)}")
        raise


def chat_completion_streaming(
    messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 1.0
):
    """
    Stream chat completion responses from the Azure OpenAI deployment from environment.
    
    Yields chunks of response text as they arrive
    """
    try:
        response = _chat_completions_create(
            {
                "model": AZURE_OPENAI_DEPLOYMENT,
                "messages": messages,
                "max_tokens": max_tokens,
                "stream": True,
            }
        )

        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield delta.content

    except Exception as e:
        print(f"Error in chat_completion_streaming: {str(e)}")
        raise


def generate_image(
    prompt: str, save_to_file: bool = True, output_dir: str = "uploads/ai_images"
) -> Dict:
    """
    Generate an image using FLUX-1.1-pro

    Args:
        prompt: Description of image to generate
        save_to_file: Whether to save image to disk
        output_dir: Directory to save images

    Returns:
        Dict with image_url, filename, and status
    """
    try:
        if not AZURE_FLUX_ENDPOINT:
            return {"success": False, "error": "AZURE_FLUX_ENDPOINT is not configured"}
        if not AZURE_FLUX_KEY:
            return {"success": False, "error": "AZURE_FLUX_KEY is not configured"}
        if not AZURE_FLUX_MODEL:
            return {"success": False, "error": "AZURE_FLUX_MODEL is not configured"}
        
        payload = {
            "prompt": prompt,
            "n": 1,
            "model": AZURE_FLUX_MODEL
        }

        auth_header_candidates = [
            {
                "Content-Type": "application/json",
                "api-key": AZURE_FLUX_KEY,
            },
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AZURE_FLUX_KEY}",
            },
        ]

        response = None
        attempted_schemes = []
        for headers in auth_header_candidates:
            scheme = "api-key" if "api-key" in headers else "bearer"
            attempted_schemes.append(scheme)
            response = requests.post(
                AZURE_FLUX_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=90
            )
            if response.status_code == 200:
                break
            if response.status_code not in (401, 403):
                break

        if response is None:
            return {
                "success": False,
                "error": "No response from FLUX endpoint",
            }
        
        if response.status_code == 200:
            data = response.json()

            if "data" in data and len(data["data"]) > 0:
                # Get base64 image data
                if "b64_json" in data["data"][0]:
                    b64_image = data["data"][0]["b64_json"]

                    if save_to_file:
                        # Create directory if it doesn't exist
                        os.makedirs(output_dir, exist_ok=True)

                        # Generate unique filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"ai_generated_{timestamp}.png"
                        filepath = os.path.join(output_dir, filename)

                        # Decode and save image
                        image_data = base64.b64decode(b64_image)
                        with open(filepath, "wb") as f:
                            f.write(image_data)

                        return {
                            "success": True,
                            "image_url": f"/{filepath}",
                            "filename": filename,
                            "filepath": filepath,
                            "prompt": prompt,
                        }
                    else:
                        # Return base64 data
                        return {
                            "success": True,
                            "image_data": b64_image,
                            "prompt": prompt,
                        }

                elif "url" in data["data"][0]:
                    # Image returned as URL
                    return {
                        "success": True,
                        "image_url": data["data"][0]["url"],
                        "prompt": prompt,
                    }

            return {"success": False, "error": "No image data in response"}

        else:
            print(
                "❌ FLUX request failed "
                f"status={response.status_code}, tried_auth={attempted_schemes}, "
                f"endpoint={AZURE_FLUX_ENDPOINT}"
            )
            return {
                "success": False,
                "error": f"API returned status code {response.status_code}",
                "details": response.text,
                "tried_auth": attempted_schemes,
            }

    except Exception as e:
        print(f"Error in generate_image: {str(e)}")
        return {"success": False, "error": str(e)}


def format_conversation_history(messages: List[Dict]) -> List[Dict[str, str]]:
    """
    Format conversation history for Azure OpenAI API

    Converts database messages to API format
    """
    formatted = []

    for msg in messages:
        formatted.append(
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
        )

    return formatted


def get_context_with_system_prompt(
    conversation_messages: List[Dict], system_prompt: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Create full context with system prompt for API call

    Args:
        conversation_messages: Previous messages from database
        system_prompt: Custom system prompt (optional)

    Returns:
        Formatted messages including system prompt
    """
    if system_prompt is None:
        system_prompt = """You are DOIT AI Assistant, a helpful and intelligent AI integrated into the DOIT project management system.

You help users with:
- Answering questions about their projects, tasks, and sprints
- Providing insights and suggestions for project management
- Generating images when requested
- Analyzing data and providing recommendations
- General assistance with any queries

Be concise, helpful, and professional. When users ask you to generate images, acknowledge that you'll create them and describe what you're generating."""

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history
    messages.extend(format_conversation_history(conversation_messages))

    return messages


def estimate_tokens(text: str) -> int:
    """
    Rough estimation of token count
    (1 token ≈ 4 characters for English text)
    """
    return len(text) // 4


def truncate_context(
    messages: List[Dict[str, str]], max_tokens: int = 8000
) -> List[Dict[str, str]]:
    """
    Truncate conversation history to fit within token limit
    Always keeps system message if present
    """
    if not messages:
        return messages

    # Always keep system message
    result = []
    system_msg = None
    other_messages = []

    for msg in messages:
        if msg.get("role") == "system":
            system_msg = msg
        else:
            other_messages.append(msg)

    if system_msg:
        result.append(system_msg)
        max_tokens -= estimate_tokens(system_msg["content"])

    # Add messages from most recent backwards until we hit limit
    total_tokens = 0
    for msg in reversed(other_messages):
        msg_tokens = estimate_tokens(msg["content"])
        if total_tokens + msg_tokens > max_tokens:
            break
        result.insert(1 if system_msg else 0, msg)
        total_tokens += msg_tokens

    return result
