import React, { useState, useEffect, useRef, useContext } from 'react';
import { BsPlus, BsTrash, BsSend, BsImage, BsPaperclip } from 'react-icons/bs';
import { FaRobot } from 'react-icons/fa';
import { AuthContext } from '../../context/AuthContext';
import './AIAssistantPage.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Get or generate tab session key for security
const getTabSessionKey = () => {
  let key = sessionStorage.getItem("tab_session_key");
  if (!key) {
    key = 'tab_' + Math.random().toString(36).substr(2, 12) + '_' + Date.now().toString(36);
    sessionStorage.setItem("tab_session_key", key);
  }
  return key;
};

// Get auth headers with tab session key
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Authorization': `Bearer ${token}`,
    'X-Tab-Session-Key': getTabSessionKey(),
    'Content-Type': 'application/json'
  };
};

const AIAssistantPage = () => {
  const { user } = useContext(AuthContext);
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load messages when conversation changes
  useEffect(() => {
    if (activeConversation) {
      setMessages([]); // Clear messages first
      loadMessages(activeConversation._id);
    } else {
      setMessages([]); // Clear messages if no conversation selected
    }
  }, [activeConversation?._id]); // Only re-run when conversation ID changes

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/ai-assistant/conversations`, {
        headers: getAuthHeaders()
      });
      const data = await response.json();
      if (data.success) {
        setConversations(data.conversations);
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  };

  const loadMessages = async (conversationId) => {
    try {
      const response = await fetch(
        `${API_BASE}/api/ai-assistant/conversations/${conversationId}/messages`,
        {
          headers: getAuthHeaders()
        }
      );
      const data = await response.json();
      if (data.success) {
        setMessages(data.messages);
      }
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const createNewConversation = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/ai-assistant/conversations`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ title: 'New Conversation' })
      });
      const data = await response.json();
      if (data.success) {
        setConversations([data.conversation, ...conversations]);
        setActiveConversation(data.conversation);
        setMessages([]);
        return data.conversation; // Return the conversation for immediate use
      }
    } catch (error) {
      console.error('Error creating conversation:', error);
      return null;
    }
  };

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    // Save input text before clearing
    const messageContent = inputText;
    let conversationToUse = activeConversation;

    // Create new conversation if none exists
    if (!conversationToUse) {
      conversationToUse = await createNewConversation();
      if (!conversationToUse) {
        console.error('Failed to create conversation');
        return;
      }
    }

    const userMessage = {
      role: 'user',
      content: messageContent,
      created_at: new Date().toISOString()
    };

    // Add user message to UI immediately
    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      const response = await fetch(
        `${API_BASE}/api/ai-assistant/conversations/${conversationToUse._id}/messages`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            content: messageContent,
            stream: false
          })
        }
      );

      const data = await response.json();
      setIsTyping(false);

      if (data.success && data.message) {
        // Add AI response
        setMessages(prev => [...prev, data.message]);
        
        // Reload conversations to update the list
        loadConversations();
      } else {
        console.error('No AI response received:', data);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setIsTyping(false);
    } finally {
      setIsLoading(false);
    }
  };

  const generateImage = async () => {
    if (!inputText.trim() || isLoading) return;

    // Save input text before clearing
    const prompt = inputText;
    let conversationToUse = activeConversation;

    if (!conversationToUse) {
      conversationToUse = await createNewConversation();
      if (!conversationToUse) {
        console.error('Failed to create conversation');
        return;
      }
    }

    const userMessage = {
      role: 'user',
      content: `Generate image: ${prompt}`,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      const response = await fetch(
        `${API_BASE}/api/ai-assistant/conversations/${conversationToUse._id}/generate-image`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ prompt })
        }
      );

      const data = await response.json();
      setIsTyping(false);

      if (data.success) {
        setMessages(prev => [...prev, data.message]);
        loadConversations();
      }
    } catch (error) {
      console.error('Error generating image:', error);
      setIsTyping(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || isLoading) return;

    let conversationToUse = activeConversation;
    if (!conversationToUse) {
      conversationToUse = await createNewConversation();
      if (!conversationToUse) {
        console.error('Failed to create conversation');
        return;
      }
    }

    const userMessage = {
      role: 'user',
      content: `Uploaded file: ${file.name}`,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setIsTyping(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(
        `${API_BASE}/api/ai-assistant/conversations/${conversationToUse._id}/upload`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'X-Tab-Session-Key': getTabSessionKey()
          },
          body: formData
        }
      );

      const data = await response.json();
      setIsTyping(false);

      if (data.success) {
        // If there's an AI response message, add it to the chat
        if (data.ai_message_id) {
          const aiMessage = {
            role: 'assistant',
            content: data.message,
            created_at: new Date().toISOString()
          };
          setMessages(prev => [...prev, aiMessage]);
        }
        
        if (data.file?.extracted) {
          console.log('File content extracted successfully:', data.file.metadata);
        }
        
        setUploadedFile(file.name);
        loadConversations();
      } else {
        throw new Error(data.message || 'Upload failed');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      const errorMessage = {
        role: 'assistant',
        content: `Sorry, I couldn't upload the file. ${error.message}`,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
      setIsTyping(false);
    } finally {
      setIsLoading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const deleteConversation = async (conversationId, e) => {
    e.stopPropagation();
    
    try {
      await fetch(`${API_BASE}/api/ai-assistant/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      
      setConversations(prev => prev.filter(c => c._id !== conversationId));
      if (activeConversation?._id === conversationId) {
        setActiveConversation(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  const suggestionPrompts = [
    "Explain how sprint planning works in Agile",
    "What are the best practices for task management?",
    "Generate a project timeline visualization",
    "Help me optimize my team's workflow"
  ];

  return (
    <div className="ai-assistant-page">
      {/* Sidebar - Conversations */}
      <div className="ai-sidebar">
        <div className="ai-sidebar-header">
          <button className="new-chat-btn" onClick={createNewConversation}>
            <BsPlus size={24} />
            New Chat
          </button>
        </div>
        
        <div className="conversations-list">
          {conversations.map(conv => (
            <div
              key={conv._id}
              className={`conversation-item ${activeConversation?._id === conv._id ? 'active' : ''}`}
              onClick={() => setActiveConversation(conv)}
            >
              <div className="conversation-title">{conv.title}</div>
              <div className="conversation-date">
                {formatTimestamp(conv.updated_at)}
              </div>
              <button
                className="conversation-delete"
                onClick={(e) => deleteConversation(conv._id, e)}
              >
                <BsTrash />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="ai-chat-area">
        <div className="ai-chat-header">
          <div className="ai-chat-title">
            <FaRobot size={24} />
            DOIT AI Assistant
          </div>
          <div className="ai-status-badge">
            <div className="ai-status-dot"></div>
            Online
          </div>
        </div>

        <div className="ai-messages-container">
          {messages.length === 0 ? (
            <div className="ai-empty-state">
              <div className="ai-empty-icon">🤖✨</div>
              <div className="ai-empty-title">
                Welcome to DOIT AI Assistant
              </div>
              <div className="ai-empty-subtitle">
                I can help you with project management questions, generate images,
                analyze data, and provide insights for your team.
              </div>
              <div className="ai-suggestion-chips">
                {suggestionPrompts.map((prompt, idx) => (
                  <div
                    key={idx}
                    className="ai-suggestion-chip"
                    onClick={() => setInputText(prompt)}
                  >
                    {prompt}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <div key={idx} className={`ai-message ${msg.role}`}>
                  <div className="ai-message-avatar">
                    {msg.role === 'user' ? user?.name?.charAt(0).toUpperCase() : '🤖'}
                  </div>
                  <div className="ai-message-content">
                    <div className="ai-message-bubble">
                      {msg.content}
                    </div>
                    {msg.image_url && (
                      <div className="ai-message-image">
                        <img src={`${API_BASE}${msg.image_url}`} alt="Generated" />
                      </div>
                    )}
                    <div className="ai-message-timestamp">
                      {formatTimestamp(msg.created_at)}
                    </div>
                  </div>
                </div>
              ))}
              
              {isTyping && (
                <div className="ai-message assistant">
                  <div className="ai-message-avatar">🤖</div>
                  <div className="ai-message-content">
                    <div className="ai-message-bubble">
                      <div className="ai-loading-dots">
                        <div className="ai-loading-dot"></div>
                        <div className="ai-loading-dot"></div>
                        <div className="ai-loading-dot"></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        <div className="ai-input-area">
          <div className="ai-input-actions">
            <button 
              className="ai-action-btn" 
              onClick={generateImage} 
              disabled={isLoading || !inputText.trim()}
              title="Generate an image from your text description"
            >
              <BsImage /> Generate Image
            </button>
            <button 
              className="ai-action-btn" 
              onClick={() => fileInputRef.current?.click()} 
              disabled={isLoading}
              title="Upload a file to analyze"
            >
              <BsPaperclip /> Upload File
            </button>
            <input
              ref={fileInputRef}
              type="file"
              style={{ display: 'none' }}
              onChange={handleFileUpload}
              accept=".txt,.pdf,.doc,.docx,.png,.jpg,.jpeg,.csv,.json"
            />
          </div>
          
          <div className="ai-input-container">
            <div className="ai-textarea-wrapper">
              <textarea
                ref={textareaRef}
                className="ai-textarea"
                placeholder={uploadedFile ? `Ask about "${uploadedFile}"...` : "Ask me anything or describe an image to generate..."}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                rows={1}
              />
            </div>
            <button
              className="ai-send-btn"
              onClick={sendMessage}
              disabled={isLoading || !inputText.trim()}
            >
              <BsSend />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIAssistantPage;
