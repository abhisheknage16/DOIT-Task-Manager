import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  MessageCircle, X, Send, Hash, ChevronDown, Plus, Trash2, RefreshCw, Users,
  Smile, Edit2, Reply, Paperclip, Image, FileText, Download, MoreVertical, Wifi, WifiOff
} from 'lucide-react';
import { chatAPI } from '../../services/api';
import { useWebSocket } from '../../utils/useWebSocket';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

export default function TeamChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [currentProject, setCurrentProject] = useState(null);
  const [currentChannel, setCurrentChannel] = useState(null);
  const [message, setMessage] = useState('');
  const [projects, setProjects] = useState([]);
  const [channels, setChannels] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [showChannelDropdown, setShowChannelDropdown] = useState(false);
  const [newChannelName, setNewChannelName] = useState('');
  const [newChannelDesc, setNewChannelDesc] = useState('');
  const [showNewChannelForm, setShowNewChannelForm] = useState(false);
  
  // Enhanced features state
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editingText, setEditingText] = useState('');
  const [replyingTo, setReplyingTo] = useState(null);
  const [showEmojiPicker, setShowEmojiPicker] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [messageMenuOpen, setMessageMenuOpen] = useState(null);
  
  const chatEndRef = useRef(null);
  const dropdownRef = useRef(null);
  const fileInputRef = useRef(null);
  const emojiPickerRef = useRef(null);

  // Common emojis for quick access
  const commonEmojis = ['👍', '❤️', '😊', '🎉', '👏', '🔥', '✅', '👀'];

  // WebSocket message handler
  const handleWebSocketMessage = useCallback((data) => {
    console.log('[TeamChat WS] Received:', data.type);
    
    switch (data.type) {
      case 'connection':
        console.log('[TeamChat WS] Connected to channel:', data.channel_id);
        break;
        
      case 'new_message':
        // Add new message to the list
        setMessages(prev => {
          // Avoid duplicates
          if (prev.some(m => m.id === data.message.id)) {
            return prev;
          }
          return [...prev, data.message];
        });
        break;
        
      case 'message_edited':
        // Update edited message
        setMessages(prev => prev.map(msg => 
          msg.id === data.message_id 
            ? { ...msg, text: data.text, edited: true }
            : msg
        ));
        break;
        
      case 'message_deleted':
        // Remove deleted message
        setMessages(prev => prev.filter(msg => msg.id !== data.message_id));
        break;
        
      case 'reaction_updated':
        // Update message reactions
        setMessages(prev => prev.map(msg => 
          msg.id === data.message_id 
            ? { ...msg, reactions: data.reactions }
            : msg
        ));
        break;
        
      case 'user_joined':
        console.log('[TeamChat WS] User joined:', data.user_id);
        break;
        
      case 'user_left':
        console.log('[TeamChat WS] User left:', data.user_id);
        break;
        
      case 'pong':
        // Heartbeat response
        break;
        
      default:
        console.log('[TeamChat WS] Unknown message type:', data.type);
    }
  }, []);

  // Build WebSocket URL
  const wsUrl = currentChannel && isOpen
    ? `${API_BASE_URL.replace('http', 'ws')}/api/team-chat/ws/${currentChannel}?token=${localStorage.getItem('token')}`
    : null;

  // WebSocket connection
  const { connectionStatus, isConnected } = useWebSocket(
    wsUrl,
    handleWebSocketMessage,
    {
      enabled: Boolean(currentChannel && isOpen),
      reconnectAttempts: 10,
      reconnectInterval: 2000
    }
  );

  // Scroll to bottom when messages change
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Click outside handlers
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowChannelDropdown(false);
      }
      if (emojiPickerRef.current && !emojiPickerRef.current.contains(event.target)) {
        setShowEmojiPicker(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch projects on mount
  useEffect(() => {
    if (isOpen) {
      fetchProjects();
    }
  }, [isOpen]);

  // Fetch channels when project changes
  useEffect(() => {
    if (currentProject) {
      fetchChannels(currentProject);
    }
  }, [currentProject]);

  // Fetch messages when channel changes (initial load only)
  useEffect(() => {
    if (currentChannel) {
      fetchMessages(currentChannel);
    }
  }, [currentChannel]);

  const fetchProjects = async () => {
    try {
      console.log('[TeamChat] Fetching projects...');
      const data = await chatAPI.getUserProjects();
      console.log('[TeamChat] Projects response:', data);
      setProjects(data.projects || []);
      
      if (!currentProject && data.projects && data.projects.length > 0) {
        console.log('[TeamChat] Auto-selecting first project:', data.projects[0].id);
        setCurrentProject(data.projects[0].id);
      }
    } catch (error) {
      console.error('[TeamChat] Error fetching projects:', error);
      console.error('[TeamChat] Error details:', error.message);
    }
  };

  const fetchChannels = async (projectId) => {
    try {
      console.log('[TeamChat] Fetching channels for project:', projectId);
      setLoading(true);
      const data = await chatAPI.getProjectChannels(projectId);
      console.log('[TeamChat] Channels response:', data);
      setChannels(data.channels || []);
      
      if (data.channels && data.channels.length > 0) {
        console.log('[TeamChat] Auto-selecting first channel:', data.channels[0].id);
        setCurrentChannel(data.channels[0].id);
      }
    } catch (error) {
      console.error('[TeamChat] Error fetching channels:', error);
      console.error('[TeamChat] Error details:', error.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (channelId) => {
    try {
      console.log('[TeamChat] Fetching messages for channel:', channelId);
      const data = await chatAPI.getChannelMessages(channelId);
      console.log('[TeamChat] Messages response:', data);
      setMessages(data.messages || []);
    } catch (error) {
      console.error('[TeamChat] Error fetching messages:', error);
      console.error('[TeamChat] Error details:', error.message);
    }
  };

  const handleSendMessage = async () => {
    if ((!message.trim() && !selectedFile) || !currentChannel || sending) return;

    const messageText = message.trim();
    const fileToUpload = selectedFile;
    
    setMessage('');
    setSelectedFile(null);
    setSending(true);

    try {
      let attachment = null;
      
      // Upload file if present
      if (fileToUpload) {
        setUploadProgress(10);
        const formData = new FormData();
        formData.append('file', fileToUpload);
        
        const uploadResponse = await chatAPI.uploadAttachment(formData);
        attachment = uploadResponse.attachment;
        setUploadProgress(100);
      }

      // Send message via HTTP (WebSocket will broadcast it to all)
      await chatAPI.sendMessage(currentChannel, {
        text: messageText,
        parent_id: replyingTo?.id || null,
        attachment: attachment
      });
      
      // Clear reply state
      setReplyingTo(null);
      setUploadProgress(0);
      
      // Message will appear via WebSocket broadcast
      // No need to manually fetch messages
    } catch (error) {
      console.error('Error sending message:', error);
      setMessage(messageText);
      setSelectedFile(fileToUpload);
    } finally {
      setSending(false);
    }
  };

  const handleEditMessage = async (messageId) => {
    if (!editingText.trim()) return;

    try {
      await chatAPI.editMessage(currentChannel, messageId, {
        text: editingText.trim()
      });
      
      setEditingMessageId(null);
      setEditingText('');
      // Message will be updated via WebSocket
    } catch (error) {
      console.error('Error editing message:', error);
      alert(error.message || 'Failed to edit message');
    }
  };

  const handleDeleteMessage = async (messageId) => {
    if (!window.confirm('Delete this message?')) return;

    try {
      await chatAPI.deleteMessage(currentChannel, messageId);
      // Message will be removed via WebSocket
    } catch (error) {
      console.error('Error deleting message:', error);
      alert(error.message || 'Failed to delete message');
    }
  };

  const handleAddReaction = async (messageId, emoji) => {
    try {
      await chatAPI.addReaction(currentChannel, messageId, { emoji });
      setShowEmojiPicker(null);
      // WebSocket will update reactions automatically
    } catch (error) {
      console.error('Error adding reaction:', error);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        alert('File size must be less than 10MB');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (editingMessageId) {
        handleEditMessage(editingMessageId);
      } else {
        handleSendMessage();
      }
    }
  };

  const handleCreateChannel = async () => {
    if (!newChannelName.trim() || !currentProject) return;

    try {
      await chatAPI.createChannel(currentProject, {
        name: newChannelName.toLowerCase().trim(),
        description: newChannelDesc.trim()
      });
      
      await fetchChannels(currentProject);
      
      setNewChannelName('');
      setNewChannelDesc('');
      setShowNewChannelForm(false);
    } catch (error) {
      console.error('Error creating channel:', error);
      alert(error.message || 'Failed to create channel');
    }
  };

  const handleDeleteChannel = async (channelId) => {
    if (!window.confirm('Are you sure you want to delete this channel? All messages will be lost.')) {
      return;
    }

    try {
      await chatAPI.deleteChannel(channelId);
      await fetchChannels(currentProject);
    } catch (error) {
      console.error('Error deleting channel:', error);
      alert(error.message || 'Failed to delete channel');
    }
  };

  const startEditing = (msg) => {
    setEditingMessageId(msg.id);
    setEditingText(msg.text);
    setMessageMenuOpen(null);
  };

  const cancelEditing = () => {
    setEditingMessageId(null);
    setEditingText('');
  };

  const currentProjectData = projects.find(p => p.id === currentProject);
  const currentChannelData = channels.find(ch => ch.id === currentChannel);
  const totalUnread = projects.reduce((sum, p) => sum + (p.unread || 0), 0);

  const getCurrentUserId = () => {
    // Get from localStorage or context
    return localStorage.getItem('user_id') || '';
  };

  return (
    <>
      {/* Floating Chat Button - LEFT BOTTOM */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="team-chat-btn"
          style={{
            position: 'fixed',
            bottom: '24px',
            left: '24px',
            width: '52px',
            height: '52px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none',
            color: 'white',
            cursor: 'pointer',
            boxShadow: '0 4px 16px rgba(102, 126, 234, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 999,
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
          }}
        >
          <MessageCircle size={22} strokeWidth={2.5} />
          {totalUnread > 0 && (
            <span style={{
              position: 'absolute',
              top: '-2px',
              right: '-2px',
              background: '#ef4444',
              color: 'white',
              fontSize: '10px',
              fontWeight: '700',
              padding: '2px 5px',
              borderRadius: '10px',
              minWidth: '18px',
              textAlign: 'center',
              border: '2px solid white',
              boxShadow: '0 2px 8px rgba(239, 68, 68, 0.3)'
            }}>
              {totalUnread > 99 ? '99+' : totalUnread}
            </span>
          )}
        </button>
      )}

      {/* Chat Window - COMPACT & PROFESSIONAL */}
      {isOpen && (
        <div style={{
          position: 'fixed',
          bottom: '20px',
          left: '20px',
          width: '380px',
          height: '540px',
          background: 'white',
          borderRadius: '12px',
          boxShadow: '0 12px 48px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 1000,
          overflow: 'hidden',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        }}>
          {/* Header - COMPACT */}
          <div style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            padding: '12px 14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              {/* Project Dropdown - COMPACT */}
              <div style={{ position: 'relative', marginBottom: '4px' }} ref={dropdownRef}>
                <button
                  onClick={() => setShowChannelDropdown(!showChannelDropdown)}
                  style={{
                    background: 'rgba(255, 255, 255, 0.15)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '6px',
                    padding: '4px 8px',
                    color: 'white',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '13px',
                    fontWeight: '600',
                    width: '100%',
                    justifyContent: 'space-between',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0 }}>
                    <Users size={13} />
                    <span style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {currentProjectData?.name || 'Select Project'}
                    </span>
                  </div>
                  <ChevronDown size={14} />
                </button>

                {/* Dropdown Menu */}
                {showChannelDropdown && (
                  <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    marginTop: '4px',
                    background: 'white',
                    borderRadius: '8px',
                    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.15)',
                    maxHeight: '240px',
                    overflowY: 'auto',
                    zIndex: 1001
                  }}>
                    {projects.map(project => (
                      <button
                        key={project.id}
                        onClick={() => {
                          setCurrentProject(project.id);
                          setShowChannelDropdown(false);
                        }}
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          border: 'none',
                          background: currentProject === project.id ? '#f3f4f6' : 'transparent',
                          cursor: 'pointer',
                          textAlign: 'left',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          color: '#1f2937',
                          fontSize: '13px',
                          transition: 'background 0.15s'
                        }}
                        onMouseEnter={(e) => {
                          if (currentProject !== project.id) {
                            e.currentTarget.style.background = '#f9fafb';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (currentProject !== project.id) {
                            e.currentTarget.style.background = 'transparent';
                          }
                        }}
                      >
                        <div style={{
                          width: '6px',
                          height: '6px',
                          borderRadius: '50%',
                          background: project.color,
                          flexShrink: 0
                        }} />
                        <span style={{
                          flex: 1,
                          fontWeight: '500',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {project.name}
                        </span>
                        {project.unread > 0 && (
                          <span style={{
                            background: '#ef4444',
                            color: 'white',
                            fontSize: '10px',
                            fontWeight: '600',
                            padding: '1px 5px',
                            borderRadius: '8px',
                            minWidth: '18px',
                            textAlign: 'center'
                          }}>
                            {project.unread}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Current Channel */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11px',
                opacity: 0.85,
                fontWeight: '500'
              }}>
                <Hash size={11} />
                <span>{currentChannelData?.name || 'general'}</span>
                {/* WebSocket Connection Status */}
                {currentChannel && (
                  <span style={{
                    marginLeft: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '3px',
                    fontSize: '10px'
                  }}>
                    {isConnected ? (
                      <>
                        <Wifi size={10} />
                        <span style={{ opacity: 0.7 }}>Live</span>
                      </>
                    ) : connectionStatus === 'connecting' ? (
                      <>
                        <WifiOff size={10} />
                        <span style={{ opacity: 0.7 }}>Connecting...</span>
                      </>
                    ) : (
                      <>
                        <WifiOff size={10} />
                        <span style={{ opacity: 0.7 }}>Offline</span>
                      </>
                    )}
                  </span>
                )}
              </div>
            </div>

            <button
              onClick={() => setIsOpen(false)}
              style={{
                background: 'rgba(255, 255, 255, 0.15)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '6px',
                width: '28px',
                height: '28px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                color: 'white',
                marginLeft: '10px',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.25)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)'}
            >
              <X size={16} />
            </button>
          </div>

          {/* Main Content */}
          <div style={{
            flex: 1,
            display: 'flex',
            minHeight: 0,
            background: '#fafafa'
          }}>
            {/* Sidebar - Channels - COMPACT */}
            <div style={{
              width: '110px',
              borderRight: '1px solid #e5e7eb',
              background: '#ffffff',
              display: 'flex',
              flexDirection: 'column'
            }}>
              <div style={{
                padding: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid #e5e7eb'
              }}>
                <span style={{
                  fontSize: '10px',
                  fontWeight: '700',
                  color: '#6b7280',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  Channels
                </span>
                {currentProjectData?.is_owner && (
                  <button
                    onClick={() => setShowNewChannelForm(!showNewChannelForm)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#667eea',
                      padding: '2px',
                      borderRadius: '3px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.2s'
                    }}
                    title="Add Channel"
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f3f4f6'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <Plus size={13} />
                  </button>
                )}
              </div>

              {/* New Channel Form - COMPACT */}
              {showNewChannelForm && (
                <div style={{
                  padding: '8px',
                  borderBottom: '1px solid #e5e7eb',
                  background: '#fafafa'
                }}>
                  <input
                    type="text"
                    placeholder="name"
                    value={newChannelName}
                    onChange={(e) => setNewChannelName(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '5px 6px',
                      border: '1px solid #e5e7eb',
                      borderRadius: '4px',
                      fontSize: '11px',
                      marginBottom: '6px'
                    }}
                  />
                  <input
                    type="text"
                    placeholder="desc"
                    value={newChannelDesc}
                    onChange={(e) => setNewChannelDesc(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '5px 6px',
                      border: '1px solid #e5e7eb',
                      borderRadius: '4px',
                      fontSize: '11px',
                      marginBottom: '6px'
                    }}
                  />
                  <button
                    onClick={handleCreateChannel}
                    disabled={!newChannelName.trim()}
                    style={{
                      width: '100%',
                      padding: '5px',
                      background: newChannelName.trim() ? '#667eea' : '#e5e7eb',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '10px',
                      fontWeight: '600',
                      cursor: newChannelName.trim() ? 'pointer' : 'not-allowed'
                    }}
                  >
                    Create
                  </button>
                </div>
              )}

              {/* Channel List - COMPACT */}
              <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '6px'
              }}>
                {channels.map(channel => (
                  <div
                    key={channel.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '2px',
                      marginBottom: '2px'
                    }}
                  >
                    <button
                      onClick={() => setCurrentChannel(channel.id)}
                      style={{
                        flex: 1,
                        padding: '6px',
                        border: 'none',
                        background: currentChannel === channel.id ? '#f3f4f6' : 'transparent',
                        borderRadius: '5px',
                        cursor: 'pointer',
                        textAlign: 'left',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        transition: 'all 0.15s'
                      }}
                      onMouseEnter={(e) => {
                        if (currentChannel !== channel.id) {
                          e.currentTarget.style.background = '#f9fafb';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (currentChannel !== channel.id) {
                          e.currentTarget.style.background = 'transparent';
                        }
                      }}
                    >
                      <Hash size={10} style={{ color: '#9ca3af', flexShrink: 0 }} />
                      <span style={{
                        fontSize: '11px',
                        color: '#1f2937',
                        fontWeight: currentChannel === channel.id ? '600' : '400',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}>
                        {channel.name}
                      </span>
                      {channel.unread > 0 && (
                        <span style={{
                          background: '#ef4444',
                          color: 'white',
                          fontSize: '8px',
                          fontWeight: '700',
                          padding: '1px 3px',
                          borderRadius: '6px',
                          minWidth: '12px',
                          textAlign: 'center'
                        }}>
                          {channel.unread}
                        </span>
                      )}
                    </button>
                    {currentProjectData?.is_owner && channel.name !== 'general' && (
                      <button
                        onClick={() => handleDeleteChannel(channel.id)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          color: '#ef4444',
                          padding: '3px',
                          borderRadius: '3px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          opacity: 0.5,
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.opacity = '1';
                          e.currentTarget.style.background = '#fee2e2';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.opacity = '0.5';
                          e.currentTarget.style.background = 'transparent';
                        }}
                        title="Delete Channel"
                      >
                        <Trash2 size={10} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Messages Area - COMPACT */}
            <div style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              minWidth: 0,
              background: '#ffffff'
            }}>
              {/* Messages */}
              <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
              }}>
                {loading ? (
                  <div style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#9ca3af',
                    fontSize: '12px'
                  }}>
                    Loading...
                  </div>
                ) : messages.length === 0 ? (
                  <div style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    textAlign: 'center',
                    color: '#9ca3af',
                    flexDirection: 'column',
                    gap: '6px'
                  }}>
                    <MessageCircle size={32} style={{ opacity: 0.3 }} />
                    <div>
                      <div style={{ fontWeight: '600', fontSize: '12px', marginBottom: '2px' }}>
                        No messages yet
                      </div>
                      <div style={{ fontSize: '11px' }}>
                        Start the conversation!
                      </div>
                    </div>
                  </div>
                ) : (
                  messages.map(msg => (
                    <div key={msg.id} style={{
                      display: 'flex',
                      gap: '8px',
                      position: 'relative'
                    }}>
                      <div style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        background: msg.color,
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '11px',
                        fontWeight: '600',
                        flexShrink: 0
                      }}>
                        {msg.avatar}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          display: 'flex',
                          alignItems: 'baseline',
                          gap: '5px',
                          marginBottom: '2px'
                        }}>
                          <span style={{
                            fontWeight: '600',
                            fontSize: '12px',
                            color: '#1f2937'
                          }}>
                            {msg.user}
                          </span>
                          <span style={{
                            fontSize: '10px',
                            color: '#9ca3af'
                          }}>
                            {new Date(msg.timestamp || msg.time).toLocaleTimeString([], { 
                              hour: '2-digit', 
                              minute: '2-digit' 
                            })}
                          </span>
                          {msg.edited && (
                            <span style={{
                              fontSize: '9px',
                              color: '#9ca3af',
                              fontStyle: 'italic'
                            }}>
                              (edited)
                            </span>
                          )}
                        </div>
                        
                        {/* Reply indicator */}
                        {msg.parent_id && msg.parent_text && (
                          <div style={{
                            fontSize: '10px',
                            color: '#6b7280',
                            padding: '4px 8px',
                            background: '#f3f4f6',
                            borderRadius: '4px',
                            marginBottom: '4px',
                            borderLeft: '2px solid #9ca3af'
                          }}>
                            <Reply size={10} style={{ display: 'inline', marginRight: '4px' }} />
                            {msg.parent_text.substring(0, 50)}...
                          </div>
                        )}
                        
                        {/* Message text (editable) */}
                        {editingMessageId === msg.id ? (
                          <div>
                            <textarea
                              value={editingText}
                              onChange={(e) => setEditingText(e.target.value)}
                              onKeyPress={handleKeyPress}
                              style={{
                                width: '100%',
                                padding: '6px',
                                border: '1px solid #e5e7eb',
                                borderRadius: '4px',
                                fontSize: '12px',
                                resize: 'none',
                                fontFamily: 'inherit'
                              }}
                              rows="2"
                              autoFocus
                            />
                            <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                              <button
                                onClick={() => handleEditMessage(msg.id)}
                                style={{
                                  padding: '4px 10px',
                                  background: '#667eea',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  cursor: 'pointer'
                                }}
                              >
                                Save
                              </button>
                              <button
                                onClick={cancelEditing}
                                style={{
                                  padding: '4px 10px',
                                  background: '#e5e7eb',
                                  color: '#374151',
                                  border: 'none',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  cursor: 'pointer'
                                }}
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <>
                            {/* Reply preview */}
                            {msg.replyTo && (
                              <div style={{
                                padding: '6px 8px',
                                marginBottom: '6px',
                                borderLeft: '3px solid #667eea',
                                background: '#f3f4f6',
                                borderRadius: '4px',
                                fontSize: '11px'
                              }}>
                                <div style={{ fontWeight: '600', color: '#667eea', marginBottom: '2px' }}>
                                  {msg.replyTo.userName}
                                </div>
                                <div style={{ color: '#6b7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {msg.replyTo.preview}
                                </div>
                              </div>
                            )}
                            
                            <div style={{
                              fontSize: '12px',
                              color: '#374151',
                              lineHeight: '1.5',
                              wordWrap: 'break-word'
                            }}>
                              {msg.text}
                            </div>
                            
                            {/* File attachment */}
                            {msg.attachment && (
                              <div style={{
                                marginTop: '6px'
                              }}>
                                {msg.attachment.type?.startsWith('image/') ? (
                                  // Image preview
                                  <div style={{
                                    maxWidth: '300px',
                                    borderRadius: '8px',
                                    overflow: 'hidden',
                                    border: '1px solid #e5e7eb'
                                  }}>
                                    <img 
                                      src={`${API_BASE_URL}${msg.attachment.url}`}
                                      alt={msg.attachment.name || msg.attachment.filename}
                                      style={{
                                        width: '100%',
                                        display: 'block',
                                        cursor: 'pointer'
                                      }}
                                      onClick={() => window.open(`${API_BASE_URL}${msg.attachment.url}`, '_blank')}
                                    />
                                    <div style={{
                                      padding: '6px 8px',
                                      background: '#f9fafb',
                                      fontSize: '10px',
                                      color: '#6b7280',
                                      display: 'flex',
                                      justifyContent: 'space-between',
                                      alignItems: 'center'
                                    }}>
                                      <span>{msg.attachment.name || msg.attachment.filename}</span>
                                      <a
                                        href={`${API_BASE_URL}${msg.attachment.url}`}
                                        download={msg.attachment.name || msg.attachment.filename}
                                        style={{ color: '#667eea', textDecoration: 'none' }}
                                      >
                                        <Download size={12} />
                                      </a>
                                    </div>
                                  </div>
                                ) : (
                                  // File card
                                  <div style={{
                                    padding: '8px',
                                    background: '#f9fafb',
                                    borderRadius: '6px',
                                    border: '1px solid #e5e7eb',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    fontSize: '11px'
                                  }}>
                                    <FileText size={16} style={{ color: '#6b7280' }} />
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                      <div style={{
                                        fontWeight: '500',
                                        color: '#1f2937',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap'
                                      }}>
                                        {msg.attachment.name || msg.attachment.filename}
                                      </div>
                                      <div style={{ fontSize: '10px', color: '#6b7280' }}>
                                        {(msg.attachment.size / 1024).toFixed(1)} KB
                                      </div>
                                    </div>
                                    <a
                                      href={`${API_BASE_URL}${msg.attachment.url}`}
                                      download={msg.attachment.name || msg.attachment.filename}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      style={{
                                        padding: '4px',
                                        borderRadius: '4px',
                                        background: '#667eea',
                                        color: 'white',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                      }}
                                    >
                                      <Download size={12} />
                                    </a>
                                  </div>
                                )}
                              </div>
                            )}
                            
                            {/* Reactions */}
                            {msg.reactions && Object.keys(msg.reactions).length > 0 && (
                              <div style={{
                                display: 'flex',
                                gap: '4px',
                                marginTop: '6px',
                                flexWrap: 'wrap'
                              }}>
                                {Object.entries(msg.reactions).map(([emoji, userIds]) => (
                                  <button
                                    key={emoji}
                                    onClick={() => handleAddReaction(msg.id, emoji)}
                                    style={{
                                      padding: '2px 6px',
                                      background: userIds?.includes(getCurrentUserId()) ? '#e0e7ff' : '#f3f4f6',
                                      border: '1px solid ' + (userIds?.includes(getCurrentUserId()) ? '#667eea' : '#e5e7eb'),
                                      borderRadius: '12px',
                                      fontSize: '11px',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '3px'
                                    }}
                                  >
                                    <span>{emoji}</span>
                                    <span style={{ fontSize: '10px', color: '#6b7280' }}>
                                      {userIds?.length || 0}
                                    </span>
                                  </button>
                                ))}
                              </div>
                            )}
                            
                            {/* Message actions */}
                            <div style={{
                              position: 'absolute',
                              top: 0,
                              right: 0,
                              display: 'flex',
                              gap: '2px',
                              opacity: 0,
                              transition: 'opacity 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                            onMouseLeave={(e) => e.currentTarget.style.opacity = '0'}
                            >
                              <button
                                onClick={() => setShowEmojiPicker(showEmojiPicker === msg.id ? null : msg.id)}
                                style={{
                                  padding: '4px',
                                  background: 'white',
                                  border: '1px solid #e5e7eb',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center'
                                }}
                                title="Add reaction"
                              >
                                <Smile size={12} />
                              </button>
                              <button
                                onClick={() => setReplyingTo(msg)}
                                style={{
                                  padding: '4px',
                                  background: 'white',
                                  border: '1px solid #e5e7eb',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center'
                                }}
                                title="Reply"
                              >
                                <Reply size={12} />
                              </button>
                              {msg.userId === getCurrentUserId() && (
                                <>
                                  <button
                                    onClick={() => startEditing(msg)}
                                    style={{
                                      padding: '4px',
                                      background: 'white',
                                      border: '1px solid #e5e7eb',
                                      borderRadius: '4px',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center'
                                    }}
                                    title="Edit"
                                  >
                                    <Edit2 size={12} />
                                  </button>
                                  <button
                                    onClick={() => handleDeleteMessage(msg.id)}
                                    style={{
                                      padding: '4px',
                                      background: 'white',
                                      border: '1px solid #e5e7eb',
                                      borderRadius: '4px',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      color: '#ef4444'
                                    }}
                                    title="Delete"
                                  >
                                    <Trash2 size={12} />
                                  </button>
                                </>
                              )}
                            </div>
                            
                            {/* Emoji picker */}
                            {showEmojiPicker === msg.id && (
                              <div
                                ref={emojiPickerRef}
                                style={{
                                  position: 'absolute',
                                  top: '100%',
                                  right: 0,
                                  marginTop: '4px',
                                  background: 'white',
                                  border: '1px solid #e5e7eb',
                                  borderRadius: '8px',
                                  padding: '8px',
                                  display: 'grid',
                                  gridTemplateColumns: 'repeat(4, 1fr)',
                                  gap: '4px',
                                  boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)',
                                  zIndex: 10
                                }}
                              >
                                {commonEmojis.map((emoji, idx) => (
                                  <button
                                    key={idx}
                                    onClick={() => handleAddReaction(msg.id, emoji)}
                                    style={{
                                      padding: '6px',
                                      background: 'transparent',
                                      border: 'none',
                                      borderRadius: '4px',
                                      fontSize: '18px',
                                      cursor: 'pointer',
                                      transition: 'background 0.2s'
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.background = '#f3f4f6'}
                                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                  >
                                    {emoji}
                                  </button>
                                ))}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  ))
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Message Input - COMPACT */}
              <div style={{
                padding: '10px',
                borderTop: '1px solid #e5e7eb',
                background: '#fafafa'
              }}>
                {/* Reply indicator */}
                {replyingTo && (
                  <div style={{
                    padding: '6px 8px',
                    background: '#f3f4f6',
                    borderRadius: '6px',
                    marginBottom: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '11px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flex: 1, minWidth: 0 }}>
                      <Reply size={12} style={{ color: '#6b7280', flexShrink: 0 }} />
                      <span style={{ color: '#6b7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        Replying to {replyingTo.user}: {replyingTo.text.substring(0, 30)}...
                      </span>
                    </div>
                    <button
                      onClick={() => setReplyingTo(null)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#6b7280',
                        padding: '2px',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                )}
                
                {/* File preview */}
                {selectedFile && (
                  <div style={{
                    padding: '6px 8px',
                    background: '#f3f4f6',
                    borderRadius: '6px',
                    marginBottom: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '11px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1, minWidth: 0 }}>
                      <Paperclip size={12} style={{ color: '#6b7280', flexShrink: 0 }} />
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {selectedFile.name}
                      </span>
                    </div>
                    <button
                      onClick={() => setSelectedFile(null)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#6b7280',
                        padding: '2px',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                )}
                
                {/* Upload progress */}
                {uploadProgress > 0 && uploadProgress < 100 && (
                  <div style={{
                    height: '3px',
                    background: '#e5e7eb',
                    borderRadius: '3px',
                    overflow: 'hidden',
                    marginBottom: '6px'
                  }}>
                    <div style={{
                      height: '100%',
                      background: '#667eea',
                      width: `${uploadProgress}%`,
                      transition: 'width 0.3s'
                    }} />
                  </div>
                )}
                
                <div style={{
                  display: 'flex',
                  alignItems: 'flex-end',
                  gap: '6px',
                  background: '#ffffff',
                  borderRadius: '6px',
                  padding: '6px',
                  border: '1px solid #e5e7eb'
                }}>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    style={{ display: 'none' }}
                    accept="image/*,.pdf,.doc,.docx,.txt"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={sending}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      cursor: sending ? 'not-allowed' : 'pointer',
                      color: '#6b7280',
                      padding: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      borderRadius: '4px',
                      transition: 'background 0.2s'
                    }}
                    title="Attach file"
                    onMouseEnter={(e) => !sending && (e.currentTarget.style.background = '#f3f4f6')}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <Paperclip size={16} />
                  </button>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={`Message #${currentChannelData?.name || 'channel'}`}
                    rows="1"
                    disabled={sending}
                    style={{
                      flex: 1,
                      border: 'none',
                      background: 'transparent',
                      resize: 'none',
                      fontSize: '12px',
                      color: '#1f2937',
                      fontFamily: 'inherit',
                      padding: '2px 0',
                      maxHeight: '60px',
                      overflowY: 'auto'
                    }}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={(!message.trim() && !selectedFile) || sending}
                    style={{
                      background: (message.trim() || selectedFile) && !sending ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#e5e7eb',
                      border: 'none',
                      borderRadius: '5px',
                      width: '28px',
                      height: '28px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: (message.trim() || selectedFile) && !sending ? 'pointer' : 'not-allowed',
                      color: 'white',
                      flexShrink: 0,
                      transition: 'all 0.2s'
                    }}
                  >
                    {sending ? <RefreshCw size={14} className="animate-spin" /> : <Send size={14} />}
                  </button>
                </div>
                <div style={{
                  fontSize: '9px',
                  color: '#9ca3af',
                  marginTop: '4px',
                  textAlign: 'center'
                }}>
                  Press Enter to send • Attach files up to 10MB
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CSS for animations */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        textarea:focus {
          outline: none;
        }
        .team-chat-btn:hover {
          transform: scale(1.1);
          box-shadow: 0 6px 24px rgba(102, 126, 234, 0.5);
        }
      `}</style>
    </>
  );
}