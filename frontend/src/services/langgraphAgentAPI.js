// frontend/src/services/langgraphAgentAPI.js
/**
 * LangGraph AI Agent API Service
 * Frontend service layer for LangGraph Agent (Azure OpenAI + LangChain Tools)
 * Stack: Azure OpenAI + LangGraph + Multi-Agent System
 */

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const getTabSessionKey = () => {
  let key = sessionStorage.getItem('tab_session_key');
  if (!key) {
    key = 'tab_' + Math.random().toString(36).substr(2, 12) + '_' + Date.now().toString(36);
    sessionStorage.setItem('tab_session_key', key);
  }
  return key;
};

const getHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
  'X-Tab-Session-Key': getTabSessionKey(),
  'Content-Type': 'application/json',
});

const BASE = `${API_BASE}/api/langgraph-agent`;

export const langgraphAgentAPI = {
  // ── Conversations ──────────────────────────────────────────────────────────
  
  /**
   * Create a new LangGraph conversation
   * @param {string} title - Conversation title
   * @returns {Promise} Conversation object
   */
  createConversation: async (title = 'LangGraph AI Chat') => {
    const res = await fetch(`${BASE}/conversations`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ title }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to create conversation');
    return data;
  },

  /**
   * List all LangGraph conversations for current user
   * @returns {Promise} Array of conversations
   */
  listConversations: async () => {
    const res = await fetch(`${BASE}/conversations`, { headers: getHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to list conversations');
    return data;
  },

  /**
   * Get all messages in a conversation
   * @param {string} conversationId - Conversation ID
   * @returns {Promise} Messages array
   */
  getMessages: async (conversationId) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to get messages');
    return data;
  },

  /**
   * Delete a conversation
   * @param {string} conversationId - Conversation ID
   * @returns {Promise} Success response
   */
  deleteConversation: async (conversationId) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to delete conversation');
    return data;
  },

  // ── Core: Send Message ─────────────────────────────────────────────────────

  /**
   * Send a message to the LangGraph Agent
   * Agent has access to tools for task/sprint/project management
   * @param {string} conversationId - Conversation ID
   * @param {string} content - User message
   * @param {boolean} includeUserContext - Include DOIT context (default true)
   * @returns {Promise} Agent response with tool execution results
   */
  sendMessage: async (conversationId, content, includeUserContext = true) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ 
        content, 
        include_user_context: includeUserContext 
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to send message');
    return data; 
    // Returns: { 
    //   success, 
    //   message: { _id, role, content, created_at, tokens_used }, 
    //   model, 
    //   tool_calls: [...],
    //   tokens 
    // }
  },

  // ── History Management ─────────────────────────────────────────────────────

  /**
   * Reset conversation history
   * @param {string} conversationId - Conversation ID
   * @returns {Promise} Success response
   */
  resetHistory: async (conversationId) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}/reset-history`, {
      method: 'POST',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to reset history');
    return data;
  },

  /**
   * Get conversation history (debug)
   * @param {string} conversationId - Conversation ID
   * @returns {Promise} History object
   */
  getHistory: async (conversationId) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}/history`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to get history');
    return data;
  },

  // ── Health Check ───────────────────────────────────────────────────────────

  /**
   * Check LangGraph Agent health
   * @returns {Promise} Health status
   */
  health: async () => {
    const res = await fetch(`${BASE}/health`, { headers: getHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Health check failed');
    return data;
  },
};

export default langgraphAgentAPI;