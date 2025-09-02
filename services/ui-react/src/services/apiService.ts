
import type {
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
  Team,
  TeamCreate,
  TeamUpdate,
  Agent,
  Task,
  Milestone,
  AgentTemplate,
  CreateCustomAgent
} from '../types'
// Removed dependency on old apiClient utils
import { API_ENDPOINTS } from '../config/api'


/**
 * Centralized API Service for FuzeAgent Frontend
 * 
 * This service provides a clean interface for all API operations,
 * removing the need for direct fetch calls in components.
 * All methods handle organization context automatically.
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */

// ============================================================================
// TYPES
// ============================================================================

interface ApiResponse<T> {
  data: T
  status: number
  ok: boolean
}

interface KnowledgeDocument {
  id: string
  title: string
  content: string
  created_at: string
  updated_at: string
}

interface DocumentContent {
  content: string
}

interface ContainerInfo {
  status: string
  image: string
  created_at: string
  ports: Record<string, string>
}

interface ContainerLogs {
  logs: string[]
}

interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
}

interface Message {
  id: string
  content: string
  sender: string
  timestamp: string
}

interface Tool {
  id: string
  name: string
  description: string
  type: string
  config: Record<string, any>
}

interface Goal {
  id: string
  title: string
  description: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  status: 'planning' | 'active' | 'completed' | 'on_hold'
  target_completion_date: string
  progress_percentage: number
  assigned_teams: string[]
  milestones: Array<{
    id: string
    title: string
    description: string
    due_date: string
    completed: boolean
  }>
}

// ============================================================================
// CORE API SERVICE
// ============================================================================

class ApiService {
  private organizationId: string | null = null
  private baseUrl: string = 'http://localhost:8001' // Default orchestrator URL

  /**
   * Set the current organization ID for all API calls
   */
  setOrganizationId(orgId: string | null) {
    this.organizationId = orgId
  }

  /**
   * Make an API request with organization context
   */
  private async request<T>(
    url: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    // Build the full URL
    const baseUrl = this.baseUrl
    const fullUrl = url.startsWith('http') ? url : `${baseUrl}${url}`
    
    // Add organization ID header if available
    const headers: Record<string, string> = {
      ...options.headers as Record<string, string>
    }
    
    if (this.organizationId) {
      headers['X-Organization-ID'] = this.organizationId
    }
    
    // Add auth token if available
    const authToken = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`
    }
    
    const response = await fetch(fullUrl, {
      ...options,
      headers
    })
    
    const data = response.ok ? await response.json() : null
    
    return {
      data,
      status: response.status,
      ok: response.ok
    }
  }

  /**
   * Make a direct fetch request (for cases where fetchWithOrg isn't suitable)
   */
  private async directRequest<T>(
    url: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const fullUrl = url.startsWith('http') ? url : `${API_ENDPOINTS.HIERARCHY_API_BASE}${url}`
    const response = await fetch(fullUrl, options)
    
    const data = response.ok ? await response.json() : null
    
    return {
      data,
      status: response.status,
      ok: response.ok
    }
  }

  // ============================================================================
  // ORGANIZATIONS
  // ============================================================================

  async getOrganizations(): Promise<ApiResponse<Organization[]>> {
    return this.request<Organization[]>('/organizations')
  }

  async getOrganization(id: string): Promise<ApiResponse<Organization>> {
    return this.request<Organization>(`/organizations/${id}`)
  }

  async createOrganization(data: OrganizationCreate): Promise<ApiResponse<Organization>> {
    return this.request<Organization>('/organizations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateOrganization(id: string, data: OrganizationUpdate): Promise<ApiResponse<Organization>> {
    return this.request<Organization>(`/organizations/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async deleteOrganization(id: string): Promise<ApiResponse<boolean>> {
    return this.request<boolean>(`/organizations/${id}`, {
      method: 'DELETE'
    })
  }

  async getOrganizationTools(id: string): Promise<ApiResponse<Tool[]>> {
    return this.request<Tool[]>(`/organizations/${id}/tools`)
  }

  async getOrganizationGoals(id: string): Promise<ApiResponse<Goal[]>> {
    return this.request<Goal[]>(`/organizations/${id}/goals`)
  }

  async getOrganizationKnowledge(id: string): Promise<ApiResponse<KnowledgeDocument[]>> {
    return this.directRequest<KnowledgeDocument[]>(`http://localhost:8000/knowledge/organizations/${id}/documents`)
  }

  async getOrganizationKnowledgeContent(orgId: string, docId: string): Promise<ApiResponse<DocumentContent>> {
    return this.directRequest<DocumentContent>(`http://localhost:8000/knowledge/organizations/${orgId}/documents/${docId}/content`)
  }

  // ============================================================================
  // TEAMS
  // ============================================================================

  async getTeams(): Promise<ApiResponse<Team[]>> {
    return this.request<Team[]>('/teams')
  }

  async getTeam(id: string): Promise<ApiResponse<Team>> {
    return this.request<Team>(`/teams/${id}`)
  }

  async createTeam(data: TeamCreate): Promise<ApiResponse<Team>> {
    return this.request<Team>('/teams', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateTeam(id: string, data: TeamUpdate): Promise<ApiResponse<Team>> {
    return this.request<Team>(`/teams/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async deleteTeam(id: string): Promise<ApiResponse<boolean>> {
    return this.request<boolean>(`/teams/${id}`, {
      method: 'DELETE'
    })
  }

  // ============================================================================
  // TASKS MANAGEMENT
  // ============================================================================

  async getTasks(
    orgId: string,
    filters?: {
      page?: number;
      page_size?: number;
      status?: string[];
      priority?: string[];
      team_id?: string;
      agent_id?: string;
      milestone_id?: string;
      date_from?: string;
      date_to?: string;
      search?: string;
      sort_by?: string;
      sort_order?: 'asc' | 'desc';
    }
  ): Promise<ApiResponse<PaginatedResponse<Task>>> {
    const params = new URLSearchParams();

    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.page_size) params.append('page_size', filters.page_size.toString());
    if (filters?.status?.length) filters.status.forEach(s => params.append('status', s));
    if (filters?.priority?.length) filters.priority.forEach(p => params.append('priority', p));
    if (filters?.team_id) params.append('team_id', filters.team_id);
    if (filters?.agent_id) params.append('agent_id', filters.agent_id);
    if (filters?.milestone_id) params.append('milestone_id', filters.milestone_id);
    if (filters?.date_from) params.append('date_from', filters.date_from);
    if (filters?.date_to) params.append('date_to', filters.date_to);
    if (filters?.search) params.append('search', filters.search);
    if (filters?.sort_by) params.append('sort_by', filters.sort_by);
    if (filters?.sort_order) params.append('sort_order', filters.sort_order);

    const queryString = params.toString();
    const url = `/organizations/${orgId}/tasks${queryString ? `?${queryString}` : ''}`;

    return this.request<PaginatedResponse<Task>>(url);
  }

  async getTask(orgId: string, taskId: string): Promise<ApiResponse<Task>> {
    return this.request<Task>(`/organizations/${orgId}/tasks/${taskId}`);
  }

  async createTask(
    orgId: string,
    data: {
      title: string;
      description?: string;
      priority?: 'low' | 'medium' | 'high' | 'critical';
      status?: 'pending' | 'in_progress' | 'completed' | 'failed';
      team_id?: string;
      agent_id?: string;
      milestone_id?: string;
    }
  ): Promise<ApiResponse<Task>> {
    return this.request<Task>(`/organizations/${orgId}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async updateTask(
    orgId: string,
    taskId: string,
    data: {
      title?: string;
      description?: string;
      priority?: 'low' | 'medium' | 'high' | 'critical';
      status?: 'pending' | 'in_progress' | 'completed' | 'failed';
      team_id?: string;
      agent_id?: string;
      milestone_id?: string;
      result?: string;
    }
  ): Promise<ApiResponse<Task>> {
    return this.request<Task>(`/organizations/${orgId}/tasks/${taskId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async deleteTask(orgId: string, taskId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/organizations/${orgId}/tasks/${taskId}`, {
      method: 'DELETE'
    });
  }

  async executeTask(orgId: string, taskId: string): Promise<ApiResponse<{ message: string; task_id: string }>> {
    return this.request<{ message: string; task_id: string }>(`/organizations/${orgId}/tasks/${taskId}/execute`, {
      method: 'POST'
    });
  }

  async getTeamTasks(orgId: string, teamId: string): Promise<ApiResponse<Task[]>> {
    return this.request<Task[]>(`/organizations/${orgId}/tasks/teams/${teamId}`);
  }

  async getAgentTasks(orgId: string, agentId: string): Promise<ApiResponse<Task[]>> {
    return this.request<Task[]>(`/organizations/${orgId}/tasks/agents/${agentId}`);
  }

  async getMilestoneTasks(orgId: string, milestoneId: string): Promise<ApiResponse<Task[]>> {
    return this.request<Task[]>(`/organizations/${orgId}/tasks/milestones/${milestoneId}`);
  }

  async getTeamTools(id: string): Promise<ApiResponse<Tool[]>> {
    return this.request<Tool[]>(`/teams/${id}/tools`);
  }

  async getTeamKnowledge(id: string): Promise<ApiResponse<KnowledgeDocument[]>> {
    return this.request<KnowledgeDocument[]>(`/teams/${id}/knowledge`)
  }

  async getTeamKnowledgeContent(teamId: string, docId: string): Promise<ApiResponse<DocumentContent>> {
    return this.request<DocumentContent>(`/teams/${teamId}/knowledge/${docId}/content`)
  }

  // ============================================================================
  // AGENTS
  // ============================================================================

  async getAgents(): Promise<ApiResponse<Agent[]>> {
    return this.request<Agent[]>('/agents')
  }

  async getAgent(id: string): Promise<ApiResponse<Agent>> {
    return this.request<Agent>(`/agents/${id}`)
  }

  async createAgent(data: CreateCustomAgent): Promise<ApiResponse<Agent>> {
    return this.request<Agent>('/agents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateAgent(id: string, data: Partial<Agent>): Promise<ApiResponse<Agent>> {
    return this.request<Agent>(`/agents/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async deleteAgent(id: string): Promise<ApiResponse<boolean>> {
    return this.request<boolean>(`/agents/${id}`, {
      method: 'DELETE'
    })
  }

  async getAgentTasks(id: string): Promise<ApiResponse<Task[]>> {
    return this.request<Task[]>(`/agents/${id}/tasks`)
  }

  async getAgentTools(id: string): Promise<ApiResponse<Tool[]>> {
    return this.request<Tool[]>(`/agents/${id}/tools`)
  }

  async getAgentKnowledge(id: string): Promise<ApiResponse<KnowledgeDocument[]>> {
    return this.directRequest<KnowledgeDocument[]>(`/knowledge/agents/${id}/documents`)
  }

  async getAgentKnowledgeContent(agentId: string, docId: string): Promise<ApiResponse<DocumentContent>> {
    return this.directRequest<DocumentContent>(`/knowledge/agents/${agentId}/documents/${docId}/content`)
  }

  async getAgentConversations(id: string): Promise<ApiResponse<Conversation[]>> {
    return this.request<Conversation[]>(`/agents/${id}/conversations`)
  }

  async createAgentConversation(agentId: string, data: { title: string }): Promise<ApiResponse<Conversation>> {
    return this.request<Conversation>(`/agents/${agentId}/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async getConversationMessages(agentId: string, conversationId: string): Promise<ApiResponse<Message[]>> {
    return this.request<Message[]>(`/agents/${agentId}/conversations/${conversationId}/messages`)
  }

  async getAgentContainerStatus(id: string): Promise<ApiResponse<ContainerInfo>> {
    return this.request<ContainerInfo>(`/agents/${id}/container/status`)
  }

  async getAgentContainerLogs(id: string): Promise<ApiResponse<ContainerLogs>> {
    return this.request<ContainerLogs>(`/agents/${id}/container/logs`)
  }

  // ============================================================================
  // AGENT TEMPLATES
  // ============================================================================

  async getAgentTemplates(): Promise<ApiResponse<AgentTemplate[]>> {
    return this.request<AgentTemplate[]>('/agent-templates')
  }

  async getAgentTemplate(id: string): Promise<ApiResponse<AgentTemplate>> {
    return this.request<AgentTemplate>(`/agent-templates/${id}`)
  }

  // ============================================================================
  // GOALS
  // ============================================================================

  async getGoals(organizationId: string): Promise<ApiResponse<Goal[]>> {
    return this.request<Goal[]>(`/organizations/${organizationId}/goals`)
  }

  async getGoal(id: string): Promise<ApiResponse<Goal>> {
    return this.request<Goal>(`/goals/${id}`)
  }

  async createGoal(data: Partial<Goal>): Promise<ApiResponse<Goal>> {
    return this.request<Goal>('/goals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateGoal(id: string, data: Partial<Goal>): Promise<ApiResponse<Goal>> {
    return this.request<Goal>(`/goals/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async deleteGoal(id: string): Promise<ApiResponse<boolean>> {
    return this.request<boolean>(`/goals/${id}`, {
      method: 'DELETE'
    })
  }

  // ============================================================================
  // TASKS
  // ============================================================================

  async getTasks(): Promise<ApiResponse<Task[]>> {
    return this.request<Task[]>('/tasks')
  }

  async getTask(id: string): Promise<ApiResponse<Task>> {
    return this.request<Task>(`/tasks/${id}`)
  }

  async createTask(data: Partial<Task>): Promise<ApiResponse<Task>> {
    return this.request<Task>('/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateTask(id: string, data: Partial<Task>): Promise<ApiResponse<Task>> {
    return this.request<Task>(`/tasks/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async deleteTask(id: string): Promise<ApiResponse<boolean>> {
    return this.request<boolean>(`/tasks/${id}`, {
      method: 'DELETE'
    })
  }

  // Legacy method for backward compatibility - use createTask instead
  async createTeamTask(teamId: string, data: { title: string; description: string; priority?: string }): Promise<ApiResponse<Task>> {
    // Note: This method needs organization context, but for backward compatibility we'll use a default org
    // In production, this should be updated to accept orgId parameter
    const orgId = '1'; // Default organization ID for backward compatibility
    return this.createTask(orgId, { ...data, team_id: teamId });
  }

  async addTeamMember(teamId: string, agentId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/teams/${teamId}/members`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId })
    })
  }

  async uploadTeamDocument(teamId: string, file: File, title: string): Promise<ApiResponse<any>> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', title)
    
    return this.directRequest<any>(`/knowledge/teams/${teamId}/documents`, {
      method: 'POST',
      body: formData
    })
  }

  async addTeamUrl(teamId: string, url: string): Promise<ApiResponse<any>> {
    return this.directRequest<any>(`/knowledge/teams/${teamId}/url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })
  }

  async deleteTeamDocument(teamId: string, docId: string): Promise<ApiResponse<boolean>> {
    return this.directRequest<boolean>(`/knowledge/teams/${teamId}/documents/${docId}`, {
      method: 'DELETE'
    })
  }

  // ============================================================================
  // ORGANIZATION KNOWLEDGE & DOCUMENTS
  // ============================================================================

  async uploadOrganizationDocument(orgId: string, file: File, title: string): Promise<ApiResponse<any>> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', title)
    
    return this.directRequest<any>(`http://localhost:8000/knowledge/organizations/${orgId}/documents`, {
      method: 'POST',
      body: formData
    })
  }

  async addOrganizationUrl(orgId: string, url: string): Promise<ApiResponse<any>> {
    return this.directRequest<any>(`http://localhost:8000/knowledge/organizations/${orgId}/url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })
  }

  async deleteOrganizationDocument(orgId: string, docId: string): Promise<ApiResponse<boolean>> {
    return this.directRequest<boolean>(`http://localhost:8000/knowledge/organizations/${orgId}/documents/${docId}`, {
      method: 'DELETE'
    })
  }

  // ============================================================================
  // AGENT KNOWLEDGE & DOCUMENTS  
  // ============================================================================

  async uploadAgentDocument(agentId: string, file: File, title: string): Promise<ApiResponse<any>> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', title)
    
    return this.directRequest<any>(`/knowledge/agents/${agentId}/documents`, {
      method: 'POST',
      body: formData
    })
  }

  async addAgentUrl(agentId: string, url: string): Promise<ApiResponse<any>> {
    return this.directRequest<any>(`/knowledge/agents/${agentId}/url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })
  }

  async deleteAgentDocument(agentId: string, docId: string): Promise<ApiResponse<boolean>> {
    return this.directRequest<boolean>(`/knowledge/agents/${agentId}/documents/${docId}`, {
      method: 'DELETE'
    })
  }

  // ============================================================================
  // CONTAINER MANAGEMENT
  // ============================================================================

  async createAgentContainer(agentId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/agents/${agentId}/container/create`, {
      method: 'POST'
    })
  }

  async startAgentContainer(agentId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/agents/${agentId}/container/start`, {
      method: 'POST'
    })
  }

  async stopAgentContainer(agentId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/agents/${agentId}/container/stop`, {
      method: 'POST'
    })
  }

  async restartAgentContainer(agentId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/agents/${agentId}/container/restart`, {
      method: 'POST'
    })
  }

  // ============================================================================
  // CONVERSATIONS & MESSAGES
  // ============================================================================

  async sendMessage(agentId: string, conversationId: string, data: any): Promise<ApiResponse<any>> {
    return this.request<any>(`/agents/${agentId}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateConversationStatus(conversationId: string, status: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/conversations/${conversationId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    })
  }

  // ============================================================================
  // TASK ASSIGNMENT
  // ============================================================================

  async assignTask(taskId: string, agentId: string): Promise<ApiResponse<Task>> {
    return this.request<Task>(`/tasks/${taskId}/assign`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId })
    })
  }

  // ============================================================================
  // TOOL MANAGEMENT
  // ============================================================================

  async updateTeamTool(teamId: string, toolId: string, data: { enabled: boolean; config_override?: any }): Promise<ApiResponse<any>> {
    return this.request<any>(`/teams/${teamId}/tools/${toolId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateAgentTool(agentId: string, toolId: string, data: { enabled: boolean }): Promise<ApiResponse<any>> {
    return this.request<any>(`/agents/${agentId}/tools/${toolId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async createOrganizationTool(orgId: string, data: { key: string; name: string; description: string; default_config: any }): Promise<ApiResponse<any>> {
    return this.request<any>(`/organizations/${orgId}/tools`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateOrganizationTool(orgId: string, toolId: string, data: { key: string; name: string; description: string; default_config: any }): Promise<ApiResponse<any>> {
    return this.request<any>(`/organizations/${orgId}/tools/${toolId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async deleteOrganizationTool(orgId: string, toolId: string): Promise<ApiResponse<boolean>> {
    return this.request<boolean>(`/organizations/${orgId}/tools/${toolId}`, {
      method: 'DELETE'
    })
  }

  // ============================================================================
  // RAG SEARCH
  // ============================================================================

  async ragSearch(query: string, organizationId: string): Promise<ApiResponse<any>> {
    return this.directRequest<any>('http://localhost:8000/rag/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        organization_id: organizationId,
        limit: 5
      })
    })
  }

  // ============================================================================
  // MILESTONES
  // ============================================================================

  /**
   * Create a new milestone for a goal
   */
  async createMilestone(data: {
    goal_id: string
    title: string
    description: string
    priority?: 'low' | 'medium' | 'high' | 'critical'
    target_date: string
  }): Promise<ApiResponse<Milestone>> {
    return this.request<Milestone>('/milestones', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  /**
   * Get a specific milestone by ID
   */
  async getMilestone(milestoneId: string): Promise<ApiResponse<Milestone>> {
    return this.request<Milestone>(`/milestones/${milestoneId}`)
  }

  /**
   * Update an existing milestone
   */
  async updateMilestone(
    milestoneId: string,
    data: {
      title?: string
      description?: string
      status?: 'not_started' | 'in_progress' | 'completed' | 'blocked' | 'cancelled'
      priority?: 'low' | 'medium' | 'high' | 'critical'
      progress_percentage?: number
      target_date?: string
    }
  ): Promise<ApiResponse<Milestone>> {
    return this.request<Milestone>(`/milestones/${milestoneId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  /**
   * Delete a milestone
   */
  async deleteMilestone(milestoneId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/milestones/${milestoneId}`, {
      method: 'DELETE'
    })
  }

  /**
   * List milestones with filtering, search, and pagination
   */
  async getMilestones(options: {
    page?: number
    page_size?: number
    goal_id?: string
    status?: ('not_started' | 'in_progress' | 'completed' | 'blocked' | 'cancelled')[]
    priority?: ('low' | 'medium' | 'high' | 'critical')[]
    search?: string
    sort_by?: 'created_at' | 'target_date' | 'priority' | 'progress_percentage' | 'title'
    sort_order?: 'asc' | 'desc'
  } = {}): Promise<ApiResponse<{
    milestones: Milestone[]
    total: number
    page: number
    page_size: number
    total_pages: number
    filters?: any
  }>> {
    const params = new URLSearchParams()

    if (options.page) params.append('page', options.page.toString())
    if (options.page_size) params.append('page_size', options.page_size.toString())
    if (options.goal_id) params.append('goal_id', options.goal_id)
    if (options.status?.length) {
      options.status.forEach(s => params.append('status', s))
    }
    if (options.priority?.length) {
      options.priority.forEach(p => params.append('priority', p))
    }
    if (options.search) params.append('search', options.search)
    if (options.sort_by) params.append('sort_by', options.sort_by)
    if (options.sort_order) params.append('sort_order', options.sort_order)

    const url = `/milestones${params.toString() ? '?' + params.toString() : ''}`

    return this.request<{
      milestones: Milestone[]
      total: number
      page: number
      page_size: number
      total_pages: number
      filters?: any
    }>(url)
  }

  /**
   * Get all tasks associated with a milestone
   */
  async getMilestoneTasks(
    milestoneId: string,
    options: {
      page?: number
      page_size?: number
      status?: ('pending' | 'in_progress' | 'completed' | 'failed')[]
    } = {}
  ): Promise<ApiResponse<{
    tasks: Task[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }>> {
    const params = new URLSearchParams()

    if (options.page) params.append('page', options.page.toString())
    if (options.page_size) params.append('page_size', options.page_size.toString())
    if (options.status?.length) {
      options.status.forEach(s => params.append('status', s))
    }

    const url = `/milestones/${milestoneId}/tasks${params.toString() ? '?' + params.toString() : ''}`

    return this.request<{
      tasks: Task[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(url)
  }

  /**
   * Assign a task to a milestone
   */
  async assignTaskToMilestone(milestoneId: string, taskId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(`/milestones/${milestoneId}/tasks/${taskId}`, {
      method: 'POST'
    })
  }

  /**
   * Remove a task from a milestone
   */
  async removeTaskFromMilestone(milestoneId: string, taskId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(`/milestones/${milestoneId}/tasks/${taskId}`, {
      method: 'DELETE'
    })
  }

  /**
   * Get milestones for a specific goal
   */
  async getGoalMilestones(goalId: string): Promise<ApiResponse<Milestone[]>> {
    const response = await this.getMilestones({ goal_id: goalId })
    if (response.ok) {
      return {
        data: response.data.milestones,
        status: response.status,
        ok: response.ok
      }
    }
    return response as any
  }

  // ============================================================================
  // FILE UPLOADS
  // ============================================================================

  async uploadFile(endpoint: string, formData: FormData): Promise<ApiResponse<any>> {
    const fullUrl = endpoint.startsWith('http') ? endpoint : `${API_ENDPOINTS.ORCHESTRATOR_API_BASE}${endpoint}`
    const response = await fetch(fullUrl, {
      method: 'POST',
      body: formData,
    })
    
    const data = response.ok ? await response.json() : null
    
    return {
      data,
      status: response.status,
      ok: response.ok
    }
  }

  // ============================================================================
  // DASHBOARD DATA
  // ============================================================================

  async getDashboardData(): Promise<{
    agents: Agent[]
    teams: Team[]
    organizations: Organization[]
  }> {
    const [agentsResponse, teamsResponse, orgsResponse] = await Promise.all([
      this.getAgents(),
      this.getTeams(),
      this.getOrganizations()
    ])

    if (!agentsResponse.ok) {
      throw new Error(`Failed to fetch agents: ${agentsResponse.status}`)
    }
    
    if (!teamsResponse.ok) {
      throw new Error(`Failed to fetch teams: ${teamsResponse.status}`)
    }

    if (!orgsResponse.ok) {
      throw new Error(`Failed to fetch organizations: ${orgsResponse.status}`)
    }

    return {
      agents: agentsResponse.data,
      teams: teamsResponse.data,
      organizations: orgsResponse.data
    }
  }
}

// ============================================================================
// SINGLETON INSTANCE
// ============================================================================

export const apiService = new ApiService()



// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Helper function to handle API responses consistently
 */
export function handleApiResponse<T>(
  response: ApiResponse<T>,
  onSuccess: (data: T) => void,
  onError?: (status: number) => void
) {
  if (response.ok) {
    onSuccess(response.data)
  } else {
    console.error(`API Error ${response.status}`)
    if (onError) {
      onError(response.status)
    } else {
      throw new Error(`API Error ${response.status}`)
    }
  }
}

/**
 * Helper function for error handling in async functions
 */
export function withErrorHandling<T extends any[], R>(
  fn: (...args: T) => Promise<R>
) {
  return async (...args: T): Promise<R | null> => {
    try {
      return await fn(...args)
    } catch (error) {
      console.error('API call failed:', error)
      return null
    }
  }
}

export default apiService
export { useApiService } from '../hooks/useApiService'
