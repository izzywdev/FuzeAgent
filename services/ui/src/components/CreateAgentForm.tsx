import React, { useState } from 'react';

interface Props {
  onCreateAgent: (agentConfig: any) => Promise<boolean>;
}

const CreateAgentForm: React.FC<Props> = ({ onCreateAgent }) => {
  const [formData, setFormData] = useState({
    name: '',
    role: '',
    type: 'developer',
    goal: '',
    backstory: '',
    tools: [] as string[],
    model: 'claude-sonnet-4-20250514',
    temperature: 0.7
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const agentTypes = [
    { value: 'executive', label: 'Executive', description: 'Strategic planning and team management' },
    { value: 'developer', label: 'Developer', description: 'Code implementation and technical tasks' },
    { value: 'qa', label: 'QA Engineer', description: 'Testing and quality assurance' },
    { value: 'designer', label: 'Designer', description: 'UI/UX design and mockups' },
    { value: 'support', label: 'Support', description: 'Customer support and troubleshooting' }
  ];

  const toolOptions = {
    executive: ['strategic_planning', 'resource_allocation', 'team_management', 'project_oversight'],
    developer: ['code_generation', 'code_review', 'debugging', 'testing', 'refactoring'],
    qa: ['test_generation', 'test_execution', 'bug_reporting', 'performance_testing'],
    designer: ['mockup_generation', 'design_review', 'accessibility_check', 'user_research'],
    support: ['ticket_handling', 'knowledge_search', 'customer_response', 'documentation']
  };

  const modelOptions = [
    { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4 (Recommended)' },
    { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
    { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku (Fast)' }
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const agentConfig = {
      name: formData.name,
      role: formData.role,
      type: formData.type,
      config: {
        goal: formData.goal || `Perform ${formData.role} tasks efficiently and effectively`,
        backstory: formData.backstory || `Expert ${formData.type} with deep knowledge and experience`,
        tools: formData.tools,
        model: formData.model,
        temperature: formData.temperature
      }
    };

    const success = await onCreateAgent(agentConfig);
    
    if (success) {
      // Reset form
      setFormData({
        name: '',
        role: '',
        type: 'developer',
        goal: '',
        backstory: '',
        tools: [],
        model: 'claude-sonnet-4-20250514',
        temperature: 0.7
      });
    }
    
    setIsSubmitting(false);
  };

  const handleToolToggle = (tool: string) => {
    setFormData(prev => ({
      ...prev,
      tools: prev.tools.includes(tool)
        ? prev.tools.filter(t => t !== tool)
        : [...prev.tools, tool]
    }));
  };

  const selectedTypeInfo = agentTypes.find(type => type.value === formData.type);
  const availableTools = toolOptions[formData.type as keyof typeof toolOptions] || [];

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold">Create New AI Agent</h2>
          <p className="text-gray-600 mt-1">Add a new team member to your AI workforce</p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Basic Information</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Agent Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Frontend Dev 1"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Role Description *
              </label>
              <input
                type="text"
                value={formData.role}
                onChange={(e) => setFormData({...formData, role: e.target.value})}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Senior React Developer"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Agent Type *
              </label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({...formData, type: e.target.value, tools: []})}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {agentTypes.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
              {selectedTypeInfo && (
                <p className="text-sm text-gray-600 mt-1">{selectedTypeInfo.description}</p>
              )}
            </div>
          </div>

          {/* Agent Configuration */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Agent Configuration</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Primary Goal
              </label>
              <textarea
                value={formData.goal}
                onChange={(e) => setFormData({...formData, goal: e.target.value})}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="What is this agent's primary objective? (optional - will use default if empty)"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Backstory
              </label>
              <textarea
                value={formData.backstory}
                onChange={(e) => setFormData({...formData, backstory: e.target.value})}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Describe the agent's background and expertise (optional)"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tools & Capabilities
              </label>
              <div className="grid grid-cols-2 gap-2">
                {availableTools.map(tool => (
                  <label key={tool} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.tools.includes(tool)}
                      onChange={() => handleToolToggle(tool)}
                      className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="text-sm text-gray-700">
                      {tool.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* AI Model Configuration */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">AI Model Configuration</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Language Model
              </label>
              <select
                value={formData.model}
                onChange={(e) => setFormData({...formData, model: e.target.value})}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {modelOptions.map(model => (
                  <option key={model.value} value={model.value}>{model.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Creativity Level (Temperature): {formData.temperature}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={formData.temperature}
                onChange={(e) => setFormData({...formData, temperature: parseFloat(e.target.value)})}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>More Focused (0.0)</span>
                <span>More Creative (1.0)</span>
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <div className="pt-6 border-t border-gray-200">
            <button
              type="submit"
              disabled={isSubmitting}
              className={`w-full py-3 px-4 rounded-md font-medium ${
                isSubmitting
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              } text-white transition-colors`}
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating Agent...
                </span>
              ) : (
                'Create Agent'
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Help Section */}
      <div className="mt-6 bg-blue-50 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">💡 Tips for Creating Effective Agents</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Give your agent a clear, descriptive name and role</li>
          <li>• Select appropriate tools based on the agent's responsibilities</li>
          <li>• Use lower temperature (0.3-0.5) for precise tasks, higher (0.7-0.9) for creative work</li>
          <li>• Developer agents automatically get access to Claude Code SDK</li>
        </ul>
      </div>
    </div>
  );
};

export default CreateAgentForm;