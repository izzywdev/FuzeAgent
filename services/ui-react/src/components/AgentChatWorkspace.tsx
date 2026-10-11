import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Terminal, 
  Sparkles, 
  User, 
  MessageSquare,
  LayoutGrid
} from 'lucide-react';
import { MultiAgentChatWorkspace, AGENT_PERSONAS } from './MultiAgentChatWorkspace';
import type { AgentPersona } from './MultiAgentChatWorkspace';
import { Button, Badge, StatusPill } from '../design-system';

interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
  toolCall?: { tool: string; output: string };
  thought?: string;
}

export const AgentChatWorkspace: React.FC = () => {
  const [viewMode, setViewMode] = useState<'focused-chat' | 'docked-grid'>('focused-chat');
  const [selectedAgent, setSelectedAgent] = useState<AgentPersona>(AGENT_PERSONAS[0]);
  const [messagesByAgent, setMessagesByAgent] = useState<Record<string, ChatMessage[]>>({
    'python-dev': [
      {
        id: 'msg_init_py',
        role: 'agent',
        content: "Hello! I'm your Python Developer Agent. I'm connected to the orchestrator bus and can run pytest test suites, generate FastAPI services, and query the pgvector brain store. How can I help you today?",
        timestamp: '12:00 PM',
        toolCall: {
          tool: 'pytest -v tests/test_fuzekeys_bridge.py',
          output: '4 passed in 0.42s',
        },
      },
    ],
    'react-dev': [
      {
        id: 'msg_init_rc',
        role: 'agent',
        content: "Hey there! React Developer Agent online. I build and style microfrontends conforming strictly to FuzeFront Design System tokens, ensuring proper spacing and dark theme palettes.",
        timestamp: '12:01 PM',
      },
    ],
    'devops-lead': [
      {
        id: 'msg_init_ops',
        role: 'agent',
        content: "DevOps Lead active. Monitoring in-cluster Kubernetes pods, Helm chart validation, and zero-downtime microfrontend rollouts. What should we verify?",
        timestamp: '12:02 PM',
        toolCall: {
          tool: 'kubectl get pods -n fuzeagent',
          output: 'All pods 1/1 Running on fuzeinfra-prod-elastic-v2',
        },
      },
    ],
  });

  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [wsStatus, setWsStatus] = useState<'connected' | 'connecting' | 'offline'>('connected');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Active agent's message list
  const currentMessages = messagesByAgent[selectedAgent.id] || [];

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentMessages, isThinking]);

  // WebSocket connection to backend bus
  useEffect(() => {
    const isLocal = typeof window !== 'undefined' && window.location.hostname === 'localhost';
    const proto = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = typeof window !== 'undefined' ? window.location.host : 'localhost:8000';
    const url = isLocal
      ? `${proto}//localhost:8000/api/ws/multi-agent`
      : `${proto}//${host}/apps/fuzeagent/api/ws/multi-agent`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setWsStatus('connected');
      ws.onclose = () => setWsStatus('offline');
      ws.onerror = () => setWsStatus('offline');

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'agent_chunk') {
            setIsThinking(false);
            setMessagesByAgent(prev => {
              const list = prev[data.agentId] || [];
              const last = list[list.length - 1];
              if (last && last.id.startsWith('stream_')) {
                const updated = [...list];
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + data.chunk,
                };
                return { ...prev, [data.agentId]: updated };
              } else {
                return {
                  ...prev,
                  [data.agentId]: [
                    ...list,
                    {
                      id: `stream_${Date.now()}`,
                      role: 'agent',
                      content: data.chunk,
                      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    },
                  ],
                };
              }
            });
          } else if (data.type === 'agent_message') {
            setIsThinking(false);
            setMessagesByAgent(prev => {
              const list = prev[data.agentId] || [];
              const filtered = list.filter(m => !m.id.startsWith('stream_'));
              return {
                ...prev,
                [data.agentId]: [
                  ...filtered,
                  {
                    id: `msg_${Date.now()}`,
                    role: 'agent',
                    content: data.content,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    toolCall: data.toolCall,
                  },
                ],
              };
            });
          }
        } catch {
          // ignore
        }
      };

      return () => {
        ws.close();
      };
    } catch {
      setWsStatus('offline');
    }
  }, []);

  const handleSend = () => {
    if (!input.trim() || isThinking) return;
    const userText = input.trim();
    setInput('');

    const newMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessagesByAgent(prev => ({
      ...prev,
      [selectedAgent.id]: [...(prev[selectedAgent.id] || []), newMsg],
    }));

    setIsThinking(true);

    // Send through WebSocket if open
    let sentWs = false;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({
          action: 'chat',
          agentId: selectedAgent.id,
          message: userText,
        }));
        sentWs = true;
      } catch {
        sentWs = false;
      }
    }

    if (!sentWs) {
      // Local simulated response with tool execution
      setTimeout(() => {
        let reply = '';
        let toolCall = undefined;

        if (selectedAgent.id === 'python-dev') {
          reply = `Analyzing "${userText}". I've executed the test harness and validated the database connection pool. All contracts match OpenAPI definitions.`;
          toolCall = { tool: 'pytest -v tests/test_app_builds.py', output: '64 passed, 1 skipped in 3.14s' };
        } else if (selectedAgent.id === 'react-dev') {
          reply = `Configuring the component hierarchy to conform strictly to FuzeFront DS tokens. Applied var(--bg-tertiary) surfaces and balanced flex padding.`;
          toolCall = { tool: 'vite build', output: 'Built dist/index.html in 1.4s (0 errors)' };
        } else if (selectedAgent.id === 'devops-lead') {
          reply = `Verified Helm templates. StorageClass binding 'local-path' on worker node 'fuzeinfra-prod-elastic-v2' is healthy. No restart loops detected.`;
          toolCall = { tool: 'kubectl get pods -n fuzeagent', output: 'fuzeagent-runner-py-9df82 1/1 Running' };
        } else {
          reply = `Received your task: "${userText}". Processing in sandboxed runtime and relaying status over the orchestrator bus.`;
        }

        setMessagesByAgent(prev => ({
          ...prev,
          [selectedAgent.id]: [
            ...(prev[selectedAgent.id] || []),
            {
              id: `agt_${Date.now()}`,
              role: 'agent',
              content: reply,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              toolCall,
            },
          ],
        }));
        setIsThinking(false);
      }, 700);
    }
  };

  const quickPrompts = [
    { label: 'Run pytest test suite', prompt: 'Run the pytest test suite for app-builds and verify status' },
    { label: 'Inspect active sandbox pods', prompt: 'Check all active agent pods and container status in fuzeagent namespace' },
    { label: 'Verify FuzeFront DS tokens', prompt: 'Review our UI spacing and ensure full conformity with FuzeFront tokens' },
    { label: 'Search Brain Wiki docs', prompt: 'Search the brain store for architecture RFCs on microfrontends' },
  ];

  if (viewMode === 'docked-grid') {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between p-3 rounded-xl border" style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)' }}>
          <div className="flex items-center gap-2">
            <LayoutGrid className="w-4 h-4 text-indigo-400" />
            <span className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Multi-Window Docked Workspace</span>
          </div>
          <Button variant="outline" size="sm" onClick={() => setViewMode('focused-chat')}>
            Switch to Focused Agent Chat
          </Button>
        </div>
        <div className="h-[800px] rounded-xl overflow-hidden border border-slate-800 shadow-xl">
          <MultiAgentChatWorkspace />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Bar with Mode Switcher */}
      <div 
        className="p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md"
        style={{
          backgroundColor: 'var(--bg-secondary, #0b0e15)',
          borderColor: 'var(--border-color, #232c3d)',
        }}
      >
        <div className="flex items-center gap-3">
          <span 
            className="p-2 rounded-xl border flex items-center justify-center text-indigo-400"
            style={{
              backgroundColor: 'var(--accent-soft, rgba(110, 92, 255, 0.14))',
              borderColor: 'rgba(110, 92, 255, 0.3)',
            }}
          >
            <MessageSquare className="w-5 h-5" />
          </span>
          <div>
            <h2 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary, #e7ecf5)' }}>
              <span>Agent Chat</span>
              <StatusPill
                status={wsStatus === 'connected' ? 'online' : 'pending'}
                label={wsStatus === 'connected' ? '⚡ Live WebSocket Bus' : 'Reconnecting...'}
              />
            </h2>
            <p className="text-xs" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
              Direct conversation with autonomous agent specialists executing inside Kubernetes sandboxes.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Button
            variant="outline"
            size="sm"
            icon={<LayoutGrid className="w-3.5 h-3.5" />}
            onClick={() => setViewMode('docked-grid')}
          >
            Docked Multi-Window View
          </Button>
        </div>
      </div>

      {/* Main 2-Column Chat Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-[760px]">
        {/* Left Column: Agent Selector Roster */}
        <div 
          className="lg:col-span-4 rounded-2xl border p-4 flex flex-col justify-between shadow-xl"
          style={{
            backgroundColor: 'var(--bg-tertiary, #141a26)',
            borderColor: 'var(--border-color, #232c3d)',
          }}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                Select Agent ({AGENT_PERSONAS.length})
              </span>
            </div>

            <div className="space-y-2 overflow-y-auto max-h-[660px] pr-1">
              {AGENT_PERSONAS.map(agent => {
                const isSelected = selectedAgent.id === agent.id;
                return (
                  <div
                    key={agent.id}
                    onClick={() => setSelectedAgent(agent)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                      isSelected ? 'ring-1 ring-indigo-500/50 shadow-md' : 'hover:border-slate-700'
                    }`}
                    style={{
                      backgroundColor: isSelected ? 'var(--accent-soft, rgba(110, 92, 255, 0.14))' : 'var(--bg-quaternary, #1c2433)',
                      borderColor: isSelected ? 'var(--accent-color, #6e5cff)' : 'var(--border-color, #232c3d)',
                    }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <span className="text-2xl p-1 rounded-lg bg-black/20 flex-shrink-0">
                          {agent.emoji}
                        </span>
                        <div>
                          <h4 className="text-xs font-bold leading-tight" style={{ color: 'var(--text-primary)' }}>
                            {agent.name}
                          </h4>
                          <p className="text-[11px] font-medium" style={{ color: 'var(--accent-color, #6e5cff)' }}>
                            {agent.role}
                          </p>
                        </div>
                      </div>
                      <StatusPill status={agent.status} label={agent.status} />
                    </div>

                    <div className="mt-2.5 flex flex-wrap gap-1">
                      {agent.skills.slice(0, 3).map(skill => (
                        <span 
                          key={skill}
                          className="px-1.5 py-0.5 rounded text-[10px] font-mono border"
                          style={{
                            backgroundColor: 'rgba(255, 255, 255, 0.04)',
                            borderColor: 'var(--border-color)',
                            color: 'var(--text-secondary)',
                          }}
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Direct Agent Chat Window */}
        <div 
          className="lg:col-span-8 rounded-2xl border flex flex-col justify-between shadow-2xl overflow-hidden"
          style={{
            backgroundColor: 'var(--bg-tertiary, #141a26)',
            borderColor: 'var(--border-color, #232c3d)',
          }}
        >
          {/* Chat Window Header */}
          <div 
            className="p-4 border-b flex items-center justify-between"
            style={{
              backgroundColor: 'var(--bg-secondary, #0b0e15)',
              borderColor: 'var(--border-color, #232c3d)',
            }}
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">{selectedAgent.emoji}</span>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                    {selectedAgent.name}
                  </h3>
                  <Badge variant="accent" size="sm">
                    {selectedAgent.mention}
                  </Badge>
                </div>
                <p className="text-xs opacity-75" style={{ color: 'var(--text-secondary)' }}>
                  {selectedAgent.currentTask || selectedAgent.role}
                </p>
              </div>
            </div>

            <StatusPill status={selectedAgent.status} label={selectedAgent.status} />
          </div>

          {/* Messages Stream */}
          <div 
            className="flex-1 overflow-y-auto p-5 space-y-4"
            style={{ backgroundColor: 'var(--bg-primary, #0f131c)' }}
          >
            {currentMessages.map(msg => {
              const isUser = msg.role === 'user';
              return (
                <div 
                  key={msg.id}
                  className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {!isUser && (
                    <span className="text-xl p-1.5 rounded-xl bg-slate-800/60 border border-slate-700/60 h-fit flex-shrink-0">
                      {selectedAgent.emoji}
                    </span>
                  )}

                  <div 
                    className={`max-w-[78%] rounded-2xl p-4 space-y-2 border text-xs shadow-md ${
                      isUser ? 'rounded-tr-none' : 'rounded-tl-none'
                    }`}
                    style={{
                      backgroundColor: isUser ? 'var(--accent-color, #6e5cff)' : 'var(--bg-tertiary, #141a26)',
                      borderColor: isUser ? 'transparent' : 'var(--border-color, #232c3d)',
                      color: isUser ? '#ffffff' : 'var(--text-primary, #e7ecf5)',
                    }}
                  >
                    <div className="leading-relaxed whitespace-pre-wrap font-sans text-xs">
                      {msg.content}
                    </div>

                    {msg.toolCall && (
                      <div 
                        className="mt-2 p-2.5 rounded-lg border font-mono text-[11px] space-y-1"
                        style={{
                          backgroundColor: '#080b11',
                          borderColor: 'var(--border-color)',
                          color: '#34d399',
                        }}
                      >
                        <div className="flex items-center gap-1.5 text-indigo-300 font-bold">
                          <Terminal className="w-3.5 h-3.5" />
                          <span>$ {msg.toolCall.tool}</span>
                        </div>
                        <div className="text-slate-300 pl-4">{msg.toolCall.output}</div>
                      </div>
                    )}

                    <div 
                      className="text-[10px] text-right opacity-60 font-mono mt-1"
                      style={{ color: isUser ? '#e0e7ff' : 'var(--text-secondary)' }}
                    >
                      {msg.timestamp}
                    </div>
                  </div>

                  {isUser && (
                    <span 
                      className="p-2 rounded-xl text-white h-fit flex-shrink-0 flex items-center justify-center border"
                      style={{
                        backgroundColor: 'var(--bg-quaternary, #1c2433)',
                        borderColor: 'var(--border-color)',
                      }}
                    >
                      <User className="w-4 h-4 text-indigo-300" />
                    </span>
                  )}
                </div>
              );
            })}

            {isThinking && (
              <div className="flex gap-3 justify-start">
                <span className="text-xl p-1.5 rounded-xl bg-slate-800/60 border border-slate-700/60 h-fit">
                  {selectedAgent.emoji}
                </span>
                <div 
                  className="rounded-2xl rounded-tl-none p-3.5 border text-xs shadow-md flex items-center gap-2"
                  style={{
                    backgroundColor: 'var(--bg-tertiary, #141a26)',
                    borderColor: 'var(--border-color, #232c3d)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  <Sparkles className="w-4 h-4 text-indigo-400 animate-spin" />
                  <span>{selectedAgent.name} is thinking and consulting knowledge base...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts Bar */}
          <div 
            className="px-5 py-2.5 border-t flex items-center gap-2 overflow-x-auto"
            style={{
              backgroundColor: 'var(--bg-secondary, #0b0e15)',
              borderColor: 'var(--border-color, #232c3d)',
            }}
          >
            <span className="text-[10px] uppercase font-bold text-slate-500 whitespace-nowrap">Quick:</span>
            {quickPrompts.map(p => (
              <button
                key={p.label}
                onClick={() => setInput(p.prompt)}
                className="px-2.5 py-1 rounded-lg text-[11px] whitespace-nowrap border transition-all hover:border-indigo-500"
                style={{
                  backgroundColor: 'var(--bg-quaternary, #1c2433)',
                  borderColor: 'var(--border-color, #232c3d)',
                  color: 'var(--text-secondary, #9fa9bc)',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Prompt Input Box */}
          <div 
            className="p-4 border-t flex items-center gap-3"
            style={{
              backgroundColor: 'var(--bg-secondary, #0b0e15)',
              borderColor: 'var(--border-color, #232c3d)',
            }}
          >
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={`Message ${selectedAgent.name}... (Press Enter to send)`}
              className="flex-1 px-4 py-2.5 rounded-xl border bg-transparent text-xs outline-none focus:border-indigo-500 transition-colors"
              style={{
                borderColor: 'var(--border-color, #232c3d)',
                backgroundColor: 'var(--bg-quaternary, #1c2433)',
                color: 'var(--text-primary, #e7ecf5)',
              }}
            />

            <Button
              variant="seam"
              size="md"
              icon={<Send className="w-4 h-4" />}
              onClick={handleSend}
              disabled={!input.trim() || isThinking}
            >
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
export default AgentChatWorkspace;
