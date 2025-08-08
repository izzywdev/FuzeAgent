import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'

interface Agent {
  id: string
  name: string
  role: string
  type: string
  status: string
  config: {
    model: string
    temperature: number
    tools: string[]
    goal?: string
    backstory?: string
  }
  created_at: string
  updated_at: string
  team_id?: string
  team_name?: string
}

interface Task {
  id: string
  title: string
  description: string
  status: string
  priority: string
  created_at: string
  completed_at?: string
}

interface Conversation {
  id: string
  title: string
  message_count: number
  last_message: string
  timestamp: string
  status: string
}

interface ChatMessage {
  id: string
  conversation_id: string
  role: 'user' | 'agent' | 'system'
  content: string
  timestamp: string
  status: 'sending' | 'sent' | 'error'
  metadata?: {
    tokens_used?: number
    model?: string
    response_time?: number
  }
}

interface ContainerInfo {
  id: string
  name: string
  status: string
  image: string
  created: string
  started?: string
  finished?: string
  restart_count: number
  cpu_usage?: number
  memory_usage?: number
  memory_limit?: number
  network_rx?: number
  network_tx?: number
  ports: Record<string, string>
  environment: Record<string, string>
  mounts: string[]
  labels: Record<string, string>
  health?: string
}

interface KnowledgeDocument {
  id: string
  title: string
  filename: string
  type: 'document' | 'link' | 'text'
  mime_type?: string
  size?: number
  status: 'active' | 'processing' | 'error'
  upload_date: string
  last_modified: string
  content_preview?: string
  tags: string[]
  source_url?: string
  agent_id?: string
  word_count?: number
  extracted_text?: string
}

export function AgentDetailsPage() {
  const { agentId } = useParams<{ agentId: string }>()
  const [agent, setAgent] = useState<Agent | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [containerInfo, setContainerInfo] = useState<ContainerInfo | null>(null)
  const [knowledgeDocs, setKnowledgeDocs] = useState<KnowledgeDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  const [showUpload, setShowUpload] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocument | null>(null)
  const [showDocumentViewer, setShowDocumentViewer] = useState(false)
  const [documentContent, setDocumentContent] = useState<string>('')
  const [containerLoading, setContainerLoading] = useState(false)
  const [showContainerLogs, setShowContainerLogs] = useState(false)
  const [containerLogs, setContainerLogs] = useState<string[]>([])
  const [isLiveLogsActive, setIsLiveLogsActive] = useState(false)
  const [logWebSocket, setLogWebSocket] = useState<WebSocket | null>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [isSendingMessage, setIsSendingMessage] = useState(false)
  const [chatWebSocket, setChatWebSocket] = useState<WebSocket | null>(null)
  const [isAgentTyping, setIsAgentTyping] = useState(false)

  useEffect(() => {
    if (!agentId) return

    // Load agent details
    fetch(`http://localhost:8000/agents/${agentId}`)
      .then(res => res.json())
      .then(data => {
        setAgent(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load agent:', err)
        setLoading(false)
        // Mock data for demo
        setAgent({
          id: agentId,
          name: 'IzzyAI CEO',
          role: 'Digital CEO',
          type: 'executive',
          status: 'active',
          config: {
            model: 'claude-sonnet-4-20250514',
            temperature: 0.7,
            tools: ['strategic_planning', 'resource_allocation', 'team_management'],
            goal: 'Lead the organization with strategic vision and effective decision-making',
            backstory: 'Executive AI with extensive experience in strategic planning, team leadership, and organizational management'
          },
          created_at: '2025-08-06T11:16:04.060569',
          updated_at: '2025-08-06T11:16:04.060598',
          team_id: '1',
          team_name: 'Executive Team'
        })
      })

    // Load agent tasks
    fetch(`http://localhost:8000/agents/${agentId}/tasks`)
      .then(res => res.json())
      .then(data => setTasks(Array.isArray(data) ? data : []))
      .catch(() => {
        // Mock tasks data
        setTasks([
          {
            id: '1',
            title: 'Strategic Planning Q4 2025',
            description: 'Develop comprehensive strategic plan for Q4 2025 expansion',
            status: 'completed',
            priority: 'high',
            created_at: '2025-08-05T09:00:00Z',
            completed_at: '2025-08-05T17:30:00Z'
          },
          {
            id: '2',
            title: 'Team Performance Review',
            description: 'Conduct quarterly performance review for all team leads',
            status: 'in_progress',
            priority: 'medium',
            created_at: '2025-08-06T08:00:00Z'
          },
          {
            id: '3',
            title: 'Budget Allocation Planning',
            description: 'Plan budget allocation for next quarter initiatives',
            status: 'pending',
            priority: 'high',
            created_at: '2025-08-06T10:00:00Z'
          }
        ])
      })

    // Load agent's primary conversation from API
    if (agentId) {
      loadAgentPrimaryConversation()
    }

    // Load container info
    if (agentId) {
      loadContainerInfo()
      loadKnowledgeDocuments()
    }
  }, [agentId])

  // Load knowledge documents for the agent
  const loadKnowledgeDocuments = async () => {
    if (!agentId) return
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/agents/${agentId}/documents`)
      if (response.ok) {
        const documents = await response.json()
        setKnowledgeDocs(documents)
      } else {
        console.error('Failed to load agent documents')
      }
    } catch (error) {
      console.error('Error loading agent documents:', error)
    }
  }

  // Load agent's primary conversation and messages
  const loadAgentPrimaryConversation = async () => {
    if (!agentId) return
    
    try {
      const response = await fetch(`http://localhost:8000/agents/${agentId}/conversations`)
      if (response.ok) {
        const conversations = await response.json()
        
        if (conversations.length > 0) {
          // Use the first (most recent) conversation as the primary one
          const primaryConversation = conversations[0]
          setSelectedConversation(primaryConversation)
          
          // Load messages for this conversation
          await loadConversationMessages(primaryConversation.id)
          
          // Start WebSocket connection
          startChatWebSocket(primaryConversation.id)
        } else {
          // No conversations exist yet - will be created when user sends first message
          console.log('No conversations found for agent')
        }
      } else {
        console.error('Failed to load agent conversations')
      }
    } catch (error) {
      console.error('Error loading agent primary conversation:', error)
    }
  }

  // Create primary conversation for agent
  const createPrimaryConversation = async () => {
    if (!agentId) return
    
    try {
      const response = await fetch(`http://localhost:8000/agents/${agentId}/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: `Conversation with ${agent?.name || 'Agent'}`,
          initial_message: null
        })
      })
      
      if (response.ok) {
        const conversation = await response.json()
        setSelectedConversation(conversation)
        setChatMessages([])
        
        // Start WebSocket connection
        startChatWebSocket(conversation.id)
        
        console.log('Created primary conversation')
      } else {
        console.error('Failed to create primary conversation')
      }
    } catch (error) {
      console.error('Error creating primary conversation:', error)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0 || !agentId) return

    setUploading(true)
    
    for (const file of Array.from(files)) {
      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('title', file.name)
        
        const response = await fetch(`http://localhost:8000/knowledge/agents/${agentId}/documents`, {
          method: 'POST',
          body: formData
        })
        
        if (response.ok) {
          console.log(`Uploaded ${file.name} successfully`)
        } else {
          console.error(`Failed to upload ${file.name}`)
        }
      } catch (error) {
        console.error(`Error uploading ${file.name}:`, error)
      }
    }
    
    setUploading(false)
    setShowUpload(false)
    await loadKnowledgeDocuments() // Reload documents
    
    // Reset file input
    event.target.value = ''
  }

  const handleUrlUpload = async () => {
    if (!agentId) return
    
    const url = prompt('Enter URL:')
    if (!url) return

    setUploading(true)
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/agents/${agentId}/url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url })
      })
      
      if (response.ok) {
        console.log('URL added successfully')
        await loadKnowledgeDocuments()
      } else {
        console.error('Failed to add URL')
      }
    } catch (error) {
      console.error('Error adding URL:', error)
    }
    
    setUploading(false)
    setShowUpload(false)
  }

  const handleDocumentClick = async (doc: KnowledgeDocument) => {
    if (!agentId) return
    
    setSelectedDocument(doc)
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/agents/${agentId}/documents/${doc.id}/content`)
      if (response.ok) {
        const data = await response.json()
        setDocumentContent(data.content)
        setShowDocumentViewer(true)
      } else {
        console.error('Failed to load document content')
      }
    } catch (error) {
      console.error('Error loading document content:', error)
    }
  }

  const handleDocumentDelete = async (docId: string) => {
    if (!agentId || !confirm('Are you sure you want to delete this document?')) return
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/agents/${agentId}/documents/${docId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        await loadKnowledgeDocuments()
      } else {
        console.error('Failed to delete document')
      }
    } catch (error) {
      console.error('Error deleting document:', error)
    }
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Container Management Functions
  const loadContainerInfo = async () => {
    if (!agentId) return
    
    try {
      const response = await fetch(`http://localhost:8000/agents/${agentId}/container/status`)
      if (response.ok) {
        const data = await response.json()
        setContainerInfo(data)
      } else {
        console.error('Failed to load container status')
        setContainerInfo(null)
      }
    } catch (error) {
      console.error('Error loading container status:', error)
      setContainerInfo(null)
    }
  }

  const handleCreateContainer = async () => {
    if (!agentId) return
    
    setContainerLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/agents/${agentId}/container/create`, {
        method: 'POST'
      })
      
      if (response.ok) {
        console.log('Container created successfully')
        await loadContainerInfo()
      } else {
        console.error('Failed to create container')
      }
    } catch (error) {
      console.error('Error creating container:', error)
    }
    setContainerLoading(false)
  }

  const handleStartContainer = async () => {
    if (!agentId) return
    
    setContainerLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/agents/${agentId}/container/start`, {
        method: 'POST'
      })
      
      if (response.ok) {
        console.log('Container started successfully')
        await loadContainerInfo()
      } else {
        console.error('Failed to start container')
      }
    } catch (error) {
      console.error('Error starting container:', error)
    }
    setContainerLoading(false)
  }

  const handleStopContainer = async () => {
    if (!agentId) return
    
    setContainerLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/agents/${agentId}/container/stop`, {
        method: 'POST'
      })
      
      if (response.ok) {
        console.log('Container stopped successfully')
        await loadContainerInfo()
      } else {
        console.error('Failed to stop container')
      }
    } catch (error) {
      console.error('Error stopping container:', error)
    }
    setContainerLoading(false)
  }

  const handleRestartContainer = async () => {
    if (!agentId) return
    
    setContainerLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/agents/${agentId}/container/restart`, {
        method: 'POST'
      })
      
      if (response.ok) {
        console.log('Container restarted successfully')
        await loadContainerInfo()
      } else {
        console.error('Failed to restart container')
      }
    } catch (error) {
      console.error('Error restarting container:', error)
    }
    setContainerLoading(false)
  }

  const handleLoadContainerLogs = async (autoStartLive = false) => {
    if (!agentId) return
    
    try {
      const response = await fetch(`http://localhost:8000/agents/${agentId}/container/logs`)
      if (response.ok) {
        const data = await response.json()
        setContainerLogs(data.logs || [])
        setShowContainerLogs(true)
        
        // Auto-start live logs if requested
        if (autoStartLive && !isLiveLogsActive) {
          setTimeout(() => startLiveLogs(), 500) // Small delay to let modal fully open
        }
      } else {
        console.error('Failed to load container logs')
      }
    } catch (error) {
      console.error('Error loading container logs:', error)
    }
  }

  const startLiveLogs = () => {
    if (!agentId || isLiveLogsActive) return

    // Create WebSocket connection for live logs
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.hostname}:8000/agents/${agentId}/container/logs/stream`
    
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('Live logs WebSocket connected')
      setIsLiveLogsActive(true)
      setLogWebSocket(ws)
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'log' && data.message) {
          const logEntry = `[${data.timestamp || new Date().toISOString()}] ${data.stream || 'stdout'}: ${data.message}`
          setContainerLogs(prevLogs => [...prevLogs, logEntry])
        }
      } catch (error) {
        // If it's not JSON, treat as plain text log
        const logEntry = `[${new Date().toISOString()}] stdout: ${event.data}`
        setContainerLogs(prevLogs => [...prevLogs, logEntry])
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    ws.onclose = () => {
      console.log('Live logs WebSocket disconnected')
      setIsLiveLogsActive(false)
      setLogWebSocket(null)
    }
  }

  const stopLiveLogs = () => {
    if (logWebSocket) {
      logWebSocket.close()
    }
  }

  const clearLogs = () => {
    setContainerLogs([])
  }

  // Cleanup WebSocket on component unmount
  useEffect(() => {
    return () => {
      if (logWebSocket) {
        logWebSocket.close()
      }
    }
  }, [logWebSocket])

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && showContainerLogs) {
      const logContainer = document.getElementById('log-container')
      if (logContainer) {
        logContainer.scrollTop = logContainer.scrollHeight
      }
    }
  }, [containerLogs, autoScroll, showContainerLogs])

  // Chat Message Loading

  const loadConversationMessages = async (conversationId: string) => {
    if (!agentId) return

    try {
      const response = await fetch(`http://localhost:8000/agents/${agentId}/conversations/${conversationId}/messages`)
      if (response.ok) {
        const messages = await response.json()
        setChatMessages(messages)
      } else {
        console.error('Failed to load conversation messages')
      }
    } catch (error) {
      console.error('Error loading conversation messages:', error)
    }
  }

  const startChatWebSocket = (conversationId: string) => {
    if (!agentId || chatWebSocket) return

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.hostname}:8000/ws/agents/${agentId}/conversations/${conversationId}`
    
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('Chat WebSocket connected')
      setChatWebSocket(ws)
      // Send ping to keep connection alive
      ws.send(JSON.stringify({ type: 'ping' }))
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'new_message') {
          const newMessage: ChatMessage = {
            id: data.message.id,
            conversation_id: data.message.conversation_id,
            role: data.message.role,
            content: data.message.content,
            timestamp: data.message.timestamp,
            status: data.message.status || 'sent',
            metadata: data.message.metadata
          }
          setChatMessages(prev => [...prev, newMessage])
          setIsAgentTyping(false)
        } else if (data.type === 'typing') {
          setIsAgentTyping(data.typing)
        } else if (data.type === 'pong') {
          // Keep alive response
          console.log('WebSocket pong received')
        } else if (data.type === 'error') {
          console.error('Chat error:', data.message)
          setIsAgentTyping(false)
        }
      } catch (error) {
        console.error('Error parsing chat message:', error)
      }
    }
    
    ws.onerror = (error) => {
      console.error('Chat WebSocket error:', error)
    }
    
    ws.onclose = () => {
      console.log('Chat WebSocket disconnected')
      setChatWebSocket(null)
      setIsAgentTyping(false)
    }
  }

  const sendMessage = async () => {
    if (!newMessage.trim() || !agentId || isSendingMessage) return

    // If no conversation exists, create one automatically
    if (!selectedConversation) {
      await createPrimaryConversation()
      if (!selectedConversation) {
        console.error('Failed to create conversation')
        return
      }
    }

    setIsSendingMessage(true)
    
    // Add user message to UI immediately
    const userMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      conversation_id: selectedConversation.id,
      role: 'user',
      content: newMessage,
      timestamp: new Date().toISOString(),
      status: 'sending'
    }
    
    setChatMessages(prev => [...prev, userMessage])
    const messageToSend = newMessage
    setNewMessage('')
    setIsAgentTyping(true)

    try {
      // First, enhance the prompt with RAG context
      let enhancedMessage = messageToSend
      try {
        const ragResponse = await fetch('http://localhost:8000/rag/enhance-prompt', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: messageToSend,
            agent_id: agentId,
            max_context_length: 4000
          })
        })
        
        if (ragResponse.ok) {
          const ragData = await ragResponse.json()
          if (ragData.context_added) {
            enhancedMessage = ragData.enhanced_prompt
            console.log('Enhanced message with RAG context')
          }
        } else {
          console.warn('RAG enhancement failed, using original message')
        }
      } catch (ragError) {
        console.warn('RAG enhancement error, using original message:', ragError)
      }

      // Send the message via WebSocket (enhanced or original)
      if (chatWebSocket && chatWebSocket.readyState === WebSocket.OPEN) {
        chatWebSocket.send(JSON.stringify({
          type: 'message',
          content: enhancedMessage,
          metadata: {
            original_content: messageToSend, // Keep track of original user message
            rag_enhanced: enhancedMessage !== messageToSend
          }
        }))
        
        // Update message status to sent
        setChatMessages(prev => 
          prev.map(msg => 
            msg.id === userMessage.id 
              ? { ...msg, status: 'sent' as const }
              : msg
          )
        )
      } else {
        // WebSocket not connected, fall back to HTTP POST
        const response = await fetch(`http://localhost:8000/agents/${agentId}/conversations/${selectedConversation.id}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            content: enhancedMessage,
            metadata: {
              original_content: messageToSend,
              rag_enhanced: enhancedMessage !== messageToSend
            }
          })
        })

        if (response.ok) {
          // Update message status to sent
          setChatMessages(prev => 
            prev.map(msg => 
              msg.id === userMessage.id 
                ? { ...msg, status: 'sent' as const }
                : msg
            )
          )
        } else {
          // Update message status to error
          setChatMessages(prev => 
            prev.map(msg => 
              msg.id === userMessage.id 
                ? { ...msg, status: 'error' as const }
                : msg
            )
          )
          setIsAgentTyping(false)
        }
      }
    } catch (error) {
      console.error('Error sending message:', error)
      setChatMessages(prev => 
        prev.map(msg => 
          msg.id === userMessage.id 
            ? { ...msg, status: 'error' as const }
            : msg
        )
      )
      setIsAgentTyping(false)
    }
    
    setIsSendingMessage(false)
  }

  // Cleanup chat WebSocket on component unmount
  useEffect(() => {
    return () => {
      if (chatWebSocket) {
        chatWebSocket.close()
      }
    }
  }, [chatWebSocket])

  // Auto-scroll chat to bottom when new messages arrive
  useEffect(() => {
    const chatContainer = document.getElementById('chat-messages-container')
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight
    }
  }, [chatMessages])

  if (loading) {
    return (
      <div style={{minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center'}}>
          <div style={{fontSize: '2rem', marginBottom: '1rem'}}>🤖</div>
          <p style={{color: '#6b7280'}}>Loading agent details...</p>
        </div>
      </div>
    )
  }

  if (!agent) {
    return (
      <div style={{minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center'}}>
          <div style={{fontSize: '2rem', marginBottom: '1rem'}}>❌</div>
          <p style={{color: '#ef4444', marginBottom: '1rem'}}>Agent not found</p>
          <Link to="/agents" style={{
            color: '#2563eb',
            textDecoration: 'none',
            fontSize: '0.875rem'
          }}>
            ← Back to Agents
          </Link>
        </div>
      </div>
    )
  }

  const completedTasks = tasks.filter(t => t.status === 'completed')
  const activeTasks = tasks.filter(t => t.status === 'in_progress')
  // const pendingTasks = tasks.filter(t => t.status === 'pending')

  return (
    <div style={{minHeight: '100vh', backgroundColor: '#f9fafb'}}>
      {/* CSS Animations */}
      <style>
        {`
          @keyframes pulse {
            0%, 100% {
              opacity: 1;
            }
            50% {
              opacity: 0.5;
            }
          }
        `}
      </style>
      {/* Navigation */}
      <nav style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
        <div style={{maxWidth: '80rem', margin: '0 auto', padding: '0 1rem'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '4rem'}}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <Link to="/" style={{display: 'flex', alignItems: 'center', textDecoration: 'none'}}>
                <div style={{
                  width: '2rem', 
                  height: '2rem', 
                  backgroundColor: '#2563eb', 
                  borderRadius: '0.5rem', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  marginRight: '0.75rem'
                }}>
                  <span style={{color: 'white', fontWeight: 'bold'}}>F</span>
                </div>
                <h1 style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#111827'}}>FuzeAgent</h1>
              </Link>
              
              {/* Breadcrumbs */}
              <div style={{display: 'flex', alignItems: 'center', marginLeft: '1.5rem', color: '#6b7280', fontSize: '0.875rem'}}>
                <Link to="/agents" style={{color: '#6b7280', textDecoration: 'none'}}>Agents</Link>
                <span style={{margin: '0 0.5rem'}}>›</span>
                <span style={{color: '#111827'}}>{agent.name}</span>
              </div>
            </div>
            
            <div style={{display: 'flex', gap: '0.5rem'}}>
              <button style={{
                padding: '0.5rem 1rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                backgroundColor: 'white',
                cursor: 'pointer'
              }}>
                Edit Agent
              </button>
              <button style={{
                padding: '0.5rem 1rem',
                backgroundColor: agent.status === 'active' ? '#dc2626' : '#16a34a',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                cursor: 'pointer'
              }}>
                {agent.status === 'active' ? 'Deactivate' : 'Activate'}
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Agent Header */}
      <div style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb'}}>
        <div style={{maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem'}}>
          <div style={{display: 'flex', alignItems: 'center'}}>
            <div style={{
              width: '5rem',
              height: '5rem',
              backgroundColor: '#f3f4f6',
              borderRadius: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '1.5rem'
            }}>
              <span style={{fontSize: '2.5rem'}}>🤖</span>
            </div>
            <div style={{flex: 1}}>
              <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem'}}>
                <h1 style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#111827', margin: 0}}>{agent.name}</h1>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '1rem',
                  backgroundColor: agent.status === 'active' ? '#dcfce7' : '#fef3c7',
                  fontSize: '0.75rem',
                  fontWeight: '500'
                }}>
                  <div style={{
                    width: '0.5rem',
                    height: '0.5rem',
                    borderRadius: '50%',
                    backgroundColor: agent.status === 'active' ? '#22c55e' : '#eab308',
                    marginRight: '0.5rem'
                  }}></div>
                  {agent.status}
                </div>
              </div>
              <p style={{fontSize: '1.125rem', color: '#6b7280', margin: '0 0 0.5rem 0'}}>{agent.role}</p>
              <div style={{display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#6b7280'}}>
                <span>Type: <strong>{agent.type}</strong></span>
                <span>Team: <strong>{agent.team_name || 'Unassigned'}</strong></span>
                <span>Model: <strong>{agent.config.model}</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb'}}>
        <div style={{maxWidth: '80rem', margin: '0 auto', padding: '0 1rem'}}>
          <div style={{display: 'flex', gap: '2rem'}}>
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'settings', label: 'Settings' },
              { id: 'tasks', label: 'Tasks' },
              { id: 'conversations', label: 'Conversations' },
              { id: 'knowledge', label: 'Knowledge' },
              { id: 'container', label: 'Container' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: '1rem 0',
                  border: 'none',
                  backgroundColor: 'transparent',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  color: activeTab === tab.id ? '#2563eb' : '#6b7280',
                  borderBottom: activeTab === tab.id ? '2px solid #2563eb' : '2px solid transparent',
                  cursor: 'pointer'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div style={{maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem'}}>
        {activeTab === 'overview' && (
          <div style={{display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem'}}>
            {/* Main Stats */}
            <div>
              <h3 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem'}}>Performance Overview</h3>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem'}}>
                <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                  <div style={{fontSize: '2rem', color: '#16a34a', textAlign: 'center', marginBottom: '0.5rem'}}>
                    {completedTasks.length}
                  </div>
                  <div style={{fontSize: '0.875rem', color: '#6b7280', textAlign: 'center'}}>Tasks Completed</div>
                </div>
                <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                  <div style={{fontSize: '2rem', color: '#2563eb', textAlign: 'center', marginBottom: '0.5rem'}}>
                    {activeTasks.length}
                  </div>
                  <div style={{fontSize: '0.875rem', color: '#6b7280', textAlign: 'center'}}>Active Tasks</div>
                </div>
                <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                  <div style={{fontSize: '2rem', color: '#ea580c', textAlign: 'center', marginBottom: '0.5rem'}}>
                    {chatMessages.length}
                  </div>
                  <div style={{fontSize: '0.875rem', color: '#6b7280', textAlign: 'center'}}>Messages</div>
                </div>
              </div>

              {/* Recent Activity */}
              <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Recent Activity</h4>
                <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                  {tasks.slice(0, 3).map(task => (
                    <div key={task.id} style={{display: 'flex', alignItems: 'center', padding: '0.75rem', backgroundColor: '#f9fafb', borderRadius: '0.375rem'}}>
                      <div style={{
                        width: '0.5rem',
                        height: '0.5rem',
                        borderRadius: '50%',
                        backgroundColor: task.status === 'completed' ? '#22c55e' : task.status === 'in_progress' ? '#2563eb' : '#6b7280',
                        marginRight: '0.75rem'
                      }}></div>
                      <div style={{flex: 1}}>
                        <div style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827'}}>{task.title}</div>
                        <div style={{fontSize: '0.75rem', color: '#6b7280'}}>
                          {task.status} • {new Date(task.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Side Panel */}
            <div>
              {/* Agent Info */}
              <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb', marginBottom: '1rem'}}>
                <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Agent Information</h4>
                <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem'}}>
                  <div style={{display: 'flex', justifyContent: 'space-between'}}>
                    <span style={{color: '#6b7280'}}>Created:</span>
                    <span>{new Date(agent.created_at).toLocaleDateString()}</span>
                  </div>
                  <div style={{display: 'flex', justifyContent: 'space-between'}}>
                    <span style={{color: '#6b7280'}}>Last Updated:</span>
                    <span>{new Date(agent.updated_at).toLocaleDateString()}</span>
                  </div>
                  <div style={{display: 'flex', justifyContent: 'space-between'}}>
                    <span style={{color: '#6b7280'}}>Temperature:</span>
                    <span>{agent.config.temperature}</span>
                  </div>
                  <div style={{display: 'flex', justifyContent: 'space-between'}}>
                    <span style={{color: '#6b7280'}}>Tools:</span>
                    <span>{agent.config.tools.length}</span>
                  </div>
                </div>
              </div>

              {/* Container Status */}
              {containerInfo ? (
                <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                  <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Container Status</h4>
                  <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem'}}>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{color: '#6b7280'}}>Status:</span>
                      <span style={{
                        color: containerInfo.status === 'running' ? '#16a34a' : 
                              containerInfo.status === 'exited' ? '#dc2626' : '#ea580c'
                      }}>
                        {containerInfo.status}
                      </span>
                    </div>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{color: '#6b7280'}}>CPU:</span>
                      <span>{containerInfo.cpu_usage ? `${containerInfo.cpu_usage.toFixed(1)}%` : 'N/A'}</span>
                    </div>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{color: '#6b7280'}}>Memory:</span>
                      <span>
                        {containerInfo.memory_usage ? 
                          `${Math.round(containerInfo.memory_usage / (1024 * 1024))}MB` : 'N/A'}
                      </span>
                    </div>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{color: '#6b7280'}}>Restarts:</span>
                      <span>{containerInfo.restart_count}</span>
                    </div>
                  </div>

                  <div style={{display: 'flex', gap: '0.5rem', marginTop: '1rem'}}>
                    {containerInfo.status === 'running' ? (
                      <>
                        <button 
                          onClick={handleStopContainer}
                          disabled={containerLoading}
                          style={{
                            flex: 1,
                            padding: '0.5rem',
                            backgroundColor: containerLoading ? '#9ca3af' : '#dc2626',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.375rem',
                            fontSize: '0.75rem',
                            cursor: containerLoading ? 'not-allowed' : 'pointer'
                          }}
                        >
                          {containerLoading ? 'Stopping...' : 'Stop'}
                        </button>
                        <button 
                          onClick={handleRestartContainer}
                          disabled={containerLoading}
                          style={{
                            flex: 1,
                            padding: '0.5rem',
                            backgroundColor: containerLoading ? '#9ca3af' : '#ea580c',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.375rem',
                            fontSize: '0.75rem',
                            cursor: containerLoading ? 'not-allowed' : 'pointer'
                          }}
                        >
                          {containerLoading ? 'Restarting...' : 'Restart'}
                        </button>
                      </>
                    ) : (
                      <button 
                        onClick={handleStartContainer}
                        disabled={containerLoading}
                        style={{
                          flex: 1,
                          padding: '0.5rem',
                          backgroundColor: containerLoading ? '#9ca3af' : '#16a34a',
                          color: 'white',
                          border: 'none',
                          borderRadius: '0.375rem',
                          fontSize: '0.75rem',
                          cursor: containerLoading ? 'not-allowed' : 'pointer'
                        }}
                      >
                        {containerLoading ? 'Starting...' : 'Start'}
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                  <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Container Status</h4>
                  <div style={{textAlign: 'center', padding: '1rem'}}>
                    <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>📦</div>
                    <p style={{color: '#6b7280', marginBottom: '1rem', fontSize: '0.875rem'}}>
                      No container found for this agent
                    </p>
                    <button 
                      onClick={handleCreateContainer}
                      disabled={containerLoading}
                      style={{
                        padding: '0.5rem 1rem',
                        backgroundColor: containerLoading ? '#9ca3af' : '#2563eb',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.375rem',
                        fontSize: '0.875rem',
                        cursor: containerLoading ? 'not-allowed' : 'pointer'
                      }}
                    >
                      {containerLoading ? 'Creating...' : 'Create Container'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div style={{maxWidth: '50rem'}}>
            <div style={{backgroundColor: 'white', padding: '2rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '1.5rem'}}>Agent Configuration</h3>
              
              <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Agent Name
                  </label>
                  <input
                    type="text"
                    value={agent.name}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Role
                  </label>
                  <input
                    type="text"
                    value={agent.role}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Goal
                  </label>
                  <textarea
                    value={agent.config.goal || ''}
                    rows={3}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      resize: 'vertical'
                    }}
                  />
                </div>

                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Backstory
                  </label>
                  <textarea
                    value={agent.config.backstory || ''}
                    rows={3}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      resize: 'vertical'
                    }}
                  />
                </div>

                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem'}}>
                  <div>
                    <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                      Model
                    </label>
                    <select style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem'
                    }}>
                      <option value={agent.config.model}>{agent.config.model}</option>
                      <option value="claude-3-opus-20240229">claude-3-opus-20240229</option>
                      <option value="gpt-4">gpt-4</option>
                    </select>
                  </div>

                  <div>
                    <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                      Temperature
                    </label>
                    <input
                      type="number"
                      value={agent.config.temperature}
                      min="0"
                      max="2"
                      step="0.1"
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        border: '1px solid #d1d5db',
                        borderRadius: '0.375rem',
                        fontSize: '0.875rem'
                      }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Available Tools
                  </label>
                  <div style={{display: 'flex', flexWrap: 'wrap', gap: '0.5rem'}}>
                    {agent.config.tools.map(tool => (
                      <span key={tool} style={{
                        padding: '0.25rem 0.5rem',
                        backgroundColor: '#dbeafe',
                        color: '#1d4ed8',
                        borderRadius: '0.25rem',
                        fontSize: '0.75rem'
                      }}>
                        {tool}
                      </span>
                    ))}
                  </div>
                </div>

                <div style={{display: 'flex', gap: '0.5rem', paddingTop: '1rem'}}>
                  <button style={{
                    padding: '0.75rem 1.5rem',
                    backgroundColor: '#2563eb',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    fontWeight: '500',
                    cursor: 'pointer'
                  }}>
                    Save Changes
                  </button>
                  <button style={{
                    padding: '0.75rem 1.5rem',
                    border: '1px solid #d1d5db',
                    backgroundColor: 'white',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: 'pointer'
                  }}>
                    Reset
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'tasks' && (
          <div>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600'}}>Agent Tasks</h3>
              <button style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                cursor: 'pointer'
              }}>
                + Assign Task
              </button>
            </div>

            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem'}}>
              {tasks.map(task => (
                <div key={task.id} style={{
                  backgroundColor: 'white',
                  padding: '1.5rem',
                  borderRadius: '0.5rem',
                  border: '1px solid #e5e7eb'
                }}>
                  <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem'}}>
                    <h4 style={{fontSize: '1rem', fontWeight: '600', color: '#111827', margin: 0}}>{task.title}</h4>
                    <div style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '0.25rem',
                      fontSize: '0.75rem',
                      fontWeight: '500',
                      backgroundColor: task.status === 'completed' ? '#dcfce7' : task.status === 'in_progress' ? '#dbeafe' : '#f3f4f6',
                      color: task.status === 'completed' ? '#15803d' : task.status === 'in_progress' ? '#1d4ed8' : '#374151'
                    }}>
                      {task.status}
                    </div>
                  </div>
                  <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem', lineHeight: '1.5'}}>
                    {task.description}
                  </p>
                  <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#9ca3af'}}>
                    <span>Priority: {task.priority}</span>
                    <span>{new Date(task.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'conversations' && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            height: '70vh',
            backgroundColor: 'white',
            borderRadius: '0.5rem',
            border: '1px solid #e5e7eb',
            overflow: 'hidden'
          }}>
            {/* Chat Header */}
            <div style={{
              padding: '1rem 1.5rem',
              borderBottom: '1px solid #e5e7eb',
              backgroundColor: '#f9fafb'
            }}>
              <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem'}}>
                <div style={{
                  width: '2.5rem',
                  height: '2.5rem',
                  borderRadius: '50%',
                  backgroundColor: '#2563eb',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontWeight: '600'
                }}>
                  {agent?.name?.charAt(0) || 'A'}
                </div>
                <div>
                  <h3 style={{fontSize: '1.125rem', fontWeight: '600', margin: 0}}>
                    {agent?.name || 'Agent'}
                  </h3>
                  <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>
                    {chatWebSocket ? 'Online' : 'Connecting...'}
                  </p>
                </div>
              </div>
            </div>

            {/* Messages Container */}
            <div 
              id="chat-messages-container"
              style={{
                flex: 1,
                padding: '1rem',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem'
              }}
            >
              {chatMessages.length === 0 ? (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  textAlign: 'center',
                  color: '#6b7280'
                }}>
                  <div style={{fontSize: '3rem', marginBottom: '1rem'}}>💬</div>
                  <h4 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem'}}>
                    Start a conversation
                  </h4>
                  <p style={{fontSize: '0.875rem', maxWidth: '24rem'}}>
                    Send a message to {agent?.name || 'this agent'} to begin your conversation.
                  </p>
                </div>
              ) : (
                chatMessages.map((message) => (
                  <div
                    key={message.id}
                    style={{
                      display: 'flex',
                      justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                      marginBottom: '0.5rem'
                    }}
                  >
                    <div
                      style={{
                        maxWidth: '70%',
                        padding: '0.75rem 1rem',
                        borderRadius: '1rem',
                        backgroundColor: message.role === 'user' ? '#2563eb' : '#f3f4f6',
                        color: message.role === 'user' ? 'white' : '#111827',
                        fontSize: '0.875rem',
                        lineHeight: '1.5',
                        wordWrap: 'break-word'
                      }}
                    >
                      {message.content}
                      <div style={{
                        fontSize: '0.75rem',
                        opacity: 0.7,
                        marginTop: '0.25rem'
                      }}>
                        {new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        {message.status === 'sending' && ' • Sending...'}
                        {message.status === 'error' && ' • Failed'}
                      </div>
                    </div>
                  </div>
                ))
              )}

              {isAgentTyping && (
                <div style={{display: 'flex', justifyContent: 'flex-start', marginBottom: '0.5rem'}}>
                  <div style={{
                    maxWidth: '70%',
                    padding: '0.75rem 1rem',
                    borderRadius: '1rem',
                    backgroundColor: '#f3f4f6',
                    color: '#111827',
                    fontSize: '0.875rem',
                    fontStyle: 'italic'
                  }}>
                    {agent?.name || 'Agent'} is typing...
                  </div>
                </div>
              )}
            </div>

            {/* Message Input */}
            <div style={{
              padding: '1rem 1.5rem',
              borderTop: '1px solid #e5e7eb',
              backgroundColor: '#f9fafb'
            }}>
              <div style={{display: 'flex', gap: '0.75rem', alignItems: 'flex-end'}}>
                <textarea
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      sendMessage()
                    }
                  }}
                  placeholder={`Message ${agent?.name || 'agent'}...`}
                  style={{
                    flex: 1,
                    padding: '0.75rem 1rem',
                    borderRadius: '1.5rem',
                    border: '1px solid #d1d5db',
                    resize: 'none',
                    outline: 'none',
                    fontSize: '0.875rem',
                    minHeight: '2.5rem',
                    maxHeight: '8rem',
                    lineHeight: '1.5'
                  }}
                  rows={1}
                  disabled={isSendingMessage}
                />
                <button
                  onClick={sendMessage}
                  disabled={!newMessage.trim() || isSendingMessage}
                  style={{
                    padding: '0.75rem',
                    backgroundColor: !newMessage.trim() || isSendingMessage ? '#9ca3af' : '#2563eb',
                    color: 'white',
                    border: 'none',
                    borderRadius: '50%',
                    cursor: !newMessage.trim() || isSendingMessage ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '2.5rem',
                    height: '2.5rem'
                  }}
                >
                  {isSendingMessage ? '...' : '↑'}
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'knowledge' && (
          <div>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600'}}>Agent Knowledge Base</h3>
              <button 
                onClick={() => setShowUpload(!showUpload)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  cursor: 'pointer'
                }}
              >
                + Add Knowledge
              </button>
            </div>

            {showUpload && (
              <div style={{backgroundColor: '#f9fafb', border: '1px dashed #d1d5db', borderRadius: '0.5rem', padding: '2rem', marginBottom: '1.5rem', textAlign: 'center'}}>
                <div style={{fontSize: '2rem', marginBottom: '1rem'}}>📁</div>
                <h4 style={{fontSize: '1rem', fontWeight: '500', marginBottom: '0.5rem'}}>Upload Agent Documents or Add Links</h4>
                <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem'}}>
                  Add documents, manuals, and resources specific to this agent
                </p>
                <div style={{display: 'flex', gap: '0.5rem', justifyContent: 'center'}}>
                  <input type="file" id="agent-file-upload" style={{display: 'none'}} multiple onChange={handleFileUpload} accept=".pdf,.docx,.doc,.txt,.md,.html" />
                  <label htmlFor="agent-file-upload" style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: 'white',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: 'pointer'
                  }}>
                    Choose Files
                  </label>
                  <button 
                    onClick={handleUrlUpload}
                    style={{
                      padding: '0.5rem 1rem',
                      backgroundColor: 'white',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      cursor: 'pointer'
                    }}
                  >
                    Add URL
                  </button>
                </div>
              </div>
            )}

            {/* Knowledge Documents */}
            {uploading && (
              <div style={{textAlign: 'center', padding: '2rem'}}>
                <div style={{fontSize: '1.5rem', marginBottom: '1rem'}}>⏳</div>
                <p>Uploading documents...</p>
              </div>
            )}

            <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
              {knowledgeDocs.map((doc) => (
                <div key={doc.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '1rem',
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '0.5rem',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s'
                }}
                onClick={() => handleDocumentClick(doc)}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}>
                  <div style={{display: 'flex', alignItems: 'center'}}>
                    <div style={{
                      width: '2.5rem',
                      height: '2.5rem',
                      backgroundColor: doc.type === 'document' ? '#dbeafe' : doc.type === 'link' ? '#dcfce7' : '#f3e8ff',
                      borderRadius: '0.375rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginRight: '0.75rem'
                    }}>
                      <span style={{fontSize: '1.25rem'}}>
                        {doc.type === 'document' ? '📄' : doc.type === 'link' ? '🔗' : '📝'}
                      </span>
                    </div>
                    <div>
                      <h4 style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', margin: '0 0 0.25rem 0'}}>
                        {doc.title}
                      </h4>
                      <div style={{fontSize: '0.75rem', color: '#6b7280'}}>
                        {doc.size && `${formatFileSize(doc.size)} • `}
                        Added {new Date(doc.upload_date).toLocaleDateString()}
                        {doc.tags.length > 0 && (
                          <span style={{marginLeft: '0.5rem'}}>
                            {doc.tags.map(tag => (
                              <span key={tag} style={{
                                marginRight: '0.25rem',
                                padding: '0.125rem 0.25rem',
                                borderRadius: '0.25rem',
                                fontSize: '0.625rem',
                                backgroundColor: '#e5e7eb',
                                color: '#374151'
                              }}>
                                {tag}
                              </span>
                            ))}
                          </span>
                        )}
                        <span style={{
                          marginLeft: '0.5rem',
                          padding: '0.125rem 0.375rem',
                          borderRadius: '0.25rem',
                          fontSize: '0.625rem',
                          fontWeight: '500',
                          backgroundColor: doc.status === 'active' ? '#dcfce7' : doc.status === 'processing' ? '#fef3c7' : '#fee2e2',
                          color: doc.status === 'active' ? '#15803d' : doc.status === 'processing' ? '#92400e' : '#dc2626'
                        }}>
                          {doc.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div style={{display: 'flex', gap: '0.5rem'}}>
                    <button style={{
                      padding: '0.375rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.25rem',
                      backgroundColor: 'white',
                      cursor: 'pointer',
                      fontSize: '0.75rem'
                    }}>
                      ⚙️
                    </button>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDocumentDelete(doc.id)
                      }}
                      style={{
                        padding: '0.375rem',
                        border: '1px solid #dc2626',
                        borderRadius: '0.25rem',
                        backgroundColor: 'white',
                        color: '#dc2626',
                        cursor: 'pointer',
                        fontSize: '0.75rem'
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
              
              {knowledgeDocs.length === 0 && !uploading && (
                <div style={{textAlign: 'center', padding: '3rem', backgroundColor: 'white', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                  <div style={{fontSize: '3rem', marginBottom: '1rem'}}>📚</div>
                  <h4 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem', color: '#111827'}}>No Knowledge Documents</h4>
                  <p style={{color: '#6b7280', marginBottom: '1.5rem'}}>
                    Upload documents, manuals, or add URLs to build this agent's knowledge base.
                  </p>
                  <button 
                    onClick={() => setShowUpload(true)}
                    style={{
                      padding: '0.75rem 1.5rem',
                      backgroundColor: '#2563eb',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      cursor: 'pointer'
                    }}
                  >
                    Add Your First Document
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'container' && (
          <div>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600'}}>Container Management</h3>
              <div style={{display: 'flex', gap: '0.5rem'}}>
                {containerInfo ? (
                  <>
                    <button 
                      onClick={() => handleLoadContainerLogs(true)}
                      style={{
                        padding: '0.5rem 1rem',
                        border: '1px solid #d1d5db',
                        backgroundColor: 'white',
                        borderRadius: '0.375rem',
                        fontSize: '0.875rem',
                        cursor: 'pointer'
                      }}
                    >
                      View Live Logs
                    </button>
                    <button 
                      onClick={() => loadContainerInfo()}
                      style={{
                        padding: '0.5rem 1rem',
                        border: '1px solid #d1d5db',
                        backgroundColor: 'white',
                        borderRadius: '0.375rem',
                        fontSize: '0.875rem',
                        cursor: 'pointer'
                      }}
                    >
                      Refresh
                    </button>
                  </>
                ) : (
                  <button 
                    onClick={handleCreateContainer}
                    disabled={containerLoading}
                    style={{
                      padding: '0.5rem 1rem',
                      backgroundColor: containerLoading ? '#9ca3af' : '#2563eb',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      cursor: containerLoading ? 'not-allowed' : 'pointer'
                    }}
                  >
                    {containerLoading ? 'Creating...' : 'Create Container'}
                  </button>
                )}
              </div>
            </div>
            
            {containerInfo ? (
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem'}}>
                <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                  <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Container Details</h4>
                  <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem'}}>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{color: '#6b7280'}}>Container ID:</span>
                      <span style={{fontFamily: 'monospace', fontSize: '0.75rem'}}>{containerInfo.id}</span>
                    </div>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{color: '#6b7280'}}>Name:</span>
                      <span>{containerInfo.name}</span>
                    </div>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{color: '#6b7280'}}>Image:</span>
                      <span>{containerInfo.image}</span>
                    </div>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{color: '#6b7280'}}>Status:</span>
                      <span style={{
                        color: containerInfo.status === 'running' ? '#16a34a' : 
                              containerInfo.status === 'exited' ? '#dc2626' : '#ea580c'
                      }}>
                        {containerInfo.status}
                      </span>
                    </div>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{color: '#6b7280'}}>Created:</span>
                      <span>{new Date(containerInfo.created).toLocaleString()}</span>
                    </div>
                    {containerInfo.started && (
                      <div style={{display: 'flex', justifyContent: 'space-between'}}>
                        <span style={{color: '#6b7280'}}>Started:</span>
                        <span>{new Date(containerInfo.started).toLocaleString()}</span>
                      </div>
                    )}
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{color: '#6b7280'}}>Restart Count:</span>
                      <span>{containerInfo.restart_count}</span>
                    </div>
                    {containerInfo.health && (
                      <div style={{display: 'flex', justifyContent: 'space-between'}}>
                        <span style={{color: '#6b7280'}}>Health:</span>
                        <span style={{
                          color: containerInfo.health === 'healthy' ? '#16a34a' : 
                                containerInfo.health === 'unhealthy' ? '#dc2626' : '#ea580c'
                        }}>
                          {containerInfo.health}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Port Mappings */}
                  {Object.keys(containerInfo.ports).length > 0 && (
                    <div style={{marginTop: '1.5rem'}}>
                      <h5 style={{fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem'}}>Port Mappings</h5>
                      <div style={{fontSize: '0.75rem', fontFamily: 'monospace', color: '#6b7280'}}>
                        {Object.entries(containerInfo.ports).map(([containerPort, hostPort]) => (
                          <div key={containerPort}>
                            {hostPort} → {containerPort}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                  <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Resource Usage & Controls</h4>
                  
                  {/* Resource Usage */}
                  <div style={{display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem'}}>
                    <div>
                      <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem'}}>
                        <span style={{fontSize: '0.875rem', color: '#6b7280'}}>CPU Usage</span>
                        <span style={{fontSize: '0.875rem'}}>
                          {containerInfo.cpu_usage ? `${containerInfo.cpu_usage.toFixed(1)}%` : 'N/A'}
                        </span>
                      </div>
                      <div style={{width: '100%', height: '0.5rem', backgroundColor: '#f3f4f6', borderRadius: '0.25rem', overflow: 'hidden'}}>
                        <div style={{
                          width: containerInfo.cpu_usage ? `${containerInfo.cpu_usage}%` : '0%',
                          height: '100%',
                          backgroundColor: '#3b82f6'
                        }}></div>
                      </div>
                    </div>
                    
                    <div>
                      <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem'}}>
                        <span style={{fontSize: '0.875rem', color: '#6b7280'}}>Memory Usage</span>
                        <span style={{fontSize: '0.875rem'}}>
                          {containerInfo.memory_usage && containerInfo.memory_limit ? 
                            `${Math.round(containerInfo.memory_usage / (1024 * 1024))}MB / ${Math.round(containerInfo.memory_limit / (1024 * 1024))}MB` :
                            containerInfo.memory_usage ? 
                              `${Math.round(containerInfo.memory_usage / (1024 * 1024))}MB` : 'N/A'
                          }
                        </span>
                      </div>
                      <div style={{width: '100%', height: '0.5rem', backgroundColor: '#f3f4f6', borderRadius: '0.25rem', overflow: 'hidden'}}>
                        <div style={{
                          width: containerInfo.memory_usage && containerInfo.memory_limit ? 
                            `${(containerInfo.memory_usage / containerInfo.memory_limit) * 100}%` : '0%',
                          height: '100%',
                          backgroundColor: '#10b981'
                        }}></div>
                      </div>
                    </div>
                  </div>

                  {/* Container Controls */}
                  <div style={{display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
                    {containerInfo.status === 'running' ? (
                      <>
                        <button 
                          onClick={handleStopContainer}
                          disabled={containerLoading}
                          style={{
                            padding: '0.75rem',
                            backgroundColor: containerLoading ? '#9ca3af' : '#dc2626',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.375rem',
                            fontSize: '0.875rem',
                            cursor: containerLoading ? 'not-allowed' : 'pointer'
                          }}
                        >
                          {containerLoading ? 'Stopping...' : 'Stop Container'}
                        </button>
                        <button 
                          onClick={handleRestartContainer}
                          disabled={containerLoading}
                          style={{
                            padding: '0.75rem',
                            backgroundColor: containerLoading ? '#9ca3af' : '#ea580c',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.375rem',
                            fontSize: '0.875rem',
                            cursor: containerLoading ? 'not-allowed' : 'pointer'
                          }}
                        >
                          {containerLoading ? 'Restarting...' : 'Restart Container'}
                        </button>
                      </>
                    ) : (
                      <button 
                        onClick={handleStartContainer}
                        disabled={containerLoading}
                        style={{
                          padding: '0.75rem',
                          backgroundColor: containerLoading ? '#9ca3af' : '#16a34a',
                          color: 'white',
                          border: 'none',
                          borderRadius: '0.375rem',
                          fontSize: '0.875rem',
                          cursor: containerLoading ? 'not-allowed' : 'pointer'
                        }}
                      >
                        {containerLoading ? 'Starting...' : 'Start Container'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{backgroundColor: 'white', padding: '3rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb', textAlign: 'center'}}>
                <div style={{fontSize: '3rem', marginBottom: '1rem'}}>📦</div>
                <h4 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem', color: '#111827'}}>No Container Found</h4>
                <p style={{color: '#6b7280', marginBottom: '1.5rem'}}>
                  This agent doesn't have a container yet. Create one to enable code execution and advanced capabilities.
                </p>
                <button 
                  onClick={handleCreateContainer}
                  disabled={containerLoading}
                  style={{
                    padding: '0.75rem 1.5rem',
                    backgroundColor: containerLoading ? '#9ca3af' : '#2563eb',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: containerLoading ? 'not-allowed' : 'pointer'
                  }}
                >
                  {containerLoading ? 'Creating Container...' : 'Create Container'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Container Logs Modal */}
      {showContainerLogs && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.75rem',
            padding: '2rem',
            maxWidth: '90vw',
            maxHeight: '90vh',
            overflow: 'auto',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            minWidth: '800px'
          }}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
              <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
                <h3 style={{fontSize: '1.25rem', fontWeight: '600', margin: 0}}>
                  Container Logs
                </h3>
                {isLiveLogsActive && (
                  <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                    <div style={{
                      width: '0.5rem',
                      height: '0.5rem',
                      borderRadius: '50%',
                      backgroundColor: '#22c55e',
                      animation: 'pulse 2s infinite'
                    }}></div>
                    <span style={{fontSize: '0.875rem', color: '#22c55e', fontWeight: '500'}}>LIVE</span>
                  </div>
                )}
              </div>
              
              <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                <label style={{display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: '#6b7280'}}>
                  <input
                    type="checkbox"
                    checked={autoScroll}
                    onChange={(e) => setAutoScroll(e.target.checked)}
                    style={{margin: 0}}
                  />
                  Auto-scroll
                </label>
                
                <button 
                  onClick={() => {
                    setShowContainerLogs(false)
                    setContainerLogs([])
                    stopLiveLogs()
                  }}
                  style={{
                    padding: '0.5rem',
                    border: 'none',
                    borderRadius: '0.375rem',
                    backgroundColor: '#f3f4f6',
                    cursor: 'pointer',
                    fontSize: '1.25rem'
                  }}
                >
                  ✕
                </button>
              </div>
            </div>
            
            <div 
              id="log-container"
              style={{
                backgroundColor: '#000000',
                color: '#00ff00',
                borderRadius: '0.5rem',
                padding: '1rem',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                lineHeight: '1.5',
                maxHeight: '70vh',
                overflow: 'auto',
                border: '1px solid #374151',
                position: 'relative'
              }}
            >
              {containerLogs.length > 0 ? (
                containerLogs.map((log, index) => (
                  <div key={index} style={{marginBottom: '0.25rem', whiteSpace: 'pre-wrap'}}>
                    {log}
                  </div>
                ))
              ) : (
                <div style={{color: '#6b7280', textAlign: 'center', padding: '2rem'}}>
                  {isLiveLogsActive ? 'Waiting for logs...' : 'No logs available. Click "Load Historical Logs" or "Start Live Logs".'}
                </div>
              )}
              
              {/* Log count indicator */}
              {containerLogs.length > 0 && (
                <div style={{
                  position: 'sticky',
                  bottom: 0,
                  right: 0,
                  display: 'flex',
                  justifyContent: 'flex-end',
                  marginTop: '0.5rem'
                }}>
                  <div style={{
                    backgroundColor: '#374151',
                    color: '#d1d5db',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '0.25rem',
                    fontSize: '0.75rem'
                  }}>
                    {containerLogs.length} lines
                  </div>
                </div>
              )}
            </div>
            
            <div style={{marginTop: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem'}}>
              <button 
                onClick={() => handleLoadContainerLogs(false)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  cursor: 'pointer'
                }}
              >
                Load Historical Logs
              </button>
              
              {!isLiveLogsActive ? (
                <button 
                  onClick={startLiveLogs}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#16a34a',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: 'pointer'
                  }}
                >
                  Start Live Logs
                </button>
              ) : (
                <button 
                  onClick={stopLiveLogs}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#dc2626',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: 'pointer'
                  }}
                >
                  Stop Live Logs
                </button>
              )}
              
              <button 
                onClick={clearLogs}
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  backgroundColor: 'white',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  cursor: 'pointer'
                }}
              >
                Clear Logs
              </button>
              
              <button 
                onClick={() => {
                  const logContainer = document.getElementById('log-container')
                  if (logContainer) {
                    logContainer.scrollTop = logContainer.scrollHeight
                  }
                }}
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  backgroundColor: 'white',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  cursor: 'pointer'
                }}
              >
                Scroll to Bottom
              </button>
              
              <button 
                onClick={() => {
                  const logContent = containerLogs.join('\n')
                  const blob = new Blob([logContent], { type: 'text/plain' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `agent-${agentId}-container-logs-${new Date().toISOString()}.txt`
                  document.body.appendChild(a)
                  a.click()
                  document.body.removeChild(a)
                  URL.revokeObjectURL(url)
                }}
                disabled={containerLogs.length === 0}
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  backgroundColor: containerLogs.length === 0 ? '#f9fafb' : 'white',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  cursor: containerLogs.length === 0 ? 'not-allowed' : 'pointer',
                  color: containerLogs.length === 0 ? '#9ca3af' : 'inherit'
                }}
              >
                Download Logs
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Old chat modal code removed - now using persistent chat interface */}
      {false && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.75rem',
            width: '90vw',
            maxWidth: '800px',
            height: '80vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
          }}>
            {/* Chat Header */}
            <div style={{
              padding: '1.5rem',
              borderBottom: '1px solid #e5e7eb',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <h3 style={{fontSize: '1.25rem', fontWeight: '600', margin: 0}}>
                  {selectedConversation?.title || 'Conversation'}
                </h3>
                <div style={{fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem'}}>
                  Chat with {agent?.name} • {chatMessages.length} messages
                  {chatWebSocket && (
                    <span style={{marginLeft: '0.5rem', color: '#22c55e'}}>
                      • Connected
                    </span>
                  )}
                </div>
              </div>
              <button 
                onClick={() => {}}
                style={{
                  padding: '0.5rem',
                  border: 'none',
                  borderRadius: '0.375rem',
                  backgroundColor: '#f3f4f6',
                  cursor: 'pointer',
                  fontSize: '1.25rem'
                }}
              >
                ✕
              </button>
            </div>

            {/* Chat Messages */}
            <div 
              id="chat-messages-container"
              style={{
                flex: 1,
                padding: '1rem',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem'
              }}
            >
              {chatMessages.map((message) => (
                <div key={message.id} style={{
                  display: 'flex',
                  justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start'
                }}>
                  <div style={{
                    maxWidth: '70%',
                    padding: '0.75rem 1rem',
                    borderRadius: '1rem',
                    backgroundColor: message.role === 'user' ? '#2563eb' : '#f3f4f6',
                    color: message.role === 'user' ? 'white' : '#111827',
                    position: 'relative'
                  }}>
                    <div style={{whiteSpace: 'pre-wrap', lineHeight: '1.5'}}>
                      {message.content}
                    </div>
                    
                    <div style={{
                      fontSize: '0.75rem',
                      marginTop: '0.5rem',
                      opacity: 0.7,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <span>
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                      
                      {message.role === 'user' && (
                        <span style={{
                          color: message.status === 'sent' ? '#22c55e' : 
                                message.status === 'error' ? '#dc2626' : '#ea580c'
                        }}>
                          {message.status === 'sent' ? '✓' : 
                           message.status === 'error' ? '✗' : '⏳'}
                        </span>
                      )}
                      
                      {message.metadata?.tokens_used && (
                        <span style={{fontSize: '0.6875rem'}}>
                          {message.metadata.tokens_used} tokens
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {/* Typing Indicator */}
              {isAgentTyping && (
                <div style={{display: 'flex', justifyContent: 'flex-start'}}>
                  <div style={{
                    maxWidth: '70%',
                    padding: '0.75rem 1rem',
                    borderRadius: '1rem',
                    backgroundColor: '#f3f4f6',
                    color: '#6b7280'
                  }}>
                    <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                      <div style={{
                        display: 'flex',
                        gap: '0.25rem'
                      }}>
                        <div style={{
                          width: '0.5rem',
                          height: '0.5rem',
                          borderRadius: '50%',
                          backgroundColor: '#9ca3af',
                          animation: 'pulse 1.5s ease-in-out infinite'
                        }}></div>
                        <div style={{
                          width: '0.5rem',
                          height: '0.5rem',
                          borderRadius: '50%',
                          backgroundColor: '#9ca3af',
                          animation: 'pulse 1.5s ease-in-out infinite 0.2s'
                        }}></div>
                        <div style={{
                          width: '0.5rem',
                          height: '0.5rem',
                          borderRadius: '50%',
                          backgroundColor: '#9ca3af',
                          animation: 'pulse 1.5s ease-in-out infinite 0.4s'
                        }}></div>
                      </div>
                      <span style={{fontSize: '0.875rem'}}>
                        {agent?.name} is typing...
                      </span>
                    </div>
                  </div>
                </div>
              )}
              
              {chatMessages.length === 0 && !isAgentTyping && (
                <div style={{
                  textAlign: 'center',
                  color: '#6b7280',
                  padding: '2rem',
                  fontSize: '0.875rem'
                }}>
                  Start a conversation with {agent?.name}!
                </div>
              )}
            </div>

            {/* Chat Input */}
            <div style={{
              padding: '1rem 1.5rem',
              borderTop: '1px solid #e5e7eb',
              display: 'flex',
              gap: '0.75rem',
              alignItems: 'flex-end'
            }}>
              <textarea
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    sendMessage()
                  }
                }}
                placeholder="Type your message here... (Shift+Enter for new line)"
                disabled={isSendingMessage}
                style={{
                  flex: 1,
                  minHeight: '2.5rem',
                  maxHeight: '8rem',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  resize: 'none',
                  outline: 'none',
                  backgroundColor: isSendingMessage ? '#f9fafb' : 'white'
                }}
              />
              <button
                onClick={sendMessage}
                disabled={!newMessage.trim() || isSendingMessage}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: !newMessage.trim() || isSendingMessage ? '#9ca3af' : '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  cursor: !newMessage.trim() || isSendingMessage ? 'not-allowed' : 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                {isSendingMessage ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Document Viewer Modal */}
      {showDocumentViewer && selectedDocument && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.75rem',
            padding: '2rem',
            maxWidth: '80vw',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
          }}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600', margin: 0}}>
                {selectedDocument.title}
              </h3>
              <button 
                onClick={() => {
                  setShowDocumentViewer(false)
                  setSelectedDocument(null)
                }}
                style={{
                  padding: '0.5rem',
                  border: 'none',
                  borderRadius: '0.375rem',
                  backgroundColor: '#f3f4f6',
                  cursor: 'pointer',
                  fontSize: '1.25rem'
                }}
              >
                ✕
              </button>
            </div>
            
            <div style={{
              backgroundColor: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: '0.5rem',
              padding: '1rem',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              lineHeight: '1.5',
              whiteSpace: 'pre-wrap',
              maxHeight: '60vh',
              overflow: 'auto'
            }}>
              {documentContent || 'Loading document content...'}
            </div>
            
            <div style={{marginTop: '1.5rem', fontSize: '0.875rem', color: '#6b7280'}}>
              <p><strong>Type:</strong> {selectedDocument.type}</p>
              <p><strong>Size:</strong> {formatFileSize(selectedDocument.size)}</p>
              <p><strong>Uploaded:</strong> {new Date(selectedDocument.upload_date).toLocaleDateString()}</p>
              {selectedDocument.word_count && (
                <p><strong>Word Count:</strong> {selectedDocument.word_count.toLocaleString()}</p>
              )}
              {selectedDocument.tags.length > 0 && (
                <p><strong>Tags:</strong> {selectedDocument.tags.join(', ')}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}