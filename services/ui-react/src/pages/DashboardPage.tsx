import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bot, Users, Activity, TrendingUp, Plus, BookOpen, Upload, FileText, MessageSquare } from 'lucide-react'
import { Layout } from '../components/layout/Layout'
import { MetricCard } from '../components/dashboard/MetricCard'
import { AgentCard } from '../components/dashboard/AgentCard'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { NotificationSystem } from '../components/NotificationSystem'
import { api } from '../config/api'

// Real data will be fetched from API
const [metrics, setMetrics] = useState({
  totalAgents: 0,
  activeAgents: 0,
  tasksCompleted: 0,
  averageResponseTime: '0s'
})

const [agents, setAgents] = useState<any[]>([])
const [recentActivity, setRecentActivity] = useState<any[]>([])

export function DashboardPage() {
  const navigate = useNavigate()
  const [knowledgeStats, setKnowledgeStats] = useState({
    totalDocuments: 0,
    recentDocuments: []
  })
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{[key: string]: number}>({})

  useEffect(() => {
    fetchKnowledgeStats()
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      // Fetch agents
      const agentsResponse = await fetch('http://localhost:8000/agents')
      if (agentsResponse.ok) {
        const agentsData = await agentsResponse.json()
        setAgents(agentsData)
        setMetrics(prev => ({
          ...prev,
          totalAgents: agentsData.length,
          activeAgents: agentsData.filter((a: any) => a.status === 'active').length
        }))
      }

      // Fetch recent activity (this would be replaced with actual API endpoint)
      // For now, set empty array
      setRecentActivity([])
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    }
  }

  const fetchKnowledgeStats = async () => {
    try {
      const response = await fetch('/api/knowledge/stats')
      if (response.ok) {
        const data = await response.json()
        setKnowledgeStats(data)
      }
    } catch (error) {
      console.error('Error fetching knowledge stats:', error)
    }
  }

  const handleAssignTask = (agentId: string) => {
    // Navigate to agent details with task assignment mode
    navigate(`/agents/${agentId}?action=assign-task`)
  }

  const handleViewDetails = (agentId: string) => {
    // Navigate to agent details page
    navigate(`/agents/${agentId}`)
  }

  const handleCreateAgent = () => {
    // Navigate to create agent page
    navigate('/agents/create')
  }

  const handleCreateTeam = () => {
    // Navigate to create team page
    navigate('/teams/create')
  }

  const handleViewAnalytics = () => {
    // Navigate to analytics page
    navigate('/analytics')
  }

  const handleUploadDocument = () => {
    setShowUploadModal(true)
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (files && files.length > 0) {
      setSelectedFiles(files)
    }
  }

  const handleFileUpload = async () => {
    if (!selectedFiles) return

    setIsUploading(true)
    const newProgress: {[key: string]: number} = {}
    
    try {
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i]
        newProgress[file.name] = 0
        setUploadProgress({...newProgress})

        const formData = new FormData()
        formData.append('file', file)
        formData.append('title', file.name)

        try {
          await api.upload('/knowledge/documents', formData)
          newProgress[file.name] = 100
          setUploadProgress({...newProgress})
          
          console.log(`Uploaded ${file.name} successfully`)
        } catch (error) {
          console.error(`Failed to upload ${file.name}:`, error)
          newProgress[file.name] = -1 // Error state
          setUploadProgress({...newProgress})
        }
      }

      // Refresh knowledge stats after upload
      await fetchKnowledgeStats()
      
      setTimeout(() => {
        setShowUploadModal(false)
        setSelectedFiles(null)
        setUploadProgress({})
      }, 1000)

    } catch (error) {
      console.error('Upload error:', error)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Layout 
      title="Dashboard" 
      subtitle="Manage your AI agents and monitor team performance"
    >
      <div className="space-y-6">
        {/* Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard
            title="Total Agents"
            value={metrics.totalAgents}
            change={{ value: '+2', type: 'increase' }}
            icon={<Bot className="w-6 h-6 text-primary" />}
          />
          <MetricCard
            title="Active Agents"
            value={metrics.activeAgents}
            change={{ value: '+1', type: 'increase' }}
            icon={<Activity className="w-6 h-6 text-primary" />}
          />
          <MetricCard
            title="Tasks Completed"
            value={metrics.tasksCompleted}
            change={{ value: '+12%', type: 'increase' }}
            icon={<TrendingUp className="w-6 h-6 text-primary" />}
          />
          <MetricCard
            title="Avg Response Time"
            value={metrics.averageResponseTime}
            change={{ value: '-0.5s', type: 'increase' }}
            icon={<Users className="w-6 h-6 text-primary" />}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Active Agents */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-foreground">Active Agents</h2>
              <Button size="sm" onClick={handleCreateAgent}>
                <Plus className="w-4 h-4 mr-2" />
                Create Agent
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {agents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  onAssignTask={handleAssignTask}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div>
            <h2 className="text-xl font-semibold text-foreground mb-4">Recent Activity</h2>
            <Card>
              <CardHeader>
                <CardTitle>Activity Feed</CardTitle>
                <CardDescription>Latest updates from your AI team</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recentActivity.map((activity) => (
                    <div key={activity.id} className="flex items-start space-x-3 p-3 rounded-lg hover:bg-accent/50 transition-colors">
                      <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                        activity.status === 'success' ? 'bg-green-500' :
                        activity.status === 'error' ? 'bg-red-500' :
                        'bg-blue-500'
                      }`}></div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-foreground">
                            {activity.agent}
                          </p>
                          <Badge variant="outline" className="text-xs">
                            {activity.time}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {activity.message}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Knowledge Management Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Knowledge Base Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="w-5 h-5" />
                Knowledge Base
              </CardTitle>
              <CardDescription>
                Manage documents and knowledge for your AI agents
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-accent/50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-primary" />
                    <div>
                      <p className="font-medium">Total Documents</p>
                      <p className="text-sm text-muted-foreground">{knowledgeStats.totalDocuments} files</p>
                    </div>
                  </div>
                  <Button size="sm" onClick={handleUploadDocument}>
                    <Upload className="w-4 h-4 mr-2" />
                    Upload
                  </Button>
                </div>
                
                {knowledgeStats.recentDocuments.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">Recent Documents</h4>
                    <div className="space-y-2">
                      {knowledgeStats.recentDocuments.slice(0, 3).map((doc: any) => (
                        <div key={doc.id} className="flex items-center justify-between p-2 border rounded">
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-muted-foreground" />
                            <span className="text-sm">{doc.title}</span>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {doc.type}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Agent Conversations */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5" />
                Agent Conversations
              </CardTitle>
              <CardDescription>
                Recent chat activity with your AI agents
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="text-center py-8 text-muted-foreground">
                  <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No recent conversations</p>
                  <p className="text-xs">Start chatting with agents to see activity here</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks and shortcuts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2" onClick={handleCreateAgent}>
                <Bot className="w-8 h-8" />
                <span>Deploy New Agent</span>
              </Button>
              <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2" onClick={handleCreateTeam}>
                <Users className="w-8 h-8" />
                <span>Create Team</span>
              </Button>
              <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2" onClick={handleUploadDocument}>
                <BookOpen className="w-8 h-8" />
                <span>Upload Knowledge</span>
              </Button>
              <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2" onClick={handleViewAnalytics}>
                <Activity className="w-8 h-8" />
                <span>View Analytics</span>
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Upload Modal */}
        {showUploadModal && (
          <div style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}>
            <div style={{
              backgroundColor: 'white',
              borderRadius: '0.5rem',
              padding: '2rem',
              maxWidth: '500px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto'
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1.5rem'
              }}>
                <h2 style={{fontSize: '1.25rem', fontWeight: '600'}}>Upload Knowledge</h2>
                <button
                  onClick={() => setShowUploadModal(false)}
                  style={{
                    padding: '0.25rem',
                    backgroundColor: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '1.5rem'
                  }}
                >
                  ×
                </button>
              </div>
              
              <div style={{textAlign: 'center', padding: '2rem', border: '2px dashed #d1d5db', borderRadius: '0.5rem'}}>
                <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                <p style={{marginBottom: '0.5rem'}}>Drag and drop files here, or click to browse</p>
                <p style={{fontSize: '0.875rem', color: '#6b7280'}}>
                  Supports PDF, DOCX, TXT, MD, HTML, and JSON files
                </p>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.docx,.doc,.txt,.md,.html,.json"
                  style={{display: 'none'}}
                  id="file-upload"
                  onChange={handleFileSelect}
                />
                <label
                  htmlFor="file-upload"
                  style={{
                    display: 'inline-block',
                    marginTop: '1rem',
                    padding: '0.5rem 1rem',
                    backgroundColor: '#3b82f6',
                    color: 'white',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    border: 'none'
                  }}
                >
                  Choose Files
                </label>
              </div>

              {selectedFiles && selectedFiles.length > 0 && (
                <div style={{marginTop: '1rem', padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem'}}>
                  <h4 style={{fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem'}}>Selected Files:</h4>
                  {Array.from(selectedFiles).map((file, index) => (
                    <div key={index} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem'}}>
                      <span style={{fontSize: '0.875rem'}}>{file.name}</span>
                      <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                        <span style={{fontSize: '0.75rem', color: '#6b7280'}}>
                          {(file.size / 1024 / 1024).toFixed(1)} MB
                        </span>
                        {uploadProgress[file.name] !== undefined && (
                          <div style={{
                            width: '60px',
                            height: '4px',
                            backgroundColor: '#e5e7eb',
                            borderRadius: '2px',
                            overflow: 'hidden'
                          }}>
                            <div style={{
                              width: `${Math.max(0, uploadProgress[file.name])}%`,
                              height: '100%',
                              backgroundColor: uploadProgress[file.name] === -1 ? '#dc2626' : uploadProgress[file.name] === 100 ? '#16a34a' : '#3b82f6',
                              transition: 'width 0.3s ease'
                            }}></div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              <div style={{marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem'}}>
                <Button variant="outline" onClick={() => {
                  setShowUploadModal(false)
                  setSelectedFiles(null)
                  setUploadProgress({})
                }} disabled={isUploading}>
                  Cancel
                </Button>
                <Button 
                  onClick={handleFileUpload}
                  disabled={!selectedFiles || selectedFiles.length === 0 || isUploading}
                  style={{
                    opacity: (!selectedFiles || selectedFiles.length === 0 || isUploading) ? 0.5 : 1
                  }}
                >
                  {isUploading ? 'Uploading...' : 'Upload Files'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Global Notification System */}
      <NotificationSystem maxNotifications={5} />
    </Layout>
  )
}