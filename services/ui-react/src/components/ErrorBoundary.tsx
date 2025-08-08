import React from 'react'

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
  errorInfo?: React.ErrorInfo
}

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ComponentType<{error: Error, resetError: () => void}>
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
    this.resetError = this.resetError.bind(this)
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error)
    console.error('Error info:', errorInfo)
    
    this.setState({
      error,
      errorInfo
    })
  }

  resetError() {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback
        return <FallbackComponent error={this.state.error!} resetError={this.resetError} />
      }

      return (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '0.5rem',
          margin: '1rem'
        }}>
          <h2 style={{ color: '#dc2626', fontSize: '1.5rem', marginBottom: '1rem' }}>
            ⚠️ Something went wrong
          </h2>
          <p style={{ color: '#7f1d1d', marginBottom: '1rem' }}>
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <details style={{ marginBottom: '1rem', textAlign: 'left' }}>
            <summary style={{ cursor: 'pointer', color: '#dc2626' }}>
              Show error details
            </summary>
            <pre style={{ 
              backgroundColor: '#fff1f1', 
              padding: '1rem', 
              borderRadius: '0.25rem',
              overflow: 'auto',
              fontSize: '0.75rem',
              marginTop: '0.5rem'
            }}>
              {this.state.error?.stack}
            </pre>
          </details>
          <button 
            onClick={this.resetError}
            style={{
              backgroundColor: '#dc2626',
              color: 'white',
              padding: '0.5rem 1rem',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer'
            }}
          >
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary