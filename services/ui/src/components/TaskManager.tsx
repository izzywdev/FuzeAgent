import React from 'react';

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

interface Agent {
  id: string;
  name: string;
  role: string;
  type: string;
  status: string;
}

interface Props {
  tasks: Task[];
  agents: Agent[];
}

const TaskManager: React.FC<Props> = ({ tasks, agents }) => {
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return '✅';
      case 'in_progress': return '🔄';
      case 'pending': return '⏳';
      case 'failed': return '❌';
      default: return '❓';
    }
  };

  const groupedTasks = {
    pending: tasks.filter(t => t.status === 'pending'),
    in_progress: tasks.filter(t => t.status === 'in_progress'),
    completed: tasks.filter(t => t.status === 'completed'),
    failed: tasks.filter(t => t.status === 'failed')
  };

  return (
    <div className="space-y-6">
      {/* Task Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <span className="text-2xl mr-3">⏳</span>
            <div>
              <p className="text-sm text-gray-600">Pending</p>
              <p className="text-2xl font-semibold">{groupedTasks.pending.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <span className="text-2xl mr-3">🔄</span>
            <div>
              <p className="text-sm text-gray-600">In Progress</p>
              <p className="text-2xl font-semibold">{groupedTasks.in_progress.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <span className="text-2xl mr-3">✅</span>
            <div>
              <p className="text-sm text-gray-600">Completed</p>
              <p className="text-2xl font-semibold">{groupedTasks.completed.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <span className="text-2xl mr-3">❌</span>
            <div>
              <p className="text-sm text-gray-600">Failed</p>
              <p className="text-2xl font-semibold">{groupedTasks.failed.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Task Board */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold">Task Board</h2>
          <p className="text-gray-600 mt-1">Track all tasks across your AI team</p>
        </div>

        <div className="p-6">
          {tasks.length === 0 ? (
            <div className="text-center py-12">
              <span className="text-4xl mb-4 block">📋</span>
              <p className="text-gray-500">No tasks found. Assign tasks to your agents to get started!</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Task</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Assigned To</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Created</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Completed</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((task) => {
                    const assignedAgent = agents.find(a => a.id === task.assigned_to);
                    return (
                      <tr key={task.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-4 px-4">
                          <div>
                            <p className="font-medium text-gray-900">{task.title}</p>
                            <p className="text-sm text-gray-600 mt-1 max-w-md truncate">
                              {task.description}
                            </p>
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                            <span className="mr-1">{getStatusIcon(task.status)}</span>
                            {task.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-4 px-4">
                          {assignedAgent ? (
                            <div>
                              <p className="font-medium text-gray-900">{assignedAgent.name}</p>
                              <p className="text-sm text-gray-600">{assignedAgent.role}</p>
                            </div>
                          ) : (
                            <span className="text-gray-400">Unassigned</span>
                          )}
                        </td>
                        <td className="py-4 px-4 text-sm text-gray-600">
                          {new Date(task.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-4 px-4 text-sm text-gray-600">
                          {task.completed_at 
                            ? new Date(task.completed_at).toLocaleDateString()
                            : '-'
                          }
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold">Recent Activity</h2>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {tasks
              .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
              .slice(0, 5)
              .map((task) => {
                const assignedAgent = agents.find(a => a.id === task.assigned_to);
                return (
                  <div key={task.id} className="flex items-start space-x-3">
                    <span className="text-lg">{getStatusIcon(task.status)}</span>
                    <div className="flex-1">
                      <p className="text-sm">
                        <span className="font-medium">{task.title}</span>
                        {assignedAgent && (
                          <>
                            {' '}assigned to{' '}
                            <span className="font-medium">{assignedAgent.name}</span>
                          </>
                        )}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(task.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                );
              })}
            {tasks.length === 0 && (
              <p className="text-gray-500 text-sm">No recent activity</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskManager;