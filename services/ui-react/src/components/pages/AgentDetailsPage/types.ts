export interface Agent {
  id: string
  name: string
  role: string
  type: string
  status: string
  // Docker image to use for this agent's container. Defaults from template but can be overridden.
  container_image?: string
  // Environment variables to inject into the agent container
  container_env?: Record<string, string>
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

export interface Task {
  id: string
  title: string
  description: string
  status: string
  priority: string
  created_at: string
  completed_at?: string
}

export interface Conversation {
  id: string
  title: string
  message_count: number
  last_message: string
  timestamp: string
  status: string
  updated_at?: string
}

export interface ChatMessage {
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

export interface ContainerInfo {
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

export interface KnowledgeDocument {
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


