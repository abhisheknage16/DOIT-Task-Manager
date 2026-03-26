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

  listConversations: async () => {
    const res = await fetch(`${BASE}/conversations`, { headers: getAuthHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to list conversations");
    return data;
  },

  getMessages: async (conversationId) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to get messages");
    return data;
  },

  deleteConversation: async (conversationId) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to delete conversation");
    return data;
  },

  sendMessage: async (conversationId, content, includeUserContext = true) => {
    const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ content, include_user_context: includeUserContext }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to send message");
    return data;
  },

  uploadFile: async (conversationId, file) => {
    const token = getToken();
    const tabSessionKey = getTabSessionKey();
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${BASE}/conversations/${conversationId}/upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tab-Session-Key": tabSessionKey,
        // No Content-Type here — browser sets multipart boundary automatically
      },
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Upload failed");
    return data;
  },

  resetThread: async () => {
    const res = await fetch(`${BASE}/reset-thread`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to reset thread");
    return data;
  },

  getThreadMessages: async () => {
    const res = await fetch(`${BASE}/thread-messages`, { headers: getAuthHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to get thread messages");
    return data;
  },

  health: async () => {
    const res = await fetch(`${BASE}/health`, { headers: getAuthHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Health check failed");
    return data;
  },

};

export default foundryAgentAPI;