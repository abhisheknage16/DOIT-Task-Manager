"""
Azure AI Foundry Integration Utilities
For GPT-5.2-chat and FLUX-1.1-pro models
"""
from openai import AzureOpenAI
import requests
import base64
from typing import List, Dict, Optional
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure OpenAI Configuration for GPT-5.2-chat
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

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

# Initialize Azure OpenAI client (for text chat)
try:
    azure_client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
    )
    print("✅ Azure OpenAI client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Azure OpenAI client: {e}")
    azure_client = None


def chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: int = 2000,
    temperature: float = 1.0,
    stream: bool = False
) -> Dict:
    """
    Send a chat completion request to GPT-5.2-chat
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        max_tokens: Maximum tokens in response
        temperature: Creativity level (GPT-5.2-chat only supports 1.0)
        stream: Whether to stream the response
    
    Returns:
        Response dict with content and token usage
    """
    try:
        if azure_client is None:
            raise Exception("Azure OpenAI client not initialized. Check environment variables.")
        
        print(f"📤 Sending request to Azure with {len(messages)} messages...")
        
        # GPT-5.2-chat only supports temperature=1.0 (default)
        # Don't pass temperature parameter to use default
        response = azure_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            max_completion_tokens=max_tokens,
            stream=stream
        )
        
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
                "total": response.usage.total_tokens
            },
            "finish_reason": response.choices[0].finish_reason
        }
    
    except Exception as e:
        print(f"❌ Error in chat_completion: {str(e)}")
        print(f"   Messages sent: {messages}")
        raise


def chat_completion_streaming(
    messages: List[Dict[str, str]],
    max_tokens: int = 2000,
    temperature: float = 1.0
):
    """
    Stream chat completion responses from GPT-5.2-chat
    
    Yields chunks of response text as they arrive
    """
    try:
        # GPT-5.2-chat only supports temperature=1.0 (default)
        # Don't pass temperature parameter to use default
        response = azure_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            max_completion_tokens=max_tokens,
            stream=True
        )
        
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    yield delta.content
    
    except Exception as e:
        print(f"Error in chat_completion_streaming: {str(e)}")
        raise


def generate_image(
    prompt: str,
    save_to_file: bool = True,
    output_dir: str = "uploads/ai_images"
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
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AZURE_FLUX_KEY}"
        }
        
        payload = {
            "prompt": prompt,
            "n": 1,
            "model": AZURE_FLUX_MODEL
        }
        
        response = requests.post(
            AZURE_FLUX_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=90
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                # Get base64 image data
                if 'b64_json' in data['data'][0]:
                    b64_image = data['data'][0]['b64_json']
                    
                    if save_to_file:
                        # Create directory if it doesn't exist
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # Generate unique filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"ai_generated_{timestamp}.png"
                        filepath = os.path.join(output_dir, filename)
                        
                        # Decode and save image
                        image_data = base64.b64decode(b64_image)
                        with open(filepath, 'wb') as f:
                            f.write(image_data)
                        
                        return {
                            "success": True,
                            "image_url": f"/{filepath}",
                            "filename": filename,
                            "filepath": filepath,
                            "prompt": prompt
                        }
                    else:
                        # Return base64 data
                        return {
                            "success": True,
                            "image_data": b64_image,
                            "prompt": prompt
                        }
                
                elif 'url' in data['data'][0]:
                    # Image returned as URL
                    return {
                        "success": True,
                        "image_url": data['data'][0]['url'],
                        "prompt": prompt
                    }
            
            return {
                "success": False,
                "error": "No image data in response"
            }
        
        else:
            return {
                "success": False,
                "error": f"API returned status code {response.status_code}",
                "details": response.text
            }
    
    except Exception as e:
        print(f"Error in generate_image: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def format_conversation_history(messages: List[Dict]) -> List[Dict[str, str]]:
    """
    Format conversation history for Azure OpenAI API
    
    Converts database messages to API format
    """
    formatted = []
    
    for msg in messages:
        formatted.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    return formatted


def get_context_with_system_prompt(
    conversation_messages: List[Dict],
    system_prompt: Optional[str] = None
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
    messages: List[Dict[str, str]],
    max_tokens: int = 8000
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
