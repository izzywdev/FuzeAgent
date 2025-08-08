import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

// Simple component for basic testing
function TestComponent() {
  return <div>Hello Test</div>
}

describe('Basic Test Setup', () => {
  it('should render a simple component', () => {
    render(<TestComponent />)
    expect(screen.getByText('Hello Test')).toBeInTheDocument()
  })

  it('should work with basic assertions', () => {
    expect(1 + 1).toBe(2)
    expect('hello').toBe('hello')
  })
})