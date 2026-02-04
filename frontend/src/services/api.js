// Import caching utilities
import { requestCache, cachedFetch, createCacheKey } from '../utils/requestCache';
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

// Get token from localStorage
const getToken = () => localStorage.getItem("token");

// Generate or get unique per-tab session key
const getTabSessionKey = () => {
  let key = sessionStorage.getItem("tab_session_key");
  
  if (!key) {
    // Generate a unique key (UUID-like)
    key = 'tab_' + Math.random().toString(36).substr(2, 12) + '_' + Date.now().toString(36);
    sessionStorage.setItem("tab_session_key", key);
  }
  
  return key;
};

// Helper to get auth headers (always includes tab key)
export const getAuthHeaders = () => {
  const headers = {
    "Content-Type": "application/json",
  };
  
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  // Always include tab session key
  headers["X-Tab-Session-Key"] = getTabSessionKey();
  
  return headers;
};

// Data Visualization API
export const dataVizAPI = {
  uploadDataset: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const token = localStorage.getItem('token');
    const tabSessionKey = getTabSessionKey();
    
    const response = await fetch(`${API_BASE_URL}/api/data-viz/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-Tab-Session-Key': tabSessionKey
      },
      body: formData
    });
    
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to upload dataset');
    return data;
  },

  getDatasets: async () => {
    const response = await fetch(`${API_BASE_URL}/api/data-viz/datasets`, {
      headers: getAuthHeaders()
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch datasets');
    return data;
  },

  analyzeDataset: async (datasetId) => {
    const response = await fetch(`${API_BASE_URL}/api/data-viz/analyze`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ dataset_id: datasetId })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to analyze dataset');
    return data;
  },

  visualizeDataset: async (datasetId, config) => {
    const response = await fetch(`${API_BASE_URL}/api/data-viz/visualize`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        dataset_id: datasetId,
        config: config
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to create visualization');
    return data;
  },

  downloadVisualization: (vizId, format = 'png') => {
    const url = `${API_BASE_URL}/api/data-viz/download/${vizId}?format=${format}`;
    window.open(url, '_blank');
  }
};
export const chatAPI = {
  // ============================================
  // EXISTING FUNCTIONS (kept as is)
  // ============================================
  
  getUserProjects: async () => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/projects`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch chat projects");
    return data;
  },

  getProjectChannels: async (projectId) => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/projects/${projectId}/channels`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch channels");
    return data;
  },

  getChannelMessages: async (channelId, limit = 50) => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/channels/${channelId}/messages?limit=${limit}`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch messages");
    return data;
  },

  // ============================================
  // UPDATED: sendMessage - Now supports objects with attachments
  // ============================================
  sendMessage: async (channelId, messageData) => {
    // Support both string and object formats
    const payload = typeof messageData === 'string' 
      ? { text: messageData } 
      : messageData;

    const response = await fetch(`${API_BASE_URL}/api/team-chat/channels/${channelId}/messages`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to send message");
    return data;
  },

  createChannel: async (projectId, channelData) => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/projects/${projectId}/channels`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(channelData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to create channel");
    return data;
  },

  deleteChannel: async (channelId) => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/channels/${channelId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to delete channel");
    return data;
  },

  getStats: async () => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/stats`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch chat stats");
    return data;
  },

  // ============================================
  // ENHANCED: Reactions - Fixed to match controller
  // ============================================
  addReaction: async (channelId, messageId, emojiData) => {
    // Support both object {emoji: "👍"} and string "👍"
    const payload = typeof emojiData === 'string' 
      ? { emoji: emojiData } 
      : emojiData;

    const response = await fetch(`${API_BASE_URL}/api/team-chat/channels/${channelId}/messages/${messageId}/reactions`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to add reaction');
    }
    
    return await response.json();
  },

  // Note: Backend uses POST to toggle reactions, so removeReaction calls addReaction
  removeReaction: async (channelId, messageId, emoji) => {
    // Same endpoint - backend toggles reactions
    return chatAPI.addReaction(channelId, messageId, emoji);
  },

  // ============================================
  // ENHANCED: Message Editing & Deletion
  // ============================================
  editMessage: async (channelId, messageId, messageData) => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/channels/${channelId}/messages/${messageId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(messageData)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to edit message');
    }
    
    return await response.json();
  },

  // Alias for consistency
  updateMessage: async (channelId, messageId, messageData) => {
    return chatAPI.editMessage(channelId, messageId, messageData);
  },

  deleteMessage: async (channelId, messageId) => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/channels/${channelId}/messages/${messageId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to delete message');
    }
    
    return await response.json();
  },

  // ============================================
  // ENHANCED: Thread Replies
  // ============================================
  getThreadReplies: async (channelId, messageId, params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const url = `${API_BASE_URL}/api/team-chat/channels/${channelId}/messages/${messageId}/replies${queryString ? '?' + queryString : ''}`;
    
    const response = await fetch(url, {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch thread replies');
    }
    
    return await response.json();
  },

  // Alias for consistency with backend
  getMessageThread: async (channelId, messageId) => {
    return chatAPI.getThreadReplies(channelId, messageId);
  },

  postThreadReply: async (channelId, messageId, replyData) => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/channels/${channelId}/messages/${messageId}/replies`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(replyData)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to post thread reply');
    }
    
    return await response.json();
  },

  // ============================================
  // ENHANCED: File Upload - FIXED VERSION
  // ============================================
  uploadAttachment: async (fileOrFormData) => {
    let formData;
    
    // Handle both File object and FormData
    if (fileOrFormData instanceof FormData) {
      formData = fileOrFormData;
    } else {
      formData = new FormData();
      formData.append('file', fileOrFormData);
    }
    
    // Get token for auth (don't use getAuthHeaders for FormData!)
    const token = localStorage.getItem('token');
    const tabSessionKey = getTabSessionKey();
    
    const response = await fetch(`${API_BASE_URL}/api/team-chat/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-Tab-Session-Key': tabSessionKey
        // IMPORTANT: Don't set Content-Type for FormData - browser will set it with boundary
      },
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to upload file');
    }
    
    return await response.json();
  },

  // ============================================
  // ENHANCED: Mentions & Search
  // ============================================
  getMentions: async () => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/mentions`, {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch mentions');
    }
    
    return await response.json();
  },

  // Alias for consistency
  getUserMentions: async () => {
    return chatAPI.getMentions();
  },

  searchMessages: async (channelId, query) => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/search/${channelId}?q=${encodeURIComponent(query)}`, {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to search messages');
    }
    
    return await response.json();
  },

  // ============================================
  // ENHANCED: Read Receipts - FIXED ENDPOINT
  // ============================================
  markAsRead: async (channelId, messageIds) => {
    const response = await fetch(`${API_BASE_URL}/api/team-chat/channels/${channelId}/read`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ message_ids: messageIds })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to mark as read');
    }
    
    return await response.json();
  }
};

// Auth API calls
export const authAPI = {
  register: async (name, email, password) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Registration failed");
    return data;
  },

  login: async (email, password) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Login failed");
    return data;
  },

  clerkSync: async (clerkToken, email, name, clerkUserId) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/clerk-sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        clerk_token: clerkToken,
        email,
        name,
        clerk_user_id: clerkUserId,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Clerk sync failed");
    return data;
  },

  getProfile: async () => {
    const response = await fetch(`${API_BASE_URL}/api/auth/profile`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to get profile");
    return data;
  },
};

// Dashboard API calls with caching
export const dashboardAPI = {
  getAnalytics: async () => {
    const cacheKey = 'dashboard:analytics';
    const cached = requestCache.get(cacheKey);
    if (cached) return cached;

    // Check if request is in progress
    if (requestCache.isPending(cacheKey)) {
      return requestCache.getPending(cacheKey);
    }

    const requestPromise = fetch(`${API_BASE_URL}/api/dashboard/analytics`, {
      headers: getAuthHeaders(),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to fetch analytics");
      requestCache.set(cacheKey, data);
      return data;
    });

    requestCache.setPending(cacheKey, requestPromise);
    return requestPromise;
  },

  getReport: async () => {
    const cacheKey = 'dashboard:report';
    const cached = requestCache.get(cacheKey);
    if (cached) return cached;

    if (requestCache.isPending(cacheKey)) {
      return requestCache.getPending(cacheKey);
    }

    const requestPromise = fetch(`${API_BASE_URL}/api/dashboard/report`, {
      headers: getAuthHeaders(),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to fetch report");
      requestCache.set(cacheKey, data);
      return data;
    });

    requestCache.setPending(cacheKey, requestPromise);
    return requestPromise;
  },

  getSystemAnalytics: async () => {
    const response = await fetch(`${API_BASE_URL}/api/dashboard/system`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch system analytics");
    return data;
  },

  // Clear dashboard cache
  clearCache: () => {
    requestCache.invalidatePattern('dashboard:');
  }
};

// User API calls
export const userAPI = {
  searchByEmail: async (emailQuery) => {
    const response = await fetch(
      `${API_BASE_URL}/api/users/search?email=${encodeURIComponent(emailQuery)}`,
      {
        headers: getAuthHeaders(),
      }
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to search users");
    return data;
  },

  getAllUsers: async () => {
    const response = await fetch(`${API_BASE_URL}/api/users`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch users");
    return data;
  },

  updateUserRole: async (userId, role) => {
    const response = await fetch(`${API_BASE_URL}/api/users/role`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ user_id: userId, role }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to update user role");
    return data;
  },
};

// Project API calls
export const projectAPI = {
  getAll: async () => {
    const cacheKey = 'projects:all';
    const cached = requestCache.get(cacheKey);
    if (cached) return cached;

    if (requestCache.isPending(cacheKey)) {
      return requestCache.getPending(cacheKey);
    }

    const requestPromise = fetch(`${API_BASE_URL}/api/projects`, {
      headers: getAuthHeaders(),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to fetch projects");
      requestCache.set(cacheKey, data);
      return data;
    });

    requestCache.setPending(cacheKey, requestPromise);
    return requestPromise;
  },

  getById: async (projectId) => {
    const cacheKey = `project:${projectId}`;
    const cached = requestCache.get(cacheKey);
    if (cached) return cached;

    if (requestCache.isPending(cacheKey)) {
      return requestCache.getPending(cacheKey);
    }

    const requestPromise = fetch(`${API_BASE_URL}/api/projects/${projectId}`, {
      headers: getAuthHeaders(),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to fetch project");
      requestCache.set(cacheKey, data);
      return data;
    });

    requestCache.setPending(cacheKey, requestPromise);
    return requestPromise;
  },

  create: async (projectData) => {
    const response = await fetch(`${API_BASE_URL}/api/projects`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(projectData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to create project");
    // Invalidate projects cache
    requestCache.invalidate('projects:all');
    requestCache.invalidatePattern('dashboard:');
    return data;
  },

  update: async (projectId, projectData) => {
    const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify(projectData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to update project");
    // Invalidate caches
    requestCache.invalidate('projects:all');
    requestCache.invalidate(`project:${projectId}`);
    requestCache.invalidatePattern('dashboard:');
    return data;
  },

  delete: async (projectId) => {
    const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to delete project");
    // Invalidate all project-related caches
    requestCache.invalidate('projects:all');
    requestCache.invalidate(`project:${projectId}`);
    requestCache.invalidate(`tasks:project:${projectId}`);
    requestCache.invalidatePattern('dashboard:');
    return data;
  },
};

// Member API calls
export const memberAPI = {
  addMember: async (projectId, email) => {
    const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/members`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ email }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to add member");
    // Invalidate member cache
    requestCache.invalidate(`members:project:${projectId}`);
    return data;
  },

  getMembers: async (projectId) => {
    const cacheKey = `members:project:${projectId}`;
    const cached = requestCache.get(cacheKey);
    if (cached) return cached;

    if (requestCache.isPending(cacheKey)) {
      return requestCache.getPending(cacheKey);
    }

    const requestPromise = fetch(`${API_BASE_URL}/api/projects/${projectId}/members`, {
      headers: getAuthHeaders(),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to fetch members");
      requestCache.set(cacheKey, data);
      return data;
    });

    requestCache.setPending(cacheKey, requestPromise);
    return requestPromise;
  },

  removeMember: async (projectId, userId) => {
    const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/members/${userId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to remove member");
    // Invalidate member cache
    requestCache.invalidate(`members:project:${projectId}`);
    return data;
  },
};

// Task API calls
export const taskAPI = {
  create: async (projectId, taskData) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        ...taskData,
        project_id: projectId,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to create task");
    // Invalidate task and dashboard caches
    requestCache.invalidate(`tasks:project:${projectId}`);
    requestCache.invalidatePattern('dashboard:');
    requestCache.invalidatePattern('tasks:');
    return data;
  },

  getByProject: async (projectId) => {
    const cacheKey = `tasks:project:${projectId}`;
    const cached = requestCache.get(cacheKey);
    if (cached) return cached;

    if (requestCache.isPending(cacheKey)) {
      return requestCache.getPending(cacheKey);
    }

    const requestPromise = fetch(`${API_BASE_URL}/api/tasks/project/${projectId}`, {
      headers: getAuthHeaders(),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to fetch tasks");
      requestCache.set(cacheKey, data);
      return data;
    });

    requestCache.setPending(cacheKey, requestPromise);
    return requestPromise;
  },

  getById: async (taskId) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch task");
    return data;
  },

  getMyTasks: async () => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/my`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch tasks");
    return data;
  },

  update: async (taskId, taskData) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify(taskData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to update task");
    // Invalidate caches
    requestCache.invalidatePattern('tasks:');
    requestCache.invalidatePattern('dashboard:');
    return data;
  },

  delete: async (taskId) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to delete task");
    // Invalidate caches
    requestCache.invalidatePattern('tasks:');
    requestCache.invalidatePattern('dashboard:');
    return data;
  },

  addLabel: async (taskId, label) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/labels`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ label }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to add label");
    return data;
  },

  removeLabel: async (taskId, label) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/labels/${encodeURIComponent(label)}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to remove label");
    return data;
  },

  addAttachment: async (taskId, attachmentData) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/attachments`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(attachmentData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to add attachment");
    return data;
  },

  removeAttachment: async (taskId, attachmentUrl) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/attachments`, {
      method: "DELETE",
      headers: getAuthHeaders(),
      body: JSON.stringify({ url: attachmentUrl }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to remove attachment");
    return data;
  },

  addLink: async (taskId, linkData) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/links`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(linkData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to add link");
    return data;
  },

  removeLink: async (taskId, linkedTicketId, linkType) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/links`, {
      method: "DELETE",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        linked_task_id: linkedTicketId,
        type: linkType
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to remove link");
    return data;
  },

  approveTask: async (taskId) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/approve`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to approve task");
    // Invalidate approval and closed task caches
    requestCache.invalidate('tasks:pending-approval');
    requestCache.invalidate('tasks:closed');
    requestCache.invalidatePattern('dashboard:');
    return data;
  },

  getDoneTasksForApproval: async (projectId) => {
    const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/tasks/done`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch done tasks");
    return data;
  },

  getAllPendingApprovalTasks: async () => {
    const cacheKey = 'tasks:pending-approval';
    const cached = requestCache.get(cacheKey);
    if (cached) return cached;

    if (requestCache.isPending(cacheKey)) {
      return requestCache.getPending(cacheKey);
    }

    const requestPromise = fetch(`${API_BASE_URL}/api/tasks/pending-approval`, {
      headers: getAuthHeaders(),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to fetch pending approval tasks");
      requestCache.set(cacheKey, data);
      return data;
    });

    requestCache.setPending(cacheKey, requestPromise);
    return requestPromise;
  },

  getAllClosedTasks: async () => {
    const cacheKey = 'tasks:closed';
    const cached = requestCache.get(cacheKey);
    if (cached) return cached;

    if (requestCache.isPending(cacheKey)) {
      return requestCache.getPending(cacheKey);
    }

    const requestPromise = fetch(`${API_BASE_URL}/api/tasks/closed`, {
      headers: getAuthHeaders(),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to fetch closed tasks");
      requestCache.set(cacheKey, data);
      return data;
    });

    requestCache.setPending(cacheKey, requestPromise);
    return requestPromise;
  },
  
  addComment: async (taskId, comment) => {
    if (!comment?.trim()) {
      throw new Error("Comment cannot be empty");
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/comments`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ comment: comment.trim() }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || errorData.message || `Server error: ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      console.error("addComment failed:", err);
      throw err;
    }
  },

  getGitActivity: async (taskId) => {
    const response = await fetch(`${API_BASE_URL}/api/tasks/git-activity/${taskId}`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch git activity");
    return data;
  },
};

// Profile API
export const profileAPI = {
  getProfile: async () => {
    const response = await fetch(`${API_BASE_URL}/api/profile`, {
      headers: getAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to fetch profile");
    return data;
  },

  updatePersonal: async (personalData) => {
    const response = await fetch(`${API_BASE_URL}/api/profile/personal`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ data: personalData }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to update personal info");
    return data;
  },

  updateEducation: async (educationData) => {
    const response = await fetch(`${API_BASE_URL}/api/profile/education`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ education: educationData }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to update education");
    return data;
  },

  updateCertificates: async (certificatesData) => {
    const response = await fetch(`${API_BASE_URL}/api/profile/certificates`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ certificates: certificatesData }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to update certificates");
    return data;
  },

  updateOrganization: async (organizationData) => {
    const response = await fetch(`${API_BASE_URL}/api/profile/organization`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ data: organizationData }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to update organization");
    return data;
  },
};