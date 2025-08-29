import React from 'react'
import type { Agent, ChatMessage, Conversation } from './types'

interface ConversationsTabProps {
  agent: Agent
  conversations: Conversation[]
  selectedConversation: Conversation | null
  loading: boolean
  creating: boolean
  updatingStatusId: string | null
  chatWebSocket: WebSocket | null
  chatMessages: ChatMessage[]
  isAgentTyping: boolean
  newMessage: string
  isSendingMessage: boolean
  onNewConversation: () => Promise<void>
  onSelectConversation: (c: Conversation) => Promise<void>
  onConversationStatus: (id: string, status: 'running' | 'paused' | 'stopped') => Promise<void>
  onNewMessageChange: (v: string) => void
  onSendMessage: () => Promise<void>
}

export function ConversationsTab(props: ConversationsTabProps): JSX.Element {
  const { agent, conversations, selectedConversation, loading, creating, updatingStatusId, chatWebSocket, chatMessages, isAgentTyping, newMessage, isSendingMessage, onNewConversation, onSelectConversation, onConversationStatus, onNewMessageChange, onSendMessage } = props

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '18rem 1fr', gap: '1rem', height: '70vh' }}>
      <div style={{backgroundColor: 'white', borderRadius: '0.5rem', border: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column'}}>
        <div style={{padding: '0.75rem', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <strong style={{fontSize: '0.9rem'}}>Conversations</strong>
          <button onClick={onNewConversation} disabled={creating} style={{ padding: '0.25rem 0.5rem', backgroundColor: creating ? '#9ca3af' : '#2563eb', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.75rem', cursor: creating ? 'not-allowed' : 'pointer' }}>+ New</button>
        </div>
        <div style={{flex: 1, overflowY: 'auto'}}>
          {loading ? (
            <div style={{padding: '0.75rem', color: '#6b7280'}}>Loading...</div>
          ) : conversations.length === 0 ? (
            <div style={{padding: '0.75rem', color: '#6b7280'}}>No conversations</div>
          ) : (
            conversations.map((c: Conversation) => (
              <div key={c.id} onClick={() => onSelectConversation(c)} style={{padding: '0.75rem', borderBottom: '1px solid #e5e7eb', cursor: 'pointer', backgroundColor: selectedConversation?.id === c.id ? '#eef2ff' : 'transparent'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                  <div style={{fontSize: '0.875rem', color: '#111827', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}} title={c.title}>{c.title}</div>
                  <span style={{fontSize: '0.7rem', padding: '0.125rem 0.375rem', borderRadius: '0.25rem', backgroundColor: c.status === 'running' ? '#dcfce7' : c.status === 'paused' ? '#fef3c7' : '#fee2e2', color: c.status === 'running' ? '#15803d' : c.status === 'paused' ? '#92400e' : '#b91c1c'}}>{c.status}</span>
                </div>
                <div style={{fontSize: '0.75rem', color: '#6b7280'}}>{new Date((c as any).updated_at || c.timestamp).toLocaleString()}</div>
                <div style={{display: 'flex', gap: '0.25rem', marginTop: '0.5rem'}}>
                  <button onClick={(e: React.MouseEvent<HTMLButtonElement>) => { e.stopPropagation(); onConversationStatus(c.id, 'running') }} disabled={updatingStatusId === c.id} style={{padding: '0.25rem 0.5rem', border: '1px solid #d1d5db', borderRadius: '0.25rem', backgroundColor: 'white', fontSize: '0.75rem', cursor: 'pointer'}}>Start</button>
                  <button onClick={(e: React.MouseEvent<HTMLButtonElement>) => { e.stopPropagation(); onConversationStatus(c.id, 'paused') }} disabled={updatingStatusId === c.id} style={{padding: '0.25rem 0.5rem', border: '1px solid #d1d5db', borderRadius: '0.25rem', backgroundColor: 'white', fontSize: '0.75rem', cursor: 'pointer'}}>Pause</button>
                  <button onClick={(e: React.MouseEvent<HTMLButtonElement>) => { e.stopPropagation(); onConversationStatus(c.id, 'stopped') }} disabled={updatingStatusId === c.id} style={{padding: '0.25rem 0.5rem', border: '1px solid #d1d5db', borderRadius: '0.25rem', backgroundColor: 'white', fontSize: '0.75rem', cursor: 'pointer'}}>Stop</button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div style={{display: 'flex', flexDirection: 'column', backgroundColor: 'white', borderRadius: '0.5rem', border: '1px solid #e5e7eb', overflow: 'hidden'}}>
        <div style={{padding: '1rem 1.5rem', borderBottom: '1px solid #e5e7eb', backgroundColor: '#f9fafb'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem'}}>
            <div style={{width: '2.5rem', height: '2.5rem', borderRadius: '50%', backgroundColor: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: '600'}}>
              {agent?.name?.charAt(0) || 'A'}
            </div>
            <div>
              <h3 style={{fontSize: '1.125rem', fontWeight: '600', margin: 0}}>{agent?.name || 'Agent'}</h3>
              <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>{chatWebSocket ? 'Online' : 'Connecting...'}</p>
            </div>
          </div>
        </div>

        <div id="chat-messages-container" style={{flex: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem'}}>
          {(chatMessages?.length || 0) === 0 ? (
            <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center', color: '#6b7280'}}>
              <div style={{fontSize: '3rem', marginBottom: '1rem'}}>💬</div>
              <h4 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem'}}>Start a conversation</h4>
              <p style={{fontSize: '0.875rem', maxWidth: '24rem'}}>Send a message to {agent?.name || 'this agent'} to begin your conversation.</p>
            </div>
          ) : (
            chatMessages.map((message: ChatMessage) => (
              <div key={message.id} style={{display: 'flex', justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: '0.5rem'}}>
                <div style={{maxWidth: '70%', padding: '0.75rem 1rem', borderRadius: '1rem', backgroundColor: message.role === 'user' ? '#2563eb' : '#f3f4f6', color: message.role === 'user' ? 'white' : '#111827', fontSize: '0.875rem', lineHeight: '1.5', wordWrap: 'break-word'}}>
                  {message.content}
                  <div style={{fontSize: '0.75rem', opacity: 0.7, marginTop: '0.25rem'}}>
                    {new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    {message.status === 'sending' && ' • Sending...'}
                    {message.status === 'error' && ' • Failed'}
                  </div>
                </div>
              </div>
            ))
          )}

          {isAgentTyping && (
            <div style={{display: 'flex', justifyContent: 'flex-start', marginBottom: '0.5rem'}}>
              <div style={{maxWidth: '70%', padding: '0.75rem 1rem', borderRadius: '1rem', backgroundColor: '#f3f4f6', color: '#111827', fontSize: '0.875rem', fontStyle: 'italic'}}>
                {agent?.name || 'Agent'} is typing...
              </div>
            </div>
          )}
        </div>

        <div style={{padding: '1rem 1.5rem', borderTop: '1px solid #e5e7eb', backgroundColor: '#f9fafb'}}>
          <div style={{display: 'flex', gap: '0.75rem', alignItems: 'flex-end'}}>
            <textarea
              value={newMessage}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => onNewMessageChange(e.target.value)}
              onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSendMessage() } }}
              placeholder={`Message ${agent?.name || 'agent'}...`}
              style={{flex: 1, padding: '0.75rem 1rem', borderRadius: '1.5rem', border: '1px solid #d1d5db', resize: 'none', outline: 'none', fontSize: '0.875rem', minHeight: '2.5rem', maxHeight: '8rem', lineHeight: '1.5'}}
              rows={1}
              disabled={isSendingMessage}
            />
            <button onClick={onSendMessage} disabled={!newMessage.trim() || isSendingMessage} style={{padding: '0.75rem', backgroundColor: !newMessage.trim() || isSendingMessage ? '#9ca3af' : '#2563eb', color: 'white', border: 'none', borderRadius: '50%', cursor: !newMessage.trim() || isSendingMessage ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '2.5rem', height: '2.5rem'}}>
              {isSendingMessage ? '...' : '↑'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}


