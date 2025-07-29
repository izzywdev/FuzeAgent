// Organization types
export interface Organization {
  id: string
  name: string
  description?: string
  settings: Record<string, any>
  created_at: string
  updated_at: string
  team_count?: number
  agent_count?: number
}

export interface OrganizationCreate {
  name: string
  description?: string
  settings?: Record<string, any>
}

export interface OrganizationUpdate {
  name?: string
  description?: string
  settings?: Record<string, any>
}

// Team types
export interface Team {
  id: string
  organization_id: string
  name: string
  description?: string
  team_type: 'development' | 'qa' | 'design' | 'management' | 'general'
  settings: Record<string, any>
  created_at: string
  updated_at: string
  organization_name?: string
  agent_count?: number
}

export interface TeamCreate {
  organization_id: string
  name: string
  description?: string
  team_type?: 'development' | 'qa' | 'design' | 'management' | 'general'
  settings?: Record<string, any>
}

export interface TeamUpdate {
  name?: string
  description?: string
  team_type?: 'development' | 'qa' | 'design' | 'management' | 'general'
  settings?: Record<string, any>
}

// Agent types (updated)
export interface Agent {
  id: string
  team_id: string
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
  team_name?: string
  organization_id?: string
  organization_name?: string
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
    team_id: string
    name?: string
    goal?: string
    backstory?: string
    temperature?: number
    [key: string]: any
  }
}

export interface CreateCustomAgent {
  team_id: string
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

// Extended types with relationships
export interface OrganizationWithTeams extends Organization {
  teams: Team[]
}

export interface TeamWithAgents extends Team {
  agents: Agent[]
}

// Hierarchy context
export interface HierarchyContext {
  currentOrganization: Organization | null
  currentTeam: Team | null
  organizations: Organization[]
  teams: Team[]
}