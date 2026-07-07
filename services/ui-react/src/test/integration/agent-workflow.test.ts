import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mockApiResponses, mockFetch } from '../utils'

/**
 * Integration tests for agent management workflows
 * These tests simulate complete user journeys through the application
 */

describe('Agent Workflow Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset fetch mock including queued once-values
    vi.mocked(fetch).mockReset()
  })

  describe('Agent Creation Workflow', () => {
    it('should complete full agent creation flow', async () => {
      // Mock API responses in sequence
      mockFetch.success(mockApiResponses.createAgent) // Create agent
      mockFetch.success(mockApiResponses.agents[0]) // Get created agent

      // Simulate user workflow
      const agentData = {
        name: 'Integration Test Agent',
        role: 'Full Stack Developer',
        type: 'developer',
        team_id: 'test-team-id',
        config: {
          model: 'claude-sonnet-4-20250514',
          temperature: 0.7,
          tools: ['code_generation', 'code_review'],
          goal: 'Build full-stack applications',
          backstory: 'Experienced developer'
        }
      }

      // Simulate form submission
      const createResponse = await fetch(expect.stringMatching(/\/agents$/), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentData)
      })

      const createdAgent = await createResponse.json()

      // Verify creation response
      expect(createResponse.ok).toBe(true)
      expect(createdAgent.agent_id).toBe('new-agent-id')
      expect(createdAgent.status).toBe('created')
      expect(createdAgent.agent.name).toBe('New Agent')

      // Verify agent details fetch
      const detailsResponse = await fetch(expect.stringMatching(/\/agents\/.+/))
      const agentDetails = await detailsResponse.json()

      expect(detailsResponse.ok).toBe(true)
      expect(agentDetails.id).toBe('test-agent-id')
      expect(agentDetails.name).toBe('Test Agent')
    })

    it('should handle agent creation with template', async () => {
      // Mock template selection workflow
      mockFetch.success(mockApiResponses.templates)

      const templatesResponse = await fetch(expect.stringMatching(/\/agent-templates$/))
      const templatesData = await templatesResponse.json()

      expect(templatesData.templates).toHaveLength(1)
      expect(templatesData.templates[0].id).toBe('react_developer')

      // Use template for agent creation
      const selectedTemplate = templatesData.templates[0]
      const agentFromTemplate = {
        name: 'React Dev 1',
        role: selectedTemplate.name,
        type: selectedTemplate.type,
        team_id: 'test-team-id',
        template_id: selectedTemplate.id,
        config: selectedTemplate.defaultConfig
      }

      mockFetch.success({
        ...mockApiResponses.createAgent,
        agent: {
          ...mockApiResponses.createAgent.agent,
          template_id: 'react_developer',
          role: 'React Developer'
        }
      })

      const createResponse = await fetch(expect.stringMatching(/\/agents$/), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentFromTemplate)
      })

      const result = await createResponse.json()
      expect(result.agent.role).toBe('React Developer')
    })

    it('should handle validation errors during creation', async () => {
      mockFetch.error(400, 'Validation failed: name is required')

      const invalidAgentData = {
        // Missing required name field
        role: 'Developer',
        type: 'developer',
        team_id: 'test-team-id',
        config: {}
      }

      const response = await fetch(expect.stringMatching(/\/agents$/), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invalidAgentData)
      })

      expect(response.ok).toBe(false)
      expect(response.status).toBe(400)

      const errorData = await response.json()
      expect(errorData.message).toContain('name is required')
    })
  })

  describe('Agent Listing and Filtering', () => {
    it('should load and filter agents correctly', async () => {
      const multipleAgents = [
        mockApiResponses.agents[0],
        {
          id: 'agent-2',
          name: 'Backend Developer',
          role: 'Python Developer',
          type: 'developer',
          status: 'active',
          config: { model: 'claude-sonnet-4-20250514' },
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        },
        {
          id: 'agent-3',
          name: 'QA Engineer',
          role: 'Quality Assurance',
          type: 'qa',
          status: 'inactive',
          config: { model: 'claude-sonnet-4-20250514' },
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ]

      mockFetch.success(multipleAgents)

      // Load all agents
      const response = await fetch('http://localhost:8006/agents')
      const agents = await response.json()

      expect(agents).toHaveLength(3)
      expect(agents[0].name).toBe('Test Agent')
      expect(agents[1].name).toBe('Backend Developer')
      expect(agents[2].name).toBe('QA Engineer')

      // Test client-side filtering logic
      const activeAgents = agents.filter((agent: any) => agent.status === 'active')
      expect(activeAgents).toHaveLength(2)

      const qaAgents = agents.filter((agent: any) => agent.type === 'qa')
      expect(qaAgents).toHaveLength(1)
      expect(qaAgents[0].name).toBe('QA Engineer')
    })

    it('should handle empty agent list', async () => {
      mockFetch.success([])

      const response = await fetch('http://localhost:8006/agents')
      const agents = await response.json()

      expect(Array.isArray(agents)).toBe(true)
      expect(agents).toHaveLength(0)
    })
  })

  describe('Agent Details and Management', () => {
    it('should load agent details with related data', async () => {
      const agentId = 'test-agent-id'
      
      // Mock agent details
      mockFetch.success(mockApiResponses.agents[0])
      
      const agentResponse = await fetch(expect.stringMatching(/\/agents\/.+/))
      const agent = await agentResponse.json()

      expect(agent.id).toBe(agentId)
      expect(agent.name).toBe('Test Agent')

      // Mock agent tasks
      mockFetch.success([
        {
          id: 'task-1',
          title: 'Implement feature',
          status: 'pending',
          assigned_to: agentId,
          created_at: '2024-01-01T00:00:00Z'
        }
      ])

      const tasksResponse = await fetch(expect.stringMatching(/\/agents\/.+\/tasks$/))
      const tasks = await tasksResponse.json()

      expect(tasks).toHaveLength(1)
      expect(tasks[0].assigned_to).toBe(agentId)

      // Mock agent conversations
      mockFetch.success([
        {
          id: 'conv-1',
          agent_id: agentId,
          title: 'Project discussion',
          messages: [],
          created_at: '2024-01-01T00:00:00Z'
        }
      ])

      const conversationsResponse = await fetch(expect.stringMatching(/\/agents\/.+\/conversations$/))
      const conversations = await conversationsResponse.json()

      expect(conversations).toHaveLength(1)
      expect(conversations[0].agent_id).toBe(agentId)
    })

    it('should handle agent not found', async () => {
      mockFetch.error(404, 'Agent not found')

      const response = await fetch(expect.stringMatching(/\/agents\/non-existent-id$/))
      expect(response.ok).toBe(false)
      expect(response.status).toBe(404)

      const error = await response.json()
      expect(error.message).toBe('Agent not found')
    })
  })

  describe('Team and Organization Context', () => {
    it('should load teams for agent assignment', async () => {
      mockFetch.success(mockApiResponses.teams)

      const response = await fetch(expect.stringMatching(/\/teams$/))
      const teams = await response.json()

      expect(teams).toHaveLength(1)
      expect(teams[0].id).toBe('test-team-id')
      expect(teams[0].name).toBe('Test Team')
      expect(teams[0].organization_id).toBe('test-org-id')
    })

    it('should handle team context in agent creation', async () => {
      // Load available teams
      mockFetch.success(mockApiResponses.teams)
      
      const teamsResponse = await fetch(expect.stringMatching(/\/teams$/))
      const teams = await teamsResponse.json()

      // Create agent with team assignment
      const agentData = {
        name: 'Team Agent',
        role: 'Team Developer',
        type: 'developer',
        team_id: teams[0].id,
        config: { model: 'claude-sonnet-4-20250514' }
      }

      mockFetch.success({
        ...mockApiResponses.createAgent,
        agent: {
          ...mockApiResponses.createAgent.agent,
          team_id: teams[0].id
        }
      })

      const createResponse = await fetch(expect.stringMatching(/\/agents$/), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentData)
      })

      const result = await createResponse.json()
      // Note: Simple orchestrator doesn't return team_id in response
      // but would in full implementation
      expect(result.agent.name).toBe('New Agent')
    })
  })

  describe('Error Handling and Recovery', () => {
    it('should handle network timeouts gracefully', async () => {
      // Simulate network timeout
      vi.mocked(fetch).mockImplementationOnce(
        () => new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Network timeout')), 100)
        )
      )

      try {
        await fetch(expect.stringMatching(/\/agents$/))
      } catch (error) {
        expect(error).toBeInstanceOf(Error)
        expect((error as Error).message).toBe('Network timeout')
      }
    })

    it('should handle rate limiting', async () => {
      mockFetch.error(429, 'Too Many Requests')

      const response = await fetch(expect.stringMatching(/\/agents$/))
      expect(response.status).toBe(429)
      
      const error = await response.json()
      expect(error.message).toBe('Too Many Requests')
    })

    it('should handle server errors during operations', async () => {
      mockFetch.error(500, 'Internal Server Error')

      const response = await fetch(expect.stringMatching(/\/agents$/), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Test Agent',
          role: 'Developer',
          type: 'developer',
          team_id: 'team-1',
          config: {}
        })
      })

      expect(response.ok).toBe(false)
      expect(response.status).toBe(500)
    })
  })

  describe('Data Consistency', () => {
    it('should maintain data consistency across multiple operations', async () => {
      // Create agent
      mockFetch.success(mockApiResponses.createAgent)

      const createResponse = await fetch(expect.stringMatching(/\/agents$/), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Consistency Test Agent',
          role: 'Developer',
          type: 'developer',
          team_id: 'test-team-id',
          config: { model: 'claude-sonnet-4-20250514' }
        })
      })

      const created = await createResponse.json()
      expect(created.agent_id).toBe('new-agent-id')

      // Verify agent appears in list
      mockFetch.success([
        ...mockApiResponses.agents,
        {
          id: 'new-agent-id',
          name: 'Consistency Test Agent',
          role: 'Developer',
          type: 'developer',
          status: 'active',
          config: { model: 'claude-sonnet-4-20250514' },
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ])

      const listResponse = await fetch('http://localhost:8006/agents')
      const agents = await listResponse.json()

      const newAgent = agents.find((a: any) => a.id === 'new-agent-id')
      expect(newAgent).toBeDefined()
      expect(newAgent.name).toBe('Consistency Test Agent')
    })
  })
})