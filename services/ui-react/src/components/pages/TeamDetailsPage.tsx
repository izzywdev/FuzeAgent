import { useState, useEffect } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'

interface TeamMember {
  id: string
  name: string
  role: string
  type: string
  status: string
  joinedDate: string
  performance: {
    tasksCompleted: number
    tasksActive: number
    efficiency: string
  }
}

interface KnowledgeDocument {
  id: string
  title: string
  filename: string
  type: 'document' | 'link' | 'text'
  mime_type?: string
  size?: number
  status: 'active' | 'processing' | 'error'
  upload_date: string
  last_modified: string
  content_preview?: string
  tags: string[]
  source_url?: string
  team_id?: string
  word_count?: number
  extracted_text?: string
}

interface Team {
  id: string
  name: string
  description: string
  color: string
  status: string
  created: string
  members: TeamMember[]
  stats: {
    totalTasks: number
    completedTasks: number
    activeTasks: number
    avgResponseTime: string
  }
  knowledgeBase: KnowledgeDocument[]
}

export function TeamDetailsPage() {
  const { teamId } = useParams<{ teamId: string }>()
  const navigate = useNavigate()
  const [team, setTeam] = useState<Team | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  const [showUpload, setShowUpload] = useState(false)
  const [knowledgeDocs, setKnowledgeDocs] = useState<KnowledgeDocument[]>([])
  const [uploading, setUploading] = useState(false)
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocument | null>(null)
  const [showDocumentViewer, setShowDocumentViewer] = useState(false)
  const [documentContent, setDocumentContent] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  // Display error if there is one
  if (error) {
    return (
      <div style={{minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center'}}>
          <div style={{fontSize: '2rem', marginBottom: '1rem'}}>⚠️</div>
          <p style={{color: '#dc2626', marginBottom: '1rem'}}>{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  useEffect(() => {
    if (!teamId) return

    // Load team data from API
    const loadTeamData = async () => {
      try {
        const response = await fetch(`http://localhost:8006/teams/${teamId}`)
        if (response.ok) {
          const teamData = await response.json()
          setTeam(teamData)
        } else {
          setError('Failed to load team data')
        }
      } catch (err) {
        setError('Error loading team data')
      } finally {
        setLoading(false)
        if (teamId) {
          loadKnowledgeDocuments()
        }
      }
    }

    loadTeamData()
  }, [teamId])

  // Load knowledge documents for the team
  const loadKnowledgeDocuments = async () => {
    if (!teamId) return
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/teams/${teamId}/documents`)
      if (response.ok) {
        const documents = await response.json()
        setKnowledgeDocs(documents)
      } else {
        console.error('Failed to load team documents')
      }
    } catch (error) {
      console.error('Error loading team documents:', error)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0 || !teamId) return

    setUploading(true)
    
    for (const file of Array.from(files)) {
      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('title', file.name)
        
        const response = await fetch(`http://localhost:8000/knowledge/teams/${teamId}/documents`, {
          method: 'POST',
          body: formData
        })
        
        if (response.ok) {
          console.log(`Uploaded ${file.name} successfully`)
        } else {
          console.error(`Failed to upload ${file.name}`)
        }
      } catch (error) {
        console.error(`Error uploading ${file.name}:`, error)
      }
    }
    
    setUploading(false)
    setShowUpload(false)
    await loadKnowledgeDocuments() // Reload documents
    
    // Reset file input
    event.target.value = ''
  }

  const handleUrlUpload = async () => {
    if (!teamId) return
    
    const url = prompt('Enter URL:')
    if (!url) return

    setUploading(true)
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/teams/${teamId}/url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url })
      })
      
      if (response.ok) {
        console.log('URL added successfully')
        await loadKnowledgeDocuments()
      } else {
        console.error('Failed to add URL')
      }
    } catch (error) {
      console.error('Error adding URL:', error)
    }
    
    setUploading(false)
    setShowUpload(false)
  }

  const handleDocumentClick = async (doc: KnowledgeDocument) => {
    if (!teamId) return
    
    setSelectedDocument(doc)
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/teams/${teamId}/documents/${doc.id}/content`)
      if (response.ok) {
        const data = await response.json()
        setDocumentContent(data.content)
        setShowDocumentViewer(true)
      } else {
        console.error('Failed to load document content')
      }
    } catch (error) {
      console.error('Error loading document content:', error)
    }
  }

  const handleDocumentDelete = async (docId: string) => {
    if (!teamId || !confirm('Are you sure you want to delete this document?')) return
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/teams/${teamId}/documents/${docId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        await loadKnowledgeDocuments()
      } else {
        console.error('Failed to delete document')
      }
    } catch (error) {
      console.error('Error deleting document:', error)
    }
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (loading) {
    return (
      <div style={{minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center'}}>
          <div style={{fontSize: '2rem', marginBottom: '1rem'}}>👥</div>
          <p style={{color: '#6b7280'}}>Loading team details...</p>
        </div>
      </div>
    )
  }

  if (!team) {
    return (
      <div style={{minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center'}}>
          <div style={{fontSize: '2rem', marginBottom: '1rem'}}>❌</div>
          <p style={{color: '#ef4444', marginBottom: '1rem'}}>Team not found</p>
          <Link to="/teams" style={{color: '#2563eb', textDecoration: 'none', fontSize: '0.875rem'}}>
            ← Back to Teams
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div style={{minHeight: '100vh', backgroundColor: '#f9fafb'}}>
      {/* Navigation */}
      <nav style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
        <div style={{maxWidth: '80rem', margin: '0 auto', padding: '0 1rem'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '4rem'}}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <Link to="/" style={{display: 'flex', alignItems: 'center', textDecoration: 'none'}}>
                <div style={{
                  width: '2rem', 
                  height: '2rem', 
                  backgroundColor: '#2563eb', 
                  borderRadius: '0.5rem', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  marginRight: '0.75rem'
                }}>
                  <span style={{color: 'white', fontWeight: 'bold'}}>F</span>
                </div>
                <h1 style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#111827'}}>FuzeAgent</h1>
              </Link>
              
              {/* Breadcrumbs */}
              <div style={{display: 'flex', alignItems: 'center', marginLeft: '1.5rem', color: '#6b7280', fontSize: '0.875rem'}}>
                <Link to="/teams" style={{color: '#6b7280', textDecoration: 'none'}}>Teams</Link>
                <span style={{margin: '0 0.5rem'}}>›</span>
                <span style={{color: '#111827'}}>{team.name}</span>
              </div>
            </div>
            
            <div style={{display: 'flex', gap: '0.5rem'}}>
              <button style={{
                padding: '0.5rem 1rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                backgroundColor: 'white',
                cursor: 'pointer'
              }}>
                Edit Team
              </button>
              <button style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                cursor: 'pointer'
              }}>
                Add Member
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Team Header */}
      <div style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb'}}>
        <div style={{maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem'}}>
          <div style={{display: 'flex', alignItems: 'center'}}>
            <div style={{
              width: '5rem',
              height: '5rem',
              backgroundColor: team.color + '20',
              borderRadius: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '1.5rem'
            }}>
              <span style={{fontSize: '2.5rem', color: team.color}}>👥</span>
            </div>
            <div style={{flex: 1}}>
              <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem'}}>
                <h1 style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#111827', margin: 0}}>{team.name}</h1>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '1rem',
                  backgroundColor: '#dcfce7',
                  fontSize: '0.75rem',
                  fontWeight: '500'
                }}>
                  <div style={{
                    width: '0.5rem',
                    height: '0.5rem',
                    borderRadius: '50%',
                    backgroundColor: '#22c55e',
                    marginRight: '0.5rem'
                  }}></div>
                  {team.status}
                </div>
              </div>
              <p style={{fontSize: '1.125rem', color: '#6b7280', margin: '0 0 0.5rem 0'}}>{team.description}</p>
              <div style={{display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#6b7280'}}>
                <span>Members: <strong>{team.members.length}</strong></span>
                <span>Created: <strong>{new Date(team.created).toLocaleDateString()}</strong></span>
                <span>Tasks Completed: <strong>{team.stats.completedTasks}</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb'}}>
        <div style={{maxWidth: '80rem', margin: '0 auto', padding: '0 1rem'}}>
          <div style={{display: 'flex', gap: '2rem'}}>
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'members', label: 'Members' },
              { id: 'tasks', label: 'Tasks' },
              { id: 'knowledge', label: 'Knowledge Base' },
              { id: 'performance', label: 'Performance' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: '1rem 0',
                  border: 'none',
                  backgroundColor: 'transparent',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  color: activeTab === tab.id ? '#2563eb' : '#6b7280',
                  borderBottom: activeTab === tab.id ? '2px solid #2563eb' : '2px solid transparent',
                  cursor: 'pointer'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div style={{maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem'}}>
        {activeTab === 'overview' && (
          <div>
            {/* Stats Grid */}
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem'}}>
              <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                  <div>
                    <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Total Tasks</p>
                    <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                      {team.stats.totalTasks}
                    </p>
                  </div>
                  <span style={{fontSize: '2rem'}}>📋</span>
                </div>
              </div>

              <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                  <div>
                    <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Completed</p>
                    <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                      {team.stats.completedTasks}
                    </p>
                  </div>
                  <span style={{fontSize: '2rem'}}>✅</span>
                </div>
              </div>

              <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                  <div>
                    <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Active Tasks</p>
                    <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                      {team.stats.activeTasks}
                    </p>
                  </div>
                  <span style={{fontSize: '2rem'}}>⏳</span>
                </div>
              </div>

              <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                  <div>
                    <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Avg Response</p>
                    <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                      {team.stats.avgResponseTime}
                    </p>
                  </div>
                  <span style={{fontSize: '2rem'}}>⚡</span>
                </div>
              </div>
            </div>

            {/* Team Members Overview */}
            <div style={{backgroundColor: 'white', borderRadius: '0.5rem', border: '1px solid #e5e7eb', padding: '1.5rem'}}>
              <h3 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem'}}>Team Members</h3>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem'}}>
                {team.members.map((member) => (
                  <div key={member.id} style={{
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.5rem',
                    padding: '1rem',
                    backgroundColor: '#fafafa'
                  }}>
                    <div style={{display: 'flex', alignItems: 'center', marginBottom: '0.75rem'}}>
                      <div style={{
                        width: '2.5rem',
                        height: '2.5rem',
                        backgroundColor: '#f3f4f6',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginRight: '0.75rem'
                      }}>
                        <span style={{fontSize: '1rem'}}>🤖</span>
                      </div>
                      <div>
                        <h4 style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', margin: 0}}>{member.name}</h4>
                        <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>{member.role}</p>
                      </div>
                    </div>
                    <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', textAlign: 'center', fontSize: '0.75rem'}}>
                      <div>
                        <div style={{fontWeight: '600', color: '#16a34a'}}>{member.performance.tasksCompleted}</div>
                        <div style={{color: '#6b7280'}}>Completed</div>
                      </div>
                      <div>
                        <div style={{fontWeight: '600', color: '#2563eb'}}>{member.performance.tasksActive}</div>
                        <div style={{color: '#6b7280'}}>Active</div>
                      </div>
                      <div>
                        <div style={{fontWeight: '600', color: '#ea580c'}}>{member.performance.efficiency}</div>
                        <div style={{color: '#6b7280'}}>Efficiency</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'members' && (
          <div>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600'}}>Team Members ({team.members.length})</h3>
              <button style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                cursor: 'pointer'
              }}>
                + Add Member
              </button>
            </div>

            <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
              {team.members.map((member) => (
                <div key={member.id} style={{
                  backgroundColor: 'white',
                  padding: '1.5rem',
                  borderRadius: '0.5rem',
                  border: '1px solid #e5e7eb'
                }}>
                  <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                    <div style={{display: 'flex', alignItems: 'center'}}>
                      <div style={{
                        width: '3rem',
                        height: '3rem',
                        backgroundColor: '#f3f4f6',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginRight: '1rem'
                      }}>
                        <span style={{fontSize: '1.5rem'}}>🤖</span>
                      </div>
                      <div>
                        <h4 style={{fontSize: '1rem', fontWeight: '600', color: '#111827', margin: '0 0 0.25rem 0'}}>
                          {member.name}
                        </h4>
                        <p style={{fontSize: '0.875rem', color: '#6b7280', margin: '0 0 0.25rem 0'}}>{member.role}</p>
                        <p style={{fontSize: '0.75rem', color: '#9ca3af', margin: 0}}>
                          Joined {new Date(member.joinedDate).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div style={{display: 'flex', gap: '1rem', alignItems: 'center'}}>
                      <div style={{textAlign: 'center'}}>
                        <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#16a34a'}}>
                          {member.performance.tasksCompleted}
                        </div>
                        <div style={{fontSize: '0.75rem', color: '#6b7280'}}>Completed</div>
                      </div>
                      <div style={{textAlign: 'center'}}>
                        <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#2563eb'}}>
                          {member.performance.tasksActive}
                        </div>
                        <div style={{fontSize: '0.75rem', color: '#6b7280'}}>Active</div>
                      </div>
                      <div style={{textAlign: 'center'}}>
                        <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#ea580c'}}>
                          {member.performance.efficiency}
                        </div>
                        <div style={{fontSize: '0.75rem', color: '#6b7280'}}>Efficiency</div>
                      </div>
                      <div style={{display: 'flex', gap: '0.5rem'}}>
                        <button 
                          onClick={() => navigate(`/agents/${member.id}`)}
                          style={{
                            padding: '0.5rem',
                            border: '1px solid #d1d5db',
                            borderRadius: '0.375rem',
                            backgroundColor: 'white',
                            cursor: 'pointer',
                            fontSize: '0.75rem'
                          }}
                        >
                          Configure
                        </button>
                        <button style={{
                          padding: '0.5rem',
                          border: '1px solid #dc2626',
                          borderRadius: '0.375rem',
                          backgroundColor: 'white',
                          color: '#dc2626',
                          cursor: 'pointer',
                          fontSize: '0.75rem'
                        }}>
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'tasks' && (
          <div style={{textAlign: 'center', padding: '3rem'}}>
            <div style={{fontSize: '3rem', marginBottom: '1rem'}}>📋</div>
            <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem'}}>Task Management</h3>
            <p style={{color: '#6b7280', marginBottom: '1.5rem'}}>
              Team task management interface coming soon...
            </p>
            <button style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
              cursor: 'pointer'
            }}>
              Create Task
            </button>
          </div>
        )}

        {activeTab === 'knowledge' && (
          <div>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600'}}>Team Knowledge Base</h3>
              <button 
                onClick={() => setShowUpload(!showUpload)}
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
                + Add Knowledge
              </button>
            </div>

            {showUpload && (
              <div style={{backgroundColor: '#f9fafb', border: '1px dashed #d1d5db', borderRadius: '0.5rem', padding: '2rem', marginBottom: '1.5rem', textAlign: 'center'}}>
                <div style={{fontSize: '2rem', marginBottom: '1rem'}}>📁</div>
                <h4 style={{fontSize: '1rem', fontWeight: '500', marginBottom: '0.5rem'}}>Upload Team Documents or Add Links</h4>
                <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem'}}>
                  Add documents, guidelines, and resources specific to this team
                </p>
                <div style={{display: 'flex', gap: '0.5rem', justifyContent: 'center'}}>
                  <input type="file" id="team-file-upload" style={{display: 'none'}} multiple onChange={handleFileUpload} accept=".pdf,.docx,.doc,.txt,.md,.html" />
                  <label htmlFor="team-file-upload" style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: 'white',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: 'pointer'
                  }}>
                    Choose Files
                  </label>
                  <button 
                    onClick={handleUrlUpload}
                    style={{
                      padding: '0.5rem 1rem',
                      backgroundColor: 'white',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      cursor: 'pointer'
                    }}
                  >
                    Add URL
                  </button>
                </div>
              </div>
            )}

            {/* Knowledge Documents */}
            {uploading && (
              <div style={{textAlign: 'center', padding: '2rem'}}>
                <div style={{fontSize: '1.5rem', marginBottom: '1rem'}}>⏳</div>
                <p>Uploading documents...</p>
              </div>
            )}

            <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
              {knowledgeDocs.map((doc) => (
                <div key={doc.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '1rem',
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '0.5rem',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s'
                }}
                onClick={() => handleDocumentClick(doc)}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}>
                  <div style={{display: 'flex', alignItems: 'center'}}>
                    <div style={{
                      width: '2.5rem',
                      height: '2.5rem',
                      backgroundColor: doc.type === 'document' ? '#dbeafe' : doc.type === 'link' ? '#dcfce7' : '#f3e8ff',
                      borderRadius: '0.375rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginRight: '0.75rem'
                    }}>
                      <span style={{fontSize: '1.25rem'}}>
                        {doc.type === 'document' ? '📄' : doc.type === 'link' ? '🔗' : '📝'}
                      </span>
                    </div>
                    <div>
                      <h4 style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', margin: '0 0 0.25rem 0'}}>
                        {doc.title}
                      </h4>
                      <div style={{fontSize: '0.75rem', color: '#6b7280'}}>
                        {doc.size && `${formatFileSize(doc.size)} • `}
                        Added {new Date(doc.upload_date).toLocaleDateString()}
                        {doc.tags.length > 0 && (
                          <span style={{marginLeft: '0.5rem'}}>
                            {doc.tags.map(tag => (
                              <span key={tag} style={{
                                marginRight: '0.25rem',
                                padding: '0.125rem 0.25rem',
                                borderRadius: '0.25rem',
                                fontSize: '0.625rem',
                                backgroundColor: '#e5e7eb',
                                color: '#374151'
                              }}>
                                {tag}
                              </span>
                            ))}
                          </span>
                        )}
                        <span style={{
                          marginLeft: '0.5rem',
                          padding: '0.125rem 0.375rem',
                          borderRadius: '0.25rem',
                          fontSize: '0.625rem',
                          fontWeight: '500',
                          backgroundColor: doc.status === 'active' ? '#dcfce7' : doc.status === 'processing' ? '#fef3c7' : '#fee2e2',
                          color: doc.status === 'active' ? '#15803d' : doc.status === 'processing' ? '#92400e' : '#dc2626'
                        }}>
                          {doc.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div style={{display: 'flex', gap: '0.5rem'}}>
                    <button style={{
                      padding: '0.375rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.25rem',
                      backgroundColor: 'white',
                      cursor: 'pointer',
                      fontSize: '0.75rem'
                    }}>
                      ⚙️
                    </button>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDocumentDelete(doc.id)
                      }}
                      style={{
                        padding: '0.375rem',
                        border: '1px solid #dc2626',
                        borderRadius: '0.25rem',
                        backgroundColor: 'white',
                        color: '#dc2626',
                        cursor: 'pointer',
                        fontSize: '0.75rem'
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'performance' && (
          <div style={{textAlign: 'center', padding: '3rem'}}>
            <div style={{fontSize: '3rem', marginBottom: '1rem'}}>📊</div>
            <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem'}}>Performance Analytics</h3>
            <p style={{color: '#6b7280'}}>
              Detailed performance analytics and charts coming soon...
            </p>
          </div>
        )}
      </div>

      {/* Document Viewer Modal */}
      {showDocumentViewer && selectedDocument && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.75rem',
            padding: '2rem',
            maxWidth: '80vw',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
          }}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600', margin: 0}}>
                {selectedDocument.title}
              </h3>
              <button 
                onClick={() => {
                  setShowDocumentViewer(false)
                  setSelectedDocument(null)
                }}
                style={{
                  padding: '0.5rem',
                  border: 'none',
                  borderRadius: '0.375rem',
                  backgroundColor: '#f3f4f6',
                  cursor: 'pointer',
                  fontSize: '1.25rem'
                }}
              >
                ✕
              </button>
            </div>
            
            <div style={{
              backgroundColor: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: '0.5rem',
              padding: '1rem',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              lineHeight: '1.5',
              whiteSpace: 'pre-wrap',
              maxHeight: '60vh',
              overflow: 'auto'
            }}>
              {documentContent || 'Loading document content...'}
            </div>
            
            <div style={{marginTop: '1.5rem', fontSize: '0.875rem', color: '#6b7280'}}>
              <p><strong>Type:</strong> {selectedDocument.type}</p>
              <p><strong>Size:</strong> {formatFileSize(selectedDocument.size)}</p>
              <p><strong>Uploaded:</strong> {new Date(selectedDocument.upload_date).toLocaleDateString()}</p>
              {selectedDocument.word_count && (
                <p><strong>Word Count:</strong> {selectedDocument.word_count.toLocaleString()}</p>
              )}
              {selectedDocument.tags.length > 0 && (
                <p><strong>Tags:</strong> {selectedDocument.tags.join(', ')}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}