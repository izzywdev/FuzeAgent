import React from 'react'

interface TabsProps {
  activeTab: string
  setActiveTab: (tab: string) => void
}

export function Tabs({ activeTab, setActiveTab }: TabsProps): JSX.Element {
  return (
    <div style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb'}}>
      <div style={{maxWidth: '80rem', margin: '0 auto', padding: '0 1rem'}}>
        <div style={{display: 'flex', gap: '2rem'}}>
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'settings', label: 'Settings' },
            { id: 'tasks', label: 'Tasks' },
            { id: 'conversations', label: 'Conversations' },
            { id: 'knowledge', label: 'Knowledge' },
            { id: 'container', label: 'Container' }
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
  )
}


