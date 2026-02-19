/**
 * localAgentAPI.js
 * Frontend service layer for the Local AI Agent (Ollama + LlamaIndex + ChromaDB)
 * Deploy to: frontend/src/services/localAgentAPI.js
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

const BASE = `${API_BASE}/api/local-agent`;

export const localAgentAPI = {
  // ── Conversations ──────────────────────────────────────────────────────────
  createConversation: (title = 'Local AI Chat') =>
    fetch(`${BASE}/conversations`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ title }),
    }).then(r => r.json()),

  listConversations: () =>
    fetch(`${BASE}/conversations`, { headers: getHeaders() }).then(r => r.json()),

  getMessages: (conversationId) =>
    fetch(`${BASE}/conversations/${conversationId}/messages`, {
      headers: getHeaders(),
    }).then(r => r.json()),

  deleteConversation: (conversationId) =>
    fetch(`${BASE}/conversations/${conversationId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    }).then(r => r.json()),

  // ── Send message ───────────────────────────────────────────────────────────
  sendMessage: (conversationId, content, includeUserContext = true) =>
    fetch(`${BASE}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ content, include_user_context: includeUserContext }),
    }).then(r => r.json()),

  // ── History management ─────────────────────────────────────────────────────
  resetHistory: () =>
    fetch(`${BASE}/reset-history`, {
      method: 'POST',
      headers: getHeaders(),
    }).then(r => r.json()),

  getHistory: () =>
    fetch(`${BASE}/history`, { headers: getHeaders() }).then(r => r.json()),

  // ── Health ─────────────────────────────────────────────────────────────────
  health: () =>
    fetch(`${BASE}/health`, { headers: getHeaders() }).then(r => r.json()),
};