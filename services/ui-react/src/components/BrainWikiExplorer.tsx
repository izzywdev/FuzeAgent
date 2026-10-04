import React, { useState } from 'react';
import { Button, Badge, Card, Input } from '../design-system';
import {
  BookOpen,
  MessageSquare,
  Search,
  Plus,
  FileText,
  Tag,
  Sparkles,
  Send,
  Database,
  Trash2,
} from 'lucide-react';

export interface WikiDocument {
  id: string;
  title: string;
  category: string;
  content: string;
  author: string;
  updatedAt: string;
  tags: string[];
  chunksCount: number;
}

export interface BrainChatMsg {
  id: string;
  role: 'user' | 'brain';
  content: string;
  citations?: Array<{ title: string; excerpt: string; page?: number }>;
  timestamp: string;
}

export interface BrainWikiProps {
  brainId?: string;
  brainName?: string;
  brainTier?: string;
  onClose?: () => void;
}

const SAMPLE_DOCS: Record<string, WikiDocument[]> = {
  default: [
    {
      id: 'doc_arch_01',
      title: 'Module Federation & Multi-Tenant MFE Architecture',
      category: 'Architecture',
      content: `# Module Federation Architecture

FuzeFront uses Webpack & Vite Module Federation to stitch autonomous microfrontends into a cohesive portal shell.

## Key Principles
1. **Isolated Lifecycles**: Each team builds, versions, and deploys independently.
2. **Shared Singletons**: React 19.x and React-DOM are shared singletons across all remotes.
3. **The Seam**: All microfrontends adopt the FuzeFront CSS tokens and seam gradients.
4. **Platform Bridge**: Remote applications talk to the host via \`window.__FUZEFRONT__\`.

\`\`\`typescript
// vite.config.ts federation setup
federation({
  name: 'fuzeagentApp',
  filename: 'remoteEntry.js',
  exposes: {
    './FuzeAgentApp': './src/App'
  },
  shared: ['react', 'react-dom']
})
\`\`\`
`,
      author: 'Izzy (Platform Architect)',
      updatedAt: '2 hours ago',
      tags: ['mfe', 'vite', 'federation', 'architecture'],
      chunksCount: 8,
    },
    {
      id: 'doc_agents_02',
      title: 'Autonomous Agent Sandboxing & TTL Policies',
      category: 'Agent Ops',
      content: `# Autonomous Agent Sandboxing

All agent pods (Python, React, DevOps, Marketing) are run with strict isolation:

- **Rootless execution**: Runs without privilege escalation.
- **Auto-Termination**: Default 30-minute hard shutdown TTL to prevent orphaned cluster costs.
- **FuzeKeys Vault Integration**: Secrets are read at runtime via the \`fuzekeys\` API, never baked into Docker images.
- **Event Bus Streaming**: All agent thought processes and tool executions stream to the central Redis/RabbitMQ bus.
`,
      author: 'DevOps Lead',
      updatedAt: 'Yesterday',
      tags: ['security', 'sandboxes', 'agents', 'ttl'],
      chunksCount: 5,
    },
    {
      id: 'doc_rag_03',
      title: '5-Tier Memory Hierarchy & Access Rules',
      category: 'RAG & Memory',
      content: `# 5-Tier Memory Specification

Agents do not hallucinate context. They pull from 5 distinct layers:

1. **Tier 1 (Personal)**: User-specific preferences and prompt tuning.
2. **Tier 2 (Team)**: Active sprint goals, shared repos, backlog items.
3. **Tier 3 (Project)**: Architectural blueprints, OpenAPI contracts.
4. **Tier 4 (Org Global)**: Corporate security, legal, compliance standards.
5. **Tier 5 (System Baseline)**: Core LLM system prompts and tool schemas.
`,
      author: 'AI Core Team',
      updatedAt: '3 days ago',
      tags: ['memory', 'rag', 'hierarchy', 'brains'],
      chunksCount: 12,
    },
  ],
};

export const BrainWikiExplorer: React.FC<BrainWikiProps> = ({
  brainId: _brainId = 'brain_org_global',
  brainName = 'Organization Global Brain',
  brainTier = 'Tier 4: Org Global',
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'wiki' | 'chat'>('wiki');
  const [documents, setDocuments] = useState<WikiDocument[]>(SAMPLE_DOCS.default);
  const [selectedDocId, setSelectedDocId] = useState<string>(SAMPLE_DOCS.default[0].id);
  const [searchQuery, setSearchQuery] = useState('');
  const [newDocModalOpen, setNewDocModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newCategory, setNewCategory] = useState('Architecture');
  const [newContent, setNewContent] = useState('');
  const [newTags, setNewTags] = useState('');

  // Brain Chat state
  const [chatMessages, setChatMessages] = useState<BrainChatMsg[]>([
    {
      id: 'msg_0',
      role: 'brain',
      content: `Hello! I am indexed with the memory of "${brainName}". Ask me anything about our architecture, sandbox policies, RAG hierarchy, or knowledge bases.`,
      timestamp: 'Just now',
    },
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);

  const selectedDoc = documents.find(d => d.id === selectedDocId) || documents[0];

  const filteredDocs = documents.filter(
    d =>
      d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleCreateDocument = () => {
    if (!newTitle.trim()) return;
    const doc: WikiDocument = {
      id: `doc_${Date.now()}`,
      title: newTitle,
      category: newCategory,
      content: newContent || `# ${newTitle}\n\nEnter document content here...`,
      author: 'You (Current User)',
      updatedAt: 'Just now',
      tags: newTags ? newTags.split(',').map(t => t.trim()) : ['general'],
      chunksCount: Math.max(1, Math.ceil(newContent.length / 400)),
    };
    setDocuments(prev => [doc, ...prev]);
    setSelectedDocId(doc.id);
    setNewDocModalOpen(false);
    setNewTitle('');
    setNewContent('');
    setNewTags('');
  };

  const handleDeleteDocument = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDocuments(prev => prev.filter(d => d.id !== id));
    if (selectedDocId === id && documents.length > 1) {
      setSelectedDocId(documents.filter(d => d.id !== id)[0].id);
    }
  };

  const handleSendChat = () => {
    if (!chatInput.trim() || isQuerying) return;
    const userMsg: BrainChatMsg = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: chatInput,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setChatMessages(prev => [...prev, userMsg]);
    const query = chatInput;
    setChatInput('');
    setIsQuerying(true);

    // Simulate grounded RAG answer from Brain knowledge
    setTimeout(() => {
      const matchDoc = documents.find(d =>
        d.title.toLowerCase().includes(query.toLowerCase()) ||
        d.content.toLowerCase().includes(query.toLowerCase())
      ) || documents[0];

      const brainResponse: BrainChatMsg = {
        id: `brn_${Date.now()}`,
        role: 'brain',
        content: `Based on **${brainName}** knowledge, here is what is recorded:\n\n${
          matchDoc.content.slice(0, 320)
        }...\n\nAll autonomous agents consulting this brain abide by this specification.`,
        citations: [
          {
            title: matchDoc.title,
            excerpt: matchDoc.content.slice(0, 140) + '...',
          },
        ],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setChatMessages(prev => [...prev, brainResponse]);
      setIsQuerying(false);
    }, 700);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--bg-primary, #0f131c)',
        color: 'var(--text-primary, #e7ecf5)',
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 20px',
          borderBottom: '1px solid var(--border-color, #232c3d)',
          backgroundColor: 'var(--bg-secondary, #0b0e15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: 'var(--radius-md, 6px)',
              background: 'var(--seam, linear-gradient(90deg, #6e5cff 0%, #29d3e6 100%))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
            }}
          >
            <Database size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>{brainName}</h2>
              <Badge variant="seam" size="sm">
                {brainTier}
              </Badge>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary, #9fa9bc)', display: 'flex', gap: '12px', marginTop: '2px' }}>
              <span>{documents.length} Articles</span>
              <span>•</span>
              <span>
                {documents.reduce((acc, d) => acc + d.chunksCount, 0) * 128} Vectors Indexed
              </span>
              <span>•</span>
              <span style={{ color: 'var(--success-color, #34d399)' }}>Real-Time Vector Sync</span>
            </div>
          </div>
        </div>

        {/* Tab switchers & actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              display: 'flex',
              backgroundColor: 'var(--bg-quaternary, #1c2433)',
              borderRadius: 'var(--radius-md, 6px)',
              padding: '3px',
              border: '1px solid var(--border-color, #232c3d)',
            }}
          >
            <button
              onClick={() => setActiveTab('wiki')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '5px 12px',
                borderRadius: 'var(--radius-sm, 4px)',
                border: 'none',
                background: activeTab === 'wiki' ? 'var(--accent-color, #6e5cff)' : 'transparent',
                color: activeTab === 'wiki' ? '#ffffff' : 'var(--text-secondary, #9fa9bc)',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 500,
              }}
            >
              <BookOpen size={14} /> Wiki & Docs
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '5px 12px',
                borderRadius: 'var(--radius-sm, 4px)',
                border: 'none',
                background: activeTab === 'chat' ? 'var(--accent-color, #6e5cff)' : 'transparent',
                color: activeTab === 'chat' ? '#ffffff' : 'var(--text-secondary, #9fa9bc)',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 500,
              }}
            >
              <MessageSquare size={14} /> Chat with Brain
            </button>
          </div>

          {activeTab === 'wiki' && (
            <Button
              size="sm"
              variant="seam"
              icon={<Plus size={14} />}
              onClick={() => setNewDocModalOpen(true)}
            >
              Add Document
            </Button>
          )}

          {onClose && (
            <Button size="sm" variant="ghost" onClick={onClose}>
              Close
            </Button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {activeTab === 'wiki' ? (
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Wiki Documents Sidebar */}
          <div
            style={{
              width: '320px',
              borderRight: '1px solid var(--border-color, #232c3d)',
              backgroundColor: 'var(--bg-tertiary, #141a26)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <div style={{ padding: '12px', borderBottom: '1px solid var(--border-color, #232c3d)' }}>
              <Input
                placeholder="Search wiki articles, tags..."
                icon={<Search size={14} />}
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
              {filteredDocs.map(doc => {
                const isSelected = doc.id === selectedDocId;
                return (
                  <div
                    key={doc.id}
                    onClick={() => setSelectedDocId(doc.id)}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md, 6px)',
                      cursor: 'pointer',
                      backgroundColor: isSelected ? 'var(--bg-quaternary, #1c2433)' : 'transparent',
                      border: isSelected
                        ? '1px solid var(--accent-color, #6e5cff)'
                        : '1px solid transparent',
                      marginBottom: '6px',
                      transition: 'all 0.15s ease',
                      position: 'relative',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          color: 'var(--accent-2, #29d3e6)',
                          fontWeight: 600,
                          textTransform: 'uppercase',
                        }}
                      >
                        {doc.category}
                      </span>
                      <button
                        onClick={e => handleDeleteDocument(doc.id, e)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--text-tertiary, #66718a)',
                          cursor: 'pointer',
                          padding: '2px',
                        }}
                        title="Delete article"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                    <div
                      style={{
                        fontSize: '13px',
                        fontWeight: 600,
                        color: isSelected ? '#ffffff' : 'var(--text-primary, #e7ecf5)',
                        margin: '4px 0',
                      }}
                    >
                      {doc.title}
                    </div>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '11px',
                        color: 'var(--text-tertiary, #66718a)',
                      }}
                    >
                      <span>{doc.chunksCount} chunks</span>
                      <span>•</span>
                      <span>{doc.updatedAt}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Wiki Document Reader */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '28px 36px',
              backgroundColor: 'var(--bg-primary, #0f131c)',
            }}
          >
            {selectedDoc ? (
              <div style={{ maxWidth: '840px', margin: '0 auto' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <Badge variant="accent">{selectedDoc.category}</Badge>
                  <span style={{ fontSize: '12px', color: 'var(--text-tertiary, #66718a)' }}>
                    Authored by {selectedDoc.author} • Updated {selectedDoc.updatedAt}
                  </span>
                </div>

                <h1 style={{ fontSize: '26px', fontWeight: 700, margin: '0 0 16px 0', color: '#ffffff' }}>
                  {selectedDoc.title}
                </h1>

                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '24px' }}>
                  {selectedDoc.tags.map(t => (
                    <Badge key={t} variant="default" size="sm" icon={<Tag size={10} />}>
                      {t}
                    </Badge>
                  ))}
                </div>

                <Card
                  style={{
                    padding: '24px',
                    fontSize: '14px',
                    lineHeight: '1.7',
                    color: 'var(--text-primary, #e7ecf5)',
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'var(--font-sans)',
                  }}
                >
                  {selectedDoc.content}
                </Card>
              </div>
            ) : (
              <div style={{ textAlign: 'center', color: 'var(--text-secondary, #9fa9bc)', marginTop: '80px' }}>
                Select an article from the left to read
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Brain Chat View */
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
          {/* Chat message list */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            {chatMessages.map(msg => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    maxWidth: '80%',
                    alignSelf: isUser ? 'flex-end' : 'flex-start',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '11px',
                      color: 'var(--text-tertiary, #66718a)',
                      marginBottom: '4px',
                    }}
                  >
                    <span>{isUser ? 'You' : brainName}</span>
                    <span>•</span>
                    <span>{msg.timestamp}</span>
                  </div>

                  <div
                    style={{
                      padding: '12px 16px',
                      borderRadius: 'var(--radius-lg, 8px)',
                      fontSize: '13px',
                      lineHeight: '1.6',
                      backgroundColor: isUser
                        ? 'var(--accent-color, #6e5cff)'
                        : 'var(--bg-tertiary, #141a26)',
                      color: isUser ? '#ffffff' : 'var(--text-primary, #e7ecf5)',
                      border: isUser ? 'none' : '1px solid var(--border-color, #232c3d)',
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {msg.content}
                  </div>

                  {msg.citations && msg.citations.length > 0 && (
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
                      {msg.citations.map((c, i) => (
                        <span
                          key={i}
                          style={{
                            fontSize: '11px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '2px 8px',
                            backgroundColor: 'var(--bg-quaternary, #1c2433)',
                            borderRadius: 'var(--radius-sm, 4px)',
                            border: '1px solid rgba(41, 211, 230, 0.3)',
                            color: 'var(--accent-2, #29d3e6)',
                          }}
                        >
                          <FileText size={10} /> {c.title}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
            {isQuerying && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-2, #29d3e6)', fontSize: '12px' }}>
                <Sparkles size={14} className="animate-spin" /> Querying vector embeddings across {brainName}...
              </div>
            )}
          </div>

          {/* Chat input box */}
          <div
            style={{
              padding: '16px 24px',
              borderTop: '1px solid var(--border-color, #232c3d)',
              backgroundColor: 'var(--bg-secondary, #0b0e15)',
              display: 'flex',
              gap: '12px',
            }}
          >
            <Input
              placeholder={`Ask anything to ${brainName}...`}
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') handleSendChat();
              }}
              style={{ flex: 1 }}
            />
            <Button variant="seam" onClick={handleSendChat} icon={<Send size={14} />}>
              Query
            </Button>
          </div>
        </div>
      )}

      {/* Add Document Modal */}
      {newDocModalOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
          }}
        >
          <Card
            seamAccent
            style={{
              width: '560px',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>Add Knowledge to Brain</h3>
            <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary, #9fa9bc)' }}>
              Add a new article or guideline. It will be chunked into vectors and indexed immediately.
            </p>

            <div>
              <label style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary, #66718a)', fontWeight: 600 }}>
                Article Title
              </label>
              <Input
                placeholder="e.g. Deployment Gate Rules"
                value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
                style={{ marginTop: '4px' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary, #66718a)', fontWeight: 600 }}>
                  Category
                </label>
                <Input
                  placeholder="e.g. Architecture, Security"
                  value={newCategory}
                  onChange={e => setNewCategory(e.target.value)}
                  style={{ marginTop: '4px' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary, #66718a)', fontWeight: 600 }}>
                  Tags (comma separated)
                </label>
                <Input
                  placeholder="e.g. k8s, helm, gate"
                  value={newTags}
                  onChange={e => setNewTags(e.target.value)}
                  style={{ marginTop: '4px' }}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary, #66718a)', fontWeight: 600 }}>
                Content (Markdown)
              </label>
              <textarea
                rows={6}
                placeholder="Write markdown content or paste document text..."
                value={newContent}
                onChange={e => setNewContent(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: '4px',
                  backgroundColor: 'var(--bg-quaternary, #1c2433)',
                  border: '1px solid var(--border-color, #232c3d)',
                  borderRadius: 'var(--radius-md, 6px)',
                  color: 'var(--text-primary, #e7ecf5)',
                  padding: '8px 12px',
                  fontSize: '13px',
                  fontFamily: 'inherit',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
              <Button variant="ghost" onClick={() => setNewDocModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="seam" onClick={handleCreateDocument}>
                Index Document
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
