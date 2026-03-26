"""
Agent Authentication Middleware
Special authentication for Azure AI Agent with service account
"""

from fastapi import Header, HTTPException, Request
from typing import Optional
import os

# Agent service account credentials
AGENT_SERVICE_TOKEN = os.getenv("AGENT_SERVICE_TOKEN")
AGENT_SERVICE_USER_ID = os.getenv("AGENT_SERVICE_USER_ID")
# Compatibility key used by OpenAPI agent tool defaults (can be overridden via env)
AGENT_COMPAT_API_KEY = os.getenv(
    "AGENT_API_KEY",
    "LX5HETBWgbO0IqOaWVu5Cs__B2ovKG_yfFu70dqpQy_mLjL0YIAfTBR-7570Q_tf",
)


def _is_valid_agent_secret(candidate: Optional[str]) -> bool:
    if not candidate:
        return False
    valid_tokens = {
        token for token in [AGENT_SERVICE_TOKEN, AGENT_COMPAT_API_KEY] if token
    }
    return candidate in valid_tokens


async def verify_agent_token(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_agent_key: Optional[str] = Header(None, alias="X-Agent-Key"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key_header: Optional[str] = Header(None, alias="Api-Key"),
    api_key_header_alt: Optional[str] = Header(None, alias="api-key"),
    api_key_header_underscore: Optional[str] = Header(None, alias="api_key"),
    api_key: Optional[str] = None,  # Query parameter as fallback
    sig: Optional[str] = None,  # Legacy connector query parameter fallback
    code: Optional[str] = None,  # Logic-app style connector query parameter fallback
    apikey: Optional[str] = None,  # Compatibility alias used by some clients
) -> str:
    """
    Verify agent authentication via service token, API key header, or query param
    Returns service user ID for operations
    """
    # Option 1: Authorization header
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

        # Bearer service token compatibility for API-key style clients.
        if _is_valid_agent_secret(token):
            if not AGENT_SERVICE_USER_ID:
                raise HTTPException(
                    status_code=500, detail="Agent service user not configured"
                )
            return AGENT_SERVICE_USER_ID

        # Bearer JWT (normal user auth)
        from utils.auth_utils import verify_token

        user_id = verify_token(token)
        if user_id:
            return user_id

    # Raw Authorization token compatibility (some clients send API key here)
    if authorization and _is_valid_agent_secret(authorization):
        if not AGENT_SERVICE_USER_ID:
            raise HTTPException(status_code=500, detail="Agent service user not configured")
        return AGENT_SERVICE_USER_ID

    # Authorization: Api-Key <token> compatibility
    if authorization and authorization.lower().startswith("api-key "):
        token = authorization[8:]
        if _is_valid_agent_secret(token):
            if not AGENT_SERVICE_USER_ID:
                raise HTTPException(status_code=500, detail="Agent service user not configured")
            return AGENT_SERVICE_USER_ID

    # Option 2: Agent service key via header (preferred)
    if _is_valid_agent_secret(x_agent_key):
        if not AGENT_SERVICE_USER_ID:
            raise HTTPException(
                status_code=500, detail="Agent service user not configured"
            )
        return AGENT_SERVICE_USER_ID

    # Option 3: Alternative API key headers (client compatibility)
    header_candidates = [
        x_api_key,
        api_key_header,
        api_key_header_alt,
        api_key_header_underscore,
    ]
    if any(_is_valid_agent_secret(candidate) for candidate in header_candidates):
        if not AGENT_SERVICE_USER_ID:
            raise HTTPException(
                status_code=500, detail="Agent service user not configured"
            )
        return AGENT_SERVICE_USER_ID
    
    # Option 4: Agent service key via query parameter (fallback for Azure AI)
    query_candidates = [api_key, sig, code, apikey]
    if any(_is_valid_agent_secret(candidate) for candidate in query_candidates):
        if not AGENT_SERVICE_USER_ID:
            raise HTTPException(
                status_code=500, detail="Agent service user not configured"
            )
        return AGENT_SERVICE_USER_ID

    # Option 5: Raw request scan for compatibility with varying connector/APIM key names.
    raw_header_candidates = [
        request.headers.get("x-agent-key"),
        request.headers.get("x-api-key"),
        request.headers.get("api-key"),
        request.headers.get("api_key"),
        request.headers.get("ocp-apim-subscription-key"),
        request.headers.get("x-functions-key"),
    ]
    if any(_is_valid_agent_secret(candidate) for candidate in raw_header_candidates):
        if not AGENT_SERVICE_USER_ID:
            raise HTTPException(
                status_code=500, detail="Agent service user not configured"
            )
        return AGENT_SERVICE_USER_ID

    raw_query_candidates = [
        request.query_params.get("api_key"),
        request.query_params.get("api-key"),
        request.query_params.get("apikey"),
        request.query_params.get("sig"),
        request.query_params.get("code"),
        request.query_params.get("key"),
        request.query_params.get("access_token"),
        request.query_params.get("token"),
    ]
    if any(_is_valid_agent_secret(candidate) for candidate in raw_query_candidates):
        if not AGENT_SERVICE_USER_ID:
            raise HTTPException(
                status_code=500, detail="Agent service user not configured"
            )
        return AGENT_SERVICE_USER_ID

    received_channels = []
    if authorization:
        received_channels.append("Authorization")
    if x_agent_key:
        received_channels.append("X-Agent-Key")
    if x_api_key or api_key_header or api_key_header_alt or api_key_header_underscore:
        received_channels.append("API-Key-Header")
    if api_key:
        received_channels.append("api_key")
    if sig:
        received_channels.append("sig")
    if code:
        received_channels.append("code")
    if apikey:
        received_channels.append("apikey")
    if any(raw_header_candidates):
        received_channels.append("raw-header-key")
    if any(raw_query_candidates):
        received_channels.append("raw-query-key")

    # Keep diagnostics non-sensitive: include only which channels were received.
    path = request.url.path if request and request.url else "unknown"

    raise HTTPException(
        status_code=401,
        detail=(
            "Authentication required. Provide Bearer token, X-Agent-Key header, "
            "or api_key/sig/code query param. "
            f"received_channels={received_channels or ['none']}; path={path}"
        ),
    )


async def verify_agent_token_optional(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_agent_key: Optional[str] = Header(None, alias="X-Agent-Key"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key_header: Optional[str] = Header(None, alias="Api-Key"),
    api_key_header_alt: Optional[str] = Header(None, alias="api-key"),
    api_key_header_underscore: Optional[str] = Header(None, alias="api_key"),
    api_key: Optional[str] = None,
    sig: Optional[str] = None,
    code: Optional[str] = None,
    apikey: Optional[str] = None,
) -> Optional[str]:
    """
    Optional variant of agent token verification.
    Returns None for missing/invalid auth instead of raising 401.
    """
    try:
        return await verify_agent_token(
            request=request,
            authorization=authorization,
            x_agent_key=x_agent_key,
            x_api_key=x_api_key,
            api_key_header=api_key_header,
            api_key_header_alt=api_key_header_alt,
            api_key_header_underscore=api_key_header_underscore,
            api_key=api_key,
            sig=sig,
            code=code,
            apikey=apikey,
        )
    except HTTPException as exc:
        if exc.status_code == 401:
            return None
        raise
