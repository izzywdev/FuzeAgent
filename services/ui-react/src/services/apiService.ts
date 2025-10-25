
import type {
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
  Team,
  TeamCreate,
  TeamUpdate,
  TeamMember,
  TeamStats,
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

interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
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

interface ChatMessage {
  id: string
  content: string
  role: string
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
  private organizationToken: string | null = null
  private baseUrl: string = API_ENDPOINTS.BACKEND_API_BASE // Backend API URL

  /**
   * Set the current organization token for all API calls
   */
  setOrganizationToken(orgToken: string | null) {
    this.organizationToken = orgToken
  }

  /**
   * Get the base URL for API calls
   */
  getBaseUrl(): string {
    return this.baseUrl
  }

  /**
   * Get the current organization token
   */
  getOrganizationToken(): string | null {
    return this.organizationToken
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
    
    // Add organization token header if available
    const headers: Record<string, string> = {
      ...options.headers as Record<string, string>
    }

    if (this.organizationToken) {
      headers['X-Organization-Token'] = this.organizationToken
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
    
    let data = null
    if (response.ok) {
      try {
        const contentType = response.headers.get('content-type')
        if (contentType && contentType.includes('application/json')) {
          data = await response.json()
        } else {
          // If not JSON, try to parse as text
          const text = await response.text()
          console.warn('Non-JSON response received for URL:', fullUrl)
          console.warn('Content-Type:', contentType)
          console.warn('Response text (first 200 chars):', text.substring(0, 200))
          data = null
        }
      } catch (parseError) {
        console.error('Failed to parse response as JSON for URL:', fullUrl)
        console.error('Parse error:', parseError)
        data = null
      }
    }
    
    // For the new backend API, if data already matches our response format, return it as-is
    // Otherwise, wrap it in our ApiResponse format
    if (response.ok && data && typeof data === 'object') {
      return {
        data,
        status: response.status,
        ok: response.ok
      }
    }
    
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

  async getOrganizations(filters?: {
    page?: number
    size?: number
    sort_by?: string
    sort_order?: 'asc' | 'desc'
    search?: string
  }): Promise<ApiResponse<PaginatedResponse<Organization>>> {
    const params = new URLSearchParams()
    
    if (filters?.page) params.append('page', filters.page.toString())
    if (filters?.size) params.append('page_size', filters.size.toString())
    if (filters?.search) params.append('search', filters.search)

    const queryString = params.toString()
    const url = queryString ? `/api/organizations?${queryString}` : '/api/organizations'
    
    return this.request<PaginatedResponse<Organization>>(url)
  }

  async getOrganization(id: string): Promise<ApiResponse<Organization>> {
    return this.request<Organization>(`/api/organizations/${id}`)
  }

  async createOrganization(data: OrganizationCreate): Promise<ApiResponse<Organization>> {
    return this.request<Organization>('/api/organizations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateOrganization(id: string, data: OrganizationUpdate): Promise<ApiResponse<Organization>> {
    return this.request<Organization>(`/api/organizations/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async deleteOrganization(id: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(`/api/organizations/${id}`, {
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

  // ============================================================================
  // TEAMS MANAGEMENT
  // ============================================================================

  async getTeams(
    filters?: {
      page?: number
      size?: number
      status?: string[]
      team_type?: string[]
      search?: string
      sort_by?: string
      sort_order?: 'asc' | 'desc'
      organization_id?: string
    }
  ): Promise<ApiResponse<PaginatedResponse<Team>>> {
    const params = new URLSearchParams()

    // Only add parameters if they have valid values
    if (filters?.page && filters.page > 0) params.append('page', filters.page.toString())
    if (filters?.size && filters.size > 0) params.append('size', filters.size.toString())
    if (filters?.status?.length) filters.status.forEach(s => params.append('status', s))
    if (filters?.team_type?.length) filters.team_type.forEach(t => params.append('team_type', t))
    if (filters?.search && filters.search.trim() && typeof filters.search === 'string') params.append('q', filters.search)
    if (filters?.sort_by && filters.sort_by.trim()) params.append('sort_by', filters.sort_by)
    if (filters?.sort_order && filters.sort_order.trim()) params.append('sort_order', filters.sort_order)
    if (filters?.organization_id) params.append('organization_id', filters.organization_id)

    const queryString = params.toString()
    const url = queryString ? `/teams?${queryString}` : '/teams'

    return this.request<PaginatedResponse<Team>>(url)
  }

  async getTeam(teamId: string): Promise<ApiResponse<Team>> {
    return this.request<Team>(`/teams/${teamId}`)
  }

  async createTeam(data: TeamCreate & { organization_id: string }): Promise<ApiResponse<Team>> {
    return this.request<Team>('/teams', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateTeam(teamId: string, data: TeamUpdate): Promise<ApiResponse<Team>> {
    return this.request<Team>(`/teams/${teamId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async deleteTeam(teamId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(`/teams/${teamId}`, {
      method: 'DELETE'
    })
  }

  async addTeamMember(teamId: string, agentId: string): Promise<ApiResponse<{ message: string; agent_id: string; team_id: string }>> {
    return this.request<{ message: string; agent_id: string; team_id: string }>(
      `/teams/${teamId}/members`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId })
      }
    )
  }

  async removeTeamMember(teamId: string, agentId: string): Promise<ApiResponse<{ message: string; agent_id: string; team_id: string }>> {
    return this.request<{ message: string; agent_id: string; team_id: string }>(
      `/teams/${teamId}/members/${agentId}`,
      {
        method: 'DELETE'
      }
    )
  }

  async getTeamMembers(teamId: string): Promise<ApiResponse<TeamMember[]>> {
    return this.request<TeamMember[]>(`/teams/${teamId}/members`)
  }

  async getAvailableAgentsForTeam(teamId: string): Promise<ApiResponse<any[]>> {
    return this.request<any[]>(`/teams/${teamId}/available-agents`)
  }

  async getTeamStats(teamId: string): Promise<ApiResponse<TeamStats>> {
    return this.request<TeamStats>(`/teams/${teamId}/stats`)
  }

  // ============================================================================
  // TASKS MANAGEMENT
  // ============================================================================

  async getTasks(
    filters?: {
      page?: number;
      size?: number;
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
    if (filters?.size) params.append('size', filters.size.toString());
    if (filters?.status?.length) filters.status.forEach(s => params.append('status', s));
    if (filters?.priority?.length) filters.priority.forEach(p => params.append('priority', p));
    if (filters?.team_id) params.append('team_id', filters.team_id);
    if (filters?.agent_id) params.append('agent_id', filters.agent_id);
    if (filters?.milestone_id) params.append('milestone_id', filters.milestone_id);
    if (filters?.date_from) params.append('date_from', filters.date_from);
    if (filters?.date_to) params.append('date_to', filters.date_to);
    if (filters?.search) params.append('q', filters.search);
    if (filters?.sort_by) params.append('sort_by', filters.sort_by);
    if (filters?.sort_order) params.append('sort_order', filters.sort_order);

    const queryString = params.toString();
    const url = `/tasks${queryString ? `?${queryString}` : ''}`;

    return this.request<PaginatedResponse<Task>>(url);
  }

  async getTask(taskId: string): Promise<ApiResponse<Task>> {
    return this.request<Task>(`/tasks/${taskId}`);
  }

  async createTask(
    data: {
      title: string;
      description?: string;
      priority?: 'low' | 'medium' | 'high';
      status?: 'pending' | 'in_progress' | 'blocked' | 'closed' | 'closed_approved';
      team_id: string;
      agent_id?: string;
      milestone_id?: string;
    }
  ): Promise<ApiResponse<Task>> {
    return this.request<Task>('/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async updateTask(
    taskId: string,
    data: {
      title?: string;
      description?: string;
      priority?: 'low' | 'medium' | 'high';
      status?: 'pending' | 'in_progress' | 'blocked' | 'closed' | 'closed_approved';
      team_id?: string;
      agent_id?: string;
      milestone_id?: string;
      progress_pct?: number;
      progress_notes?: string;
    }
  ): Promise<ApiResponse<Task>> {
    return this.request<Task>(`/tasks/${taskId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async deleteTask(taskId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(`/tasks/${taskId}`, {
      method: 'DELETE'
    });
  }

  async executeTask(taskId: string): Promise<ApiResponse<{ message: string; task_id: string }>> {
    return this.request<{ message: string; task_id: string }>(`/tasks/${taskId}/execute`, {
      method: 'POST'
    });
  }

  async getTeamTasks(teamId: string): Promise<ApiResponse<Task[]>> {
    return this.request<Task[]>(`/tasks/teams/${teamId}`);
  }

  async getAgentTasks(agentId: string): Promise<ApiResponse<Task[]>> {
    return this.request<Task[]>(`/tasks/agents/${agentId}`);
  }

  async getMilestoneTasks(milestoneId: string): Promise<ApiResponse<Task[]>> {
    return this.request<Task[]>(`/tasks/milestones/${milestoneId}`);
  }

  async getTeamTools(id: string): Promise<ApiResponse<Tool[]>> {
    return this.request<Tool[]>(`/teams/${id}/tools`);
  }

  async getTeamKnowledge(teamId: string): Promise<ApiResponse<KnowledgeDocument[]>> {
    return this.request<KnowledgeDocument[]>(`/teams/${teamId}/knowledge`)
  }

  async getTeamKnowledgeContent(teamId: string, docId: string): Promise<ApiResponse<DocumentContent>> {
    return this.request<DocumentContent>(`/teams/${teamId}/knowledge/${docId}/content`)
  }

  // ============================================================================
  // AGENTS
  // ============================================================================

  async getAgents(filters?: {
    page?: number
    size?: number
    status?: string[]
    type?: string[]
    team_id?: string
    search?: string
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  }): Promise<ApiResponse<PaginatedResponse<Agent>>> {
    const params = new URLSearchParams()

    // Only add parameters if they have valid values
    if (filters?.page && filters.page > 0) params.append('page', filters.page.toString())
    if (filters?.size && filters.size > 0) params.append('size', filters.size.toString())
    if (filters?.status?.length) filters.status.forEach(s => params.append('status', s))
    if (filters?.type?.length) filters.type.forEach(t => params.append('type', t))
    if (filters?.team_id && filters.team_id.trim()) params.append('team_id', filters.team_id)
    if (filters?.search && filters.search.trim() && typeof filters.search === 'string') params.append('q', filters.search)
    if (filters?.sort_by && filters.sort_by.trim()) params.append('sort_by', filters.sort_by)
    if (filters?.sort_order && filters.sort_order.trim()) params.append('sort_order', filters.sort_order)

    const queryString = params.toString()
    const url = `/agents${queryString ? `?${queryString}` : ''}`

    return this.request<PaginatedResponse<Agent>>(url)
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



  async getAgentTools(id: string): Promise<ApiResponse<Tool[]>> {
    return this.request<Tool[]>(`/agents/${id}/tools`)
  }

  async getAgentKnowledge(id: string): Promise<ApiResponse<KnowledgeDocument[]>> {
    return this.request<KnowledgeDocument[]>(`/agents/${id}/knowledge`)
  }

  async getAgentKnowledgeContent(agentId: string, docId: string): Promise<ApiResponse<DocumentContent>> {
    return this.directRequest<DocumentContent>(`/knowledge/agents/${agentId}/documents/${docId}/content`)
  }

  async getAgentConversations(id: string): Promise<ApiResponse<Conversation[]>> {
    return this.request<Conversation[]>(`/agents/${id}/conversations`)
  }

  async getAgentContainerStatus(id: string): Promise<ApiResponse<ContainerInfo>> {
    return this.request<ContainerInfo>(`/agents/${id}/container/status`)
  }

  async getAgentConversationMessages(agentId: string, conversationId: string): Promise<ApiResponse<ChatMessage[]>> {
    return this.request<ChatMessage[]>(`/agents/${agentId}/conversations/${conversationId}/messages`)
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

  async getGoals(filters?: {
    page?: number
    size?: number
    organization_id?: string
    status?: string[]
    priority?: string[]
    search?: string
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  }): Promise<ApiResponse<PaginatedResponse<Goal>>> {
    const params = new URLSearchParams()
    
    if (filters?.page) params.append('page', filters.page.toString())
    if (filters?.size) params.append('size', filters.size.toString())
    if (filters?.organization_id) params.append('organization_id', filters.organization_id)
    if (filters?.status?.length) filters.status.forEach(s => params.append('status', s))
    if (filters?.priority?.length) filters.priority.forEach(p => params.append('priority', p))
    if (filters?.search) params.append('q', filters.search)
    if (filters?.sort_by) params.append('sort_by', filters.sort_by)
    if (filters?.sort_order) params.append('sort_order', filters.sort_order)

    const queryString = params.toString()
    const url = queryString ? `/goals?${queryString}` : '/goals'
    
    return this.request<PaginatedResponse<Goal>>(url)
  }

  async getGoal(id: string): Promise<ApiResponse<Goal>> {
    return this.request<Goal>(`/goals/${id}`)
  }

  async createGoal(data: {
    organization_id: string
    title: string
    description?: string
    priority?: 'low' | 'medium' | 'high' | 'critical'
    status?: 'planning' | 'active' | 'completed' | 'on_hold'
    target_completion_date?: string
    progress_percentage?: number
  }): Promise<ApiResponse<Goal>> {
    return this.request<Goal>('/goals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async updateGoal(id: string, data: {
    title?: string
    description?: string
    priority?: 'low' | 'medium' | 'high' | 'critical'
    status?: 'planning' | 'active' | 'completed' | 'on_hold'
    target_completion_date?: string
    progress_percentage?: number
  }): Promise<ApiResponse<Goal>> {
    return this.request<Goal>(`/goals/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }

  async deleteGoal(id: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(`/goals/${id}`, {
      method: 'DELETE'
    })
  }



  // Legacy method for backward compatibility - use createTask instead
  async createTeamTask(teamId: string, data: { title: string; description: string; priority?: string }): Promise<ApiResponse<Task>> {
    return this.createTask({ 
      ...data, 
      team_id: teamId,
      priority: data.priority as 'low' | 'medium' | 'high' || 'medium'
    });
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
    status?: 'planned' | 'in_progress' | 'completed' | 'on_hold' | 'cancelled'
    due_date?: string
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
      status?: 'planned' | 'in_progress' | 'completed' | 'on_hold' | 'cancelled'
      due_date?: string
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
  async deleteMilestone(milestoneId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(`/milestones/${milestoneId}`, {
      method: 'DELETE'
    })
  }

  /**
   * List milestones with filtering, search, and pagination
   */
  async getMilestones(options: {
    page?: number
    size?: number
    goal_id?: string
    status?: ('planned' | 'in_progress' | 'completed' | 'on_hold' | 'cancelled')[]
    search?: string
    sort_by?: 'created_at' | 'due_date' | 'title'
    sort_order?: 'asc' | 'desc'
  } = {}): Promise<ApiResponse<PaginatedResponse<Milestone>>> {
    const params = new URLSearchParams()

    if (options.page) params.append('page', options.page.toString())
    if (options.size) params.append('size', options.size.toString())
    if (options.goal_id) params.append('goal_id', options.goal_id)
    if (options.status?.length) {
      options.status.forEach(s => params.append('status', s))
    }
    if (options.search) params.append('q', options.search)
    if (options.sort_by) params.append('sort_by', options.sort_by)
    if (options.sort_order) params.append('sort_order', options.sort_order)

    const url = `/milestones${params.toString() ? '?' + params.toString() : ''}`

    return this.request<PaginatedResponse<Milestone>>(url)
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
        data: response.data.items,
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
      agents: agentsResponse.data?.items || [],
      teams: teamsResponse.data?.items || [],
      organizations: orgsResponse.data?.items || []
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
