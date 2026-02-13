"""
Agent Authentication Middleware
Special authentication for Azure AI Agent with service account
"""

from fastapi import Header, HTTPException
from typing import Optional
import os

# Agent service account credentials
AGENT_SERVICE_TOKEN = os.getenv("AGENT_SERVICE_TOKEN")
AGENT_SERVICE_USER_ID = os.getenv("AGENT_SERVICE_USER_ID")


async def verify_agent_token(
    authorization: Optional[str] = Header(None),
    x_agent_key: Optional[str] = Header(None, alias="X-Agent-Key"),
    api_key: Optional[str] = None,  # Query parameter as fallback
) -> str:
    """
    Verify agent authentication via service token, API key header, or query param
    Returns service user ID for operations
    """
    # Option 1: Bearer token (normal user auth)
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        from utils.auth_utils import verify_token

        user_id = verify_token(token)
        if user_id:
            return user_id

    # Option 2: Agent service key via header (preferred)
    if x_agent_key and x_agent_key == AGENT_SERVICE_TOKEN:
        if not AGENT_SERVICE_USER_ID:
            raise HTTPException(
                status_code=500, detail="Agent service user not configured"
            )
        return AGENT_SERVICE_USER_ID
    
    # Option 3: Agent service key via query parameter (fallback for Azure AI)
    if api_key and api_key == AGENT_SERVICE_TOKEN:
        if not AGENT_SERVICE_USER_ID:
            raise HTTPException(
                status_code=500, detail="Agent service user not configured"
            )
        return AGENT_SERVICE_USER_ID

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide Bearer token, X-Agent-Key header, or api_key query param",
    )
