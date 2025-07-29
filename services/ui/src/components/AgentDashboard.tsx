import React, { useState } from 'react';

interface Agent {
  id: string;
  name: string;
  role: string;
  type: string;
  status: string;
  config: any;
  created_at: string;
}

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  assigned_to: string;
  assigned_agent_name?: string;
  created_at: string;
}

interface Props {
  agents: Agent[];
  tasks: Task[];
  onAssignTask: (agentId: string, task: any) => Promise<boolean>;
}

const AgentDashboard: React.FC<Props> = ({ agents, tasks, onAssignTask }) => {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [taskForm, setTaskForm] = useState({
    title: '',
    description: '',
    type: 'implement_feature'
  });

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'busy': return 'bg-yellow-100 text-yellow-800';
      case 'inactive': return 'bg-gray-100 text-gray-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'executive': return 'bg-blue-100 text-blue-800';
      case 'developer': return 'bg-green-100 text-green-800';
      case 'qa': return 'bg-yellow-100 text-yellow-800';
      case 'designer': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const handleAssignTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAgent) return;

    const success = await onAssignTask(selectedAgent, taskForm);
    if (success) {
      setTaskForm({ title: '', description: '', type: 'implement_feature' });
      setShowTaskForm(false);
      setSelectedAgent(null);
    }
  };

  const agentTasks = selectedAgent 
    ? tasks.filter(task => task.assigned_to === selectedAgent)
    : [];

  return (
    <div className="space-y-6">
      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-md">
              <span className="text-2xl">🤖</span>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-600">Total Agents</p>
              <p className="text-2xl font-semibold">{agents.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-md">
              <span className="text-2xl">✅</span>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-600">Active Agents</p>
              <p className="text-2xl font-semibold">
                {agents.filter(a => a.status === 'active').length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 rounded-md">
              <span className="text-2xl">📋</span>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-600">Total Tasks</p>
              <p className="text-2xl font-semibold">{tasks.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-md">
              <span className="text-2xl">⏳</span>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-600">Pending Tasks</p>
              <p className="text-2xl font-semibold">
                {tasks.filter(t => t.status === 'pending').length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Agents Grid */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold">AI Agents</h2>
          <p className="text-gray-600 mt-1">Manage your AI team members</p>
        </div>
        
        <div className="p-6">
          {agents.length === 0 ? (
            <div className="text-center py-12">
              <span className="text-4xl mb-4 block">🤖</span>
              <p className="text-gray-500">No agents found. Create your first agent to get started!</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  className={`border rounded-lg p-4 cursor-pointer transition-all hover:shadow-md ${
                    selectedAgent === agent.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  }`}
                  onClick={() => setSelectedAgent(agent.id)}
                >
                  <div className="flex justify-between items-start mb-3">
                    <h3 className="font-semibold text-lg">{agent.name}</h3>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(agent.status)}`}>
                      {agent.status}
                    </span>
                  </div>
                  
                  <p className="text-gray-600 text-sm mb-2">{agent.role}</p>
                  
                  <div className="flex justify-between items-center">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getTypeColor(agent.type)}`}>
                      {agent.type}
                    </span>
                    <span className="text-xs text-gray-500">
                      {agentTasks.length} tasks
                    </span>
                  </div>
                  
                  <div className="mt-3 text-xs text-gray-500">
                    Created: {new Date(agent.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Selected Agent Details */}
      {selectedAgent && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold">
                Agent Details: {agents.find(a => a.id === selectedAgent)?.name}
              </h2>
              <button
                onClick={() => setShowTaskForm(true)}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
              >
                Assign Task
              </button>
            </div>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-medium mb-3">Agent Information</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="font-medium">Role:</span> {agents.find(a => a.id === selectedAgent)?.role}</div>
                  <div><span className="font-medium">Type:</span> {agents.find(a => a.id === selectedAgent)?.type}</div>
                  <div><span className="font-medium">Status:</span> {agents.find(a => a.id === selectedAgent)?.status}</div>
                </div>
              </div>
              
              <div>
                <h3 className="font-medium mb-3">Recent Tasks ({agentTasks.length})</h3>
                <div className="space-y-2">
                  {agentTasks.slice(0, 3).map(task => (
                    <div key={task.id} className="text-sm p-2 bg-gray-50 rounded">
                      <div className="font-medium">{task.title}</div>
                      <div className="text-gray-600">{task.status}</div>
                    </div>
                  ))}
                  {agentTasks.length === 0 && (
                    <p className="text-gray-500 text-sm">No tasks assigned yet</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Task Assignment Modal */}
      {showTaskForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold mb-4">Assign New Task</h3>
            
            <form onSubmit={handleAssignTask} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Task Title
                </label>
                <input
                  type="text"
                  value={taskForm.title}
                  onChange={(e) => setTaskForm({...taskForm, title: e.target.value})}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={taskForm.description}
                  onChange={(e) => setTaskForm({...taskForm, description: e.target.value})}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 h-24"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Task Type
                </label>
                <select
                  value={taskForm.type}
                  onChange={(e) => setTaskForm({...taskForm, type: e.target.value})}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  <option value="implement_feature">Implement Feature</option>
                  <option value="fix_bug">Fix Bug</option>
                  <option value="code_review">Code Review</option>
                  <option value="refactor_code">Refactor Code</option>
                </select>
              </div>
              
              <div className="flex space-x-3 pt-4">
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700"
                >
                  Assign Task
                </button>
                <button
                  type="button"
                  onClick={() => setShowTaskForm(false)}
                  className="flex-1 bg-gray-300 text-gray-700 py-2 rounded-md hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentDashboard;