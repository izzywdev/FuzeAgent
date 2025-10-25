/**
 * Backend API Service for FuzeAgent Frontend
 * Integrates with the new unified backend API
 */

import { API_ENDPOINTS } from '../config/api'

// ============================================================================
// TYPES
// ============================================================================

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ApiResponse<T> {
  data: T | null
  error: string | null
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const baseUrl = API_ENDPOINTS.BACKEND_API_BASE
    const url = `${baseUrl}${endpoint}`
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      return {
        data: null,
        error: `HTTP ${response.status}: ${errorText || response.statusText}`,
      }
    }

    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    }
  }
}

// ============================================================================
// BACKEND API SERVICE
// ============================================================================

class BackendApiService {
  // Generic CRUD operations
  
  async list<T>(
    resource: string,
    options?: { page?: number; page_size?: number; search?: string }
  ): Promise<ApiResponse<PaginatedResponse<T>>> {
    const params = new URLSearchParams()
    if (options?.page) params.append('page', options.page.toString())
    if (options?.page_size) params.append('page_size', options.page_size.toString())
    if (options?.search) params.append('search', options.search)

    const query = params.toString()
    const endpoint = `/api/${resource}${query ? `?${query}` : ''}`
    return apiRequest<PaginatedResponse<T>>(endpoint)
  }

  async get<T>(resource: string, id: string): Promise<ApiResponse<T>> {
    return apiRequest<T>(`/api/${resource}/${id}`)
  }

  async create<T>(resource: string, data: any): Promise<ApiResponse<T>> {
    return apiRequest<T>(`/api/${resource}`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async update<T>(resource: string, id: string, data: any): Promise<ApiResponse<T>> {
    return apiRequest<T>(`/api/${resource}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async delete(resource: string, id: string): Promise<ApiResponse<{ message: string }>> {
    return apiRequest<{ message: string }>(`/api/${resource}/${id}`, {
      method: 'DELETE',
    })
  }

  // ============================================================================
  // ORGANIZATIONS
  // ============================================================================

  async getOrganizations(options?: { page?: number; page_size?: number; search?: string }) {
    return this.list('organizations', options)
  }

  async getOrganization(id: string) {
    return this.get('organizations', id)
  }

  async createOrganization(data: any) {
    return this.create('organizations', data)
  }

  async updateOrganization(id: string, data: any) {
    return this.update('organizations', id, data)
  }

  async deleteOrganization(id: string) {
    return this.delete('organizations', id)
  }

  // ============================================================================
  // TEAMS
  // ============================================================================

  async getTeams(options?: { page?: number; page_size?: number; search?: string }) {
    return this.list('teams', options)
  }

  async getTeam(id: string) {
    return this.get('teams', id)
  }

  async createTeam(data: any) {
    return this.create('teams', data)
  }

  async updateTeam(id: string, data: any) {
    return this.update('teams', id, data)
  }

  async deleteTeam(id: string) {
    return this.delete('teams', id)
  }

  // ============================================================================
  // AGENTS
  // ============================================================================

  async getAgents(options?: { page?: number; page_size?: number; search?: string }) {
    return this.list('agents', options)
  }

  async getAgent(id: string) {
    return this.get('agents', id)
  }

  async createAgent(data: any) {
    return this.create('agents', data)
  }

  async updateAgent(id: string, data: any) {
    return this.update('agents', id, data)
  }

  async deleteAgent(id: string) {
    return this.delete('agents', id)
  }

  // ============================================================================
  // TASKS
  // ============================================================================

  async getTasks(options?: { page?: number; page_size?: number; search?: string }) {
    return this.list('tasks', options)
  }

  async getTask(id: string) {
    return this.get('tasks', id)
  }

  async createTask(data: any) {
    return this.create('tasks', data)
  }

  async updateTask(id: string, data: any) {
    return this.update('tasks', id, data)
  }

  async deleteTask(id: string) {
    return this.delete('tasks', id)
  }

  // ============================================================================
  // GOALS
  // ============================================================================

  async getGoals(options?: { page?: number; page_size?: number; search?: string }) {
    return this.list('goals', options)
  }

  async getGoal(id: string) {
    return this.get('goals', id)
  }

  async createGoal(data: any) {
    return this.create('goals', data)
  }

  async updateGoal(id: string, data: any) {
    return this.update('goals', id, data)
  }

  async deleteGoal(id: string) {
    return this.delete('goals', id)
  }

  // ============================================================================
  // MILESTONES
  // ============================================================================

  async getMilestones(options?: { page?: number; page_size?: number; search?: string }) {
    return this.list('milestones', options)
  }

  async getMilestone(id: string) {
    return this.get('milestones', id)
  }

  async createMilestone(data: any) {
    return this.create('milestones', data)
  }

  async updateMilestone(id: string, data: any) {
    return this.update('milestones', id, data)
  }

  async deleteMilestone(id: string) {
    return this.delete('milestones', id)
  }

  // ============================================================================
  // KNOWLEDGE
  // ============================================================================

  async getKnowledge(options?: { page?: number; page_size?: number; search?: string }) {
    return this.list('knowledge', options)
  }

  async getKnowledgeItem(id: string) {
    return this.get('knowledge', id)
  }

  async createKnowledge(data: any) {
    return this.create('knowledge', data)
  }

  async updateKnowledge(id: string, data: any) {
    return this.update('knowledge', id, data)
  }

  async deleteKnowledge(id: string) {
    return this.delete('knowledge', id)
  }

  // ============================================================================
  // CONVERSATIONS & MESSAGES
  // ============================================================================

  async getConversations(options?: { page?: number; page_size?: number; search?: string }) {
    return this.list('conversations', options)
  }

  async getConversation(id: string) {
    return this.get('conversations', id)
  }

  async getConversationMessages(options?: { page?: number; page_size?: number; search?: string }) {
    return this.list('conversation-messages', options)
  }

  async createConversationMessage(data: any) {
    return this.create('conversation-messages', data)
  }
}

// Export singleton instance
export const backendApiService = new BackendApiService()

export default backendApiService
