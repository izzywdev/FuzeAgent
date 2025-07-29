import React, { useEffect, useState } from 'react';
import AgentDashboard from './components/AgentDashboard';
import TaskManager from './components/TaskManager';
import CreateAgentForm from './components/CreateAgentForm';

interface Agent {
  id: string;
  name: string;
  role: string;
  type: string;
  status: string;
  config: any;
  created_at: string;
  updated_at: string;
}

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  assigned_to: string;
  assigned_agent_name?: string;
  created_at: string;
  completed_at?: string;
}

function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchAgents = async () => {
    try {
      const response = await fetch('/agents');
      if (response.ok) {
        const data = await response.json();
        setAgents(data);
      } else {
        setError('Failed to fetch agents');
      }
    } catch (err) {
      setError('Error connecting to server');
      console.error('Error fetching agents:', err);
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await fetch('/tasks');
      if (response.ok) {
        const data = await response.json();
        setTasks(data);
      }
    } catch (err) {
      console.error('Error fetching tasks:', err);
    }
  };

  const createAgent = async (agentConfig: any) => {
    try {
      const response = await fetch('/agents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(agentConfig),
      });
      
      if (response.ok) {
        await fetchAgents(); // Refresh agents list
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create agent');
        return false;
      }
    } catch (err) {
      setError('Error creating agent');
      console.error('Error creating agent:', err);
      return false;
    }
  };

  const assignTask = async (agentId: string, task: any) => {
    try {
      const response = await fetch(`/agents/${agentId}/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(task),
      });
      
      if (response.ok) {
        await fetchTasks(); // Refresh tasks list
        return true;
      }
      return false;
    } catch (err) {
      console.error('Error assigning task:', err);
      return false;
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchAgents(), fetchTasks()]);
      setLoading(false);
    };

    loadData();
    
    // Refresh data every 10 seconds
    const interval = setInterval(() => {
      fetchAgents();
      fetchTasks();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading FuzeAgent...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <nav className="bg-white shadow-lg border-b">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-blue-600">🤖 FuzeAgent</h1>
              <span className="ml-2 text-sm text-gray-500">AI Team Manager</span>
            </div>
            <div className="flex space-x-4 items-center">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-4 py-2 rounded-md ${
                  activeTab === 'dashboard' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-blue-600'
                }`}
              >
                Dashboard
              </button>
              <button
                onClick={() => setActiveTab('tasks')}
                className={`px-4 py-2 rounded-md ${
                  activeTab === 'tasks' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-blue-600'
                }`}
              >
                Tasks
              </button>
              <button
                onClick={() => setActiveTab('create')}
                className={`px-4 py-2 rounded-md ${
                  activeTab === 'create' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-blue-600'
                }`}
              >
                Create Agent
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex">
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
              <button 
                onClick={() => setError('')}
                className="text-red-400 hover:text-red-600 text-xs underline"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4">
        {activeTab === 'dashboard' && (
          <AgentDashboard agents={agents} tasks={tasks} onAssignTask={assignTask} />
        )}
        {activeTab === 'tasks' && (
          <TaskManager tasks={tasks} agents={agents} />
        )}
        {activeTab === 'create' && (
          <CreateAgentForm onCreateAgent={createAgent} />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto py-4 px-4 text-center text-gray-500 text-sm">
          FuzeAgent - AI Team Orchestration Platform | {agents.length} Active Agents | {tasks.length} Total Tasks
        </div>
      </footer>
    </div>
  );
}

export default App;