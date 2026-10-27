import React, { useState } from 'react'
import { FiX } from 'react-icons/fi'
import { Button } from '../design-system'

interface AssignTaskModalProps {
  agentId: string
  agentName: string
  onClose: () => void
  onSubmit: (taskData: any) => Promise<void>
}

export const AssignTaskModal: React.FC<AssignTaskModalProps> = ({
  agentId,
  agentName,
  onClose,
  onSubmit
}) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    type: 'implement_feature',
    priority: 5
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim() || !formData.description.trim()) {
      setError('Title and description are required')
      return
    }

    try {
      setLoading(true)
      setError(null)
      await onSubmit({
        ...formData,
        agent_id: agentId,
        status: 'pending'
      })
      onClose()
    } catch (err: any) {
      setError(err?.message || 'Failed to assign task')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div 
      className="modal-overlay"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        zIndex: 99999,
      }}
    >
      <div 
        className="modal-dialog panel"
        style={{
          width: '100%',
          maxWidth: '480px',
          backgroundColor: 'var(--bg-secondary, #0b0e15)',
          borderColor: 'var(--border-color, #232c3d)',
          borderRadius: 'var(--radius-xl, 14px)',
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.75)',
          color: 'var(--text-primary, #e7ecf5)',
        }}
      >
        <div 
          className="p-5 border-b flex justify-between items-center"
          style={{ borderColor: 'var(--border-color, #232c3d)' }}
        >
          <h3 className="text-base font-bold m-0" style={{ color: 'var(--text-primary, #e7ecf5)' }}>
            Assign Task to {agentName}
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg opacity-60 hover:opacity-100 transition-colors"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mx-5 mt-4 p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          <div>
            <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>
              Task Title *
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border bg-transparent outline-none focus:border-indigo-500"
              style={{ 
                borderColor: 'var(--border-color, #232c3d)', 
                backgroundColor: 'var(--bg-quaternary, #1c2433)',
                color: 'var(--text-primary, #e7ecf5)'
              }}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>
              Description *
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border bg-transparent outline-none focus:border-indigo-500"
              style={{ 
                borderColor: 'var(--border-color, #232c3d)', 
                backgroundColor: 'var(--bg-quaternary, #1c2433)',
                color: 'var(--text-primary, #e7ecf5)'
              }}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>
              Task Type
            </label>
            <select
              value={formData.type}
              onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border bg-transparent outline-none"
              style={{ 
                borderColor: 'var(--border-color, #232c3d)', 
                backgroundColor: 'var(--bg-tertiary, #141a26)',
                color: 'var(--text-primary, #e7ecf5)'
              }}
            >
              <option value="implement_feature">Implement Feature</option>
              <option value="fix_bug">Fix Bug</option>
              <option value="code_review">Code Review</option>
              <option value="refactor_code">Refactor Code</option>
              <option value="documentation">Documentation</option>
              <option value="testing">Testing</option>
            </select>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>Priority (1-10)</span>
              <span className="font-mono text-cyan-400 font-bold">{formData.priority}</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              value={formData.priority}
              onChange={(e) => setFormData(prev => ({ ...prev, priority: parseInt(e.target.value) }))}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
              <span>Low (1)</span>
              <span>High (10)</span>
            </div>
          </div>

          <div className="flex gap-3 pt-3">
            <Button
              type="submit"
              variant="seam"
              size="md"
              loading={loading}
              style={{ flex: 1 }}
            >
              Assign Task
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={onClose}
              style={{ flex: 1 }}
            >
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default AssignTaskModal