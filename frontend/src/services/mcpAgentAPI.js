// frontend/src/services/mcpAgentAPI.js
/**
 * MCP Agent API Service
 * Frontend service layer for MCP-only agent mode
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

const BASE = `${API_BASE}/api/mcp-agent`;

export const mcpAgentAPI = {
  createConversation: async (title = 'MCP Chat') => {
    const res = await fetch(`${BASE}/conversations`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ title }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to create conversation');
    return data;
  },

  listConversations: async () => {
    const res = await fetch(`${BASE}/conversations`, { headers: getHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to list conversations');
    return data;
  },

  getMessages: async (conversationId) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to get messages');
    return data;
  },

  deleteConversation: async (conversationId) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to delete conversation');
    return data;
  },

  sendMessage: async (conversationId, content) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ content }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Failed to send message');
    return data;
  },

  health: async () => {
    const res = await fetch(`${BASE}/health`, { headers: getHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || 'Health check failed');
    return data;
  },
};

export default mcpAgentAPI;
