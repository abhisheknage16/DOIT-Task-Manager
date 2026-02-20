// // import React, { useState, useEffect, useRef, useContext } from 'react';
// // import { 
// //   Plus, Trash2, Send, Image, Paperclip, Bot, User, 
// //   AlertCircle, CheckCircle2, Info, AlertTriangle,
// //   Clock, TrendingUp, Users, Target
// // } from 'lucide-react';
// // import { AuthContext } from '../../context/AuthContext';
// // import './AIAssistantPage.css';

// // const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// // // Get or generate tab session key for security
// // const getTabSessionKey = () => {
// //   let key = sessionStorage.getItem("tab_session_key");
// //   if (!key) {
// //     key = 'tab_' + Math.random().toString(36).substr(2, 12) + '_' + Date.now().toString(36);
// //     sessionStorage.setItem("tab_session_key", key);
// //   }
// //   return key;
// // };

// // // Get auth headers with tab session key
// // const getAuthHeaders = () => {
// //   const token = localStorage.getItem('token');
// //   return {
// //     'Authorization': `Bearer ${token}`,
// //     'X-Tab-Session-Key': getTabSessionKey(),
// //     'Content-Type': 'application/json'
// //   };
// // };

// // // Message formatter component for rich text rendering with command results
// // const FormattedMessage = ({ content, insights, userDataSummary, commandResult }) => {
// //   // Parse markdown-like formatting
// //   const formatText = (text) => {
// //     if (!text) return null;

// //     // Split by code blocks first
// //     const parts = text.split(/(```[\s\S]*?```|`[^`]+`)/g);
    
// //     return parts.map((part, index) => {
// //       // Code block
// //       if (part.startsWith('```')) {
// //         const code = part.replace(/```(\w*)\n?/g, '').replace(/```$/g, '');
// //         return (
// //           <pre key={index}>
// //             <code>{code}</code>
// //           </pre>
// //         );
// //       }
      
// //       // Inline code
// //       if (part.startsWith('`') && part.endsWith('`')) {
// //         return <code key={index}>{part.slice(1, -1)}</code>;
// //       }

// //       // Regular text with formatting
// //       let formatted = part;
      
// //       // Bold
// //       formatted = formatted.split(/(\*\*[^*]+\*\*)/g).map((segment, i) => {
// //         if (segment.startsWith('**') && segment.endsWith('**')) {
// //           return <strong key={`bold-${i}`}>{segment.slice(2, -2)}</strong>;
// //         }
// //         return segment;
// //       });

// //       return <span key={index}>{formatted}</span>;
// //     });
// //   };

// //   // Parse lists and structure
// //   const parseContent = (text) => {
// //     const lines = text.split('\n');
// //     const elements = [];
// //     let currentList = [];
// //     let listType = null;

// //     lines.forEach((line, index) => {
// //       // Headers
// //       if (line.startsWith('## ')) {
// //         if (currentList.length > 0) {
// //           elements.push(
// //             listType === 'ul' ? (
// //               <ul key={`list-${index}`}>{currentList}</ul>
// //             ) : (
// //               <ol key={`list-${index}`}>{currentList}</ol>
// //             )
// //           );
// //           currentList = [];
// //           listType = null;
// //         }
// //         elements.push(<h2 key={index}>{formatText(line.replace('## ', ''))}</h2>);
// //       } 
// //       else if (line.startsWith('### ')) {
// //         if (currentList.length > 0) {
// //           elements.push(
// //             listType === 'ul' ? (
// //               <ul key={`list-${index}`}>{currentList}</ul>
// //             ) : (
// //               <ol key={`list-${index}`}>{currentList}</ol>
// //             )
// //           );
// //           currentList = [];
// //           listType = null;
// //         }
// //         elements.push(<h3 key={index}>{formatText(line.replace('### ', ''))}</h3>);
// //       }
// //       // Bullet points
// //       else if (line.match(/^[-*]\s/)) {
// //         if (listType !== 'ul' && currentList.length > 0) {
// //           elements.push(<ol key={`list-${index}`}>{currentList}</ol>);
// //           currentList = [];
// //         }
// //         listType = 'ul';
// //         currentList.push(<li key={index}>{formatText(line.replace(/^[-*]\s/, ''))}</li>);
// //       }
// //       // Numbered lists
// //       else if (line.match(/^\d+\.\s/)) {
// //         if (listType !== 'ol' && currentList.length > 0) {
// //           elements.push(<ul key={`list-${index}`}>{currentList}</ul>);
// //           currentList = [];
// //         }
// //         listType = 'ol';
// //         currentList.push(<li key={index}>{formatText(line.replace(/^\d+\.\s/, ''))}</li>);
// //       }
// //       // Horizontal rule
// //       else if (line.trim() === '---') {
// //         if (currentList.length > 0) {
// //           elements.push(
// //             listType === 'ul' ? (
// //               <ul key={`list-${index}`}>{currentList}</ul>
// //             ) : (
// //               <ol key={`list-${index}`}>{currentList}</ol>
// //             )
// //           );
// //           currentList = [];
// //           listType = null;
// //         }
// //         elements.push(<hr key={index} />);
// //       }
// //       // Regular paragraph
// //       else if (line.trim()) {
// //         if (currentList.length > 0) {
// //           elements.push(
// //             listType === 'ul' ? (
// //               <ul key={`list-${index}`}>{currentList}</ul>
// //             ) : (
// //               <ol key={`list-${index}`}>{currentList}</ol>
// //             )
// //           );
// //           currentList = [];
// //           listType = null;
// //         }
// //         elements.push(<p key={index}>{formatText(line)}</p>);
// //       }
// //     });

// //     // Add remaining list items
// //     if (currentList.length > 0) {
// //       elements.push(
// //         listType === 'ul' ? (
// //           <ul key="final-list">{currentList}</ul>
// //         ) : (
// //           <ol key="final-list">{currentList}</ol>
// //         )
// //       );
// //     }

// //     return elements;
// //   };

// //   return (
// //     <div>
// //       {/* Command Execution Result - Show at top */}
// //       {commandResult && (
// //         <div className="ai-command-result">
// //           <div className={`ai-command-badge ${commandResult.success ? 'success' : 'error'}`}>
// //             {commandResult.success ? (
// //               <>
// //                 <CheckCircle2 size={14} />
// //                 Command Executed
// //               </>
// //             ) : (
// //               <>
// //                 <AlertCircle size={14} />
// //                 Command Failed
// //               </>
// //             )}
// //           </div>
          
// //           {/* Show Tasks if present */}
// //           {commandResult.tasks && commandResult.tasks.length > 0 && (
// //             <div className="ai-command-tasks">
// //               <h4>
// //                 <Target size={16} />
// //                 Tasks ({commandResult.count})
// //               </h4>
// //               <ul>
// //                 {commandResult.tasks.map((task, idx) => (
// //                   <li key={idx}>
// //                     <span className="task-ticket">[{task.ticket_id}]</span>
// //                     <span className="task-title">{task.title}</span>
// //                     <span className="task-status">{task.status}</span>
// //                     <span className={`task-priority priority-${task.priority.toLowerCase()}`}>
// //                       {task.priority}
// //                     </span>
// //                     {task.assignee && task.assignee !== 'Unassigned' && (
// //                       <span className="task-assignee">
// //                         <User size={12} />
// //                         {task.assignee}
// //                       </span>
// //                     )}
// //                   </li>
// //                 ))}
// //               </ul>
// //             </div>
// //           )}

// //           {/* Show Projects if present */}
// //           {commandResult.projects && commandResult.projects.length > 0 && (
// //             <div className="ai-command-projects">
// //               <h4>
// //                 <Target size={16} />
// //                 Projects ({commandResult.count})
// //               </h4>
// //               <ul>
// //                 {commandResult.projects.map((project, idx) => (
// //                   <li key={idx}>
// //                     <span className="project-name">{project.name}</span>
// //                     <span className="project-role">{project.role}</span>
// //                     {project.description && (
// //                       <span className="project-description">{project.description}</span>
// //                     )}
// //                   </li>
// //                 ))}
// //               </ul>
// //             </div>
// //           )}

// //           {/* Show detailed result if present */}
// //           {commandResult.result && (
// //             <div className="ai-command-details">
// //               <details>
// //                 <summary>View Full Result</summary>
// //                 <pre>
// //                   <code>{JSON.stringify(commandResult.result, null, 2)}</code>
// //                 </pre>
// //               </details>
// //             </div>
// //           )}
// //         </div>
// //       )}

// //       {/* User Data Summary Cards */}
// //       {userDataSummary && (
// //         <div className="ai-data-summary">
// //           <div className="ai-data-card">
// //             <div className="ai-data-value">{userDataSummary.tasks_total}</div>
// //             <div className="ai-data-label">Total Tasks</div>
// //           </div>
// //           <div className="ai-data-card">
// //             <div className="ai-data-value" style={{ color: userDataSummary.tasks_overdue > 0 ? '#f44336' : '#4caf50' }}>
// //               {userDataSummary.tasks_overdue}
// //             </div>
// //             <div className="ai-data-label">Overdue</div>
// //           </div>
// //           <div className="ai-data-card">
// //             <div className="ai-data-value">{userDataSummary.projects_total}</div>
// //             <div className="ai-data-label">Projects</div>
// //           </div>
// //           <div className="ai-data-card">
// //             <div className="ai-data-value">{userDataSummary.velocity}</div>
// //             <div className="ai-data-label">Tasks/Week</div>
// //           </div>
// //         </div>
// //       )}

// //       {/* Insights Cards */}
// //       {insights && insights.length > 0 && (
// //         <div className="ai-insights-container">
// //           {insights.slice(0, 3).map((insight, idx) => (
// //             <div key={idx} className={`ai-insight-card ${insight.type}`}>
// //               <div className="ai-insight-icon">
// //                 {insight.type === 'warning' && <AlertTriangle size={16} />}
// //                 {insight.type === 'success' && <CheckCircle2 size={16} />}
// //                 {insight.type === 'info' && <Info size={16} />}
// //                 {insight.type === 'critical' && <AlertCircle size={16} />}
// //               </div>
// //               <div className="ai-insight-content">
// //                 <div className="ai-insight-title">{insight.title}</div>
// //                 <div className="ai-insight-description">{insight.description}</div>
// //               </div>
// //             </div>
// //           ))}
// //         </div>
// //       )}

// //       {/* Main content */}
// //       <div>{parseContent(content)}</div>
// //     </div>
// //   );
// // };

// // const AIAssistantPage = () => {
// //   const { user } = useContext(AuthContext);
// //   const [conversations, setConversations] = useState([]);
// //   const [activeConversation, setActiveConversation] = useState(null);
// //   const [messages, setMessages] = useState([]);
// //   const [inputText, setInputText] = useState('');
// //   const [isLoading, setIsLoading] = useState(false);
// //   const [isTyping, setIsTyping] = useState(false);
// //   const [uploadedFile, setUploadedFile] = useState(null);
// //   const messagesEndRef = useRef(null);
// //   const textareaRef = useRef(null);
// //   const fileInputRef = useRef(null);

// //   // Load conversations on mount
// //   useEffect(() => {
// //     loadConversations();
// //   }, []);

// //   // Load messages when conversation changes
// //   useEffect(() => {
// //     if (activeConversation) {
// //       setMessages([]);
// //       loadMessages(activeConversation._id);
// //     } else {
// //       setMessages([]);
// //     }
// //   }, [activeConversation?._id]);

// //   // Auto-scroll to bottom when new messages arrive
// //   useEffect(() => {
// //     scrollToBottom();
// //   }, [messages, isTyping]);

// //   const scrollToBottom = () => {
// //     messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
// //   };

// //   const loadConversations = async () => {
// //     try {
// //       const response = await fetch(`${API_BASE}/api/ai-assistant/conversations`, {
// //         headers: getAuthHeaders()
// //       });
// //       const data = await response.json();
// //       if (data.success) {
// //         setConversations(data.conversations);
// //       }
// //     } catch (error) {
// //       console.error('Error loading conversations:', error);
// //     }
// //   };

// //   const loadMessages = async (conversationId) => {
// //     try {
// //       const response = await fetch(
// //         `${API_BASE}/api/ai-assistant/conversations/${conversationId}/messages`,
// //         {
// //           headers: getAuthHeaders()
// //         }
// //       );
// //       const data = await response.json();
// //       if (data.success) {
// //         setMessages(data.messages);
// //       }
// //     } catch (error) {
// //       console.error('Error loading messages:', error);
// //     }
// //   };

// //   const createNewConversation = async () => {
// //     try {
// //       const response = await fetch(`${API_BASE}/api/ai-assistant/conversations`, {
// //         method: 'POST',
// //         headers: getAuthHeaders(),
// //         body: JSON.stringify({ title: 'New Conversation' })
// //       });
// //       const data = await response.json();
// //       if (data.success) {
// //         setConversations([data.conversation, ...conversations]);
// //         setActiveConversation(data.conversation);
// //         setMessages([]);
// //         return data.conversation;
// //       }
// //     } catch (error) {
// //       console.error('Error creating conversation:', error);
// //       return null;
// //     }
// //   };

// //   const sendMessage = async () => {
// //     if (!inputText.trim() || isLoading) return;

// //     const messageContent = inputText;
// //     let conversationToUse = activeConversation;

// //     if (!conversationToUse) {
// //       conversationToUse = await createNewConversation();
// //       if (!conversationToUse) {
// //         console.error('Failed to create conversation');
// //         return;
// //       }
// //     }

// //     const userMessage = {
// //       role: 'user',
// //       content: messageContent,
// //       created_at: new Date().toISOString()
// //     };

// //     setMessages(prev => [...prev, userMessage]);
// //     setInputText('');
// //     setIsLoading(true);
// //     setIsTyping(true);

// //     try {
// //       const response = await fetch(
// //         `${API_BASE}/api/ai-assistant/conversations/${conversationToUse._id}/messages`,
// //         {
// //           method: 'POST',
// //           headers: getAuthHeaders(),
// //           body: JSON.stringify({
// //             content: messageContent,
// //             stream: false,
// //             include_user_context: true
// //           })
// //         }
// //       );

// //       const data = await response.json();
// //       setIsTyping(false);

// //       if (data.success && data.message) {
// //         // Add AI response with all metadata including command results
// //         setMessages(prev => [...prev, {
// //           ...data.message,
// //           insights: data.insights,
// //           user_data_summary: data.user_data_summary,
// //           command_result: data.command_result // NEW: Include command results
// //         }]);
        
// //         // Show success notification for commands
// //         if (data.command_executed && data.command_result?.success) {
// //           console.log('✅ Command executed successfully:', data.command_result);
// //         }
        
// //         loadConversations();
// //       } else {
// //         console.error('No AI response received:', data);
// //       }
// //     } catch (error) {
// //       console.error('Error sending message:', error);
// //       setIsTyping(false);
      
// //       // Add error message
// //       const errorMessage = {
// //         role: 'assistant',
// //         content: '❌ Sorry, I encountered an error processing your request. Please try again.',
// //         created_at: new Date().toISOString()
// //       };
// //       setMessages(prev => [...prev, errorMessage]);
// //     } finally {
// //       setIsLoading(false);
// //     }
// //   };

// //   const generateImage = async () => {
// //     if (!inputText.trim() || isLoading) return;

// //     const prompt = inputText;
// //     let conversationToUse = activeConversation;

// //     if (!conversationToUse) {
// //       conversationToUse = await createNewConversation();
// //       if (!conversationToUse) {
// //         console.error('Failed to create conversation');
// //         return;
// //       }
// //     }

// //     const userMessage = {
// //       role: 'user',
// //       content: `Generate image: ${prompt}`,
// //       created_at: new Date().toISOString()
// //     };

// //     setMessages(prev => [...prev, userMessage]);
// //     setInputText('');
// //     setIsLoading(true);
// //     setIsTyping(true);

// //     try {
// //       const response = await fetch(
// //         `${API_BASE}/api/ai-assistant/conversations/${conversationToUse._id}/generate-image`,
// //         {
// //           method: 'POST',
// //           headers: getAuthHeaders(),
// //           body: JSON.stringify({ prompt })
// //         }
// //       );

// //       const data = await response.json();
// //       setIsTyping(false);

// //       if (data.success) {
// //         setMessages(prev => [...prev, data.message]);
// //         loadConversations();
// //       }
// //     } catch (error) {
// //       console.error('Error generating image:', error);
// //       setIsTyping(false);
// //     } finally {
// //       setIsLoading(false);
// //     }
// //   };

// //   const handleFileUpload = async (e) => {
// //     const file = e.target.files[0];
// //     if (!file || isLoading) return;

// //     let conversationToUse = activeConversation;
// //     if (!conversationToUse) {
// //       conversationToUse = await createNewConversation();
// //       if (!conversationToUse) {
// //         console.error('Failed to create conversation');
// //         return;
// //       }
// //     }

// //     const userMessage = {
// //       role: 'user',
// //       content: `Uploaded file: ${file.name}`,
// //       created_at: new Date().toISOString()
// //     };

// //     setMessages(prev => [...prev, userMessage]);
// //     setIsLoading(true);
// //     setIsTyping(true);

// //     try {
// //       const formData = new FormData();
// //       formData.append('file', file);

// //       const response = await fetch(
// //         `${API_BASE}/api/ai-assistant/conversations/${conversationToUse._id}/upload`,
// //         {
// //           method: 'POST',
// //           headers: {
// //             'Authorization': `Bearer ${localStorage.getItem('token')}`,
// //             'X-Tab-Session-Key': getTabSessionKey()
// //           },
// //           body: formData
// //         }
// //       );

// //       const data = await response.json();
// //       setIsTyping(false);

// //       if (data.success) {
// //         if (data.ai_message_id) {
// //           const aiMessage = {
// //             role: 'assistant',
// //             content: data.message,
// //             created_at: new Date().toISOString()
// //           };
// //           setMessages(prev => [...prev, aiMessage]);
// //         }
        
// //         if (data.file?.extracted) {
// //           console.log('File content extracted successfully:', data.file.metadata);
// //         }
        
// //         setUploadedFile(file.name);
// //         loadConversations();
// //       } else {
// //         throw new Error(data.message || 'Upload failed');
// //       }
// //     } catch (error) {
// //       console.error('Error uploading file:', error);
// //       const errorMessage = {
// //         role: 'assistant',
// //         content: `Sorry, I couldn't upload the file. ${error.message}`,
// //         created_at: new Date().toISOString()
// //       };
// //       setMessages(prev => [...prev, errorMessage]);
// //       setIsTyping(false);
// //     } finally {
// //       setIsLoading(false);
// //       if (fileInputRef.current) {
// //         fileInputRef.current.value = '';
// //       }
// //     }
// //   };

// //   const deleteConversation = async (conversationId, e) => {
// //     e.stopPropagation();
    
// //     try {
// //       await fetch(`${API_BASE}/api/ai-assistant/conversations/${conversationId}`, {
// //         method: 'DELETE',
// //         headers: getAuthHeaders()
// //       });
      
// //       setConversations(prev => prev.filter(c => c._id !== conversationId));
// //       if (activeConversation?._id === conversationId) {
// //         setActiveConversation(null);
// //         setMessages([]);
// //       }
// //     } catch (error) {
// //       console.error('Error deleting conversation:', error);
// //     }
// //   };

// //   const handleKeyPress = (e) => {
// //     if (e.key === 'Enter' && !e.shiftKey) {
// //       e.preventDefault();
// //       sendMessage();
// //     }
// //   };

// //   const formatTimestamp = (timestamp) => {
// //     const date = new Date(timestamp);
// //     const now = new Date();
// //     const diff = now - date;
    
// //     if (diff < 60000) return 'Just now';
// //     if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
// //     if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
// //     return date.toLocaleDateString();
// //   };

// //   const suggestionPrompts = [
// //     "Show me my task overview and priorities",
// //     "Create a high priority task for login bug fix",
// //     "List all my overdue tasks",
// //     "What should I focus on today?"
// //   ];

// //   return (
// //     <div className="ai-assistant-page">
// //       {/* Sidebar - Conversations */}
// //       <div className="ai-sidebar">
// //         <div className="ai-sidebar-header">
// //           <button className="new-chat-btn" onClick={createNewConversation}>
// //             <Plus size={20} />
// //             New Chat
// //           </button>
// //         </div>
        
// //         <div className="conversations-list">
// //           {conversations.map(conv => (
// //             <div
// //               key={conv._id}
// //               className={`conversation-item ${activeConversation?._id === conv._id ? 'active' : ''}`}
// //               onClick={() => setActiveConversation(conv)}
// //             >
// //               <div className="conversation-title">{conv.title}</div>
// //               <div className="conversation-date">
// //                 {formatTimestamp(conv.updated_at)}
// //               </div>
// //               <button
// //                 className="conversation-delete"
// //                 onClick={(e) => deleteConversation(conv._id, e)}
// //               >
// //                 <Trash2 size={14} />
// //               </button>
// //             </div>
// //           ))}
// //         </div>
// //       </div>

// //       {/* Main Chat Area */}
// //       <div className="ai-chat-area">
// //         <div className="ai-chat-header">
// //           <div className="ai-chat-title">
// //             <Bot size={20} />
// //             DOIT AI Assistant
// //           </div>
// //           <div className="ai-status-badge">
// //             <div className="ai-status-dot"></div>
// //             Online
// //           </div>
// //         </div>

// //         <div className="ai-messages-container">
// //           {messages.length === 0 ? (
// //             <div className="ai-empty-state">
// //               <div className="ai-empty-icon">
// //                 <Bot size={56} color="#667eea" />
// //               </div>
// //               <div className="ai-empty-title">
// //                 Welcome to DOIT AI Assistant
// //               </div>
// //               <div className="ai-empty-subtitle">
// //                 Get personalized insights, task analytics, and intelligent recommendations 
// //                 based on your project data and team performance. I can also help you create, 
// //                 assign, and manage tasks automatically!
// //               </div>
// //               <div className="ai-suggestion-chips">
// //                 {suggestionPrompts.map((prompt, idx) => (
// //                   <div
// //                     key={idx}
// //                     className="ai-suggestion-chip"
// //                     onClick={() => setInputText(prompt)}
// //                   >
// //                     {prompt}
// //                   </div>
// //                 ))}
// //               </div>
// //             </div>
// //           ) : (
// //             <>
// //               {messages.map((msg, idx) => (
// //                 <div key={idx} className={`ai-message ${msg.role}`}>
// //                   <div className="ai-message-avatar">
// //                     {msg.role === 'user' ? (
// //                       <User size={20} />
// //                     ) : (
// //                       <Bot size={20} />
// //                     )}
// //                   </div>
// //                   <div className="ai-message-content">
// //                     <div className="ai-message-bubble">
// //                       <FormattedMessage 
// //                         content={msg.content}
// //                         insights={msg.insights}
// //                         userDataSummary={msg.user_data_summary}
// //                         commandResult={msg.command_result}
// //                       />
// //                     </div>
// //                     {msg.image_url && (
// //                       <div className="ai-message-image">
// //                         <img src={`${API_BASE}${msg.image_url}`} alt="Generated" />
// //                       </div>
// //                     )}
// //                     <div className="ai-message-timestamp">
// //                       <Clock size={11} />
// //                       {formatTimestamp(msg.created_at)}
// //                     </div>
// //                   </div>
// //                 </div>
// //               ))}
              
// //               {isTyping && (
// //                 <div className="ai-message assistant">
// //                   <div className="ai-message-avatar">
// //                     <Bot size={20} />
// //                   </div>
// //                   <div className="ai-message-content">
// //                     <div className="ai-message-bubble">
// //                       <div className="ai-loading-dots">
// //                         <div className="ai-loading-dot"></div>
// //                         <div className="ai-loading-dot"></div>
// //                         <div className="ai-loading-dot"></div>
// //                       </div>
// //                     </div>
// //                   </div>
// //                 </div>
// //               )}
              
// //               <div ref={messagesEndRef} />
// //             </>
// //           )}
// //         </div>

// //         <div className="ai-input-area">
// //           <div className="ai-input-actions">
// //             <button 
// //               className="ai-action-btn" 
// //               onClick={generateImage} 
// //               disabled={isLoading || !inputText.trim()}
// //               title="Generate an image from your text description"
// //             >
// //               <Image size={16} /> Generate Image
// //             </button>
// //             <button 
// //               className="ai-action-btn" 
// //               onClick={() => fileInputRef.current?.click()} 
// //               disabled={isLoading}
// //               title="Upload a file to analyze"
// //             >
// //               <Paperclip size={16} /> Upload File
// //             </button>
// //             <input
// //               ref={fileInputRef}
// //               type="file"
// //               style={{ display: 'none' }}
// //               onChange={handleFileUpload}
// //               accept=".txt,.pdf,.doc,.docx,.png,.jpg,.jpeg,.csv,.json"
// //             />
// //           </div>
          
// //           <div className="ai-input-container">
// //             <div className="ai-textarea-wrapper">
// //               <textarea
// //                 ref={textareaRef}
// //                 className="ai-textarea"
// //                 placeholder={uploadedFile ? `Ask about "${uploadedFile}"...` : "Ask me anything or give me commands like 'Create a task for...' or 'Show my tasks'"}
// //                 value={inputText}
// //                 onChange={(e) => setInputText(e.target.value)}
// //                 onKeyPress={handleKeyPress}
// //                 disabled={isLoading}
// //                 rows={1}
// //               />
// //             </div>
// //             <button
// //               className="ai-send-btn"
// //               onClick={sendMessage}
// //               disabled={isLoading || !inputText.trim()}
// //             >
// //               <Send size={18} />
// //             </button>
// //           </div>
// //         </div>
// //       </div>
// //     </div>
// //   );
// // };

// // export default AIAssistantPage;
// import React, { useState, useEffect, useRef, useContext, useCallback } from 'react';
// import { 
//   Plus, Trash2, Send, Image, Paperclip, Bot, User, 
//   AlertCircle, CheckCircle2, Info, AlertTriangle,
//   Clock, TrendingUp, Users, Target, Zap
// } from 'lucide-react';
// import { AuthContext } from '../../context/AuthContext';
// import { foundryAgentAPI } from '../../services/foundryAgentAPI';
// import './AIAssistantPage.css';

// const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// // Get or generate tab session key for security
// const getTabSessionKey = () => {
//   let key = sessionStorage.getItem("tab_session_key");
//   if (!key) {
//     key = 'tab_' + Math.random().toString(36).substr(2, 12) + '_' + Date.now().toString(36);
//     sessionStorage.setItem("tab_session_key", key);
//   }
//   return key;
// };

// // Get auth headers with tab session key
// const getAuthHeaders = () => {
//   const token = localStorage.getItem('token');
//   return {
//     'Authorization': `Bearer ${token}`,
//     'X-Tab-Session-Key': getTabSessionKey(),
//     'Content-Type': 'application/json'
//   };
// };

// // ─────────────────────────────────────────────────────────────────────────────
// // Message formatter — unchanged from original
// // ─────────────────────────────────────────────────────────────────────────────
// const FormattedMessage = ({ content, insights, userDataSummary, commandResult }) => {
//   const formatText = (text) => {
//     if (!text) return null;
//     const parts = text.split(/(```[\s\S]*?```|`[^`]+`)/g);
//     return parts.map((part, index) => {
//       if (part.startsWith('```')) {
//         const code = part.replace(/```(\w*)\n?/g, '').replace(/```$/g, '');
//         return <pre key={index}><code>{code}</code></pre>;
//       }
//       if (part.startsWith('`') && part.endsWith('`')) {
//         return <code key={index}>{part.slice(1, -1)}</code>;
//       }
//       let formatted = part;
//       formatted = formatted.split(/(\*\*[^*]+\*\*)/g).map((segment, i) => {
//         if (segment.startsWith('**') && segment.endsWith('**')) {
//           return <strong key={`bold-${i}`}>{segment.slice(2, -2)}</strong>;
//         }
//         return segment;
//       });
//       return <span key={index}>{formatted}</span>;
//     });
//   };

//   const parseContent = (text) => {
//     const lines = text.split('\n');
//     const elements = [];
//     let currentList = [];
//     let listType = null;

//     lines.forEach((line, index) => {
//       if (line.startsWith('## ')) {
//         if (currentList.length > 0) {
//           elements.push(listType === 'ul' ? <ul key={`list-${index}`}>{currentList}</ul> : <ol key={`list-${index}`}>{currentList}</ol>);
//           currentList = []; listType = null;
//         }
//         elements.push(<h2 key={index}>{formatText(line.replace('## ', ''))}</h2>);
//       } else if (line.startsWith('### ')) {
//         if (currentList.length > 0) {
//           elements.push(listType === 'ul' ? <ul key={`list-${index}`}>{currentList}</ul> : <ol key={`list-${index}`}>{currentList}</ol>);
//           currentList = []; listType = null;
//         }
//         elements.push(<h3 key={index}>{formatText(line.replace('### ', ''))}</h3>);
//       } else if (line.match(/^[-*]\s/)) {
//         if (listType !== 'ul' && currentList.length > 0) { elements.push(<ol key={`list-${index}`}>{currentList}</ol>); currentList = []; }
//         listType = 'ul';
//         currentList.push(<li key={index}>{formatText(line.replace(/^[-*]\s/, ''))}</li>);
//       } else if (line.match(/^\d+\.\s/)) {
//         if (listType !== 'ol' && currentList.length > 0) { elements.push(<ul key={`list-${index}`}>{currentList}</ul>); currentList = []; }
//         listType = 'ol';
//         currentList.push(<li key={index}>{formatText(line.replace(/^\d+\.\s/, ''))}</li>);
//       } else if (line.trim() === '---') {
//         if (currentList.length > 0) {
//           elements.push(listType === 'ul' ? <ul key={`list-${index}`}>{currentList}</ul> : <ol key={`list-${index}`}>{currentList}</ol>);
//           currentList = []; listType = null;
//         }
//         elements.push(<hr key={index} />);
//       } else if (line.trim()) {
//         if (currentList.length > 0) {
//           elements.push(listType === 'ul' ? <ul key={`list-${index}`}>{currentList}</ul> : <ol key={`list-${index}`}>{currentList}</ol>);
//           currentList = []; listType = null;
//         }
//         elements.push(<p key={index}>{formatText(line)}</p>);
//       }
//     });

//     if (currentList.length > 0) {
//       elements.push(listType === 'ul' ? <ul key="final-list">{currentList}</ul> : <ol key="final-list">{currentList}</ol>);
//     }
//     return elements;
//   };

//   return (
//     <div>
//       {commandResult && (
//         <div className="ai-command-result">
//           <div className={`ai-command-badge ${commandResult.success ? 'success' : 'error'}`}>
//             {commandResult.success ? (<><CheckCircle2 size={14} />Command Executed</>) : (<><AlertCircle size={14} />Command Failed</>)}
//           </div>
//           {commandResult.tasks && commandResult.tasks.length > 0 && (
//             <div className="ai-command-tasks">
//               <h4><Target size={16} />Tasks ({commandResult.count})</h4>
//               <ul>
//                 {commandResult.tasks.map((task, idx) => (
//                   <li key={idx}>
//                     <span className="task-ticket">[{task.ticket_id}]</span>
//                     <span className="task-title">{task.title}</span>
//                     <span className="task-status">{task.status}</span>
//                     <span className={`task-priority priority-${task.priority.toLowerCase()}`}>{task.priority}</span>
//                     {task.assignee && task.assignee !== 'Unassigned' && (
//                       <span className="task-assignee"><User size={12} />{task.assignee}</span>
//                     )}
//                   </li>
//                 ))}
//               </ul>
//             </div>
//           )}
//           {commandResult.projects && commandResult.projects.length > 0 && (
//             <div className="ai-command-projects">
//               <h4><Target size={16} />Projects ({commandResult.count})</h4>
//               <ul>
//                 {commandResult.projects.map((project, idx) => (
//                   <li key={idx}>
//                     <span className="project-name">{project.name}</span>
//                     <span className="project-role">{project.role}</span>
//                     {project.description && <span className="project-description">{project.description}</span>}
//                   </li>
//                 ))}
//               </ul>
//             </div>
//           )}
//           {commandResult.result && (
//             <div className="ai-command-details">
//               <details>
//                 <summary>View Full Result</summary>
//                 <pre><code>{JSON.stringify(commandResult.result, null, 2)}</code></pre>
//               </details>
//             </div>
//           )}
//         </div>
//       )}

//       {userDataSummary && (
//         <div className="ai-data-summary">
//           <div className="ai-data-card">
//             <div className="ai-data-value">{userDataSummary.tasks_total}</div>
//             <div className="ai-data-label">Total Tasks</div>
//           </div>
//           <div className="ai-data-card">
//             <div className="ai-data-value" style={{ color: userDataSummary.tasks_overdue > 0 ? '#f44336' : '#4caf50' }}>
//               {userDataSummary.tasks_overdue}
//             </div>
//             <div className="ai-data-label">Overdue</div>
//           </div>
//           <div className="ai-data-card">
//             <div className="ai-data-value">{userDataSummary.projects_total}</div>
//             <div className="ai-data-label">Projects</div>
//           </div>
//           <div className="ai-data-card">
//             <div className="ai-data-value">{userDataSummary.velocity}</div>
//             <div className="ai-data-label">Tasks/Week</div>
//           </div>
//         </div>
//       )}

//       {insights && insights.length > 0 && (
//         <div className="ai-insights-container">
//           {insights.slice(0, 3).map((insight, idx) => (
//             <div key={idx} className={`ai-insight-card ${insight.type}`}>
//               <div className="ai-insight-icon">
//                 {insight.type === 'warning' && <AlertTriangle size={16} />}
//                 {insight.type === 'success' && <CheckCircle2 size={16} />}
//                 {insight.type === 'info' && <Info size={16} />}
//                 {insight.type === 'critical' && <AlertCircle size={16} />}
//               </div>
//               <div className="ai-insight-content">
//                 <div className="ai-insight-title">{insight.title}</div>
//                 <div className="ai-insight-description">{insight.description}</div>
//               </div>
//             </div>
//           ))}
//         </div>
//       )}

//       <div>{parseContent(content)}</div>
//     </div>
//   );
// };

// // ─────────────────────────────────────────────────────────────────────────────
// // Foundry message renderer — simple markdown, no command cards needed
// // ─────────────────────────────────────────────────────────────────────────────
// const FoundryMessage = ({ content }) => {
//   const formatText = (text) => {
//     if (!text) return null;
//     const parts = text.split(/(```[\s\S]*?```|`[^`]+`)/g);
//     return parts.map((part, index) => {
//       if (part.startsWith('```')) {
//         const code = part.replace(/```(\w*)\n?/g, '').replace(/```$/g, '');
//         return <pre key={index}><code>{code}</code></pre>;
//       }
//       if (part.startsWith('`') && part.endsWith('`')) {
//         return <code key={index}>{part.slice(1, -1)}</code>;
//       }
//       const formatted = part.split(/(\*\*[^*]+\*\*)/g).map((s, i) =>
//         s.startsWith('**') && s.endsWith('**')
//           ? <strong key={i}>{s.slice(2, -2)}</strong>
//           : s
//       );
//       return <span key={index}>{formatted}</span>;
//     });
//   };

//   const lines = content.split('\n');
//   const elements = [];
//   let currentList = []; let listType = null;

//   lines.forEach((line, index) => {
//     if (line.startsWith('## ')) {
//       if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`l${index}`}>{currentList}</ul> : <ol key={`l${index}`}>{currentList}</ol>); currentList = []; listType = null; }
//       elements.push(<h2 key={index}>{formatText(line.replace('## ', ''))}</h2>);
//     } else if (line.startsWith('### ')) {
//       if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`l${index}`}>{currentList}</ul> : <ol key={`l${index}`}>{currentList}</ol>); currentList = []; listType = null; }
//       elements.push(<h3 key={index}>{formatText(line.replace('### ', ''))}</h3>);
//     } else if (line.match(/^[-*]\s/)) {
//       if (listType !== 'ul' && currentList.length > 0) { elements.push(<ol key={`l${index}`}>{currentList}</ol>); currentList = []; }
//       listType = 'ul'; currentList.push(<li key={index}>{formatText(line.replace(/^[-*]\s/, ''))}</li>);
//     } else if (line.match(/^\d+\.\s/)) {
//       if (listType !== 'ol' && currentList.length > 0) { elements.push(<ul key={`l${index}`}>{currentList}</ul>); currentList = []; }
//       listType = 'ol'; currentList.push(<li key={index}>{formatText(line.replace(/^\d+\.\s/, ''))}</li>);
//     } else if (line.trim() === '---') {
//       if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`l${index}`}>{currentList}</ul> : <ol key={`l${index}`}>{currentList}</ol>); currentList = []; listType = null; }
//       elements.push(<hr key={index} />);
//     } else if (line.trim()) {
//       if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`l${index}`}>{currentList}</ul> : <ol key={`l${index}`}>{currentList}</ol>); currentList = []; listType = null; }
//       elements.push(<p key={index}>{formatText(line)}</p>);
//     }
//   });
//   if (currentList.length > 0) elements.push(listType === 'ul' ? <ul key="fl">{currentList}</ul> : <ol key="fl">{currentList}</ol>);

//   return <div>{elements}</div>;
// };

// // ─────────────────────────────────────────────────────────────────────────────
// // Main page
// // ─────────────────────────────────────────────────────────────────────────────
// const AIAssistantPage = () => {
//   const { user } = useContext(AuthContext);

//   // ── Active tab: 'doit' | 'foundry' ──────────────────────────────────────
//   const [activeTab, setActiveTab] = useState('doit');
//   const isFoundry = activeTab === 'foundry';

//   // ── DOIT-AI state ────────────────────────────────────────────────────────
//   const [conversations, setConversations] = useState([]);
//   const [activeConversation, setActiveConversation] = useState(null);
//   const [messages, setMessages] = useState([]);

//   // ── Foundry Agent state ──────────────────────────────────────────────────
//   const [foundryConvs, setFoundryConvs] = useState([]);
//   const [foundryActiveConv, setFoundryActiveConv] = useState(null);
//   const [foundryMessages, setFoundryMessages] = useState([]);

//   // ── Shared UI state ──────────────────────────────────────────────────────
//   const [inputText, setInputText] = useState('');
//   const [isLoading, setIsLoading] = useState(false);
//   const [isTyping, setIsTyping] = useState(false);
//   const [uploadedFile, setUploadedFile] = useState(null);

//   const messagesEndRef = useRef(null);
//   const textareaRef = useRef(null);
//   const fileInputRef = useRef(null);

//   // ── Load conversations when tab changes ──────────────────────────────────
//   const loadDoitConversations = useCallback(async () => {
//     try {
//       const response = await fetch(`${API_BASE}/api/ai-assistant/conversations`, {
//         headers: getAuthHeaders()
//       });
//       const data = await response.json();
//       if (data.success) setConversations(data.conversations);
//     } catch (error) {
//       console.error('Error loading DOIT conversations:', error);
//     }
//   }, []);

//   const loadFoundryConversations = useCallback(async () => {
//     try {
//       const data = await foundryAgentAPI.listConversations();
//       if (data.success) setFoundryConvs(data.conversations || []);
//     } catch (error) {
//       console.error('Error loading Foundry conversations:', error);
//     }
//   }, []);

//   useEffect(() => {
//     loadDoitConversations();
//     loadFoundryConversations();
//   }, [loadDoitConversations, loadFoundryConversations]);

//   // Auto-scroll
//   useEffect(() => {
//     messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
//   }, [messages, foundryMessages, isTyping]);

//   // ── Load DOIT messages ───────────────────────────────────────────────────
//   useEffect(() => {
//     if (activeConversation) {
//       setMessages([]);
//       loadDoitMessages(activeConversation._id);
//     } else {
//       setMessages([]);
//     }
//   }, [activeConversation?._id]); // eslint-disable-line

//   const loadDoitMessages = async (conversationId) => {
//     try {
//       const response = await fetch(
//         `${API_BASE}/api/ai-assistant/conversations/${conversationId}/messages`,
//         { headers: getAuthHeaders() }
//       );
//       const data = await response.json();
//       if (data.success) setMessages(data.messages);
//     } catch (error) {
//       console.error('Error loading DOIT messages:', error);
//     }
//   };

//   // ── Load Foundry messages ────────────────────────────────────────────────
//   useEffect(() => {
//     if (foundryActiveConv) {
//       setFoundryMessages([]);
//       loadFoundryMessages(foundryActiveConv._id);
//     } else {
//       setFoundryMessages([]);
//     }
//   }, [foundryActiveConv?._id]); // eslint-disable-line

//   const loadFoundryMessages = async (conversationId) => {
//     try {
//       const data = await foundryAgentAPI.getMessages(conversationId);
//       if (data.success) setFoundryMessages(data.messages || []);
//     } catch (error) {
//       console.error('Error loading Foundry messages:', error);
//     }
//   };

//   // ─────────────────────────────────────────────────────────────────────────
//   // DOIT-AI actions (unchanged from original)
//   // ─────────────────────────────────────────────────────────────────────────
//   const createNewDoitConversation = async () => {
//     try {
//       const response = await fetch(`${API_BASE}/api/ai-assistant/conversations`, {
//         method: 'POST',
//         headers: getAuthHeaders(),
//         body: JSON.stringify({ title: 'New Conversation' })
//       });
//       const data = await response.json();
//       if (data.success) {
//         setConversations([data.conversation, ...conversations]);
//         setActiveConversation(data.conversation);
//         setMessages([]);
//         return data.conversation;
//       }
//     } catch (error) {
//       console.error('Error creating DOIT conversation:', error);
//       return null;
//     }
//   };

//   const sendDoitMessage = async () => {
//     if (!inputText.trim() || isLoading) return;

//     const messageContent = inputText;
//     let conversationToUse = activeConversation;

//     if (!conversationToUse) {
//       conversationToUse = await createNewDoitConversation();
//       if (!conversationToUse) return;
//     }

//     const userMessage = {
//       role: 'user',
//       content: messageContent,
//       created_at: new Date().toISOString()
//     };

//     setMessages(prev => [...prev, userMessage]);
//     setInputText('');
//     setIsLoading(true);
//     setIsTyping(true);

//     try {
//       const response = await fetch(
//         `${API_BASE}/api/ai-assistant/conversations/${conversationToUse._id}/messages`,
//         {
//           method: 'POST',
//           headers: getAuthHeaders(),
//           body: JSON.stringify({
//             content: messageContent,
//             stream: false,
//             include_user_context: true
//           })
//         }
//       );

//       const data = await response.json();
//       setIsTyping(false);

//       if (data.success && data.message) {
//         setMessages(prev => [...prev, {
//           ...data.message,
//           insights: data.insights,
//           user_data_summary: data.user_data_summary,
//           command_result: data.command_result
//         }]);
//         loadDoitConversations();
//       }
//     } catch (error) {
//       console.error('Error sending DOIT message:', error);
//       setIsTyping(false);
//       setMessages(prev => [...prev, {
//         role: 'assistant',
//         content: '❌ Sorry, I encountered an error processing your request. Please try again.',
//         created_at: new Date().toISOString()
//       }]);
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const generateImage = async () => {
//     if (!inputText.trim() || isLoading) return;

//     const prompt = inputText;
//     let conversationToUse = activeConversation;

//     if (!conversationToUse) {
//       conversationToUse = await createNewDoitConversation();
//       if (!conversationToUse) return;
//     }

//     setMessages(prev => [...prev, {
//       role: 'user',
//       content: `Generate image: ${prompt}`,
//       created_at: new Date().toISOString()
//     }]);
//     setInputText('');
//     setIsLoading(true);
//     setIsTyping(true);

//     try {
//       const response = await fetch(
//         `${API_BASE}/api/ai-assistant/conversations/${conversationToUse._id}/generate-image`,
//         {
//           method: 'POST',
//           headers: getAuthHeaders(),
//           body: JSON.stringify({ prompt })
//         }
//       );
//       const data = await response.json();
//       setIsTyping(false);
//       if (data.success) {
//         setMessages(prev => [...prev, data.message]);
//         loadDoitConversations();
//       }
//     } catch (error) {
//       console.error('Error generating image:', error);
//       setIsTyping(false);
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handleFileUpload = async (e) => {
//     const file = e.target.files[0];
//     if (!file || isLoading) return;

//     let conversationToUse = activeConversation;
//     if (!conversationToUse) {
//       conversationToUse = await createNewDoitConversation();
//       if (!conversationToUse) return;
//     }

//     setMessages(prev => [...prev, {
//       role: 'user',
//       content: `Uploaded file: ${file.name}`,
//       created_at: new Date().toISOString()
//     }]);
//     setIsLoading(true);
//     setIsTyping(true);

//     try {
//       const formData = new FormData();
//       formData.append('file', file);

//       const response = await fetch(
//         `${API_BASE}/api/ai-assistant/conversations/${conversationToUse._id}/upload`,
//         {
//           method: 'POST',
//           headers: {
//             'Authorization': `Bearer ${localStorage.getItem('token')}`,
//             'X-Tab-Session-Key': getTabSessionKey()
//           },
//           body: formData
//         }
//       );

//       const data = await response.json();
//       setIsTyping(false);

//       if (data.success) {
//         if (data.ai_message_id) {
//           setMessages(prev => [...prev, {
//             role: 'assistant',
//             content: data.message,
//             created_at: new Date().toISOString()
//           }]);
//         }
//         setUploadedFile(file.name);
//         loadDoitConversations();
//       } else {
//         throw new Error(data.message || 'Upload failed');
//       }
//     } catch (error) {
//       console.error('Error uploading file:', error);
//       setMessages(prev => [...prev, {
//         role: 'assistant',
//         content: `Sorry, I couldn't upload the file. ${error.message}`,
//         created_at: new Date().toISOString()
//       }]);
//       setIsTyping(false);
//     } finally {
//       setIsLoading(false);
//       if (fileInputRef.current) fileInputRef.current.value = '';
//     }
//   };

//   const deleteDoitConversation = async (conversationId, e) => {
//     e.stopPropagation();
//     try {
//       await fetch(`${API_BASE}/api/ai-assistant/conversations/${conversationId}`, {
//         method: 'DELETE',
//         headers: getAuthHeaders()
//       });
//       setConversations(prev => prev.filter(c => c._id !== conversationId));
//       if (activeConversation?._id === conversationId) {
//         setActiveConversation(null);
//         setMessages([]);
//       }
//     } catch (error) {
//       console.error('Error deleting DOIT conversation:', error);
//     }
//   };

//   // ─────────────────────────────────────────────────────────────────────────
//   // Foundry Agent actions
//   // ─────────────────────────────────────────────────────────────────────────
//   const createNewFoundryConversation = async () => {
//     try {
//       const data = await foundryAgentAPI.createConversation('Agent Chat');
//       if (data.success && data.conversation) {
//         setFoundryConvs(prev => [data.conversation, ...prev]);
//         setFoundryActiveConv(data.conversation);
//         setFoundryMessages([]);
//         return data.conversation;
//       }
//     } catch (error) {
//       console.error('Error creating Foundry conversation:', error);
//       return null;
//     }
//   };

//   const sendFoundryMessage = async () => {
//     if (!inputText.trim() || isLoading) return;

//     const messageContent = inputText;
//     let convToUse = foundryActiveConv;

//     if (!convToUse) {
//       convToUse = await createNewFoundryConversation();
//       if (!convToUse) return;
//     }

//     const optimisticMsg = {
//       _id: `opt-${Date.now()}`,
//       role: 'user',
//       content: messageContent,
//       created_at: new Date().toISOString()
//     };

//     setFoundryMessages(prev => [...prev, optimisticMsg]);
//     setInputText('');
//     setIsLoading(true);
//     setIsTyping(true);

//     try {
//       const data = await foundryAgentAPI.sendMessage(convToUse._id, messageContent, true);
//       setIsTyping(false);

//       if (data.success && data.message) {
//         setFoundryMessages(prev => [...prev, data.message]);
//         loadFoundryConversations();
//       } else {
//         throw new Error(data.detail || data.error || 'No response');
//       }
//     } catch (error) {
//       console.error('Error sending Foundry message:', error);
//       setIsTyping(false);
//       // Remove optimistic message and show error
//       setFoundryMessages(prev => prev.filter(m => m._id !== optimisticMsg._id));
//       setFoundryMessages(prev => [...prev, {
//         role: 'assistant',
//         content: `❌ Agent error: ${error.message}. Please try again.`,
//         created_at: new Date().toISOString()
//       }]);
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const deleteFoundryConversation = async (conversationId, e) => {
//     e.stopPropagation();
//     try {
//       await foundryAgentAPI.deleteConversation(conversationId);
//       setFoundryConvs(prev => prev.filter(c => c._id !== conversationId));
//       if (foundryActiveConv?._id === conversationId) {
//         setFoundryActiveConv(null);
//         setFoundryMessages([]);
//       }
//     } catch (error) {
//       console.error('Error deleting Foundry conversation:', error);
//     }
//   };

//   const resetFoundryThread = async () => {
//     try {
//       await foundryAgentAPI.resetThread();
//       setFoundryMessages([]);
//     } catch (error) {
//       console.error('Error resetting Foundry thread:', error);
//     }
//   };

//   // ─────────────────────────────────────────────────────────────────────────
//   // Unified send / key handler
//   // ─────────────────────────────────────────────────────────────────────────
//   const sendMessage = () => isFoundry ? sendFoundryMessage() : sendDoitMessage();

//   const handleKeyPress = (e) => {
//     if (e.key === 'Enter' && !e.shiftKey) {
//       e.preventDefault();
//       sendMessage();
//     }
//   };

//   // ─────────────────────────────────────────────────────────────────────────
//   // Helpers
//   // ─────────────────────────────────────────────────────────────────────────
//   const formatTimestamp = (timestamp) => {
//     const date = new Date(timestamp);
//     const now = new Date();
//     const diff = now - date;
//     if (diff < 60000) return 'Just now';
//     if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
//     if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
//     return date.toLocaleDateString();
//   };

//   // Derived values based on active tab
//   const activeConvList     = isFoundry ? foundryConvs : conversations;
//   const selectedConv       = isFoundry ? foundryActiveConv : activeConversation;
//   const activeMessages     = isFoundry ? foundryMessages : messages;
//   const setSelectedConv    = isFoundry
//     ? (c) => { setFoundryActiveConv(c); }
//     : (c) => { setActiveConversation(c); };
//   const handleNewChat      = isFoundry ? createNewFoundryConversation : createNewDoitConversation;
//   const handleDeleteConv   = isFoundry ? deleteFoundryConversation : deleteDoitConversation;

//   const doitSuggestions = [
//     "Show me my task overview and priorities",
//     "Create a high priority task for login bug fix",
//     "List all my overdue tasks",
//     "What should I focus on today?"
//   ];
//   const foundrySuggestions = [
//     "What's the status of my projects?",
//     "Which tasks are blocked or at risk?",
//     "Help me plan this week's priorities",
//     "Analyse my sprint velocity"
//   ];
//   const suggestions = isFoundry ? foundrySuggestions : doitSuggestions;

//   // ─────────────────────────────────────────────────────────────────────────
//   // Render
//   // ─────────────────────────────────────────────────────────────────────────
//   return (
//     <div className="ai-assistant-page">
//       {/* ── Sidebar ──────────────────────────────────────────────────────── */}
//       <div className="ai-sidebar">
//         <div className="ai-sidebar-header">
//           {/* Tab switcher */}
//           <div className="ai-tab-switcher">
//             <button
//               className={`ai-tab-btn ${!isFoundry ? 'active' : ''}`}
//               onClick={() => setActiveTab('doit')}
//             >
//               <Bot size={14} />
//               DOIT-AI
//             </button>
//             <button
//               className={`ai-tab-btn foundry ${isFoundry ? 'active' : ''}`}
//               onClick={() => setActiveTab('foundry')}
//             >
//               <Zap size={14} />
//               Foundry
//             </button>
//           </div>

//           <button className={`new-chat-btn ${isFoundry ? 'foundry' : ''}`} onClick={handleNewChat}>
//             <Plus size={20} />
//             New {isFoundry ? 'Agent' : ''} Chat
//           </button>
//         </div>

//         <div className="conversations-list">
//           {activeConvList.length === 0 && (
//             <div className="ai-no-convs">No conversations yet</div>
//           )}
//           {activeConvList.map(conv => (
//             <div
//               key={conv._id}
//               className={`conversation-item ${selectedConv?._id === conv._id ? 'active' : ''} ${isFoundry ? 'foundry' : ''}`}
//               onClick={() => setSelectedConv(conv)}
//             >
//               <div className="conversation-title">{conv.title}</div>
//               <div className="conversation-date">{formatTimestamp(conv.updated_at || conv.created_at)}</div>
//               <button
//                 className="conversation-delete"
//                 onClick={(e) => handleDeleteConv(conv._id, e)}
//               >
//                 <Trash2 size={14} />
//               </button>
//             </div>
//           ))}
//         </div>

//         {/* Sidebar footer badge */}
//         <div className="ai-sidebar-footer">
//           {isFoundry ? (
//             <span className="ai-engine-badge foundry">
//               <Zap size={11} /> Azure AI Foundry Agent
//             </span>
//           ) : (
//             <span className="ai-engine-badge">
//               <Bot size={11} /> GPT-powered DOIT-AI
//             </span>
//           )}
//         </div>
//       </div>

//       {/* ── Main Chat Area ────────────────────────────────────────────────── */}
//       <div className="ai-chat-area">
//         <div className={`ai-chat-header ${isFoundry ? 'foundry' : ''}`}>
//           <div className="ai-chat-title">
//             {isFoundry ? <Zap size={20} /> : <Bot size={20} />}
//             {isFoundry ? 'Azure AI Foundry Agent' : 'DOIT AI Assistant'}
//           </div>
//           <div className="ai-header-right">
//             {isFoundry && selectedConv && (
//               <button className="ai-reset-btn" onClick={resetFoundryThread} title="Reset Foundry thread">
//                 ↺ Reset Thread
//               </button>
//             )}
//             <div className="ai-status-badge">
//               <div className={`ai-status-dot ${isFoundry ? 'foundry' : ''}`}></div>
//               Online
//             </div>
//           </div>
//         </div>

//         <div className="ai-messages-container">
//           {activeMessages.length === 0 ? (
//             <div className="ai-empty-state">
//               <div className={`ai-empty-icon ${isFoundry ? 'foundry' : ''}`}>
//                 {isFoundry ? <Zap size={56} color="#7C3AED" /> : <Bot size={56} color="#667eea" />}
//               </div>
//               <div className="ai-empty-title">
//                 {isFoundry ? 'Azure AI Foundry Agent' : 'Welcome to DOIT AI Assistant'}
//               </div>
//               <div className="ai-empty-subtitle">
//                 {isFoundry
//                   ? 'Pre-configured with your DOIT context, Foundry tools, and full multi-turn memory. Ask about your tasks, projects, sprints, or anything else.'
//                   : 'Get personalized insights, task analytics, and intelligent recommendations based on your project data and team performance. I can also help you create, assign, and manage tasks automatically!'}
//               </div>
//               <div className="ai-suggestion-chips">
//                 {suggestions.map((prompt, idx) => (
//                   <div
//                     key={idx}
//                     className={`ai-suggestion-chip ${isFoundry ? 'foundry' : ''}`}
//                     onClick={() => setInputText(prompt)}
//                   >
//                     {prompt}
//                   </div>
//                 ))}
//               </div>
//             </div>
//           ) : (
//             <>
//               {activeMessages.map((msg, idx) => (
//                 <div key={msg._id || idx} className={`ai-message ${msg.role}`}>
//                   <div className={`ai-message-avatar ${isFoundry && msg.role === 'assistant' ? 'foundry' : ''}`}>
//                     {msg.role === 'user' ? <User size={20} /> : isFoundry ? <Zap size={20} /> : <Bot size={20} />}
//                   </div>
//                   <div className="ai-message-content">
//                     <div className="ai-message-bubble">
//                       {isFoundry ? (
//                         <FoundryMessage content={msg.content} />
//                       ) : (
//                         <FormattedMessage
//                           content={msg.content}
//                           insights={msg.insights}
//                           userDataSummary={msg.user_data_summary}
//                           commandResult={msg.command_result}
//                         />
//                       )}
//                     </div>
//                     {/* Image support (DOIT-AI only) */}
//                     {msg.image_url && (
//                       <div className="ai-message-image">
//                         <img src={`${API_BASE}${msg.image_url}`} alt="Generated" />
//                       </div>
//                     )}
//                     {/* Token count badge for Foundry */}
//                     {isFoundry && msg.tokens_used > 0 && (
//                       <div className="ai-token-badge">{msg.tokens_used} tokens</div>
//                     )}
//                     <div className="ai-message-timestamp">
//                       <Clock size={11} />
//                       {formatTimestamp(msg.created_at)}
//                     </div>
//                   </div>
//                 </div>
//               ))}

//               {isTyping && (
//                 <div className="ai-message assistant">
//                   <div className={`ai-message-avatar ${isFoundry ? 'foundry' : ''}`}>
//                     {isFoundry ? <Zap size={20} /> : <Bot size={20} />}
//                   </div>
//                   <div className="ai-message-content">
//                     <div className="ai-message-bubble">
//                       <div className="ai-loading-dots">
//                         <div className="ai-loading-dot"></div>
//                         <div className="ai-loading-dot"></div>
//                         <div className="ai-loading-dot"></div>
//                       </div>
//                     </div>
//                   </div>
//                 </div>
//               )}

//               <div ref={messagesEndRef} />
//             </>
//           )}
//         </div>

//         {/* ── Input area ──────────────────────────────────────────────── */}
//         <div className="ai-input-area">
//           {/* Action buttons — only show for DOIT-AI tab */}
//           {!isFoundry && (
//             <div className="ai-input-actions">
//               <button
//                 className="ai-action-btn"
//                 onClick={generateImage}
//                 disabled={isLoading || !inputText.trim()}
//                 title="Generate an image from your text description"
//               >
//                 <Image size={16} /> Generate Image
//               </button>
//               <button
//                 className="ai-action-btn"
//                 onClick={() => fileInputRef.current?.click()}
//                 disabled={isLoading}
//                 title="Upload a file to analyze"
//               >
//                 <Paperclip size={16} /> Upload File
//               </button>
//               <input
//                 ref={fileInputRef}
//                 type="file"
//                 style={{ display: 'none' }}
//                 onChange={handleFileUpload}
//                 accept=".txt,.pdf,.doc,.docx,.png,.jpg,.jpeg,.csv,.json"
//               />
//             </div>
//           )}

//           {/* Foundry info strip */}
//           {isFoundry && (
//             <div className="ai-foundry-strip">
//               <Zap size={12} />
//               Foundry Agent has live access to your tasks, projects &amp; sprints via context injection
//             </div>
//           )}

//           <div className="ai-input-container">
//             <div className="ai-textarea-wrapper">
//               <textarea
//                 ref={textareaRef}
//                 className={`ai-textarea ${isFoundry ? 'foundry' : ''}`}
//                 placeholder={
//                   isFoundry
//                     ? 'Message the Foundry Agent… (Shift+Enter for newline)'
//                     : uploadedFile
//                     ? `Ask about "${uploadedFile}"...`
//                     : "Ask me anything or give me commands like 'Create a task for...' or 'Show my tasks'"
//                 }
//                 value={inputText}
//                 onChange={(e) => setInputText(e.target.value)}
//                 onKeyPress={handleKeyPress}
//                 disabled={isLoading}
//                 rows={1}
//               />
//             </div>
//             <button
//               className={`ai-send-btn ${isFoundry ? 'foundry' : ''}`}
//               onClick={sendMessage}
//               disabled={isLoading || !inputText.trim()}
//             >
//               <Send size={18} />
//             </button>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default AIAssistantPage;
import React, { useState, useEffect, useRef, useContext, useCallback } from 'react';
import { 
  Plus, Trash2, Send, Image, Paperclip, Bot, User, 
  AlertCircle, CheckCircle2, Info, AlertTriangle,
  Clock, Target, Zap, Shield
} from 'lucide-react';
import { AuthContext } from '../../context/AuthContext';
import { foundryAgentAPI } from '../../services/foundryAgentAPI';
import { localAgentAPI }   from '../../services/localAgentAPI';
import './AIAssistantPage.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const getTabSessionKey = () => {
  let key = sessionStorage.getItem("tab_session_key");
  if (!key) {
    key = 'tab_' + Math.random().toString(36).substr(2, 12) + '_' + Date.now().toString(36);
    sessionStorage.setItem("tab_session_key", key);
  }
  return key;
};

const getAuthHeaders = () => ({
  'Authorization': `Bearer ${localStorage.getItem('token')}`,
  'X-Tab-Session-Key': getTabSessionKey(),
  'Content-Type': 'application/json'
});

// ─────────────────────────────────────────────────────────────────────────────
// Shared markdown renderer (used by Foundry + Local tabs)
// ─────────────────────────────────────────────────────────────────────────────
const MarkdownMessage = ({ content }) => {
  const formatText = (text) => {
    if (!text) return null;
    const parts = text.split(/(```[\s\S]*?```|`[^`]+`)/g);
    return parts.map((part, index) => {
      if (part.startsWith('```')) {
        const code = part.replace(/```(\w*)\n?/g, '').replace(/```$/g, '');
        return <pre key={index}><code>{code}</code></pre>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={index}>{part.slice(1, -1)}</code>;
      }
      const formatted = part.split(/(\*\*[^*]+\*\*)/g).map((s, i) =>
        s.startsWith('**') && s.endsWith('**')
          ? <strong key={i}>{s.slice(2, -2)}</strong>
          : s
      );
      return <span key={index}>{formatted}</span>;
    });
  };

  const lines = content.split('\n');
  const elements = [];
  let currentList = []; let listType = null;
  lines.forEach((line, index) => {
    if (line.startsWith('## ')) {
      if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`l${index}`}>{currentList}</ul> : <ol key={`l${index}`}>{currentList}</ol>); currentList = []; listType = null; }
      elements.push(<h2 key={index}>{formatText(line.replace('## ', ''))}</h2>);
    } else if (line.startsWith('### ')) {
      if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`l${index}`}>{currentList}</ul> : <ol key={`l${index}`}>{currentList}</ol>); currentList = []; listType = null; }
      elements.push(<h3 key={index}>{formatText(line.replace('### ', ''))}</h3>);
    } else if (line.match(/^[-*]\s/)) {
      if (listType !== 'ul' && currentList.length > 0) { elements.push(<ol key={`l${index}`}>{currentList}</ol>); currentList = []; }
      listType = 'ul'; currentList.push(<li key={index}>{formatText(line.replace(/^[-*]\s/, ''))}</li>);
    } else if (line.match(/^\d+\.\s/)) {
      if (listType !== 'ol' && currentList.length > 0) { elements.push(<ul key={`l${index}`}>{currentList}</ul>); currentList = []; }
      listType = 'ol'; currentList.push(<li key={index}>{formatText(line.replace(/^\d+\.\s/, ''))}</li>);
    } else if (line.trim() === '---') {
      if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`l${index}`}>{currentList}</ul> : <ol key={`l${index}`}>{currentList}</ol>); currentList = []; listType = null; }
      elements.push(<hr key={index} />);
    } else if (line.trim()) {
      if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`l${index}`}>{currentList}</ul> : <ol key={`l${index}`}>{currentList}</ol>); currentList = []; listType = null; }
      elements.push(<p key={index}>{formatText(line)}</p>);
    }
  });
  if (currentList.length > 0) elements.push(listType === 'ul' ? <ul key="fl">{currentList}</ul> : <ol key="fl">{currentList}</ol>);
  return <div>{elements}</div>;
};

// ─────────────────────────────────────────────────────────────────────────────
// FormattedMessage — DOIT-AI rich renderer (unchanged)
// ─────────────────────────────────────────────────────────────────────────────
const FormattedMessage = ({ content, insights, userDataSummary, commandResult }) => {
  const formatText = (text) => {
    if (!text) return null;
    const parts = text.split(/(```[\s\S]*?```|`[^`]+`)/g);
    return parts.map((part, index) => {
      if (part.startsWith('```')) {
        const code = part.replace(/```(\w*)\n?/g, '').replace(/```$/g, '');
        return <pre key={index}><code>{code}</code></pre>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={index}>{part.slice(1, -1)}</code>;
      }
      let formatted = part;
      formatted = formatted.split(/(\*\*[^*]+\*\*)/g).map((segment, i) => {
        if (segment.startsWith('**') && segment.endsWith('**')) {
          return <strong key={`bold-${i}`}>{segment.slice(2, -2)}</strong>;
        }
        return segment;
      });
      return <span key={index}>{formatted}</span>;
    });
  };

  const parseContent = (text) => {
    const lines = text.split('\n');
    const elements = [];
    let currentList = [];
    let listType = null;
    lines.forEach((line, index) => {
      if (line.startsWith('## ')) {
        if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`list-${index}`}>{currentList}</ul> : <ol key={`list-${index}`}>{currentList}</ol>); currentList = []; listType = null; }
        elements.push(<h2 key={index}>{formatText(line.replace('## ', ''))}</h2>);
      } else if (line.startsWith('### ')) {
        if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`list-${index}`}>{currentList}</ul> : <ol key={`list-${index}`}>{currentList}</ol>); currentList = []; listType = null; }
        elements.push(<h3 key={index}>{formatText(line.replace('### ', ''))}</h3>);
      } else if (line.match(/^[-*]\s/)) {
        if (listType !== 'ul' && currentList.length > 0) { elements.push(<ol key={`list-${index}`}>{currentList}</ol>); currentList = []; }
        listType = 'ul';
        currentList.push(<li key={index}>{formatText(line.replace(/^[-*]\s/, ''))}</li>);
      } else if (line.match(/^\d+\.\s/)) {
        if (listType !== 'ol' && currentList.length > 0) { elements.push(<ul key={`list-${index}`}>{currentList}</ul>); currentList = []; }
        listType = 'ol';
        currentList.push(<li key={index}>{formatText(line.replace(/^\d+\.\s/, ''))}</li>);
      } else if (line.trim() === '---') {
        if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`list-${index}`}>{currentList}</ul> : <ol key={`list-${index}`}>{currentList}</ol>); currentList = []; listType = null; }
        elements.push(<hr key={index} />);
      } else if (line.trim()) {
        if (currentList.length > 0) { elements.push(listType === 'ul' ? <ul key={`list-${index}`}>{currentList}</ul> : <ol key={`list-${index}`}>{currentList}</ol>); currentList = []; listType = null; }
        elements.push(<p key={index}>{formatText(line)}</p>);
      }
    });
    if (currentList.length > 0) elements.push(listType === 'ul' ? <ul key="final-list">{currentList}</ul> : <ol key="final-list">{currentList}</ol>);
    return elements;
  };

  return (
    <div>
      {commandResult && (
        <div className="ai-command-result">
          <div className={`ai-command-badge ${commandResult.success ? 'success' : 'error'}`}>
            {commandResult.success ? (<><CheckCircle2 size={14} />Command Executed</>) : (<><AlertCircle size={14} />Command Failed</>)}
          </div>
          {commandResult.tasks && commandResult.tasks.length > 0 && (
            <div className="ai-command-tasks">
              <h4><Target size={16} />Tasks ({commandResult.count})</h4>
              <ul>
                {commandResult.tasks.map((task, idx) => (
                  <li key={idx}>
                    <span className="task-ticket">[{task.ticket_id}]</span>
                    <span className="task-title">{task.title}</span>
                    <span className="task-status">{task.status}</span>
                    <span className={`task-priority priority-${task.priority.toLowerCase()}`}>{task.priority}</span>
                    {task.assignee && task.assignee !== 'Unassigned' && (
                      <span className="task-assignee"><User size={12} />{task.assignee}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {commandResult.projects && commandResult.projects.length > 0 && (
            <div className="ai-command-projects">
              <h4><Target size={16} />Projects ({commandResult.count})</h4>
              <ul>
                {commandResult.projects.map((project, idx) => (
                  <li key={idx}>
                    <span className="project-name">{project.name}</span>
                    <span className="project-role">{project.role}</span>
                    {project.description && <span className="project-description">{project.description}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {commandResult.result && (
            <div className="ai-command-details">
              <details><summary>View Full Result</summary>
                <pre><code>{JSON.stringify(commandResult.result, null, 2)}</code></pre>
              </details>
            </div>
          )}
        </div>
      )}
      {userDataSummary && (
        <div className="ai-data-summary">
          <div className="ai-data-card"><div className="ai-data-value">{userDataSummary.tasks_total}</div><div className="ai-data-label">Total Tasks</div></div>
          <div className="ai-data-card"><div className="ai-data-value" style={{ color: userDataSummary.tasks_overdue > 0 ? '#f44336' : '#4caf50' }}>{userDataSummary.tasks_overdue}</div><div className="ai-data-label">Overdue</div></div>
          <div className="ai-data-card"><div className="ai-data-value">{userDataSummary.projects_total}</div><div className="ai-data-label">Projects</div></div>
          <div className="ai-data-card"><div className="ai-data-value">{userDataSummary.velocity}</div><div className="ai-data-label">Tasks/Week</div></div>
        </div>
      )}
      {insights && insights.length > 0 && (
        <div className="ai-insights-container">
          {insights.slice(0, 3).map((insight, idx) => (
            <div key={idx} className={`ai-insight-card ${insight.type}`}>
              <div className="ai-insight-icon">
                {insight.type === 'warning'  && <AlertTriangle size={16} />}
                {insight.type === 'success'  && <CheckCircle2  size={16} />}
                {insight.type === 'info'     && <Info          size={16} />}
                {insight.type === 'critical' && <AlertCircle   size={16} />}
              </div>
              <div className="ai-insight-content">
                <div className="ai-insight-title">{insight.title}</div>
                <div className="ai-insight-description">{insight.description}</div>
              </div>
            </div>
          ))}
        </div>
      )}
      <div>{parseContent(content)}</div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Main page component
// ─────────────────────────────────────────────────────────────────────────────
const AIAssistantPage = () => {
  const { user } = useContext(AuthContext);

  // ── Active tab: 'doit' | 'foundry' | 'local' ────────────────────────────
  const [activeTab, setActiveTab] = useState('doit');
  const isFoundry = activeTab === 'foundry';
  const isLocal   = activeTab === 'local';

  // ── DOIT-AI state ────────────────────────────────────────────────────────
  const [conversations,     setConversations]     = useState([]);
  const [activeConversation,setActiveConversation] = useState(null);
  const [messages,          setMessages]           = useState([]);

  // ── Foundry state ────────────────────────────────────────────────────────
  const [foundryConvs,     setFoundryConvs]     = useState([]);
  const [foundryActiveConv,setFoundryActiveConv] = useState(null);
  const [foundryMessages,  setFoundryMessages]   = useState([]);

  // ── Local Agent state ────────────────────────────────────────────────────
  const [localConvs,     setLocalConvs]     = useState([]);
  const [localActiveConv,setLocalActiveConv] = useState(null);
  const [localMessages,  setLocalMessages]   = useState([]);
  const [localHealth,    setLocalHealth]     = useState(null); // {healthy, model, error}

  // ── Shared UI state ──────────────────────────────────────────────────────
  const [inputText,    setInputText]    = useState('');
  const [isLoading,    setIsLoading]    = useState(false);
  const [isTyping,     setIsTyping]     = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);

  const messagesEndRef = useRef(null);
  const textareaRef    = useRef(null);
  const fileInputRef   = useRef(null);

  // ── Load all conversation lists on mount ─────────────────────────────────
  const loadDoitConversations = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/ai-assistant/conversations`, { headers: getAuthHeaders() });
      const data = await response.json();
      if (data.success) setConversations(data.conversations);
    } catch (e) { console.error('DOIT convs:', e); }
  }, []);

  const loadFoundryConversations = useCallback(async () => {
    try {
      const data = await foundryAgentAPI.listConversations();
      if (data.success) setFoundryConvs(data.conversations || []);
    } catch (e) { console.error('Foundry convs:', e); }
  }, []);

  const loadLocalConversations = useCallback(async () => {
    try {
      const data = await localAgentAPI.listConversations();
      if (data.success) setLocalConvs(data.conversations || []);
    } catch (e) { console.error('Local convs:', e); }
  }, []);

  // Health-check local agent when tab is first opened
  const checkLocalHealth = useCallback(async () => {
    if (localHealth !== null) return;
    try {
      const data = await localAgentAPI.health();
      setLocalHealth(data);
    } catch (e) {
      setLocalHealth({ healthy: false, error: 'Cannot reach backend' });
    }
  }, [localHealth]);

  useEffect(() => {
    loadDoitConversations();
    loadFoundryConversations();
    loadLocalConversations();
  }, [loadDoitConversations, loadFoundryConversations, loadLocalConversations]);

  useEffect(() => {
    if (isLocal) checkLocalHealth();
  }, [isLocal, checkLocalHealth]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, foundryMessages, localMessages, isTyping]);

  // ── Load messages when active conversation changes ────────────────────────
  useEffect(() => {
    if (activeConversation) { 
      // 🎯 Only clear and reload if we don't have optimistic messages
      // (Prevents clearing user message that was just added)
      if (messages.length === 0 || !messages.some(m => m._id?.startsWith('temp-'))) {
        setMessages([]); 
        loadDoitMessages(activeConversation._id); 
      }
    }
    else setMessages([]);
  }, [activeConversation?._id]); // eslint-disable-line

  useEffect(() => {
    if (foundryActiveConv) { setFoundryMessages([]); loadFoundryMessages(foundryActiveConv._id); }
    else setFoundryMessages([]);
  }, [foundryActiveConv?._id]); // eslint-disable-line

  useEffect(() => {
    if (localActiveConv) { setLocalMessages([]); loadLocalMessages(localActiveConv._id); }
    else setLocalMessages([]);
  }, [localActiveConv?._id]); // eslint-disable-line

  const loadDoitMessages = async (id) => {
    try {
      const r = await fetch(`${API_BASE}/api/ai-assistant/conversations/${id}/messages`, { headers: getAuthHeaders() });
      const d = await r.json();
      if (d.success) setMessages(d.messages);
    } catch (e) { console.error(e); }
  };

  const loadFoundryMessages = async (id) => {
    try {
      const d = await foundryAgentAPI.getMessages(id);
      if (d.success) setFoundryMessages(d.messages || []);
    } catch (e) { console.error(e); }
  };

  const loadLocalMessages = async (id) => {
    try {
      const d = await localAgentAPI.getMessages(id);
      if (d.success) setLocalMessages(d.messages || []);
    } catch (e) { console.error(e); }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // DOIT-AI actions
  // ─────────────────────────────────────────────────────────────────────────
  const createNewDoitConversation = async (skipClearMessages = false) => {
    try {
      const r = await fetch(`${API_BASE}/api/ai-assistant/conversations`, {
        method: 'POST', headers: getAuthHeaders(), body: JSON.stringify({ title: 'New Conversation' })
      });
      const d = await r.json();
      if (d.success) {
        setConversations(p => [d.conversation, ...p]);
        setActiveConversation(d.conversation);
        // 🎯 Don't clear messages if we're about to add one (optimistic update)
        if (!skipClearMessages) setMessages([]);
        return d.conversation;
      }
    } catch (e) { console.error(e); return null; }
  };

  const sendDoitMessage = async () => {
    if (!inputText.trim() || isLoading) return;
    const messageContent = inputText;
    
    // 🎯 OPTIMIZATION: Add user message IMMEDIATELY before any async operations
    // This ensures the UI updates instantly, hiding the welcome screen
    const optimisticUserMessage = { 
      _id: `temp-${Date.now()}`, 
      role: 'user', 
      content: messageContent, 
      created_at: new Date().toISOString() 
    };
    setMessages(p => [...p, optimisticUserMessage]);
    setInputText('');
    
    // Create conversation if needed (will not clear messages now)
    let conv = activeConversation || await createNewDoitConversation(true); // Pass flag to skip clearing
    if (!conv) {
      // Rollback optimistic message on failure
      setMessages(p => p.filter(m => m._id !== optimisticUserMessage._id));
      return;
    }
    
    setIsLoading(true); setIsTyping(true);
    try {
      const r = await fetch(`${API_BASE}/api/ai-assistant/conversations/${conv._id}/messages`, {
        method: 'POST', headers: getAuthHeaders(),
        body: JSON.stringify({ content: messageContent, stream: false, include_user_context: true })
      });
      const d = await r.json();
      setIsTyping(false);
      if (d.success && d.message) {
        // Keep optimistic user message, just add AI response
        setMessages(p => [...p, { ...d.message, insights: d.insights, user_data_summary: d.user_data_summary, command_result: d.command_result }]);
        loadDoitConversations();
      }
    } catch (e) {
      setIsTyping(false);
      setMessages(p => [...p, { role: 'assistant', content: '❌ Error processing request. Please try again.', created_at: new Date().toISOString() }]);
    } finally { setIsLoading(false); }
  };

  const generateImage = async () => {
    if (!inputText.trim() || isLoading) return;
    const prompt = inputText;
    
    // 🎯 Show user message immediately
    const optimisticMsg = { _id: `temp-${Date.now()}`, role: 'user', content: `Generate image: ${prompt}`, created_at: new Date().toISOString() };
    setMessages(p => [...p, optimisticMsg]);
    setInputText('');
    
    let conv = activeConversation || await createNewDoitConversation(true);
    if (!conv) {
      setMessages(p => p.filter(m => m._id !== optimisticMsg._id));
      return;
    }
    
    setIsLoading(true); setIsTyping(true);
    try {
      const r = await fetch(`${API_BASE}/api/ai-assistant/conversations/${conv._id}/generate-image`, {
        method: 'POST', headers: getAuthHeaders(), body: JSON.stringify({ prompt })
      });
      const d = await r.json();
      setIsTyping(false);
      if (d.success) { 
        setMessages(p => [...p.filter(m => m._id !== optimisticMsg._id), d.message]); 
        loadDoitConversations(); 
      }
    } catch (e) { console.error(e); setIsTyping(false); }
    finally { setIsLoading(false); }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || isLoading) return;
    
    // 🎯 Show user message immediately
    const optimisticMsg = { _id: `temp-${Date.now()}`, role: 'user', content: `Uploaded file: ${file.name}`, created_at: new Date().toISOString() };
    setMessages(p => [...p, optimisticMsg]);
    
    let conv = activeConversation || await createNewDoitConversation(true);
    if (!conv) {
      setMessages(p => p.filter(m => m._id !== optimisticMsg._id));
      return;
    }
    
    setIsLoading(true); setIsTyping(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const r = await fetch(`${API_BASE}/api/ai-assistant/conversations/${conv._id}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}`, 'X-Tab-Session-Key': getTabSessionKey() },
        body: formData
      });
      const d = await r.json();
      setIsTyping(false);
      if (d.success) {
        if (d.ai_message_id) setMessages(p => [...p.filter(m => m._id !== optimisticMsg._id), { role: 'assistant', content: d.message, created_at: new Date().toISOString() }]);
        setUploadedFile(file.name); loadDoitConversations();
      } else throw new Error(d.message || 'Upload failed');
    } catch (e) {
      setMessages(p => [...p, { role: 'assistant', content: `Sorry, couldn't upload file. ${e.message}`, created_at: new Date().toISOString() }]);
      setIsTyping(false);
    } finally { setIsLoading(false); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };

  const deleteDoitConversation = async (id, e) => {
    e.stopPropagation();
    try {
      await fetch(`${API_BASE}/api/ai-assistant/conversations/${id}`, { method: 'DELETE', headers: getAuthHeaders() });
      setConversations(p => p.filter(c => c._id !== id));
      if (activeConversation?._id === id) { setActiveConversation(null); setMessages([]); }
    } catch (e) { console.error(e); }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Foundry actions
  // ─────────────────────────────────────────────────────────────────────────
  const createNewFoundryConversation = async () => {
    try {
      const d = await foundryAgentAPI.createConversation('Agent Chat');
      if (d.success && d.conversation) {
        setFoundryConvs(p => [d.conversation, ...p]);
        setFoundryActiveConv(d.conversation);
        setFoundryMessages([]);
        return d.conversation;
      }
    } catch (e) { console.error(e); return null; }
  };

  const sendFoundryMessage = async () => {
    if (!inputText.trim() || isLoading) return;
    const messageContent = inputText;
    let conv = foundryActiveConv || await createNewFoundryConversation();
    if (!conv) return;
    const opt = { _id: `opt-${Date.now()}`, role: 'user', content: messageContent, created_at: new Date().toISOString() };
    setFoundryMessages(p => [...p, opt]);
    setInputText(''); setIsLoading(true); setIsTyping(true);
    try {
      const d = await foundryAgentAPI.sendMessage(conv._id, messageContent, true);
      setIsTyping(false);
      if (d.success && d.message) { setFoundryMessages(p => [...p, d.message]); loadFoundryConversations(); }
      else throw new Error(d.detail || d.error || 'No response');
    } catch (e) {
      setIsTyping(false);
      setFoundryMessages(p => p.filter(m => m._id !== opt._id));
      setFoundryMessages(p => [...p, { role: 'assistant', content: `❌ Agent error: ${e.message}`, created_at: new Date().toISOString() }]);
    } finally { setIsLoading(false); }
  };

  const deleteFoundryConversation = async (id, e) => {
    e.stopPropagation();
    try {
      await foundryAgentAPI.deleteConversation(id);
      setFoundryConvs(p => p.filter(c => c._id !== id));
      if (foundryActiveConv?._id === id) { setFoundryActiveConv(null); setFoundryMessages([]); }
    } catch (e) { console.error(e); }
  };

  const resetFoundryThread = async () => {
    try { await foundryAgentAPI.resetThread(); setFoundryMessages([]); }
    catch (e) { console.error(e); }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Local Agent actions
  // ─────────────────────────────────────────────────────────────────────────
  const createNewLocalConversation = async () => {
    try {
      const d = await localAgentAPI.createConversation('Local AI Chat');
      if (d.success && d.conversation) {
        setLocalConvs(p => [d.conversation, ...p]);
        setLocalActiveConv(d.conversation);
        setLocalMessages([]);
        return d.conversation;
      }
    } catch (e) { console.error(e); return null; }
  };

  const sendLocalMessage = async () => {
    if (!inputText.trim() || isLoading) return;
    const messageContent = inputText;
    let conv = localActiveConv || await createNewLocalConversation();
    if (!conv) return;
    const opt = { _id: `opt-${Date.now()}`, role: 'user', content: messageContent, created_at: new Date().toISOString() };
    setLocalMessages(p => [...p, opt]);
    setInputText(''); setIsLoading(true); setIsTyping(true);
    try {
      const d = await localAgentAPI.sendMessage(conv._id, messageContent, true);
      setIsTyping(false);
      if (d.success && d.message) {
        setLocalMessages(p => [...p, {
          ...d.message,
          rag_used: d.rag_used,
          model:    d.model,
        }]);
        loadLocalConversations();
      } else throw new Error(d.detail || d.error || 'No response');
    } catch (e) {
      setIsTyping(false);
      setLocalMessages(p => p.filter(m => m._id !== opt._id));
      setLocalMessages(p => [...p, { role: 'assistant', content: `❌ Local agent error: ${e.message}. Is Ollama running?`, created_at: new Date().toISOString() }]);
    } finally { setIsLoading(false); }
  };

  const deleteLocalConversation = async (id, e) => {
    e.stopPropagation();
    try {
      await localAgentAPI.deleteConversation(id);
      setLocalConvs(p => p.filter(c => c._id !== id));
      if (localActiveConv?._id === id) { setLocalActiveConv(null); setLocalMessages([]); }
    } catch (e) { console.error(e); }
  };

  const resetLocalHistory = async () => {
    try { await localAgentAPI.resetHistory(); setLocalMessages([]); }
    catch (e) { console.error(e); }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Unified handlers
  // ─────────────────────────────────────────────────────────────────────────
  const sendMessage = () => {
    if (isFoundry) return sendFoundryMessage();
    if (isLocal)   return sendLocalMessage();
    return sendDoitMessage();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const formatTimestamp = (ts) => {
    const date = new Date(ts); const now = new Date(); const diff = now - date;
    if (diff < 60000)    return 'Just now';
    if (diff < 3600000)  return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  // ── Derived tab values ───────────────────────────────────────────────────
  const activeConvList  = isFoundry ? foundryConvs  : isLocal ? localConvs  : conversations;
  const selectedConv    = isFoundry ? foundryActiveConv : isLocal ? localActiveConv : activeConversation;
  const activeMessages  = isFoundry ? foundryMessages : isLocal ? localMessages : messages;
  const setSelectedConv = isFoundry ? setFoundryActiveConv : isLocal ? setLocalActiveConv : setActiveConversation;
  const handleNewChat   = isFoundry ? createNewFoundryConversation : isLocal ? createNewLocalConversation : createNewDoitConversation;
  const handleDeleteConv = isFoundry ? deleteFoundryConversation : isLocal ? deleteLocalConversation : deleteDoitConversation;

  const suggestions = isFoundry ? [
    "What's the status of my projects?",
    "Which tasks are blocked or at risk?",
    "Help me plan this week's priorities",
    "Analyse my sprint velocity",
  ] : isLocal ? [
    "Summarise my current tasks",
    "What are my overdue items?",
    "Which project needs attention?",
    "What should I work on next?",
  ] : [
    "Show me my task overview and priorities",
    "Create a high priority task for login bug fix",
    "List all my overdue tasks",
    "What should I focus on today?",
  ];

  // ─────────────────────────────────────────────────────────────────────────
  // Render helpers
  // ─────────────────────────────────────────────────────────────────────────
  const tabIcon = (tab) => {
    if (tab === 'foundry') return <Zap   size={20} />;
    if (tab === 'local')   return <Shield size={20} />;
    return <Bot size={20} />;
  };

  const tabLabel = () => {
    if (isFoundry) return 'Azure AI Foundry Agent';
    if (isLocal)   return 'Local AI (On-Premise)';
    return 'DOIT AI Assistant';
  };

  const avatarClass = (msgRole) => {
    if (msgRole !== 'assistant') return '';
    if (isFoundry) return 'foundry';
    if (isLocal)   return 'local';
    return '';
  };

  const renderAvatar = (msgRole) => {
    if (msgRole === 'user') return <User size={20} />;
    if (isFoundry) return <Zap    size={20} />;
    if (isLocal)   return <Shield size={20} />;
    return <Bot size={20} />;
  };

  const renderBubbleContent = (msg) => {
    if (isFoundry || isLocal) return <MarkdownMessage content={msg.content} />;
    return <FormattedMessage content={msg.content} insights={msg.insights} userDataSummary={msg.user_data_summary} commandResult={msg.command_result} />;
  };

  // ─────────────────────────────────────────────────────────────────────────
  // JSX
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="ai-assistant-page">

      {/* ── Sidebar ────────────────────────────────────────────────────────── */}
      <div className="ai-sidebar">
        <div className="ai-sidebar-header">

          {/* Three-tab switcher */}
          <div className="ai-tab-switcher">
            <button className={`ai-tab-btn ${activeTab === 'doit' ? 'active' : ''}`} onClick={() => setActiveTab('doit')}>
              <Bot size={13} />DOIT-AI
            </button>
            <button className={`ai-tab-btn foundry ${activeTab === 'foundry' ? 'active' : ''}`} onClick={() => setActiveTab('foundry')}>
              <Zap size={13} />Foundry
            </button>
            <button className={`ai-tab-btn local ${activeTab === 'local' ? 'active' : ''}`} onClick={() => setActiveTab('local')}>
              <Shield size={13} />Local
            </button>
          </div>

          <button
            className={`new-chat-btn ${isFoundry ? 'foundry' : isLocal ? 'local' : ''}`}
            onClick={handleNewChat}
          >
            <Plus size={18} />
            New {isLocal ? 'Private' : isFoundry ? 'Agent' : ''} Chat
          </button>
        </div>

        <div className="conversations-list">
          {activeConvList.length === 0 && <div className="ai-no-convs">No conversations yet</div>}
          {activeConvList.map(conv => (
            <div
              key={conv._id}
              className={`conversation-item ${selectedConv?._id === conv._id ? 'active' : ''} ${isFoundry ? 'foundry' : isLocal ? 'local' : ''}`}
              onClick={() => setSelectedConv(conv)}
            >
              <div className="conversation-title">{conv.title}</div>
              <div className="conversation-date">{formatTimestamp(conv.updated_at || conv.created_at)}</div>
              <button className="conversation-delete" onClick={(e) => handleDeleteConv(conv._id, e)}>
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>

        <div className="ai-sidebar-footer">
          {isFoundry ? (
            <span className="ai-engine-badge foundry"><Zap size={11} /> Azure AI Foundry</span>
          ) : isLocal ? (
            <span className="ai-engine-badge local"><Shield size={11} /> On-Premise · Ollama</span>
          ) : (
            <span className="ai-engine-badge"><Bot size={11} /> GPT-powered DOIT-AI</span>
          )}
        </div>
      </div>

      {/* ── Main Chat Area ──────────────────────────────────────────────────── */}
      <div className="ai-chat-area">
        <div className={`ai-chat-header ${isFoundry ? 'foundry' : isLocal ? 'local' : ''}`}>
          <div className="ai-chat-title">
            {tabIcon(activeTab)}
            {tabLabel()}
          </div>
          <div className="ai-header-right">
            {isFoundry && selectedConv && (
              <button className="ai-reset-btn" onClick={resetFoundryThread}>↺ Reset Thread</button>
            )}
            {isLocal && selectedConv && (
              <button className="ai-reset-btn local" onClick={resetLocalHistory}>↺ Clear History</button>
            )}
            {/* Local health pill */}
            {isLocal && localHealth && (
              <div className={`ai-status-badge ${localHealth.healthy ? '' : 'offline'}`}>
                <div className={`ai-status-dot ${localHealth.healthy ? 'local' : 'offline'}`}></div>
                {localHealth.healthy ? `${localHealth.model || 'Ollama'} ready` : 'Ollama offline'}
              </div>
            )}
            {!isLocal && (
              <div className="ai-status-badge">
                <div className={`ai-status-dot ${isFoundry ? 'foundry' : ''}`}></div>
                Online
              </div>
            )}
          </div>
        </div>

        <div className="ai-messages-container">
          {activeMessages.length === 0 ? (
            <div className="ai-empty-state">
              <div className={`ai-empty-icon ${isFoundry ? 'foundry' : isLocal ? 'local' : ''}`}>
                {isFoundry ? <Zap size={52} color="#7C3AED" /> : isLocal ? <Shield size={52} color="#059669" /> : <Bot size={52} color="#667eea" />}
              </div>
              <div className="ai-empty-title">
                {isFoundry ? 'Azure AI Foundry Agent' : isLocal ? 'Local AI — 100% On-Premise' : 'Welcome to DOIT AI Assistant'}
              </div>
              <div className="ai-empty-subtitle">
                {isFoundry
                  ? 'Pre-configured with your DOIT context, Foundry tools, and full multi-turn memory. Ask about your tasks, projects, sprints, or anything else.'
                  : isLocal
                  ? `Powered by Ollama + LlamaIndex + ChromaDB. All data stays on your infrastructure — nothing is sent to external APIs. RAG retrieves relevant context from your live DOIT data.${localHealth && !localHealth.healthy ? `\n\n⚠️ ${localHealth.error}` : ''}`
                  : 'Get personalized insights, task analytics, and intelligent recommendations based on your project data and team performance. I can also help you create, assign, and manage tasks automatically!'}
              </div>
              {isLocal && localHealth && !localHealth.healthy && (
                <div className="ai-local-offline-banner">
                  <AlertCircle size={16} />
                  <div>
                    <strong>Ollama not reachable</strong>
                    <p>Start Ollama: <code>ollama serve</code> · Pull model: <code>ollama pull llama3</code></p>
                  </div>
                </div>
              )}
              <div className="ai-suggestion-chips">
                {suggestions.map((prompt, idx) => (
                  <div
                    key={idx}
                    className={`ai-suggestion-chip ${isFoundry ? 'foundry' : isLocal ? 'local' : ''}`}
                    onClick={() => setInputText(prompt)}
                  >
                    {prompt}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              {activeMessages.map((msg, idx) => (
                <div key={msg._id || idx} className={`ai-message ${msg.role}`}>
                  <div className={`ai-message-avatar ${avatarClass(msg.role)}`}>
                    {renderAvatar(msg.role)}
                  </div>
                  <div className="ai-message-content">
                    <div className="ai-message-bubble">
                      {renderBubbleContent(msg)}
                    </div>
                    {msg.image_url && (
                      <div className="ai-message-image">
                        <img src={`${API_BASE}${msg.image_url}`} alt="Generated" />
                      </div>
                    )}
                    {/* RAG badge (Local only) */}
                    {isLocal && msg.role === 'assistant' && msg.rag_used && (
                      <div className="ai-rag-badge">
                        <Shield size={10} /> RAG · {msg.model}
                      </div>
                    )}
                    {/* Token badge */}
                    {(isFoundry || isLocal) && msg.tokens_used > 0 && (
                      <div className="ai-token-badge">{msg.tokens_used} tokens</div>
                    )}
                    <div className="ai-message-timestamp">
                      <Clock size={11} />
                      {formatTimestamp(msg.created_at)}
                    </div>
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="ai-message assistant">
                  <div className={`ai-message-avatar ${isFoundry ? 'foundry' : isLocal ? 'local' : ''}`}>
                    {isFoundry ? <Zap size={20} /> : isLocal ? <Shield size={20} /> : <Bot size={20} />}
                  </div>
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

        {/* ── Input area ────────────────────────────────────────────────────── */}
        <div className="ai-input-area">
          {/* DOIT-AI action buttons */}
          {!isFoundry && !isLocal && (
            <div className="ai-input-actions">
              <button className="ai-action-btn" onClick={generateImage} disabled={isLoading || !inputText.trim()} title="Generate an image">
                <Image size={16} /> Generate Image
              </button>
              <button className="ai-action-btn" onClick={() => fileInputRef.current?.click()} disabled={isLoading} title="Upload a file">
                <Paperclip size={16} /> Upload File
              </button>
              <input ref={fileInputRef} type="file" style={{ display: 'none' }} onChange={handleFileUpload}
                accept=".txt,.pdf,.doc,.docx,.png,.jpg,.jpeg,.csv,.json" />
            </div>
          )}

          {/* Foundry info strip */}
          {isFoundry && (
            <div className="ai-foundry-strip">
              <Zap size={12} />
              Foundry Agent has live access to your tasks, projects &amp; sprints via context injection
            </div>
          )}

          {/* Local info strip */}
          {isLocal && (
            <div className="ai-local-strip">
              <Shield size={12} />
              Private &amp; on-premise · Ollama LLM · ChromaDB RAG · no data leaves your network
            </div>
          )}

          <div className="ai-input-container">
            <div className="ai-textarea-wrapper">
              <textarea
                ref={textareaRef}
                className={`ai-textarea ${isFoundry ? 'foundry' : isLocal ? 'local' : ''}`}
                placeholder={
                  isFoundry ? 'Message the Foundry Agent… (Shift+Enter for newline)'
                  : isLocal  ? 'Message the local Ollama model… (Shift+Enter for newline)'
                  : uploadedFile ? `Ask about "${uploadedFile}"...`
                  : "Ask me anything or give me commands like 'Create a task for...' or 'Show my tasks'"
                }
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                rows={1}
              />
            </div>
            <button
              className={`ai-send-btn ${isFoundry ? 'foundry' : isLocal ? 'local' : ''}`}
              onClick={sendMessage}
              disabled={isLoading || !inputText.trim()}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIAssistantPage;
// (intentional empty — file complete above)