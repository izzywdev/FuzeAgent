import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CreateAgentPage } from './CreateAgentPage'
import { renderWithRouter, mockApiResponses, mockFetch } from '../../test/utils'

// Mock react-router-dom navigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('CreateAgentPage', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
  })

  describe('Initial Loading', () => {
    it('should show loading state initially', () => {
      // Mock pending API calls
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      expect(screen.getByText('Loading agent creation form...')).toBeInTheDocument()
      expect(screen.getByText('🤖')).toBeInTheDocument()
    })

    it('should load teams and templates on mount', async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })

      expect(fetch).toHaveBeenCalledWith('http://localhost:8000/teams')
      expect(fetch).toHaveBeenCalledWith('http://localhost:8000/agent-templates')
    })
  })

  describe('Form Rendering', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })
    })

    it('should render all required form fields', () => {
      expect(screen.getByLabelText(/Agent Name/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Role/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Team Assignment/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Agent Type/)).toBeInTheDocument()
    })

    it('should render agent templates', () => {
      expect(screen.getByText('React Developer')).toBeInTheDocument()
      expect(screen.getByText('Frontend developer specialized in React')).toBeInTheDocument()
    })

    it('should render configuration section', () => {
      expect(screen.getByText('Agent Configuration')).toBeInTheDocument()
      expect(screen.getByLabelText(/Model/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Temperature/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Goal/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Backstory/)).toBeInTheDocument()
    })
  })

  describe('Template Selection', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })
    })

    it('should update form when template is selected', async () => {
      const templateCard = screen.getByText('React Developer').closest('div')
      expect(templateCard).toBeInTheDocument()

      await user.click(templateCard!)

      // Check if role field is updated
      const roleInput = screen.getByLabelText(/Role/) as HTMLInputElement
      expect(roleInput.value).toBe('React Developer')

      // Check if goal is updated
      const goalTextarea = screen.getByLabelText(/Goal/) as HTMLTextAreaElement
      expect(goalTextarea.value).toBe('Build React applications')
    })

    it('should highlight selected template', async () => {
      const templateCard = screen.getByText('React Developer').closest('div')
      
      await user.click(templateCard!)

      expect(templateCard).toHaveStyle('border: 2px solid #2563eb')
      expect(templateCard).toHaveStyle('background-color: #f0f9ff')
    })
  })

  describe('Form Validation', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })
    })

    it('should require agent name', async () => {
      const submitButton = screen.getByRole('button', { name: /Create Agent/ })
      
      await user.click(submitButton)

      // HTML5 validation should prevent form submission
      const nameInput = screen.getByLabelText(/Agent Name/) as HTMLInputElement
      expect(nameInput.validity.valid).toBe(false)
    })

    it('should require role', async () => {
      const nameInput = screen.getByLabelText(/Agent Name/)
      await user.type(nameInput, 'Test Agent')

      const submitButton = screen.getByRole('button', { name: /Create Agent/ })
      await user.click(submitButton)

      const roleInput = screen.getByLabelText(/Role/) as HTMLInputElement
      expect(roleInput.validity.valid).toBe(false)
    })

    it('should require team selection', async () => {
      const nameInput = screen.getByLabelText(/Agent Name/)
      const roleInput = screen.getByLabelText(/Role/)
      
      await user.type(nameInput, 'Test Agent')
      await user.type(roleInput, 'Test Role')

      const submitButton = screen.getByRole('button', { name: /Create Agent/ })
      await user.click(submitButton)

      const teamSelect = screen.getByLabelText(/Team Assignment/) as HTMLSelectElement
      expect(teamSelect.validity.valid).toBe(false)
    })
  })

  describe('Form Submission', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })
    })

    it('should submit valid form successfully', async () => {
      // Fill out the form
      const nameInput = screen.getByLabelText(/Agent Name/)
      const roleInput = screen.getByLabelText(/Role/)
      const teamSelect = screen.getByLabelText(/Team Assignment/)

      await user.type(nameInput, 'Test Agent')
      await user.type(roleInput, 'Test Developer')
      await user.selectOptions(teamSelect, 'test-team-id')

      // Mock successful API response
      mockFetch.success(mockApiResponses.createAgent)

      const submitButton = screen.getByRole('button', { name: /Create Agent/ })
      await user.click(submitButton)

      // Should show creating state
      await waitFor(() => {
        expect(screen.getByText('Creating...')).toBeInTheDocument()
      })

      // Should call API with correct data
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith('http://localhost:8000/agents', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name: 'Test Agent',
            role: 'Test Developer',
            type: 'developer',
            team_id: 'test-team-id',
            config: expect.objectContaining({
              model: 'claude-sonnet-4-20250514',
              temperature: 0.7,
              tools: [],
              goal: '',
              backstory: ''
            })
          })
        })
      })

      // Should navigate to agent details page
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/agents/new-agent-id')
      })
    })

    it('should handle API errors gracefully', async () => {
      // Fill out the form
      const nameInput = screen.getByLabelText(/Agent Name/)
      const roleInput = screen.getByLabelText(/Role/)
      const teamSelect = screen.getByLabelText(/Team Assignment/)

      await user.type(nameInput, 'Test Agent')
      await user.type(roleInput, 'Test Developer')  
      await user.selectOptions(teamSelect, 'test-team-id')

      // Mock API error
      mockFetch.error(400, 'Invalid agent data')

      const submitButton = screen.getByRole('button', { name: /Create Agent/ })
      await user.click(submitButton)

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText('Failed to create agent. Please try again.')).toBeInTheDocument()
      })

      // Should not navigate
      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('should handle network errors gracefully', async () => {
      // Fill out the form
      const nameInput = screen.getByLabelText(/Agent Name/)
      const roleInput = screen.getByLabelText(/Role/)
      const teamSelect = screen.getByLabelText(/Team Assignment/)

      await user.type(nameInput, 'Test Agent')
      await user.type(roleInput, 'Test Developer')
      await user.selectOptions(teamSelect, 'test-team-id')

      // Mock network error
      mockFetch.networkError()

      const submitButton = screen.getByRole('button', { name: /Create Agent/ })
      await user.click(submitButton)

      // Should show network error message
      await waitFor(() => {
        expect(screen.getByText('Error creating agent. Please check your connection.')).toBeInTheDocument()
      })
    })
  })

  describe('Navigation', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })
    })

    it('should render breadcrumbs correctly', () => {
      expect(screen.getByText('Agents')).toBeInTheDocument()
      expect(screen.getByText('Create Agent')).toBeInTheDocument()
    })

    it('should have working cancel buttons', () => {
      const cancelButtons = screen.getAllByText('Cancel')
      expect(cancelButtons).toHaveLength(2) // Header and footer cancel buttons
      
      cancelButtons.forEach(button => {
        expect(button.closest('a')).toHaveAttribute('href', '/agents')
      })
    })
  })

  describe('Error Handling', () => {
    it('should show mock data when teams API fails', async () => {
      mockFetch.networkError() // Teams API fails
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })

      // Should show mock teams
      const teamSelect = screen.getByLabelText(/Team Assignment/)
      expect(teamSelect).toBeInTheDocument()
      expect(screen.getByText('Executive Team')).toBeInTheDocument()
      expect(screen.getByText('Development Team')).toBeInTheDocument()
    })

    it('should show mock data when templates API fails', async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.networkError() // Templates API fails

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })

      // Should show mock templates
      expect(screen.getByText('React Developer')).toBeInTheDocument()
      expect(screen.getByText('Python Developer')).toBeInTheDocument()
    })
  })
})