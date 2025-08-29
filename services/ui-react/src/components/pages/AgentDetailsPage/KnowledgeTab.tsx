import React from 'react'
import type { KnowledgeDocument } from './types'

interface KnowledgeTabProps {
  showUpload: boolean
  setShowUpload: (open: boolean) => void
  uploading: boolean
  knowledgeDocs: KnowledgeDocument[]
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => Promise<void>
  onUrlUpload: () => Promise<void>
  onOpenDoc: (doc: KnowledgeDocument) => Promise<void>
  onDeleteDoc: (id: string) => Promise<void>
}

const formatFileSize = (bytes?: number): string => {
  if (!bytes) return 'Unknown'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function KnowledgeTab(props: KnowledgeTabProps): JSX.Element {
  const { showUpload, setShowUpload, uploading, knowledgeDocs, onFileUpload, onUrlUpload, onOpenDoc, onDeleteDoc } = props
  return (
    <div>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
        <h3 style={{fontSize: '1.25rem', fontWeight: '600'}}>Agent Knowledge Base</h3>
        <button onClick={() => setShowUpload(!showUpload)} style={{padding: '0.5rem 1rem', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: 'pointer'}}>+ Add Knowledge</button>
      </div>

      {showUpload && (
        <div style={{backgroundColor: '#f9fafb', border: '1px dashed #d1d5db', borderRadius: '0.5rem', padding: '2rem', marginBottom: '1.5rem', textAlign: 'center'}}>
          <div style={{fontSize: '2rem', marginBottom: '1rem'}}>📁</div>
          <h4 style={{fontSize: '1rem', fontWeight: '500', marginBottom: '0.5rem'}}>Upload Agent Documents or Add Links</h4>
          <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem'}}>Add documents, manuals, and resources specific to this agent</p>
          <div style={{display: 'flex', gap: '0.5rem', justifyContent: 'center'}}>
            <input type="file" id="agent-file-upload" style={{display: 'none'}} multiple onChange={onFileUpload} accept=".pdf,.docx,.doc,.txt,.md,.html" />
            <label htmlFor="agent-file-upload" style={{padding: '0.5rem 1rem', backgroundColor: 'white', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: 'pointer'}}>Choose Files</label>
            <button onClick={onUrlUpload} style={{padding: '0.5rem 1rem', backgroundColor: 'white', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: 'pointer'}}>Add URL</button>
          </div>
        </div>
      )}

      {uploading && (
        <div style={{textAlign: 'center', padding: '2rem'}}>
          <div style={{fontSize: '1.5rem', marginBottom: '1rem'}}>⏳</div>
          <p>Uploading documents...</p>
        </div>
      )}

      <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
        {knowledgeDocs.map((doc: KnowledgeDocument) => (
          <div key={doc.id} style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '0.5rem', cursor: 'pointer', transition: 'background-color 0.2s'}}
            onClick={() => onOpenDoc(doc)}
            onMouseEnter={(e: React.MouseEvent<HTMLDivElement>) => e.currentTarget.style.backgroundColor = '#f9fafb'}
            onMouseLeave={(e: React.MouseEvent<HTMLDivElement>) => e.currentTarget.style.backgroundColor = 'white'}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <div style={{width: '2.5rem', height: '2.5rem', backgroundColor: doc.type === 'document' ? '#dbeafe' : doc.type === 'link' ? '#dcfce7' : '#f3e8ff', borderRadius: '0.375rem', display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '0.75rem'}}>
                <span style={{fontSize: '1.25rem'}}>{doc.type === 'document' ? '📄' : doc.type === 'link' ? '🔗' : '📝'}</span>
              </div>
              <div>
                <h4 style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', margin: '0 0 0.25rem 0'}}>{doc.title}</h4>
                <div style={{fontSize: '0.75rem', color: '#6b7280'}}>
                  {doc.size && `${formatFileSize(doc.size)} • `}
                  Added {new Date(doc.upload_date).toLocaleDateString()}
                  {(doc.tags && doc.tags.length > 0) && (
                    <span style={{marginLeft: '0.5rem'}}>
                      {doc.tags.map((tag: string) => (
                        <span key={tag} style={{marginRight: '0.25rem', padding: '0.125rem 0.25rem', borderRadius: '0.25rem', fontSize: '0.625rem', backgroundColor: '#e5e7eb', color: '#374151'}}>{tag}</span>
                      ))}
                    </span>
                  )}
                  <span style={{marginLeft: '0.5rem', padding: '0.125rem 0.375rem', borderRadius: '0.25rem', fontSize: '0.625rem', fontWeight: '500', backgroundColor: doc.status === 'active' ? '#dcfce7' : doc.status === 'processing' ? '#fef3c7' : '#fee2e2', color: doc.status === 'active' ? '#15803d' : doc.status === 'processing' ? '#92400e' : '#dc2626'}}>
                    {doc.status}
                  </span>
                </div>
              </div>
            </div>
            <div style={{display: 'flex', gap: '0.5rem'}}>
              <button style={{padding: '0.375rem', border: '1px solid #d1d5db', borderRadius: '0.25rem', backgroundColor: 'white', cursor: 'pointer', fontSize: '0.75rem'}}>⚙️</button>
              <button onClick={(e: React.MouseEvent<HTMLButtonElement>) => { e.stopPropagation(); onDeleteDoc(doc.id) }} style={{padding: '0.375rem', border: '1px solid #dc2626', borderRadius: '0.25rem', backgroundColor: 'white', color: '#dc2626', cursor: 'pointer', fontSize: '0.75rem'}}>🗑️</button>
            </div>
          </div>
        ))}

        {knowledgeDocs.length === 0 && !uploading && (
          <div style={{textAlign: 'center', padding: '3rem', backgroundColor: 'white', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{fontSize: '3rem', marginBottom: '1rem'}}>📚</div>
            <h4 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem', color: '#111827'}}>No Knowledge Documents</h4>
            <p style={{color: '#6b7280', marginBottom: '1.5rem'}}>Upload documents, manuals, or add URLs to build this agent's knowledge base.</p>
            <button onClick={() => setShowUpload(true)} style={{padding: '0.75rem 1.5rem', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: 'pointer'}}>Add Your First Document</button>
          </div>
        )}
      </div>
    </div>
  )
}


