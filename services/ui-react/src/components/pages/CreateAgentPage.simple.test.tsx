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

describe('CreateAgentPage - Simple Tests', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
  })

  describe('Basic Rendering', () => {
    it('should show loading state initially', () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      expect(screen.getByText('Loading agent creation form...')).toBeInTheDocument()
    })

    it('should load and display the form after data loads', async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })

      expect(screen.getByText('Agent Details')).toBeInTheDocument()
      expect(screen.getByText('Agent Templates')).toBeInTheDocument()
      expect(screen.getByText('Agent Configuration')).toBeInTheDocument()
    })
  })

  describe('Form Elements', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })
    })

    it('should have required form fields', () => {
      // Check for labels (not using getByLabelText due to styling implementation)
      expect(screen.getByText('Agent Name *')).toBeInTheDocument()
      expect(screen.getByText('Role *')).toBeInTheDocument()
      expect(screen.getByText('Team Assignment *')).toBeInTheDocument()
      expect(screen.getByText('Agent Type')).toBeInTheDocument()

      // Check for input fields by placeholder
      expect(screen.getByPlaceholderText('e.g., Frontend Developer 1')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('e.g., Senior React Developer')).toBeInTheDocument()
    })

    it('should display templates', () => {
      expect(screen.getByText('React Developer')).toBeInTheDocument()
      expect(screen.getByText('Frontend developer specialized in React')).toBeInTheDocument()
    })

    it('should have submit and cancel buttons', () => {
      expect(screen.getByRole('button', { name: /Create Agent/ })).toBeInTheDocument()
      expect(screen.getAllByText('Cancel')).toHaveLength(2) // Header and footer
    })
  })

  describe('Form Interaction', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })
    })

    it('should allow typing in input fields', async () => {
      const nameInput = screen.getByPlaceholderText('e.g., Frontend Developer 1')
      const roleInput = screen.getByPlaceholderText('e.g., Senior React Developer')

      await user.type(nameInput, 'Test Agent')
      await user.type(roleInput, 'Test Role')

      expect(nameInput).toHaveValue('Test Agent')
      expect(roleInput).toHaveValue('Test Role')
    })

    it('should allow template selection', async () => {
      const templateCard = screen.getByText('React Developer').parentElement!
      expect(templateCard).toBeInTheDocument()

      await user.click(templateCard)

      // Check if the template card gets highlighted (changes styling)
      await waitFor(() => {
        expect(templateCard).toHaveStyle('border: 2px solid #2563eb')
      })
    })
  })

  describe('API Integration', () => {
    beforeEach(async () => {
      mockFetch.success(mockApiResponses.teams)
      mockFetch.success(mockApiResponses.templates)

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })
    })

    it('should make initial API calls for teams and templates', () => {
      expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/teams$/))
      expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/agent-templates$/))
    })

    it('should handle form submission', async () => {
      // Fill out form
      const nameInput = screen.getByPlaceholderText('e.g., Frontend Developer 1')
      const roleInput = screen.getByPlaceholderText('e.g., Senior React Developer')
      
      await user.type(nameInput, 'Test Agent')
      await user.type(roleInput, 'Test Developer')

      // Select team
      const teamSelect = screen.getByDisplayValue('') // Empty select initially
      await user.selectOptions(teamSelect, 'test-team-id')

      // Mock API response
      mockFetch.success(mockApiResponses.createAgent)

      const submitButton = screen.getByRole('button', { name: /Create Agent/ })
      await user.click(submitButton)

      // Should show creating state
      expect(screen.getByText('Creating...')).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('should show fallback teams when API fails', async () => {
      mockFetch.networkError() // Teams API fails
      mockFetch.success(mockApiResponses.templates) // Templates succeed

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })

      // Should show mock/fallback teams
      expect(screen.getByText('Executive Team')).toBeInTheDocument()
      expect(screen.getByText('Development Team')).toBeInTheDocument()
    })

    it('should show fallback templates when API fails', async () => {
      mockFetch.success(mockApiResponses.teams) // Teams succeed
      mockFetch.networkError() // Templates API fails

      renderWithRouter(<CreateAgentPage />)

      await waitFor(() => {
        expect(screen.getByText('Create New Agent')).toBeInTheDocument()
      })

      // Should show mock/fallback templates
      expect(screen.getByText('React Developer')).toBeInTheDocument()
      expect(screen.getByText('Python Developer')).toBeInTheDocument()
    })
  })
})