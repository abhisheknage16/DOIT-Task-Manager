import jwt
import datetime
from datetime import timezone
import bcrypt
import hashlib
import uuid
from config import JWT_SECRET, JWT_EXPIRY_HOURS
from functools import wraps
from database import db
from bson import ObjectId

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))

def generate_token_id(user_id: str, timestamp: str) -> str:
    """Generate unique token identifier for tracking and blacklisting"""
    unique_string = f"{user_id}:{timestamp}"
    return hashlib.sha256(unique_string.encode()).hexdigest()[:32]

def generate_device_fingerprint(ip_address: str, user_agent: str) -> str:
    """Generate unique device fingerprint for strict session binding"""
    fingerprint_data = f"{ip_address}:{user_agent}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]

def generate_session_id() -> str:
    """Generate globally unique session ID for strict session validation"""
    return str(uuid.uuid4())

def create_token(user_id: str, ip_address: str = None, user_agent: str = None) -> tuple:
    """
    Create JWT token with STRICT security features:
    - Token ID for blacklisting
    - Token version for invalidating all tokens
    - Session tracking with IP/User-Agent
    - Device fingerprinting for binding
    - SINGLE SESSION ENFORCEMENT (auto-logout previous sessions)
    - Tab-specific session binding (prevents token sharing across tabs)
    Returns: (token, token_id, tab_session_key)
    """
    # Get user's current token version
    user = db.users.find_one({"_id": ObjectId(user_id)}, {"token_version": 1})
    token_version = user.get("token_version", 1) if user else 1
    
    # Generate device fingerprint for strict binding
    device_fingerprint = generate_device_fingerprint(ip_address or "unknown", user_agent or "unknown")
    
    # 🔒 SINGLE SESSION ENFORCEMENT: Deactivate ALL previous sessions
    # This prevents token theft - only the latest login session is valid
    previous_sessions = db.sessions.update_many(
        {
            "user_id": ObjectId(user_id),
            "is_active": True
        },
        {
            "$set": {
                "is_active": False,
                "ended_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None),
                "end_reason": "new_login_detected"
            }
        }
    )
    
    if previous_sessions.modified_count > 0:
        print(f"[SECURITY] Auto-logged out {previous_sessions.modified_count} previous session(s) for user {user_id}")
    
    # 🔑 Generate UNIQUE session ID - this is the core of our security
    # This session_id will be stored in JWT and MUST exist in database for this user
    session_id = generate_session_id()
    
    # 🔐 Generate TAB-SPECIFIC session key
    # This prevents token sharing across browser tabs
    tab_session_key = str(uuid.uuid4())
    
    # Create token ID for tracking (legacy support)
    timestamp = datetime.datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    token_id = generate_token_id(str(user_id), timestamp)
    
    # Build payload with security metadata
    payload = {
        "user_id": str(user_id),
        "session_id": session_id,  # 🔑 CRITICAL: Unique session identifier
        "tab_key": tab_session_key,  # 🔐 NEW: Tab-specific key
        "token_id": token_id,
        "token_version": token_version,
        "device_fp": device_fingerprint,
        "exp": datetime.datetime.now(timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.datetime.now(timezone.utc).replace(tzinfo=None),
    }
    
    # Add IP/User-Agent for additional tracking
    if ip_address:
        payload["ip"] = ip_address
    if user_agent:
        payload["ua_hash"] = hashlib.md5(user_agent.encode()).hexdigest()[:16]
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    # Store NEW session info with session_id as primary key
    session_data = {
        "session_id": session_id,  # 🔑 Primary identifier
        "tab_session_key": tab_session_key,  # 🔐 Tab-specific key
        "user_id": ObjectId(user_id),
        "token_id": token_id,
        "device_fingerprint": device_fingerprint,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None),
        "expires_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
        "is_active": True
    }
    db.sessions.insert_one(session_data)
    
    return token, token_id, tab_session_key


def verify_token_for_websocket(token: str):
    """
    Simplified token verification for WebSocket connections.
    Bypasses device fingerprint checks since WebSocket headers differ from HTTP.
    Still validates: token format, expiry, user existence, session validity.
    """
    try:
        # Decode the token
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")
        token_id = payload.get("token_id")
        
        if not user_id or not session_id:
            print(f"[WS AUTH] Token missing user_id or session_id")
            return None
        
        # Check if token is blacklisted
        if token_id:
            blacklisted = db.token_blacklist.find_one({"token_id": token_id})
            if blacklisted:
                print(f"[WS AUTH] Blacklisted token attempted: {token_id}")
                return None
        
        # Validate user exists
        user = db.users.find_one({"_id": ObjectId(user_id)}, {"token_version": 1})
        if not user:
            print(f"[WS AUTH] User not found: {user_id}")
            return None
        
        # Check token version
        token_version = payload.get("token_version", 1)
        current_version = user.get("token_version", 1)
        if token_version != current_version:
            print(f"[WS AUTH] Invalid token version")
            return None
        
        # Validate session exists and is active (skip device fingerprint check)
        session = db.sessions.find_one({
            "session_id": session_id,
            "user_id": ObjectId(user_id),
            "is_active": True
        })
        
        if not session:
            print(f"[WS AUTH] Session invalid or inactive")
            return None
        
        print(f"[WS AUTH] ✓ Token verified for user: {user_id}")
        return user_id
        
    except jwt.ExpiredSignatureError:
        print(f"[WS AUTH] Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"[WS AUTH] Invalid token: {str(e)}")
        return None
    except Exception as e:
        print(f"[WS AUTH] Error verifying token: {str(e)}")
        return None


def verify_token(token: str, ip_address: str = None, user_agent: str = None, tab_session_key: str = None, skip_tab_validation: bool = False):
    """
    Verify JWT token with STRICT security checks:
    - Token not expired
    - Token not blacklisted
    - Token version matches user's current version
    - Device fingerprint matches (STRICT binding)
    - Session still active
    - Tab session key matches (prevents cross-tab token theft)
    
    Args:
        skip_tab_validation: If True, skip tab session key validation (for refresh-session endpoint)
    
    Returns: user_id or None
    """
    try:
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["user_id"]
        token_id = payload.get("token_id")
        token_version = payload.get("token_version", 1)
        token_device_fp = payload.get("device_fp")
        token_tab_key = payload.get("tab_key")  # 🔐 Tab-specific key from token
        
        # Check 1: Token blacklisted (after logout)?
        if token_id and is_token_blacklisted(token_id):
            print(f"[SECURITY] Blacklisted token attempted: {token_id}")
            return None
        
        # Check 2: Token version matches user's current version?
        user = db.users.find_one({"_id": ObjectId(user_id)}, {"token_version": 1})
        if not user:
            return None
        
        current_version = user.get("token_version", 1)
        if token_version != current_version:
            print(f"[SECURITY] Invalid token version: {token_version} vs {current_version}")
            return None
        
        # 🔒 Check 3: CRITICAL - Session-to-User Validation
        # This is our PRIMARY defense against token theft
        # The session_id in the token MUST exist AND belong to the token's user_id
        session_id = payload.get("session_id")
        if not session_id:
            print(f"[SECURITY] Token missing session_id (old token format)")
            return None
        
        # Validate: session exists, is active, AND belongs to this user
        session = db.sessions.find_one({
            "session_id": session_id,
            "user_id": ObjectId(user_id),
            "is_active": True
        })
        
        if not session:
            # Check if this is actual token theft or just expired session
            stolen_session = db.sessions.find_one({"session_id": session_id})
            
            if stolen_session:
                actual_owner = str(stolen_session.get("user_id"))
                
                # ONLY blacklist if token belongs to DIFFERENT user (actual theft)
                if actual_owner != user_id:
                    print(f"[SECURITY] 🚨 TOKEN THEFT DETECTED!")
                    print(f"   🔥 CRITICAL: Token belongs to user {actual_owner}, but used by {user_id}")
                    
                    # Log critical security breach
                    db.security_logs.insert_one({
                        "user_id": ObjectId(user_id),
                        "token_id": token_id,
                        "event": "token_theft_attempt",
                        "severity": "critical",
                        "details": {
                            "session_id": session_id,
                            "token_owner": actual_owner,
                            "attempted_by": user_id,
                            "ip": ip_address,
                            "user_agent": user_agent[:100] if user_agent else "unknown"
                        },
                        "timestamp": datetime.datetime.now(timezone.utc).replace(tzinfo=None)
                    })
                    
                    # Blacklist the stolen token
                    if token_id:
                        blacklist_token(token_id, user_id, "token_theft_detected")
                else:
                    # Same user, but session is inactive - likely expired/logout
                    print(f"[SECURITY] Session inactive for user {user_id} (expired or logged out)")
            else:
                # Session doesn't exist at all - likely expired and cleaned up
                print(f"[SECURITY] Session not found: {session_id} (likely expired)")
            
            return None
        
        # 🔒 Check 4: STRICT Device Fingerprint Validation
        # Prevent token use from different device/browser
        if token_device_fp and session.get("device_fingerprint"):
            current_device_fp = generate_device_fingerprint(ip_address or "unknown", user_agent or "unknown")
            session_device_fp = session.get("device_fingerprint")
            
            if current_device_fp != session_device_fp:
                print(f"[SECURITY] 🚨 DEVICE MISMATCH DETECTED!")
                print(f"   Session ID: {session_id}")
                print(f"   User ID: {user_id}")
                print(f"   Token device FP: {token_device_fp}")
                print(f"   Session device FP: {session_device_fp}")
                print(f"   Current device FP: {current_device_fp}")
                print(f"   This token is being used from a DIFFERENT device/browser!")
                
                # Log device mismatch attack
                db.security_logs.insert_one({
                    "user_id": ObjectId(user_id),
                    "session_id": session_id,
                    "event": "device_fingerprint_mismatch",
                    "severity": "critical",
                    "details": {
                        "expected_fp": session_device_fp,
                        "received_fp": current_device_fp,
                        "ip": ip_address,
                        "user_agent": user_agent[:100] if user_agent else "unknown"
                    },
                    "timestamp": datetime.datetime.now(timezone.utc).replace(tzinfo=None)
                })
                
                # Deactivate the compromised session
                db.sessions.update_one(
                    {"session_id": session_id},
                    {
                        "$set": {
                            "is_active": False,
                            "ended_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None),
                            "end_reason": "device_fingerprint_mismatch"
                        }
                    }
                )
                
                # Blacklist the token
                if token_id:
                    blacklist_token(token_id, user_id, "device_mismatch")
                
                return None
        
        # 🔐 Check 5: CRITICAL - Tab Session Key Validation
        # This prevents token sharing across browser tabs/windows
        # Only validate if token has tab_key (new tokens) AND session has tab key
        # UNLESS skip_tab_validation is True (for refresh-session endpoint)
        if not skip_tab_validation and token_tab_key and session.get("tab_session_key"):
            # Tab key must be provided by client and must match session
            if not tab_session_key:
                print(f"[SECURITY] ❌ TAB SESSION KEY MISSING - BLOCKING REQUEST!")
                print(f"   Session ID: {session_id}")
                print(f"   User ID: {user_id}")
                print(f"   Token has tab key but client didn't provide one")
                print(f"   This indicates token theft - token copied without sessionStorage")
                
                # Log critical security incident
                db.security_logs.insert_one({
                    "user_id": ObjectId(user_id),
                    "session_id": session_id,
                    "event": "tab_key_missing_blocked",
                    "severity": "high",
                    "details": {
                        "ip": ip_address,
                        "user_agent": user_agent[:100] if user_agent else "unknown",
                        "note": "Tab key in token but not provided by client - BLOCKED (likely token theft)"
                    },
                    "timestamp": datetime.datetime.now(timezone.utc).replace(tzinfo=None)
                })
                
                # BLOCK the request - missing tab key is a strong indicator of token theft
                # If user refreshes page, they will be logged out and need to login again
                print(f"   ❌ BLOCKING REQUEST - Token theft suspected")
                return None
            
            # Validate tab key matches the one in session (if tab_session_key is provided)
            elif tab_session_key and session.get("tab_session_key") != tab_session_key:
                print(f"[SECURITY] ❌ TAB SESSION KEY MISMATCH - TOKEN THEFT SUSPECTED!")
                print(f"   Session ID: {session_id}")
                print(f"   User ID: {user_id}")
                print(f"   Expected tab key: {session.get('tab_session_key')}")
                print(f"   Received tab key: {tab_session_key}")
                print(f"   This token is being used with WRONG tab key!")
                print(f"   BLOCKING REQUEST - Likely token theft")
                
                # Log critical security incident
                db.security_logs.insert_one({
                    "user_id": ObjectId(user_id),
                    "session_id": session_id,
                    "event": "tab_session_key_mismatch_blocked",
                    "severity": "high",
                    "details": {
                        "expected_key": session.get("tab_session_key"),
                        "received_key": tab_session_key,
                        "ip": ip_address,
                        "user_agent": user_agent[:100] if user_agent else "unknown",
                        "note": "Request blocked - tab key mismatch indicates token theft"
                    },
                    "timestamp": datetime.datetime.now(timezone.utc).replace(tzinfo=None)
                })
                
                # BLOCK the request - tab key mismatch is strong indicator of token theft
                return None
        
        # Session validated successfully
        return user_id
        
    except jwt.ExpiredSignatureError:
        print("[SECURITY] Expired token attempted")
        return None
    except jwt.InvalidTokenError as e:
        print(f"[SECURITY] Invalid token: {str(e)}")
        return None
    except Exception as e:
        print(f"[SECURITY] Token verification error: {str(e)}")
        return None

def is_token_blacklisted(token_id: str) -> bool:
    """Check if token is blacklisted"""
    blacklisted = db.token_blacklist.find_one({"token_id": token_id})
    return blacklisted is not None

def blacklist_token(token_id: str, user_id: str, reason: str = "logout", session_id: str = None):
    """
    Add token to blacklist and deactivate session by session_id or token_id
    """
    try:
        # Add to blacklist
        db.token_blacklist.insert_one({
            "token_id": token_id,
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "blacklisted_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None),
            "reason": reason,
            # Auto-expire after token's lifetime (cleanup old entries)
            "expires_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=JWT_EXPIRY_HOURS + 24)
        })
        
        # Deactivate session by session_id (preferred) or token_id (fallback)
        if session_id:
            db.sessions.update_one(
                {"session_id": session_id},
                {"$set": {"is_active": False, "ended_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None), "end_reason": reason}}
            )
        else:
            db.sessions.update_one(
                {"token_id": token_id},
                {"$set": {"is_active": False, "ended_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None), "end_reason": reason}}
            )
        
        print(f"[SECURITY] Token blacklisted: {token_id} (reason: {reason})")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to blacklist token: {str(e)}")
        return False

def revoke_all_user_tokens(user_id: str, reason: str = "security_action"):
    """
    Invalidate ALL tokens for a user by incrementing token version
    Use cases:
    - Password changed
    - Account compromised
    - Admin forced logout
    """
    try:
        # Increment token version (invalidates all existing tokens)
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"token_version": 1}}
        )
        
        # Deactivate all active sessions
        db.sessions.update_many(
            {"user_id": ObjectId(user_id), "is_active": True},
            {"$set": {"is_active": False, "ended_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None)}}
        )
        
        print(f"[SECURITY] All tokens revoked for user {user_id} (reason: {reason})")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to revoke tokens: {str(e)}")
        return False

def get_active_sessions(user_id: str, limit: int = 10):
    """Get user's active sessions for security dashboard"""
    sessions = list(db.sessions.find(
        {"user_id": ObjectId(user_id), "is_active": True},
        {"token_id": 1, "ip_address": 1, "user_agent": 1, "created_at": 1}
    ).sort("created_at", -1).limit(limit))
    
    for session in sessions:
        session["_id"] = str(session["_id"])
        session["token_id"] = session.get("token_id", "unknown")
    
    return sessions