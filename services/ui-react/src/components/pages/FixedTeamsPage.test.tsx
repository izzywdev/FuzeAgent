import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { FixedTeamsPage } from './FixedTeamsPage'
import { renderWithRouter, mockFetch } from '../../test/utils'

// Mock react-router-dom navigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('FixedTeamsPage - Error Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
  })

  describe('API Response Handling', () => {
    it('should handle undefined/null API responses gracefully', async () => {
      mockFetch.success(null)
      
      renderWithRouter(<FixedTeamsPage />)
      
      await waitFor(() => {
        expect(screen.getByText(/Total Teams/)).toBeInTheDocument()
      })
      
      // Should show 0 teams when API returns null
      expect(screen.getByText('0')).toBeInTheDocument() // Total teams count
    })

    it('should handle API responses with teams property', async () => {
      const teamsResponse = {
        teams: [
          {
            id: '1',
            name: 'Test Team',
            description: 'Test Description',
            members: ['Test Member'],
            status: 'active',
            color: '#2563eb',
            team_type: 'development'
          }
        ]
      }
      
      mockFetch.success(teamsResponse)
      
      renderWithRouter(<FixedTeamsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Test Team')).toBeInTheDocument()
      })
    })

    it('should handle teams with invalid/missing members array', async () => {
      const teamsResponse = [
        {
          id: '1',
          name: 'Test Team',
          description: 'Test Description',
          members: null, // Invalid members
          status: 'active',
          color: '#2563eb'
        },
        {
          id: '2',
          name: 'Test Team 2',
          description: 'Test Description 2',
          // Missing members property
          status: 'active',
          color: '#2563eb'
        }
      ]
      
      mockFetch.success(teamsResponse)
      
      renderWithRouter(<FixedTeamsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Test Team')).toBeInTheDocument()
      })
      
      // Should show "No members assigned" for teams with invalid members
      expect(screen.getAllByText('No members assigned')).toHaveLength(2)
    })

    it('should handle network errors gracefully', async () => {
      mockFetch.networkError()
      
      renderWithRouter(<FixedTeamsPage />)
      
      await waitFor(() => {
        expect(screen.getByText(/Loading Error/)).toBeInTheDocument()
      })
      
      // Should fall back to mock data
      expect(screen.getByText('Executive Team')).toBeInTheDocument()
    })
  })

  describe('Defensive Rendering', () => {
    it('should not crash when team data is malformed during render', async () => {
      // This test simulates the scenario where data becomes corrupted during navigation
      const malformedTeams = [
        null,
        undefined,
        { id: '1' }, // Missing required fields
        {
          id: '2',
          name: 'Valid Team',
          description: 'Valid Description',
          members: ['Member 1'],
          status: 'active',
          color: '#2563eb'
        }
      ]
      
      mockFetch.success(malformedTeams)
      
      renderWithRouter(<FixedTeamsPage />)
      
      // Should render without throwing errors
      await waitFor(() => {
        expect(screen.getByText(/Total Teams/)).toBeInTheDocument()
      })
      
      // Should only show the valid team
      expect(screen.getByText('Valid Team')).toBeInTheDocument()
    })
  })
})