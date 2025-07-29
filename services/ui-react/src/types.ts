export interface Agent {
  id: string
  name: string
  role: string
  type: string
  template_id?: string
  status: 'active' | 'inactive' | 'busy' | 'error'
  config: {
    goal?: string
    backstory?: string
    system_prompt?: string
    tools?: string[]
    skills?: string[]
    model?: string
    temperature?: number
  }
  created_at: string
  updated_at: string
}

export interface Task {
  id: string
  title: string
  description: string
  type: string
  assigned_to: string
  assigned_agent_name: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  priority: number
  created_at: string
  completed_at?: string
  result?: string
}

export interface AgentTemplate {
  template_id: string
  name: string
  category: string
  description: string
  system_prompt: string
  default_goal: string
  default_backstory: string
  tools: string[]
  skills: string[]
  default_model: string
  default_temperature: number
  customizable_fields: string[]
}

export interface CreateAgentFromTemplate {
  template_id: string
  overrides: {
    name?: string
    goal?: string
    backstory?: string
    temperature?: number
    [key: string]: any
  }
}

export interface CreateCustomAgent {
  name: string
  role: string
  type: string
  config: {
    goal: string
    tools: string[]
    model: string
    temperature: number
  }
}