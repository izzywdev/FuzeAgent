import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { OrganizationToolsSection } from './OrganizationToolsSection'

interface OrganizationInfo {
  id: string
  name: string
  description: string
  industry: string
  size: string
  founded: string
  website?: string
  logo?: string
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
  organization_id?: string
  word_count?: number
  extracted_text?: string
}

export function OrganizationProfilePage() {
  const [orgInfo, setOrgInfo] = useState<OrganizationInfo>({
    id: '1',
    name: 'WCG - World Class Group',
    description: 'A leading AI-powered organization focused on innovation and excellence in software development and automation.',
    industry: 'Technology / AI Services',
    size: '10-50 employees',
    founded: '2025',
    website: 'https://worldclassgroup.ai'
  })
  const [originalOrgInfo, setOriginalOrgInfo] = useState<OrganizationInfo | null>(null)
  
  const [knowledgeDocs, setKnowledgeDocs] = useState<KnowledgeDocument[]>([])
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocument | null>(null)
  const [showDocumentViewer, setShowDocumentViewer] = useState(false)
  const [documentContent, setDocumentContent] = useState<string>('')
  const [showRAGSearch, setShowRAGSearch] = useState(false)
  const [ragQuery, setRagQuery] = useState('')
  const [ragResults, setRagResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [saveMessage, setSaveMessage] = useState<{type: 'success' | 'error', text: string} | null>(null)
  const [stats, setStats] = useState({
    totalAgents: 0,
    activeTeams: 0,
    tasksCompleted: 0
  })

  // Organization tools state
  const [orgTools, setOrgTools] = useState<any[]>([])

  // Load organization data and knowledge documents on component mount
  useEffect(() => {
    loadFirstOrganization()
  }, [])

  // Load organization tools
  useEffect(() => {
    if (orgInfo.id) {
      loadOrganizationTools()
    }
  }, [orgInfo.id])

  // Clear save message after 3 seconds
  useEffect(() => {
    if (saveMessage) {
      const timer = setTimeout(() => setSaveMessage(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [saveMessage])

  const loadFirstOrganization = async () => {
    try {
      // First, get all organizations to find the first one
      const orgsResponse = await fetch('/organizations')
      if (orgsResponse.ok) {
        const organizations = await orgsResponse.json()
        if (organizations && organizations.length > 0) {
          const firstOrg = organizations[0]
          await loadOrganizationData(firstOrg.id)
          await loadKnowledgeDocuments(firstOrg.id)
          await loadStats()
        } else {
          console.error('No organizations found')
        }
      } else {
        console.error('Failed to load organizations')
      }
    } catch (error) {
      console.error('Error loading organizations:', error)
    }
  }

  const loadOrganizationData = async (orgId?: string) => {
    const targetId = orgId || orgInfo.id
    try {
      const response = await fetch(`/organizations/${targetId}`)
      if (response.ok) {
        const data = await response.json()
        const loadedOrgInfo: OrganizationInfo = {
          id: data.id,
          name: data.name,
          description: data.description || '',
          industry: data.industry || 'Technology / AI Services',
          size: data.size || '10-50 employees', 
          founded: data.founded || '2025',
          website: data.website || ''
        }
        setOrgInfo(loadedOrgInfo)
        setOriginalOrgInfo({...loadedOrgInfo})
      } else {
        console.error('Failed to load organization data')
      }
    } catch (error) {
      console.error('Error loading organization data:', error)
    }
  }

  const loadKnowledgeDocuments = async (orgId?: string) => {
    const targetId = orgId || orgInfo.id
    try {
      const response = await fetch(`http://localhost:8000/knowledge/organizations/${targetId}/documents`)
      if (response.ok) {
        const documents = await response.json()
        setKnowledgeDocs(documents)
      } else {
        console.error('Failed to load documents')
      }
    } catch (error) {
      console.error('Error loading documents:', error)
    }
  }

  const loadStats = async () => {
    try {
      // Load agents and teams to calculate stats
      const [agentsResponse, teamsResponse] = await Promise.all([
        fetch('/agents'),
        fetch('/teams')
      ])

      if (agentsResponse.ok && teamsResponse.ok) {
        const agents = await agentsResponse.json()
        const teams = await teamsResponse.json()

        setStats({
          totalAgents: Array.isArray(agents) ? agents.length : 0,
          activeTeams: Array.isArray(teams) ? teams.filter(t => t.status === 'active').length : 0,
          tasksCompleted: Array.isArray(agents) ? 
            agents.reduce((total, agent) => total + (agent?.tasks?.completed || 0), 0) : 0
        })
      }
    } catch (error) {
      console.error('Error loading stats:', error)
    }
  }

  const loadOrganizationTools = async () => {
    try {
      const response = await fetch(`/organizations/${orgInfo.id}/tools`)
      if (response.ok) {
        const tools = await response.json()
        setOrgTools(tools)
      }
    } catch (error) {
      console.error('Error loading organization tools:', error)
    }
  }

  const handleStartEditing = () => {
    setOriginalOrgInfo({...orgInfo})
    setIsEditing(true)
    setSaveMessage(null)
  }

  const handleCancelEditing = () => {
    if (originalOrgInfo) {
      setOrgInfo({...originalOrgInfo})
    }
    setIsEditing(false)
    setSaveMessage(null)
  }

  const handleSaveChanges = async () => {
    setIsSaving(true)
    setSaveMessage(null)
    
    try {
      const response = await fetch(`/organizations/${orgInfo.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: orgInfo.name,
          description: orgInfo.description,
          industry: orgInfo.industry,
          size: orgInfo.size,
          founded: orgInfo.founded,
          website: orgInfo.website
        })
      })
      
      if (response.ok) {
        await response.json()
        setOriginalOrgInfo({...orgInfo})
        setIsEditing(false)
        setSaveMessage({type: 'success', text: 'Organization profile updated successfully!'})
        
        // Reload the data to ensure consistency
        await loadOrganizationData()
      } else {
        const errorData = await response.json().catch(() => ({}))
        setSaveMessage({
          type: 'error', 
          text: errorData.detail || 'Failed to update organization profile'
        })
      }
    } catch (error) {
      console.error('Error saving organization:', error)
      setSaveMessage({
        type: 'error', 
        text: 'Network error. Please check your connection and try again.'
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    
    for (const file of Array.from(files)) {
      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('title', file.name)
        
        const response = await fetch(`http://localhost:8000/knowledge/organizations/${orgInfo.id}/documents`, {
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
    const url = prompt('Enter URL:')
    if (!url) return

    setUploading(true)
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/organizations/${orgInfo.id}/url`, {
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
    setSelectedDocument(doc)
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/organizations/${orgInfo.id}/documents/${doc.id}/content`)
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
    if (!confirm('Are you sure you want to delete this document?')) return
    
    try {
      const response = await fetch(`http://localhost:8000/knowledge/organizations/${orgInfo.id}/documents/${docId}`, {
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

  const handleRAGSearch = async () => {
    if (!ragQuery.trim()) return
    
    setIsSearching(true)
    
    try {
      const response = await fetch('http://localhost:8000/rag/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: ragQuery,
          organization_id: orgInfo.id,
          max_results: 10,
          similarity_threshold: 0.6
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setRagResults(data.relevant_chunks || [])
      } else {
        console.error('RAG search failed')
        setRagResults([])
      }
    } catch (error) {
      console.error('Error performing RAG search:', error)
      setRagResults([])
    }
    
    setIsSearching(false)
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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
                <Link to="/" style={{color: '#6b7280', textDecoration: 'none'}}>Dashboard</Link>
                <span style={{margin: '0 0.5rem'}}>›</span>
                <span style={{color: '#111827'}}>Organization Profile</span>
              </div>
            </div>
            
            <div style={{display: 'flex', gap: '0.5rem'}}>
              <button 
                onClick={isEditing ? handleCancelEditing : handleStartEditing}
                disabled={isSaving}
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  backgroundColor: 'white',
                  cursor: isSaving ? 'not-allowed' : 'pointer',
                  opacity: isSaving ? 0.6 : 1
                }}
              >
                {isEditing ? 'Cancel' : 'Edit Profile'}
              </button>
              {isEditing && (
                <button 
                  onClick={handleSaveChanges}
                  disabled={isSaving}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: isSaving ? '#9ca3af' : '#2563eb',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: isSaving ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}
                >
                  {isSaving && <span style={{animation: 'spin 1s linear infinite'}}>⏳</span>}
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main style={{maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem'}}>
        {/* Success/Error Messages */}
        {saveMessage && (
          <div style={{
            padding: '1rem',
            borderRadius: '0.5rem',
            marginBottom: '1.5rem',
            backgroundColor: saveMessage.type === 'success' ? '#dcfce7' : '#fee2e2',
            border: `1px solid ${saveMessage.type === 'success' ? '#16a34a' : '#dc2626'}`,
            color: saveMessage.type === 'success' ? '#15803d' : '#dc2626',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <span>{saveMessage.type === 'success' ? '✅' : '❌'}</span>
            <span>{saveMessage.text}</span>
          </div>
        )}

        {/* Header */}
        <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', marginBottom: '2rem'}}>
          <div style={{padding: '2rem'}}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <div style={{
                width: '6rem',
                height: '6rem',
                backgroundColor: '#f3f4f6',
                borderRadius: '1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginRight: '2rem'
              }}>
                <span style={{fontSize: '3rem'}}>🏢</span>
              </div>
              <div style={{flex: 1}}>
                {isEditing ? (
                  <input
                    type="text"
                    value={orgInfo.name}
                    onChange={(e) => setOrgInfo({...orgInfo, name: e.target.value})}
                    style={{
                      fontSize: '2rem',
                      fontWeight: 'bold',
                      color: '#111827',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      padding: '0.5rem',
                      width: '100%',
                      marginBottom: '0.5rem'
                    }}
                  />
                ) : (
                  <h1 style={{fontSize: '2rem', fontWeight: 'bold', color: '#111827', margin: '0 0 0.5rem 0'}}>
                    {orgInfo.name}
                  </h1>
                )}
                <p style={{fontSize: '1.125rem', color: '#6b7280', margin: 0}}>{orgInfo.industry}</p>
              </div>
            </div>
          </div>
        </div>

        <div style={{display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem'}}>
          {/* Main Information */}
          <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', padding: '2rem'}}>
            <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '1.5rem'}}>Organization Information</h3>
            
            <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
              <div>
                <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                  Description
                </label>
                {isEditing ? (
                  <textarea
                    value={orgInfo.description}
                    onChange={(e) => setOrgInfo({...orgInfo, description: e.target.value})}
                    rows={3}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      resize: 'vertical'
                    }}
                  />
                ) : (
                  <p style={{fontSize: '0.875rem', color: '#111827', lineHeight: '1.5', margin: 0}}>
                    {orgInfo.description}
                  </p>
                )}
              </div>

              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem'}}>
                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Industry
                  </label>
                  {isEditing ? (
                    <input
                      type="text"
                      value={orgInfo.industry}
                      onChange={(e) => setOrgInfo({...orgInfo, industry: e.target.value})}
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        border: '1px solid #d1d5db',
                        borderRadius: '0.375rem',
                        fontSize: '0.875rem'
                      }}
                    />
                  ) : (
                    <p style={{fontSize: '0.875rem', color: '#111827', margin: 0}}>{orgInfo.industry}</p>
                  )}
                </div>
                
                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Size
                  </label>
                  {isEditing ? (
                    <select 
                      value={orgInfo.size}
                      onChange={(e) => setOrgInfo({...orgInfo, size: e.target.value})}
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        border: '1px solid #d1d5db',
                        borderRadius: '0.375rem',
                        fontSize: '0.875rem'
                      }}
                    >
                      <option value="1-10 employees">1-10 employees</option>
                      <option value="10-50 employees">10-50 employees</option>
                      <option value="50-200 employees">50-200 employees</option>
                      <option value="200+ employees">200+ employees</option>
                    </select>
                  ) : (
                    <p style={{fontSize: '0.875rem', color: '#111827', margin: 0}}>{orgInfo.size}</p>
                  )}
                </div>
              </div>

              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem'}}>
                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Founded
                  </label>
                  {isEditing ? (
                    <input
                      type="text"
                      value={orgInfo.founded}
                      onChange={(e) => setOrgInfo({...orgInfo, founded: e.target.value})}
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        border: '1px solid #d1d5db',
                        borderRadius: '0.375rem',
                        fontSize: '0.875rem'
                      }}
                    />
                  ) : (
                    <p style={{fontSize: '0.875rem', color: '#111827', margin: 0}}>{orgInfo.founded}</p>
                  )}
                </div>
                
                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Website
                  </label>
                  {isEditing ? (
                    <input
                      type="url"
                      value={orgInfo.website || ''}
                      onChange={(e) => setOrgInfo({...orgInfo, website: e.target.value})}
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        border: '1px solid #d1d5db',
                        borderRadius: '0.375rem',
                        fontSize: '0.875rem'
                      }}
                    />
                  ) : (
                    <p style={{fontSize: '0.875rem', color: '#111827', margin: 0}}>
                      {orgInfo.website ? (
                        <a href={orgInfo.website} target="_blank" rel="noopener noreferrer" style={{color: '#2563eb', textDecoration: 'none'}}>
                          {orgInfo.website}
                        </a>
                      ) : (
                        'Not specified'
                      )}
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
            {/* Quick Stats */}
            <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', padding: '1.5rem'}}>
              <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Quick Stats</h4>
              <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem'}}>
                <div style={{display: 'flex', justifyContent: 'space-between'}}>
                  <span style={{color: '#6b7280'}}>Total Agents:</span>
                  <span style={{fontWeight: '500'}}>{stats.totalAgents}</span>
                </div>
                <div style={{display: 'flex', justifyContent: 'space-between'}}>
                  <span style={{color: '#6b7280'}}>Active Teams:</span>
                  <span style={{fontWeight: '500'}}>{stats.activeTeams}</span>
                </div>
                <div style={{display: 'flex', justifyContent: 'space-between'}}>
                  <span style={{color: '#6b7280'}}>Tasks Completed:</span>
                  <span style={{fontWeight: '500'}}>{stats.tasksCompleted}</span>
                </div>
                <div style={{display: 'flex', justifyContent: 'space-between'}}>
                  <span style={{color: '#6b7280'}}>Knowledge Docs:</span>
                  <span style={{fontWeight: '500'}}>{knowledgeDocs.length}</span>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', padding: '1.5rem'}}>
              <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Recent Activity</h4>
              <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                <div style={{fontSize: '0.875rem'}}>
                  <div style={{fontWeight: '500', color: '#111827'}}>Organization Profile</div>
                  <div style={{color: '#6b7280', fontSize: '0.75rem'}}>Loaded from API</div>
                </div>
                <div style={{fontSize: '0.875rem'}}>
                  <div style={{fontWeight: '500', color: '#111827'}}>Teams: {stats.activeTeams} active</div>
                  <div style={{color: '#6b7280', fontSize: '0.75rem'}}>Updated from API</div>
                </div>
                <div style={{fontSize: '0.875rem'}}>
                  <div style={{fontWeight: '500', color: '#111827'}}>Knowledge: {knowledgeDocs.length} docs</div>
                  <div style={{color: '#6b7280', fontSize: '0.75rem'}}>Synced from API</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Knowledge Management Section */}
        <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', marginTop: '2rem', padding: '2rem'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
            <h3 style={{fontSize: '1.25rem', fontWeight: '600'}}>Knowledge Management</h3>
            <div style={{display: 'flex', gap: '0.5rem'}}>
              <button 
                onClick={() => setShowRAGSearch(!showRAGSearch)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#7c3aed',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  cursor: 'pointer'
                }}
              >
                🔍 Smart Search
              </button>
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
          </div>

          {showUpload && (
            <div style={{backgroundColor: '#f9fafb', border: '1px dashed #d1d5db', borderRadius: '0.5rem', padding: '2rem', marginBottom: '1.5rem', textAlign: 'center'}}>
              <div style={{fontSize: '2rem', marginBottom: '1rem'}}>📁</div>
              <h4 style={{fontSize: '1rem', fontWeight: '500', marginBottom: '0.5rem'}}>Upload Documents or Add Links</h4>
              <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem'}}>
                Drag and drop files here, or click to browse
              </p>
              <div style={{display: 'flex', gap: '0.5rem', justifyContent: 'center'}}>
                <input type="file" id="file-upload" style={{display: 'none'}} multiple onChange={handleFileUpload} accept=".pdf,.docx,.doc,.txt,.md,.html" />
                <label htmlFor="file-upload" style={{
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

          {showRAGSearch && (
            <div style={{backgroundColor: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '0.5rem', padding: '2rem', marginBottom: '1.5rem'}}>
              <div style={{display: 'flex', alignItems: 'center', marginBottom: '1rem'}}>
                <div style={{fontSize: '1.5rem', marginRight: '1rem'}}>🧠</div>
                <h4 style={{fontSize: '1rem', fontWeight: '500', margin: 0}}>AI-Powered Knowledge Search</h4>
              </div>
              <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem'}}>
                Search through your organization's knowledge using natural language. Ask questions and get contextual answers based on your uploaded documents.
              </p>
              <div style={{display: 'flex', gap: '0.75rem', alignItems: 'flex-start'}}>
                <textarea
                  value={ragQuery}
                  onChange={(e) => setRagQuery(e.target.value)}
                  placeholder="Ask a question about your organization's knowledge... (e.g., 'What are our key processes?' or 'How do we handle customer support?')"
                  rows={3}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    resize: 'vertical',
                    minHeight: '4rem'
                  }}
                />
                <button 
                  onClick={handleRAGSearch}
                  disabled={!ragQuery.trim() || isSearching}
                  style={{
                    padding: '0.75rem 1.5rem',
                    backgroundColor: !ragQuery.trim() || isSearching ? '#9ca3af' : '#7c3aed',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: !ragQuery.trim() || isSearching ? 'not-allowed' : 'pointer',
                    whiteSpace: 'nowrap',
                    minHeight: '4rem',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                >
                  {isSearching ? '🔍 Searching...' : '🔍 Search'}
                </button>
              </div>
              
              {ragResults.length > 0 && (
                <div style={{marginTop: '1.5rem'}}>
                  <h5 style={{fontSize: '0.875rem', fontWeight: '600', marginBottom: '1rem', color: '#374151'}}>
                    Found {ragResults.length} relevant results:
                  </h5>
                  <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                    {ragResults.map((result, index) => (
                      <div key={index} style={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '0.5rem',
                        padding: '1rem'
                      }}>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem'}}>
                          <h6 style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', margin: 0}}>
                            📄 {result.document_title}
                          </h6>
                          <div style={{
                            padding: '0.125rem 0.5rem',
                            backgroundColor: '#dcfce7',
                            color: '#16a34a',
                            borderRadius: '0.25rem',
                            fontSize: '0.75rem',
                            fontWeight: '500'
                          }}>
                            {Math.round((1 - parseFloat(result.metadata?.distance || 0)) * 100)}% match
                          </div>
                        </div>
                        <p style={{
                          fontSize: '0.875rem', 
                          color: '#374151', 
                          margin: 0, 
                          lineHeight: '1.5',
                          backgroundColor: '#f9fafb',
                          padding: '0.75rem',
                          borderRadius: '0.375rem',
                          border: '1px solid #f3f4f6'
                        }}>
                          {result.content.length > 300 ? result.content.substring(0, 300) + '...' : result.content}
                        </p>
                        <div style={{
                          fontSize: '0.75rem', 
                          color: '#6b7280', 
                          marginTop: '0.5rem',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}>
                          <span>Chunk {result.chunk_index + 1}</span>
                          <button
                            onClick={() => {
                              // Find and open the full document
                              const fullDoc = knowledgeDocs.find(doc => doc.id === result.document_id)
                              if (fullDoc) {
                                handleDocumentClick(fullDoc)
                              }
                            }}
                            style={{
                              padding: '0.25rem 0.5rem',
                              backgroundColor: '#2563eb',
                              color: 'white',
                              border: 'none',
                              borderRadius: '0.25rem',
                              fontSize: '0.75rem',
                              cursor: 'pointer'
                            }}
                          >
                            View Full Document
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {ragResults.length === 0 && ragQuery && !isSearching && (
                <div style={{
                  marginTop: '1.5rem',
                  textAlign: 'center',
                  color: '#6b7280',
                  fontSize: '0.875rem',
                  padding: '2rem'
                }}>
                  No relevant results found. Try rephrasing your question or check if documents are uploaded and indexed.
                </div>
              )}
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
            {(Array.isArray(knowledgeDocs) ? knowledgeDocs : []).map((doc) => (
              <div key={doc.id} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1rem',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
                backgroundColor: '#fafafa',
                cursor: 'pointer',
                transition: 'background-color 0.2s'
              }}
              onClick={() => handleDocumentClick(doc)}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f0f0f0'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#fafafa'}>
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
                      {Array.isArray(doc.tags) && doc.tags.length > 0 && (
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

        {/* Organization Tools Section */}
        <OrganizationToolsSection 
          orgId={orgInfo.id}
          tools={orgTools}
          onToolsChange={loadOrganizationTools}
        />

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
                {Array.isArray(selectedDocument.tags) && selectedDocument.tags.length > 0 && (
                  <p><strong>Tags:</strong> {selectedDocument.tags.join(', ')}</p>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* CSS Animations */}
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
    </div>
  )
}