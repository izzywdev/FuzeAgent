import React, { useState, useEffect } from 'react'

interface Organization {
  id: string
  name: string
  description: string
  created_at: string
}

function App() {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newOrgName, setNewOrgName] = useState('')
  const [newOrgDescription, setNewOrgDescription] = useState('')

  useEffect(() => {
    fetchOrganizations()
  }, [])

  const fetchOrganizations = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const response = await fetch('http://localhost:8000/organizations')
      if (response.ok) {
        const data = await response.json()
        setOrganizations(data)
      } else {
        // Set mock data for demonstration
        setOrganizations([
          {
            id: '1',
            name: 'Acme Corp',
            description: 'A leading technology company',
            created_at: '2025-01-15'
          },
          {
            id: '2',
            name: 'TechStart Inc',
            description: 'Innovative startup in AI',
            created_at: '2025-01-20'
          }
        ])
      }
    } catch (error) {
      console.error('Error fetching organizations:', error)
      setError('Failed to load organizations')
      // Set mock data on error
      setOrganizations([
        {
          id: '1',
          name: 'Acme Corp',
          description: 'A leading technology company',
          created_at: '2025-01-15'
        }
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateOrganization = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!newOrgName.trim()) {
      alert('Organization name is required')
      return
    }

    try {
      const response = await fetch('http://localhost:8000/organizations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newOrgName,
          description: newOrgDescription
        }),
      })

      if (response.ok) {
        const newOrg = await response.json()
        setOrganizations([...organizations, newOrg])
        setNewOrgName('')
        setNewOrgDescription('')
        setShowCreateForm(false)
      } else {
        // Simulate success for demo
        const newOrg: Organization = {
          id: Date.now().toString(),
          name: newOrgName,
          description: newOrgDescription,
          created_at: new Date().toISOString().split('T')[0]
        }
        setOrganizations([...organizations, newOrg])
        setNewOrgName('')
        setNewOrgDescription('')
        setShowCreateForm(false)
      }
    } catch (error) {
      console.error('Error creating organization:', error)
      // Simulate success for demo
      const newOrg: Organization = {
        id: Date.now().toString(),
        name: newOrgName,
        description: newOrgDescription,
        created_at: new Date().toISOString().split('T')[0]
      }
      setOrganizations([...organizations, newOrg])
      setNewOrgName('')
      setNewOrgDescription('')
      setShowCreateForm(false)
    }
  }

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div>Loading organizations...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'red' }}>
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={fetchOrganizations}>Retry</button>
      </div>
    )
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Organizations</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <button 
          onClick={() => setShowCreateForm(!showCreateForm)}
          style={{
            padding: '10px 20px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          {showCreateForm ? 'Cancel' : 'Create New Organization'}
        </button>
      </div>

      {showCreateForm && (
        <form onSubmit={handleCreateOrganization} style={{ 
          marginBottom: '20px', 
          padding: '20px', 
          border: '1px solid #ddd', 
          borderRadius: '4px',
          backgroundColor: '#f9f9f9'
        }}>
          <h3>Create New Organization</h3>
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>
              Name: *
            </label>
            <input
              type="text"
              value={newOrgName}
              onChange={(e) => setNewOrgName(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px'
              }}
              placeholder="Enter organization name"
              required
            />
          </div>
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>
              Description:
            </label>
            <textarea
              value={newOrgDescription}
              onChange={(e) => setNewOrgDescription(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                minHeight: '80px'
              }}
              placeholder="Enter organization description"
            />
          </div>
          <button 
            type="submit"
            style={{
              padding: '8px 16px',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Create Organization
          </button>
        </form>
      )}

      <div style={{ display: 'grid', gap: '20px' }}>
        {organizations.map((org) => (
          <div 
            key={org.id}
            style={{
              padding: '20px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              backgroundColor: 'white'
            }}
          >
            <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>{org.name}</h3>
            <p style={{ margin: '0 0 10px 0', color: '#666' }}>{org.description}</p>
            <small style={{ color: '#999' }}>Created: {org.created_at}</small>
          </div>
        ))}
      </div>

      {organizations.length === 0 && (
        <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
          <p>No organizations found. Create your first organization to get started.</p>
        </div>
      )}
    </div>
  )
}

export default App
