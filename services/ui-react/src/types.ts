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
  description: string
  team_type: 'development' | 'operations' | 'management' | 'research'
  color: string
  status: 'active' | 'inactive'
  settings: Record<string, any>
  created_at: string
  updated_at: string
  member_count: number
  agent_count: number
  task_count: number
  completed_task_count: number
  active_task_count: number
  goal_count: number
  milestone_count: number
  efficiency_rate: number
  avg_response_time: string
}

export interface TeamCreate {
  name: string
  description?: string
  team_type?: 'development' | 'operations' | 'management' | 'research'
  color?: string
  settings?: Record<string, any>
}

export interface TeamUpdate {
  name?: string
  description?: string
  team_type?: 'development' | 'operations' | 'management' | 'research'
  color?: string
  status?: 'active' | 'inactive'
  settings?: Record<string, any>
}

export interface TeamFilters {
  status?: string[]
  team_type?: string[]
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface PaginatedTeamsResponse {
  teams: Team[]
  total: number
  page: number
  page_size: number
  total_pages: number
  filters?: TeamFilters
}

export interface AddTeamMemberRequest {
  agent_id: string
}

export interface TeamMember {
  id: string
  name: string
  role?: string
  type: string
  status: string
  task_count: number
  completed_task_count: number
  active_task_count: number
  efficiency_rate: number
  joined_date: string
  performance: {
    tasksCompleted: number
    tasksActive: number
    efficiency: string
  }
}

export interface TeamStats {
  team_id: string
  team_name: string
  agent_count: number
  tasks: {
    total: number
    completed: number
    active: number
    pending: number
    completion_rate: number
  }
  performance: {
    efficiency_rate: number
    avg_tasks_per_agent: number
    avg_completed_per_agent: number
  }
  created_at: string
  last_updated: string
}

// Agent types (updated)
export interface Agent {
  id: string
  team_id: string
  name: string
  role: string
  type: string
  template_id?: string
  status: 'active' | 'inactive' | 'busy' | 'error' | 'idle'
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
  tasks?: {
    completed: number
    running: number
    pending: number
  }
  lastActivity?: string
  performance?: {
    tasksCompleted: number
    tasksActive: number
    efficiency: string
  }
  joinedDate?: string
}

export interface Task {
  id: string
  title: string
  description: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  team_id: string
  agent_id: string
  milestone_id?: string
  result: string
  created_at: string
  updated_at: string
  completed_at: string
  team_name: string
  agent_name: string
  milestone_title?: string
}

export interface TaskCreate {
  title: string
  description?: string
  priority?: 'low' | 'medium' | 'high' | 'critical'
  status?: 'pending' | 'in_progress' | 'completed' | 'failed'
  team_id?: string
  agent_id?: string
  milestone_id?: string
}

export interface TaskUpdate {
  title?: string
  description?: string
  priority?: 'low' | 'medium' | 'high' | 'critical'
  status?: 'pending' | 'in_progress' | 'completed' | 'failed'
  team_id?: string
  agent_id?: string
  milestone_id?: string
  result?: string
}

export interface TaskFilters {
  status?: string[]
  priority?: string[]
  team_id?: string
  agent_id?: string
  milestone_id?: string
  date_range?: {
    from?: string
    to?: string
  }
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface PaginatedTasksResponse {
  tasks: Task[]
  total: number
  page: number
  page_size: number
  total_pages: number
  filters?: TaskFilters
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

// ============================================================================
// MILESTONES SYSTEM
// ============================================================================

// Milestone types
export interface Milestone {
  id: string
  goal_id: string
  title: string
  description: string
  status: 'not_started' | 'in_progress' | 'completed' | 'blocked' | 'cancelled'
  priority: 'low' | 'medium' | 'high' | 'critical'
  progress_percentage: number
  target_date: string
  completed_at?: string
  created_at: string
  updated_at: string

  // Relationships
  goal?: Goal
  tasks?: Task[]
  task_count?: number
  completed_task_count?: number
}

export interface MilestoneCreate {
  goal_id: string
  title: string
  description: string
  priority?: 'low' | 'medium' | 'high' | 'critical'
  target_date: string
}

export interface MilestoneUpdate {
  title?: string
  description?: string
  status?: 'not_started' | 'in_progress' | 'completed' | 'blocked' | 'cancelled'
  priority?: 'low' | 'medium' | 'high' | 'critical'
  progress_percentage?: number
  target_date?: string
}

// Milestone search and filter options
export interface MilestoneFilters {
  status?: Milestone['status'][]
  priority?: Milestone['priority'][]
  goal_id?: string
  date_range?: {
    start_date: string
    end_date: string
  }
  search?: string
  sort_by?: 'created_at' | 'target_date' | 'priority' | 'progress_percentage' | 'title'
  sort_order?: 'asc' | 'desc'
}

export interface MilestoneSearchResponse {
  milestones: Milestone[]
  total: number
  page: number
  page_size: number
  total_pages: number
  filters?: MilestoneFilters
}

// Goal types
export interface Goal {
  id: string
  organization_id: string
  title: string
  description: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  status: 'planning' | 'active' | 'completed' | 'on_hold'
  target_completion_date?: string
  progress_percentage: number
  created_at: string
  updated_at: string
  milestones?: Milestone[]
  milestone_count?: number
  completed_milestone_count?: number
}

export interface GoalCreate {
  organization_id: string
  title: string
  description?: string
  priority?: 'low' | 'medium' | 'high' | 'critical'
  status?: 'planning' | 'active' | 'completed' | 'on_hold'
  target_completion_date?: string
}

export interface GoalUpdate {
  title?: string
  description?: string
  priority?: 'low' | 'medium' | 'high' | 'critical'
  status?: 'planning' | 'active' | 'completed' | 'on_hold'
  progress_percentage?: number
  target_completion_date?: string
}

// Extended Goal type with milestones
export interface GoalWithMilestones extends Goal {
  milestones: Milestone[]
  milestone_count?: number
  completed_milestone_count?: number
}

// Extended Task type with milestone relationship
export interface TaskWithMilestone extends Task {
  milestone_id?: string
  milestone?: Milestone
}

// ============================================================================
// EXTENDED TYPES WITH RELATIONSHIPS
// ============================================================================

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

// ============================================================================
// PAGINATION TYPES
// ============================================================================

export interface PaginationOptions {
  page?: number
  page_size?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}