/* @jsxImportSource react */
import React, { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import type { Agent, Task, Conversation, ChatMessage, ContainerInfo, KnowledgeDocument } from './AgentDetailsPage/types'
import { TopNav } from './AgentDetailsPage/TopNav'
import { Header } from './AgentDetailsPage/Header'
import { Tabs } from './AgentDetailsPage/Tabs'
import { OverviewTab } from './AgentDetailsPage/OverviewTab'
import { SettingsTab } from './AgentDetailsPage/SettingsTab'
import { TasksTab } from './AgentDetailsPage/TasksTab'
import { ConversationsTab } from './AgentDetailsPage/ConversationsTab'
import { KnowledgeTab } from './AgentDetailsPage/KnowledgeTab'
import { ContainerTab } from './AgentDetailsPage/ContainerTab'
import { AssignTaskModal } from './AgentDetailsPage/AssignTaskModal'
import { DocumentViewer } from './AgentDetailsPage/DocumentViewer'
import { InlineCss } from './AgentDetailsPage/InlineCss'
import { useApiService } from '../../hooks/useApiService'



export function AgentDetailsPage(): React.ReactElement {
  const { agentId } = useParams<{ agentId: string }>()
  const apiService = useApiService()
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
  const [conversationsList, setConversationsList] = useState<Conversation[]>([])
  const [loadingConversations, setLoadingConversations] = useState(false)
  const [creatingConversation, setCreatingConversation] = useState(false)
  const [updatingStatusId, setUpdatingStatusId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [showAssignTask, setShowAssignTask] = useState(false)
  const [teamTasks, setTeamTasks] = useState<Task[]>([])
  const [selectedTeamTaskId, setSelectedTeamTaskId] = useState('')
  const [assigningTask, setAssigningTask] = useState(false)
  const [assignTaskError, setAssignTaskError] = useState<string | null>(null)

  const hasInitializedRef = useRef(false)
  const wsConnectingRef = useRef(false)
  const creatingConversationRef = useRef(false)

  useEffect(() => {
    if (!agentId) return
    if (hasInitializedRef.current) return
    hasInitializedRef.current = true

    // Load agent details
    const loadAgent = async () => {
      if (!agentId) return
      if (!currentOrganization) return // Wait for organization context
      
      try {
        const response = await apiService.getAgent(agentId)
        if (response.ok) {
          setAgent(response.data)
        } else {
          console.error('Failed to load agent:', response.status)
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
        }
      } catch (err) {
        console.error('Failed to load agent:', err)
        // Mock data for demo (same as above)
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
      } finally {
        setLoading(false)
      }
    }
    
    loadAgent()

    // Load agent tasks
    const loadAgentTasks = async () => {
      if (!agentId) return
      if (!currentOrganization) return // Wait for organization context
      
      try {
        const response = await apiService.getAgentTasks(agentId)
        if (response.ok) {
          setTasks(Array.isArray(response.data) ? response.data : [])
        } else {
          console.error('Failed to load agent tasks:', response.status)
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
        }
      } catch (error) {
        console.error('Failed to load agent tasks:', error)
        // Same mock data as above
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
      }
    }
    
    loadAgentTasks()

    // Load agent's primary conversation from API
    if (agentId) {
      loadAgentPrimaryConversation()
    }

    // Load container info
    if (agentId) {
      loadContainerInfo()
      loadKnowledgeDocuments()
    }
  }, [agentId, currentOrganization])

  const handleAssignTask = async () => {
    if (!agentId) return
    if (!selectedTeamTaskId) {
      setAssignTaskError('Please select a team task')
      return
    }
    setAssigningTask(true)
    setAssignTaskError(null)
    try {
      const res = await apiService.assignTask(selectedTeamTaskId, agentId)
      if (res.ok) {
        setTasks((prev: Task[]) => [res.data, ...prev.filter((t: Task) => t.id !== res.data.id)])
        setShowAssignTask(false)
        setSelectedTeamTaskId('')
      } else {
        setAssignTaskError(`Failed to assign task: HTTP ${res.status}`)
      }
    } catch {
      setAssignTaskError('Error assigning task')
    } finally {
      setAssigningTask(false)
    }
  }

  // Load knowledge documents for the agent
  const loadKnowledgeDocuments = async () => {
    if (!agentId) return
    if (!currentOrganization) return // Wait for organization context
    
    try {
      const response = await apiService.getAgentKnowledge(agentId)
      if (response.ok) {
        setKnowledgeDocs(response.data)
      } else {
        console.error('Failed to load agent documents:', response.status)
      }
    } catch (error) {
      console.error('Error loading agent documents:', error)
    }
  }

  // Load agent's primary conversation and messages
  const loadAgentPrimaryConversation = async () => {
    if (!agentId) return
    
    try {
      const response = await fetch(`/agents/${agentId}/conversations`)
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
          // Create a default conversation immediately to persist state
          const created = await fetch(`/agents/${agentId}/conversations`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: `Conversation with ${agent?.name || 'Agent'}` }) })
          if (created.ok) {
            const c = await created.json()
            setSelectedConversation(c)
            await loadConversationMessages(c.id)
            startChatWebSocket(c.id)
          }
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
    if (creatingConversationRef.current) return
    creatingConversationRef.current = true
    
    try {
      const response = await fetch(`/agents/${agentId}/conversations`, {
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
        
        // created
      } else {
        console.error('Failed to create primary conversation')
      }
    } catch (error) {
      console.error('Error creating primary conversation:', error)
    }
    creatingConversationRef.current = false
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files: FileList | null = event.target.files
    if (!files || files.length === 0 || !agentId) return

    setUploading(true)
    
    for (const file of Array.from(files as FileList)) {
      try {
        const formData = new FormData()
        formData.append('file', file as File)
        formData.append('title', (file as File).name)
        
        const response = await fetch(`/knowledge/agents/${agentId}/documents`, {
          method: 'POST',
          body: formData
        })
        
        if (response.ok) {
          console.log(`Uploaded ${(file as File).name} successfully`)
        } else {
          console.error(`Failed to upload ${(file as File).name}`)
        }
      } catch (error) {
        console.error(`Error uploading ${(file as File).name}:`, error)
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
      const response = await fetch(`/knowledge/agents/${agentId}/url`, {
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
      const response = await fetch(`/knowledge/agents/${agentId}/documents/${doc.id}/content`)
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
      const response = await fetch(`/knowledge/agents/${agentId}/documents/${docId}`, {
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
      const response = await fetch(`/agents/${agentId}/container/status`)
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
      const response = await fetch(`/agents/${agentId}/container/create`, {
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
      const response = await fetch(`/agents/${agentId}/container/start`, {
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
      const response = await fetch(`/agents/${agentId}/container/stop`, {
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
      const response = await fetch(`/agents/${agentId}/container/restart`, {
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
      const response = await fetch(`/agents/${agentId}/container/logs`)
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
          setContainerLogs((prevLogs: string[]) => [...prevLogs, logEntry])
        }
      } catch (error) {
        // If it's not JSON, treat as plain text log
        const logEntry = `[${new Date().toISOString()}] stdout: ${event.data}`
        setContainerLogs((prevLogs: string[]) => [...prevLogs, logEntry])
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
      const response = await fetch(`/agents/${agentId}/conversations/${conversationId}/messages`)
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
    if (!agentId) return
    if (chatWebSocket || wsConnectingRef.current) return
    wsConnectingRef.current = true

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.hostname}:8000/ws/agents/${agentId}/conversations/${conversationId}`
    
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      // connected
      setChatWebSocket(ws)
      // Send ping to keep connection alive
      ws.send(JSON.stringify({ type: 'ping' }))
      wsConnectingRef.current = false
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
          setChatMessages((prev: ChatMessage[]) => prev.some((m: ChatMessage) => m.id === newMessage.id) ? prev : [...prev, newMessage])
          setIsAgentTyping(false)
        } else if (data.type === 'typing') {
          setIsAgentTyping(data.typing)
        } else if (data.type === 'pong') {
          // keep-alive
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
      setChatWebSocket(null)
      setIsAgentTyping(false)
      wsConnectingRef.current = false
    }
  }

  const loadConversations = async () => {
    if (!agentId) return
    setLoadingConversations(true)
    try {
      const response = await fetch(`/agents/${agentId}/conversations`)
      if (response.ok) {
        const list = await response.json()
        setConversationsList(Array.isArray(list) ? list : [])
        // Auto-select a conversation if none selected
        if (!selectedConversation && Array.isArray(list) && list.length > 0) {
          const first = list[0]
          setSelectedConversation(first)
          // Optimistically load any nested messages if the server returned them
          if ((first as any)?.messages && Array.isArray((first as any).messages)) {
            setChatMessages((first as any).messages)
          }
          await loadConversationMessages(first.id)
          startChatWebSocket(first.id)
        }
      }
    } finally {
      setLoadingConversations(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'conversations') {
      loadConversations()
    }
  }, [activeTab, agentId])

  const handleNewConversation = async () => {
    if (!agentId || creatingConversation) return
    setCreatingConversation(true)
    try {
      const title = `Conversation ${new Date().toLocaleString()}`
      const response = await fetch(`/agents/${agentId}/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title })
      })
      if (response.ok) {
        const convo = await response.json()
        setConversationsList((prev: any[]) => [convo, ...prev])
        // Switch to new conversation
        if (chatWebSocket) {
          try { chatWebSocket.close() } catch {}
          setChatWebSocket(null)
        }
        setSelectedConversation(convo)
        setChatMessages([])
        startChatWebSocket(convo.id)
      }
    } finally {
      setCreatingConversation(false)
    }
  }

  const handleSelectConversation = async (convo: any) => {
    if (!agentId) return
    if (selectedConversation?.id === convo.id) return
    if (chatWebSocket) {
      try { chatWebSocket.close() } catch {}
      setChatWebSocket(null)
    }
    setSelectedConversation(convo)
    // Seed from nested messages if present, then refresh from server
    if ((convo as any)?.messages && Array.isArray((convo as any).messages)) {
      setChatMessages((convo as any).messages)
    } else {
      setChatMessages([])
    }
    await loadConversationMessages(convo.id)
    startChatWebSocket(convo.id)
  }

  const handleConversationStatus = async (convoId: string, status: 'running' | 'paused' | 'stopped') => {
    setUpdatingStatusId(convoId)
    try {
      const res = await fetch(`/conversations/${convoId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      })
      if (res.ok) {
        const updated = await res.json()
        setConversationsList((prev: any[]) => prev.map((c: any) => c.id === updated.id ? updated : c))
        if (selectedConversation?.id === updated.id) {
          setSelectedConversation(updated)
        }
      }
    } finally {
      setUpdatingStatusId(null)
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
    
    setChatMessages((prev: any) => (Array.isArray(prev) ? [...prev, userMessage] : [userMessage]))
    const messageToSend = newMessage
    setNewMessage('')
    setIsAgentTyping(true)

    try {
      // First, enhance the prompt with RAG context
      let enhancedMessage = messageToSend
      try {
        const ragResponse = await fetch('/rag/enhance-prompt', {
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
        setChatMessages((prev: any) => {
          const base: ChatMessage[] = Array.isArray(prev) ? prev : []
          return base.map((msg) => msg.id === userMessage.id ? { ...msg, status: 'sent' as const } : msg)
        })
      } else {
        // WebSocket not connected, fall back to HTTP POST
        const response = await fetch(`/agents/${agentId}/conversations/${selectedConversation.id}/messages`, {
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
          setChatMessages((prev: ChatMessage[]) => 
            prev.map((msg: ChatMessage) => 
              msg.id === userMessage.id 
                ? { ...msg, status: 'sent' as const }
                : msg
            )
          )
        } else {
          // Update message status to error
          setChatMessages((prev: ChatMessage[]) => 
            prev.map((msg: ChatMessage) => 
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
      setChatMessages((prev: ChatMessage[]) => 
        prev.map((msg: ChatMessage) => 
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

  const completedTasks = tasks.filter((t: Task) => t.status === 'completed')
  const activeTasks = tasks.filter((t: Task) => t.status === 'in_progress')
  // const pendingTasks = tasks.filter(t => t.status === 'pending')

  return (
    <div style={{minHeight: '100vh', backgroundColor: '#f9fafb'}}>
      <InlineCss />
      <TopNav agent={agent} />

      <Header agent={agent} />

      <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Tab Content */}
      <div style={{maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem'}}>
        {activeTab === 'overview' && (
          <OverviewTab
            agent={agent}
            tasks={tasks}
            chatMessages={chatMessages}
            containerInfo={containerInfo}
            containerLoading={containerLoading}
            handleCreateContainer={handleCreateContainer}
            handleStartContainer={handleStartContainer}
            handleStopContainer={handleStopContainer}
            handleRestartContainer={handleRestartContainer}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsTab
            agent={agent}
            saving={saving}
            setAgent={(updater: (prev: Agent) => Agent) => setAgent((prev: Agent | null) => prev ? updater(prev) : prev as any)}
            onSave={async () => {
                    if (!agent) return
                    setSaving(true)
                    try {
                      const res = await fetch(`/agents/${agent.id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          name: agent.name,
                          role: agent.role,
                          type: agent.type,
                          team_id: agent.team_id,
                          container_image: agent.container_image || null,
                          container_env: agent.container_env || {},
                          config: agent.config,
                        })
                      })
                      if (res.ok) {
                        const updated = await res.json()
                        setAgent(updated)
                        alert('Agent settings saved')
                      } else {
                        alert('Failed to save settings')
                      }
                    } catch {
                      alert('Network error saving settings')
                    } finally {
                      setSaving(false)
                    }
            }}
          />
        )}

        {activeTab === 'tasks' && (
          <TasksTab
            tasks={tasks}
            onOpenAssign={() => {
                if (agent?.team_id) {
                  apiService.getTeamTasks(agent.team_id).then(response => {
                    if (response.ok) {
                      setTeamTasks(Array.isArray(response.data) ? response.data : [])
                    } else {
                      setTeamTasks([])
                    }
                  }).catch(() => setTeamTasks([]))
                } else {
                  setTeamTasks([])
                }
                setShowAssignTask(true)
            }}
          />
        )}

        {/* Assign Task Modal */}
        <AssignTaskModal
          open={showAssignTask}
          onClose={() => setShowAssignTask(false)}
          teamTasks={teamTasks}
          selectedTeamTaskId={selectedTeamTaskId}
          onChangeSelected={setSelectedTeamTaskId}
          assigning={assigningTask}
          error={assignTaskError}
          onAssign={handleAssignTask}
        />

        {activeTab === 'conversations' && (
          <ConversationsTab
            agent={agent}
            conversations={conversationsList}
            selectedConversation={selectedConversation}
            loading={loadingConversations}
            chatWebSocket={chatWebSocket}
            chatMessages={chatMessages}
            isAgentTyping={isAgentTyping}
            newMessage={newMessage}
            isSendingMessage={isSendingMessage}
            
            onNewMessageChange={setNewMessage}
            onSendMessage={sendMessage}
          />
        )}

        {activeTab === 'knowledge' && (
          <KnowledgeTab
            showUpload={showUpload}
            setShowUpload={setShowUpload}
            uploading={uploading}
            knowledgeDocs={knowledgeDocs}
            onFileUpload={handleFileUpload}
            onUrlUpload={handleUrlUpload}
            onOpenDoc={handleDocumentClick}
            onDeleteDoc={async (id: string) => { await handleDocumentDelete(id) }}
          />
        )}

        {activeTab === 'container' && (
          <ContainerTab
            containerInfo={containerInfo}
            containerLoading={containerLoading}
            onCreate={handleCreateContainer}
            onStart={handleStartContainer}
            onStop={handleStopContainer}
            onRestart={handleRestartContainer}
            onRefresh={loadContainerInfo}
            onViewLogs={async () => { await handleLoadContainerLogs(true) }}
          />
        )}
                  </div>
      <DocumentViewer
        open={showDocumentViewer}
        document={selectedDocument}
        content={documentContent}
        onClose={() => { setShowDocumentViewer(false); setSelectedDocument(null) }}
      />
    </div>
  )
}
