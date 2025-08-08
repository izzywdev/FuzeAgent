import { render, RenderOptions, RenderResult } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { ReactElement, ReactNode } from 'react'
import { vi } from 'vitest'

// Test data factories
export const mockAgent = {
  id: 'test-agent-id',
  name: 'Test Agent',
  role: 'Test Developer',
  type: 'developer',
  status: 'active',
  config: {
    model: 'claude-sonnet-4-20250514',
    temperature: 0.7,
    tools: ['code_generation', 'code_review'],
    goal: 'Test goal',
    backstory: 'Test backstory'
  },
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
}

export const mockTeam = {
  id: 'test-team-id',
  name: 'Test Team',
  description: 'Test team for testing',
  organization_id: 'test-org-id',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
}

export const mockTemplate = {
  id: 'react_developer',
  name: 'React Developer',
  description: 'Frontend developer specialized in React',
  type: 'developer',
  defaultConfig: {
    model: 'claude-sonnet-4-20250514',
    temperature: 0.7,
    tools: ['code_generation', 'code_review'],
    goal: 'Build React applications',
    backstory: 'Experienced React developer'
  }
}

export const mockOrganization = {
  id: 'test-org-id',
  name: 'Test Organization',
  description: 'Test organization for testing',
  settings: {},
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
}

// Mock API responses
export const mockApiResponses = {
  agents: [mockAgent],
  teams: [mockTeam],
  templates: { templates: [mockTemplate] },
  organizations: [mockOrganization],
  createAgent: {
    agent_id: 'new-agent-id',
    status: 'created',
    agent: {
      ...mockAgent,
      id: 'new-agent-id',
      name: 'New Agent'
    }
  }
}

// Custom render function with router wrapper
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: string[]
}

function AllTheProviders({ children, initialEntries = ['/'] }: { children: ReactNode, initialEntries?: string[] }) {
  return (
    <BrowserRouter>
      {children}
    </BrowserRouter>
  )
}

export function renderWithRouter(ui: ReactElement, options: CustomRenderOptions = {}): RenderResult {
  const { initialEntries, ...renderOptions } = options
  return render(ui, {
    wrapper: ({ children }) => <AllTheProviders children={children} initialEntries={initialEntries} />,
    ...renderOptions,
  })
}

// API mocking utilities
export const mockFetch = {
  success: (data: any) => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(data),
      status: 200,
      statusText: 'OK',
    } as Response)
  },

  error: (status = 500, message = 'Internal Server Error') => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ message }),
      status,
      statusText: message,
    } as Response)
  },

  networkError: () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error('Network Error'))
  }
}

// Wait for async operations
export const waitForLoading = () => new Promise(resolve => setTimeout(resolve, 0))

// Test IDs for consistent element selection
export const testIds = {
  // Agent page elements
  agentCard: (agentId: string) => `agent-card-${agentId}`,
  agentName: (agentId: string) => `agent-name-${agentId}`,
  agentStatus: (agentId: string) => `agent-status-${agentId}`,
  createAgentButton: 'create-agent-button',
  
  // Create agent form elements
  agentNameInput: 'agent-name-input',
  agentRoleInput: 'agent-role-input',
  agentTypeSelect: 'agent-type-select',
  teamSelect: 'team-select',
  templateCard: (templateId: string) => `template-card-${templateId}`,
  submitButton: 'submit-button',
  cancelButton: 'cancel-button',
  
  // Navigation elements
  navLink: (path: string) => `nav-link-${path}`,
  breadcrumb: 'breadcrumb',
  
  // Common elements
  loadingSpinner: 'loading-spinner',
  errorMessage: 'error-message',
  successMessage: 'success-message',
}

// Custom matchers for better assertions
export const customMatchers = {
  toBeLoading: (element: HTMLElement) => {
    const isLoading = element.textContent?.includes('Loading') || 
                     element.querySelector('[data-testid="loading-spinner"]') !== null
    return {
      pass: isLoading,
      message: () => isLoading ? 
        'Expected element not to be loading' : 
        'Expected element to be loading'
    }
  },

  toHaveError: (element: HTMLElement, errorText?: string) => {
    const errorElement = element.querySelector('[data-testid="error-message"]')
    const hasError = errorElement !== null
    const hasCorrectText = errorText ? errorElement?.textContent?.includes(errorText) : true
    
    return {
      pass: hasError && hasCorrectText,
      message: () => hasError && hasCorrectText ?
        `Expected element not to have error${errorText ? ` "${errorText}"` : ''}` :
        `Expected element to have error${errorText ? ` "${errorText}"` : ''}`
    }
  }
}

// Extend expect with custom matchers
declare global {
  namespace Vi {
    interface JestAssertion<T = any> {
      toBeLoading(): T
      toHaveError(errorText?: string): T
    }
  }
}

// User interaction helpers
export const userInteractions = {
  fillForm: async (user: any, formData: Record<string, string>) => {
    for (const [field, value] of Object.entries(formData)) {
      const element = document.querySelector(`[data-testid="${field}"]`) as HTMLInputElement
      if (element) {
        await user.clear(element)
        await user.type(element, value)
      }
    }
  },

  selectOption: async (user: any, selectTestId: string, optionText: string) => {
    const select = document.querySelector(`[data-testid="${selectTestId}"]`)
    if (select) {
      await user.click(select)
      const option = document.querySelector(`option:contains("${optionText}")`)
      if (option) {
        await user.click(option)
      }
    }
  },

  clickButton: async (user: any, buttonTestId: string) => {
    const button = document.querySelector(`[data-testid="${buttonTestId}"]`)
    if (button) {
      await user.click(button)
    }
  }
}