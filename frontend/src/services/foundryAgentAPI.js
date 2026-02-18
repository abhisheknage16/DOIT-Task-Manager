// frontend/src/services/foundryAgentAPI.js
// Service layer for the Azure AI Foundry Agent backend (/api/foundry-agent)

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

const getToken = () => localStorage.getItem("token");

const getTabSessionKey = () => {
  let key = sessionStorage.getItem("tab_session_key");
  if (!key) {
    key = "tab_" + Math.random().toString(36).substr(2, 12) + "_" + Date.now().toString(36);
    sessionStorage.setItem("tab_session_key", key);
  }
  return key;
};

const getAuthHeaders = () => {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  headers["X-Tab-Session-Key"] = getTabSessionKey();
  return headers;
};

const BASE = `${API_BASE_URL}/api/foundry-agent`;

export const foundryAgentAPI = {
  // ── Conversations ────────────────────────────────────────────────────────

  /** Create a new conversation record */
  createConversation: async (title = "Agent Chat") => {
    const res = await fetch(`${BASE}/conversations`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ title }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to create conversation");
    return data;
  },

  /** List all conversations for the current user */
  listConversations: async () => {
    const res = await fetch(`${BASE}/conversations`, { headers: getAuthHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to list conversations");
    return data;
  },

  /** Get all stored messages in a conversation */
  getMessages: async (conversationId) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to get messages");
    return data;
  },

  /** Delete a conversation (also resets the Foundry thread) */
  deleteConversation: async (conversationId) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to delete conversation");
    return data;
  },

  // ── Core: send message ───────────────────────────────────────────────────

  /**
   * Send a message to the Foundry Agent and receive a reply.
   * @param {string} conversationId
   * @param {string} content - User message text
   * @param {boolean} includeUserContext - Inject live DOIT context (default true)
   */
  sendMessage: async (conversationId, content, includeUserContext = true) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ content, include_user_context: includeUserContext }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to send message");
    return data; // { success, message: { _id, role, content, created_at, tokens_used }, thread_id, tokens }
  },

  // ── Thread management ────────────────────────────────────────────────────

  /** Reset the Foundry thread for the current user (start fresh) */
  resetThread: async () => {
    const res = await fetch(`${BASE}/reset-thread`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to reset thread");
    return data;
  },

  /** Fetch raw messages directly from the Foundry thread (debug/sync) */
  getThreadMessages: async () => {
    const res = await fetch(`${BASE}/thread-messages`, { headers: getAuthHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to get thread messages");
    return data;
  },

  // ── Health ───────────────────────────────────────────────────────────────

  /** Check Foundry Agent connectivity */
  health: async () => {
    const res = await fetch(`${BASE}/health`, { headers: getAuthHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Health check failed");
    return data;
  },
};

export default foundryAgentAPI;