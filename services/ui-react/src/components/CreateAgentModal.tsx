import React, { useState, useCallback, useMemo } from 'react'
import { FiX, FiFileText, FiSettings } from 'react-icons/fi'
import type { AgentTemplate, CreateAgentFromTemplate, CreateCustomAgent } from '../types'

interface CreateAgentModalProps {
  templates: AgentTemplate[]
  onClose: () => void
  onSubmit: (data: CreateAgentFromTemplate | CreateCustomAgent) => Promise<void>
}

const CreateAgentModal: React.FC<CreateAgentModalProps> = React.memo(({ templates, onClose, onSubmit }) => {
  const [activeTab, setActiveTab] = useState<'template' | 'custom'>('template')
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Template form state
  const [templateForm, setTemplateForm] = useState({
    name: '',
    goal: '',
    backstory: '',
    temperature: 0.7
  })

  // Custom form state
  const [customForm, setCustomForm] = useState({
    name: '',
    role: '',
    type: 'developer',
    goal: ''
  })

  // Memoize template lookup
  const templateMap = useMemo(() => {
    return templates.reduce((map, template) => {
      map[template.template_id] = template
      return map
    }, {} as Record<string, AgentTemplate>)
  }, [templates])

  const handleTemplateChange = useCallback((templateId: string) => {
    setSelectedTemplate(templateId)
    const template = templateMap[templateId]
    if (template) {
      setTemplateForm(prev => ({
        ...prev,
        name: `${template.name} Agent`,
        goal: template.default_goal,
        backstory: template.default_backstory,
        temperature: template.default_temperature
      }))
    }
  }, [templateMap])

  const handleTemplateSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedTemplate) {
      setError('Please select a template')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const data: CreateAgentFromTemplate = {
        template_id: selectedTemplate,
        overrides: {
          name: templateForm.name,
          ...(templateForm.goal && { goal: templateForm.goal }),
          ...(templateForm.backstory && { backstory: templateForm.backstory }),
          temperature: templateForm.temperature
        }
      }
      await onSubmit(data)
    } catch (err) {
      setError('Failed to create agent from template')
    } finally {
      setLoading(false)
    }
  }, [selectedTemplate, templateForm, onSubmit])

  const handleCustomSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const data: CreateCustomAgent = {
        name: customForm.name,
        role: customForm.role,
        type: customForm.type,
        config: {
          goal: customForm.goal || `Perform ${customForm.role} tasks efficiently`,
          tools: ['code_generation', 'code_review'],
          model: 'claude-sonnet-4-20250514',
          temperature: 0.7
        }
      }
      await onSubmit(data)
    } catch (err) {
      setError('Failed to create custom agent')
    } finally {
      setLoading(false)
    }
  }, [customForm, onSubmit])

  const selectedTemplateData = useMemo(() => {
    return templateMap[selectedTemplate]
  }, [templateMap, selectedTemplate])

  // Group templates by category
  const groupedTemplates = templates.reduce((groups, template) => {
    const category = template.category
    if (!groups[category]) groups[category] = []
    groups[category].push(template)
    return groups
  }, {} as Record<string, AgentTemplate[]>)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold">Create New Agent</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <FiX className="w-6 h-6" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="p-6 pb-0">
          <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
            <button
              type="button"
              onClick={() => setActiveTab('template')}
              className={`flex-1 py-2 px-4 rounded-md font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === 'template'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <FiFileText />
              From Template
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('custom')}
              className={`flex-1 py-2 px-4 rounded-md font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === 'custom'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <FiSettings />
              Custom
            </button>
          </div>
        </div>

        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded-md">
            {error}
          </div>
        )}

        <div className="p-6">
          {activeTab === 'template' ? (
            <form onSubmit={handleTemplateSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Agent Template
                </label>
                <select
                  value={selectedTemplate}
                  onChange={(e) => handleTemplateChange(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Select a template...</option>
                  {Object.entries(groupedTemplates).map(([category, categoryTemplates]) => (
                    <optgroup key={category} label={category.replace('_', ' ').toUpperCase()}>
                      {categoryTemplates.map((template) => (
                        <option key={template.template_id} value={template.template_id}>
                          {template.name}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>

              {selectedTemplateData && (
                <div className="bg-gray-50 p-4 rounded-md">
                  <div className="mb-2">
                    <strong>Description:</strong> {selectedTemplateData.description}
                  </div>
                  <div className="text-xs text-gray-500">
                    <strong>Category:</strong> {selectedTemplateData.category.replace('_', ' ').toUpperCase()} |
                    <strong> Tools:</strong> {selectedTemplateData.tools.join(', ')}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    <strong>Skills:</strong> {selectedTemplateData.skills.join(', ')}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Agent Name
                </label>
                <input
                  type="text"
                  value={templateForm.name}
                  onChange={(e) => setTemplateForm(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Agent name"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Goal (Optional)
                </label>
                <textarea
                  value={templateForm.goal}
                  onChange={(e) => setTemplateForm(prev => ({ ...prev, goal: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 h-20 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Leave empty to use template default"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Temperature
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={templateForm.temperature}
                  onChange={(e) => setTemplateForm(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Conservative (0)</span>
                  <span>Current: {templateForm.temperature}</span>
                  <span>Creative (1)</span>
                </div>
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Creating...' : 'Create from Template'}
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 bg-gray-300 text-gray-700 py-2 rounded-md hover:bg-gray-400 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleCustomSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Agent Name
                </label>
                <input
                  type="text"
                  value={customForm.name}
                  onChange={(e) => setCustomForm(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role
                </label>
                <input
                  type="text"
                  value={customForm.role}
                  onChange={(e) => setCustomForm(prev => ({ ...prev, role: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Type
                </label>
                <select
                  value={customForm.type}
                  onChange={(e) => setCustomForm(prev => ({ ...prev, type: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="developer">Developer</option>
                  <option value="executive">Executive</option>
                  <option value="qa">QA Engineer</option>
                  <option value="designer">Designer</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Goal (Optional)
                </label>
                <textarea
                  value={customForm.goal}
                  onChange={(e) => setCustomForm(prev => ({ ...prev, goal: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 h-20 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="What should this agent focus on?"
                />
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Creating...' : 'Create Custom Agent'}
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 bg-gray-300 text-gray-700 py-2 rounded-md hover:bg-gray-400 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
})

export default CreateAgentModal