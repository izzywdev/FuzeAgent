import React, { useState } from 'react'
import { useApiService } from '../../hooks/useApiService'

interface Props {
  orgId: string
  tools: Array<{
    id: string
    key: string
    name: string
    description?: string
    default_config: Record<string, any>
    is_active: boolean
  }>
  onToolsChange: () => void
}

export function OrganizationToolsSection({ orgId, tools, onToolsChange }: Props): JSX.Element {
  const apiService = useApiService()
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingTool, setEditingTool] = useState<any>(null)
  const [formData, setFormData] = useState({
    key: '',
    name: '',
    description: '',
    default_config: '{}'
  })

  const handleCreate = async () => {
    try {
      const response = await apiService.createOrganizationTool(orgId, {
        key: formData.key,
        name: formData.name,
        description: formData.description,
        default_config: JSON.parse(formData.default_config)
      })
      if (response.ok) {
        setShowCreateForm(false)
        setFormData({ key: '', name: '', description: '', default_config: '{}' })
        onToolsChange()
      } else {
        console.error('Error creating tool:', response.status)
      }
    } catch (error) {
      console.error('Error creating tool:', error)
    }
  }

  const handleUpdate = async () => {
    if (!editingTool) return
    try {
      const response = await apiService.updateOrganizationTool(orgId, editingTool.id, {
        key: formData.key,
        name: formData.name,
        description: formData.description,
        default_config: JSON.parse(formData.default_config)
      })
      if (response.ok) {
        setEditingTool(null)
        setFormData({ key: '', name: '', description: '', default_config: '{}' })
        onToolsChange()
      } else {
        console.error('Error updating tool:', response.status)
      }
    } catch (error) {
      console.error('Error updating tool:', error)
    }
  }

  const handleDelete = async (toolId: string) => {
    if (!confirm('Are you sure you want to delete this tool?')) return
    try {
      const response = await apiService.deleteOrganizationTool(orgId, toolId)
      if (response.ok) {
        onToolsChange()
      } else {
        console.error('Error deleting tool:', response.status)
      }
    } catch (error) {
      console.error('Error deleting tool:', error)
    }
  }

  const startEdit = (tool: any) => {
    setEditingTool(tool)
    setFormData({
      key: tool.key,
      name: tool.name,
      description: tool.description || '',
      default_config: JSON.stringify(tool.default_config, null, 2)
    })
  }

  const cancelEdit = () => {
    setEditingTool(null)
    setShowCreateForm(false)
    setFormData({ key: '', name: '', description: '', default_config: '{}' })
  }

  return (
    <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', marginTop: '2rem', padding: '2rem'}}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
        <h3 style={{fontSize: '1.25rem', fontWeight: '600'}}>Organization Tools</h3>
        <button 
          onClick={() => setShowCreateForm(true)}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            fontSize: '0.875rem',
            cursor: 'pointer'
          }}
        >
          + Add Tool
        </button>
      </div>

      {/* Create/Edit Form */}
      {(showCreateForm || editingTool) && (
        <div style={{backgroundColor: '#f9fafb', border: '1px solid #d1d5db', borderRadius: '0.5rem', padding: '1.5rem', marginBottom: '1.5rem'}}>
          <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>
            {editingTool ? 'Edit Tool' : 'Create New Tool'}
          </h4>
          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem'}}>
            <div>
              <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                Tool Key
              </label>
              <input
                type="text"
                value={formData.key}
                onChange={(e) => setFormData({...formData, key: e.target.value})}
                placeholder="e.g., code_generation"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem'
                }}
              />
            </div>
            <div>
              <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                Tool Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="e.g., Code Generation"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem'
                }}
              />
            </div>
          </div>
          <div style={{marginBottom: '1rem'}}>
            <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
              Description
            </label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              placeholder="Brief description of what this tool does"
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem'
              }}
            />
          </div>
          <div style={{marginBottom: '1rem'}}>
            <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
              Default Configuration (JSON)
            </label>
            <textarea
              value={formData.default_config}
              onChange={(e) => setFormData({...formData, default_config: e.target.value})}
              placeholder='{"model": "claude-sonnet-4", "temperature": 0.7}'
              rows={4}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                fontFamily: 'monospace',
                resize: 'vertical'
              }}
            />
          </div>
          <div style={{display: 'flex', gap: '0.5rem'}}>
            <button
              onClick={editingTool ? handleUpdate : handleCreate}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                cursor: 'pointer'
              }}
            >
              {editingTool ? 'Update Tool' : 'Create Tool'}
            </button>
            <button
              onClick={cancelEdit}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Tools List */}
      <div style={{display: 'grid', gap: '1rem'}}>
        {tools.map(tool => (
          <div key={tool.id} style={{
            border: '1px solid #e5e7eb',
            borderRadius: '0.5rem',
            padding: '1rem',
            backgroundColor: tool.is_active ? 'white' : '#f9fafb'
          }}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
              <div style={{flex: 1}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem'}}>
                  <h4 style={{fontSize: '1rem', fontWeight: '600', margin: 0}}>{tool.name}</h4>
                  <span style={{
                    fontSize: '0.75rem',
                    padding: '0.25rem 0.5rem',
                    backgroundColor: tool.is_active ? '#dcfce7' : '#fee2e2',
                    color: tool.is_active ? '#15803d' : '#dc2626',
                    borderRadius: '0.25rem'
                  }}>
                    {tool.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p style={{fontSize: '0.875rem', color: '#6b7280', margin: '0 0 0.5rem 0'}}>
                  <strong>Key:</strong> {tool.key}
                </p>
                {tool.description && (
                  <p style={{fontSize: '0.875rem', color: '#6b7280', margin: '0 0 0.5rem 0'}}>
                    {tool.description}
                  </p>
                )}
                <div style={{fontSize: '0.75rem', color: '#9ca3af'}}>
                  <strong>Config:</strong> {Object.keys(tool.default_config || {}).length} properties
                </div>
              </div>
              <div style={{display: 'flex', gap: '0.5rem'}}>
                <button
                  onClick={() => startEdit(tool)}
                  style={{
                    padding: '0.25rem 0.5rem',
                    backgroundColor: 'white',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.25rem',
                    fontSize: '0.75rem',
                    cursor: 'pointer'
                  }}
                >
                  ✏️ Edit
                </button>
                <button
                  onClick={() => handleDelete(tool.id)}
                  style={{
                    padding: '0.25rem 0.5rem',
                    backgroundColor: '#fee2e2',
                    border: '1px solid #dc2626',
                    borderRadius: '0.25rem',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    color: '#dc2626'
                  }}
                >
                  🗑️ Delete
                </button>
              </div>
            </div>
          </div>
        ))}
        {tools.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '2rem',
            color: '#6b7280',
            fontSize: '0.875rem'
          }}>
            No tools configured yet. Create your first tool to get started.
          </div>
        )}
      </div>
    </div>
  )
}
