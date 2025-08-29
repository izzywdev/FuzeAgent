import React from 'react'
import type { KnowledgeDocument } from './types'

interface DocumentViewerProps {
  open: boolean
  document: KnowledgeDocument | null
  content: string
  onClose: () => void
}

const formatFileSize = (bytes?: number): string => {
  if (!bytes) return 'Unknown'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function DocumentViewer({ open, document, content, onClose }: DocumentViewerProps): JSX.Element | null {
  if (!open || !document) return null
  return (
    <div style={{position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000}}>
      <div style={{backgroundColor: 'white', borderRadius: '0.75rem', padding: '2rem', maxWidth: '80vw', maxHeight: '80vh', overflow: 'auto', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
          <h3 style={{fontSize: '1.25rem', fontWeight: '600', margin: 0}}>{document.title}</h3>
          <button onClick={onClose} style={{padding: '0.5rem', border: 'none', borderRadius: '0.375rem', backgroundColor: '#f3f4f6', cursor: 'pointer', fontSize: '1.25rem'}}>✕</button>
        </div>
        <div style={{backgroundColor: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '1rem', fontFamily: 'monospace', fontSize: '0.875rem', lineHeight: '1.5', whiteSpace: 'pre-wrap', maxHeight: '60vh', overflow: 'auto'}}>
          {content || 'Loading document content...'}
        </div>
        <div style={{marginTop: '1.5rem', fontSize: '0.875rem', color: '#6b7280'}}>
          <p><strong>Type:</strong> {document.type}</p>
          <p><strong>Size:</strong> {formatFileSize(document.size)}</p>
          <p><strong>Uploaded:</strong> {new Date(document.upload_date).toLocaleDateString()}</p>
          {document.word_count && (
            <p><strong>Word Count:</strong> {document.word_count.toLocaleString()}</p>
          )}
          {document.tags.length > 0 && (
            <p><strong>Tags:</strong> {document.tags.join(', ')}</p>
          )}
        </div>
      </div>
    </div>
  )
}


