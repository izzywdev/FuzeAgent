import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FixedAgentsPage } from './FixedAgentsPage'
import { renderWithRouter, mockApiResponses, mockFetch } from '../../test/utils'

describe('FixedAgentsPage', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial Loading', () => {
    it('should show loading state initially', () => {
      // Mock pending API call
      mockFetch.success(mockApiResponses.agents)
      
      renderWithRouter(<FixedAgentsPage />)

      expect(screen.getByText('Loading agents...')).toBeInTheDocument()
    })

    it('should load agents on mount', async () => {
      mockFetch.success(mockApiResponses.agents)

      renderWithRouter(<FixedAgentsPage />)

      await waitFor(() => {
        expect(screen.getByText('AI Agents')).toBeInTheDocument()
      })

      expect(fetch).toHaveBeenCalledWith('http://localhost:8006/agents')
    })
  })

  describe('Agents Display', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.agents)

      renderWithRouter(<FixedAgentsPage />)

      await waitFor(() => {
        expect(screen.getByText('AI Agents')).toBeInTheDocument()
      })
    })

    it('should display agent cards', () => {
      expect(screen.getByText('Test Agent')).toBeInTheDocument()
      expect(screen.getByText('Test Developer')).toBeInTheDocument()
      expect(screen.getByText('active')).toBeInTheDocument()
    })

    it('should show create agent button', () => {
      const createButton = screen.getByText('Create Agent')
      expect(createButton).toBeInTheDocument()
      expect(createButton.closest('a')).toHaveAttribute('href', '/agents/create')
    })

    it('should display agent count', () => {
      expect(screen.getByText('1 Active Agents')).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('should show empty state when no agents exist', async () => {
      mockFetch.success([])

      renderWithRouter(<FixedAgentsPage />)

      await waitFor(() => {
        expect(screen.getByText('No Agents Found')).toBeInTheDocument()
      })

      expect(screen.getByText('Get started by creating your first AI agent')).toBeInTheDocument()
      expect(screen.getByText('Create Agent')).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      mockFetch.error(500, 'Server Error')

      renderWithRouter(<FixedAgentsPage />)

      await waitFor(() => {
        expect(screen.getByText('Error loading agents')).toBeInTheDocument()
      })

      expect(screen.getByText('Please try again later')).toBeInTheDocument()
    })

    it('should handle network errors', async () => {
      mockFetch.networkError()

      renderWithRouter(<FixedAgentsPage />)

      await waitFor(() => {
        expect(screen.getByText('Error loading agents')).toBeInTheDocument()
      })
    })

    it('should have retry functionality', async () => {
      mockFetch.networkError()

      renderWithRouter(<FixedAgentsPage />)

      await waitFor(() => {
        expect(screen.getByText('Error loading agents')).toBeInTheDocument()
      })

      // Mock successful retry
      mockFetch.success(mockApiResponses.agents)

      const retryButton = screen.getByText('Retry')
      await user.click(retryButton)

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument()
      })
    })
  })

  describe('Search and Filter', () => {
    beforeEach(async () => {
      const multipleAgents = [
        ...mockApiResponses.agents,
        {
          id: 'agent-2',
          name: 'Backend Agent',
          role: 'Python Developer',
          type: 'developer',
          status: 'active',
          config: {},
          created_at: '2024-01-02T00:00:00Z',
          updated_at: '2024-01-02T00:00:00Z'
        },
        {
          id: 'agent-3',
          name: 'QA Agent',
          role: 'QA Engineer',
          type: 'qa',
          status: 'inactive',
          config: {},
          created_at: '2024-01-03T00:00:00Z',
          updated_at: '2024-01-03T00:00:00Z'
        }
      ]

      mockFetch.success(multipleAgents)

      renderWithRouter(<FixedAgentsPage />)

      await waitFor(() => {
        expect(screen.getByText('AI Agents')).toBeInTheDocument()
      })
    })

    it('should filter agents by search term', async () => {
      const searchInput = screen.getByPlaceholderText('Search agents...')
      
      await user.type(searchInput, 'Backend')

      await waitFor(() => {
        expect(screen.getByText('Backend Agent')).toBeInTheDocument()
        expect(screen.queryByText('Test Agent')).not.toBeInTheDocument()
        expect(screen.queryByText('QA Agent')).not.toBeInTheDocument()
      })
    })

    it('should filter agents by status', async () => {
      const statusFilter = screen.getByRole('combobox', { name: /status/i })
      
      await user.selectOptions(statusFilter, 'inactive')

      await waitFor(() => {
        expect(screen.getByText('QA Agent')).toBeInTheDocument()
        expect(screen.queryByText('Test Agent')).not.toBeInTheDocument()
        expect(screen.queryByText('Backend Agent')).not.toBeInTheDocument()
      })
    })

    it('should filter agents by type', async () => {
      const typeFilter = screen.getByRole('combobox', { name: /type/i })
      
      await user.selectOptions(typeFilter, 'qa')

      await waitFor(() => {
        expect(screen.getByText('QA Agent')).toBeInTheDocument()
        expect(screen.queryByText('Test Agent')).not.toBeInTheDocument()
        expect(screen.queryByText('Backend Agent')).not.toBeInTheDocument()
      })
    })

    it('should clear filters', async () => {
      // Apply search filter
      const searchInput = screen.getByPlaceholderText('Search agents...')
      await user.type(searchInput, 'Backend')

      // Clear search
      await user.clear(searchInput)

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument()
        expect(screen.getByText('Backend Agent')).toBeInTheDocument()
        expect(screen.getByText('QA Agent')).toBeInTheDocument()
      })
    })
  })

  describe('Agent Actions', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.agents)

      renderWithRouter(<FixedAgentsPage />)

      await waitFor(() => {
        expect(screen.getByText('AI Agents')).toBeInTheDocument()
      })
    })

    it('should navigate to agent details', async () => {
      const agentCard = screen.getByText('Test Agent').closest('a')
      expect(agentCard).toHaveAttribute('href', '/agents/test-agent-id')
    })

    it('should show agent status badge', () => {
      const statusBadge = screen.getByText('active')
      expect(statusBadge).toHaveClass('bg-green-100', 'text-green-800')
    })

    it('should show agent type icon', () => {
      const typeIcon = screen.getByText('👨‍💻')
      expect(typeIcon).toBeInTheDocument()
    })
  })

  describe('Responsive Design', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.agents)

      renderWithRouter(<FixedAgentsPage />)

      await waitFor(() => {
        expect(screen.getByText('AI Agents')).toBeInTheDocument()
      })
    })

    it('should render agent grid layout', () => {
      const agentGrid = screen.getByRole('main').querySelector('.grid')
      expect(agentGrid).toBeInTheDocument()
    })

    it('should be accessible', () => {
      expect(screen.getByRole('main')).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'AI Agents' })).toBeInTheDocument()
      expect(screen.getByRole('searchbox')).toBeInTheDocument()
    })
  })

  describe('Performance', () => {
    it('should not make unnecessary API calls', async () => {
      mockFetch.success(mockApiResponses.agents)

      const { rerender } = renderWithRouter(<FixedAgentsPage />)

      await waitFor(() => {
        expect(screen.getByText('AI Agents')).toBeInTheDocument()
      })

      // Rerender shouldn't trigger new API call
      rerender(<FixedAgentsPage />)

      expect(fetch).toHaveBeenCalledTimes(1)
    })
  })
})