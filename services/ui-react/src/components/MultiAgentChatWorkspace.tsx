import React, { useState, useRef, useEffect } from 'react';
import { DockviewReact } from 'dockview-react';
import type {
  DockviewReadyEvent,
  IDockviewPanelProps,
  DockviewApi,
} from 'dockview-react';
import 'dockview-react/dist/styles/dockview.css';
import { Button, Badge, StatusPill, Input, Avatar } from '../design-system';
import {
  Send,
  Terminal,
  Sparkles,
  LayoutGrid,
} from 'lucide-react';

export interface AgentPersona {
  id: string;
  mention: string;
  name: string;
  role: string;
  avatar: string;
  emoji: string;
  skills: string[];
  status: 'online' | 'executing' | 'idle';
  currentTask?: string;
}

export const AGENT_PERSONAS: AgentPersona[] = [
  {
    id: 'python-dev',
    mention: '@python-dev',
    name: 'Python Developer',
    role: 'Backend & ML Engineer',
    avatar: '',
    emoji: '🐍',
    skills: ['FastAPI', 'PyTorch', 'Asyncpg', 'LangChain'],
    status: 'online',
    currentTask: 'Optimizing asyncpg connection pooling & RAG vectors',
  },
  {
    id: 'react-dev',
    mention: '@react-dev',
    name: 'React Developer',
    role: 'Frontend & UI Specialist',
    avatar: '',
    emoji: '⚛️',
    skills: ['React 19', 'Vite', 'Module Federation', 'Tailwind'],
    status: 'online',
    currentTask: 'Dockview window layout & FuzeFront DS alignment',
  },
  {
    id: 'devops-lead',
    mention: '@devops-lead',
    name: 'DevOps Lead',
    role: 'Cluster & GitOps Lead',
    avatar: '',
    emoji: '🚢',
    skills: ['Kubernetes', 'Helm', 'Argo CD', 'Kaniko'],
    status: 'executing',
    currentTask: 'Monitoring local-path storageClass rollout in fuzeagent',
  },
  {
    id: 'marketing-lead',
    mention: '@marketing-lead',
    name: 'Marketing Lead',
    role: 'Growth & Social Strategist',
    avatar: '',
    emoji: '📈',
    skills: ['FuzeSocial', 'Funnels', 'Copywriting', 'SEO'],
    status: 'idle',
    currentTask: 'Reviewing cross-org engagement metrics',
  },
  {
    id: 'core-eng',
    mention: '@core-eng',
    name: 'Core Architect',
    role: 'Platform & Security Architect',
    avatar: '',
    emoji: '🛡️',
    skills: ['Permit ReBAC', 'AuthZ', 'Security Gate', 'A2A Bus'],
    status: 'online',
    currentTask: 'Auditing S2S token rotation and org-level ACLs',
  },
];

interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
  toolCall?: { tool: string; output: string };
}

type AgentWsListener = (data: any) => void;
const wsListeners = new Set<AgentWsListener>();

function subscribeAgentWs(fn: AgentWsListener) {
  wsListeners.add(fn);
  return () => wsListeners.delete(fn);
}

function broadcastAgentWs(data: any) {
  wsListeners.forEach(fn => fn(data));
}

let activeWs: WebSocket | null = null;

function sendToAgentWs(payload: any) {
  if (activeWs && activeWs.readyState === WebSocket.OPEN) {
    activeWs.send(JSON.stringify(payload));
    return true;
  }
  return false;
}

// Individual Agent Chat Panel
const AgentChatPanel: React.FC<IDockviewPanelProps<{ agent: AgentPersona }>> = props => {
  const agent = props.params.agent;
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init_msg',
      role: 'agent',
      content: `Hello! I am ${agent.name} (${agent.mention}). Ready to collaborate. Ask me anything or mention other agents with @ to coordinate.`,
      timestamp: 'Just now',
    },
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  // Subscribe to live agent WebSocket stream
  useEffect(() => {
    const unsub = subscribeAgentWs((evt) => {
      if (evt.agentId !== agent.id) return;

      if (evt.type === 'agent_chunk') {
        setIsThinking(false);
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'agent' && last.id.startsWith('live_')) {
            return [
              ...prev.slice(0, -1),
              { ...last, content: evt.accumulated || last.content + evt.chunk },
            ];
          } else {
            return [
              ...prev,
              {
                id: `live_${Date.now()}`,
                role: 'agent',
                content: evt.chunk,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              },
            ];
          }
        });
      } else if (evt.type === 'agent_thought') {
        setIsThinking(true);
      } else if (evt.type === 'agent_message') {
        setIsThinking(false);
        setMessages(prev => {
          const filtered = prev.filter(m => !m.id.startsWith('live_'));
          return [
            ...filtered,
            {
              id: `msg_${Date.now()}`,
              role: 'agent',
              content: evt.content,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ];
        });
      }
    });
    return () => {
      unsub();
    };
  }, [agent.id]);

  const handleSend = () => {
    if (!input.trim() || isThinking) return;
    const userText = input;
    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);

    const sent = sendToAgentWs({
      action: 'chat',
      agentId: agent.id,
      message: userText,
    });

    if (!sent) {
      // Fallback local simulation if WebSocket is offline
      setTimeout(() => {
        let agentReply = '';
        let toolCall = undefined;

        if (agent.id === 'python-dev') {
          agentReply = `I've analyzed the request for Python services. Using asyncpg connection pools and validating OpenAPI schema contracts at \`/app/contracts/openapi.yaml\`.`;
          toolCall = { tool: 'pytest -v tests/test_hierarchy.py', output: '42 passed, 0 failed in 1.4s' };
        } else if (agent.id === 'devops-lead') {
          agentReply = `Checked the Helm templates. Verified \`local-path\` storageClass binding on active worker node \`fuzeinfra-prod-elastic-v2\`. Deploying with zero downtime.`;
          toolCall = { tool: 'kubectl get pods -n fuzeagent', output: 'All pods 1/1 Running' };
        } else if (agent.id === 'react-dev') {
          agentReply = `Configured Dockview layout manager with FuzeFront DS tokens. Multi-chat tabs and drag-and-drop window docking are active.`;
        } else {
          agentReply = `Received prompt: "${userText}". Executing autonomous task in sandbox with 30m timeout and streaming outputs to centralized bus.`;
        }

        setMessages(prev => [
          ...prev,
          {
            id: `agt_${Date.now()}`,
            role: 'agent',
            content: agentReply,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            toolCall,
          },
        ]);
        setIsThinking(false);
      }, 700);
    }
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
      {/* Panel Top Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          borderBottom: '1px solid var(--border-color, #232c3d)',
          backgroundColor: 'var(--bg-secondary, #0b0e15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Avatar
            name={agent.name}
            fallbackEmoji={agent.emoji}
            size="sm"
            status={agent.status === 'executing' ? 'busy' : agent.status === 'online' ? 'online' : 'offline'}
          />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>{agent.name}</span>
              <Badge variant="accent" size="sm">
                {agent.mention}
              </Badge>
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-tertiary, #66718a)' }}>
              {agent.currentTask}
            </div>
          </div>
        </div>

        <StatusPill status={agent.status} />
      </div>

      {/* Message List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
        }}
      >
        {messages.map(m => {
          const isUser = m.role === 'user';
          return (
            <div
              key={m.id}
              style={{
                alignSelf: isUser ? 'flex-end' : 'flex-start',
                maxWidth: '88%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: isUser ? 'flex-end' : 'flex-start',
              }}
            >
              <div
                style={{
                  fontSize: '10px',
                  color: 'var(--text-tertiary, #66718a)',
                  marginBottom: '2px',
                }}
              >
                {isUser ? 'You' : agent.name} • {m.timestamp}
              </div>

              <div
                style={{
                  padding: '9px 13px',
                  borderRadius: 'var(--radius-md, 6px)',
                  fontSize: '12px',
                  lineHeight: '1.5',
                  backgroundColor: isUser
                    ? 'var(--accent-color, #6e5cff)'
                    : 'var(--bg-tertiary, #141a26)',
                  color: isUser ? '#ffffff' : 'var(--text-primary, #e7ecf5)',
                  border: isUser ? 'none' : '1px solid var(--border-color, #232c3d)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {m.content}
              </div>

              {m.toolCall && (
                <div
                  style={{
                    marginTop: '6px',
                    padding: '6px 10px',
                    backgroundColor: 'var(--bg-secondary, #0b0e15)',
                    border: '1px solid var(--border-color, #232c3d)',
                    borderRadius: 'var(--radius-sm, 4px)',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--accent-2, #29d3e6)',
                    width: '100%',
                    boxSizing: 'border-box',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '2px' }}>
                    <Terminal size={11} /> <strong>{m.toolCall.tool}</strong>
                  </div>
                  <div style={{ color: 'var(--text-secondary, #9fa9bc)', fontSize: '10px' }}>
                    {m.toolCall.output}
                  </div>
                </div>
              )}
            </div>
          );
        })}
        {isThinking && (
          <div style={{ fontSize: '11px', color: 'var(--accent-2, #29d3e6)', display: 'flex', gap: '6px', alignItems: 'center' }}>
            <Sparkles size={12} className="animate-spin" /> {agent.name} is executing...
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input Composer */}
      <div
        style={{
          padding: '8px 12px',
          borderTop: '1px solid var(--border-color, #232c3d)',
          backgroundColor: 'var(--bg-secondary, #0b0e15)',
          display: 'flex',
          gap: '8px',
        }}
      >
        <Input
          placeholder={`Message ${agent.name} (type @ to coordinate)...`}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') handleSend();
          }}
          style={{ fontSize: '12px', padding: '6px 10px' }}
        />
        <Button size="sm" variant="seam" onClick={handleSend} icon={<Send size={12} />}>
          Send
        </Button>
      </div>
    </div>
  );
};

export const MultiAgentChatWorkspace: React.FC = () => {
  const [api, setApi] = useState<DockviewApi | null>(null);
  const [activeLayout, setActiveLayout] = useState<string>('dual');
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'offline'>('connecting');

  // Multi-Agent WebSocket lifecycle
  useEffect(() => {
    const isLocal = typeof window !== 'undefined' && window.location.hostname === 'localhost';
    const proto = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = typeof window !== 'undefined' ? window.location.host : 'localhost:8000';
    const url = isLocal
      ? 'ws://localhost:8000/api/ws/multi-agent'
      : `${proto}//${host}/apps/fuzeagent/api/ws/multi-agent`;

    let ws: WebSocket | null = null;
    let pingInterval: any = null;

    try {
      ws = new WebSocket(url);
      activeWs = ws;

      ws.onopen = () => {
        setWsStatus('connected');
        pingInterval = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: 'ping' }));
          }
        }, 15000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          broadcastAgentWs(data);
        } catch {
          // ignore
        }
      };

      ws.onclose = () => {
        setWsStatus('offline');
        clearInterval(pingInterval);
      };

      ws.onerror = () => {
        setWsStatus('offline');
      };
    } catch {
      setWsStatus('offline');
    }

    return () => {
      clearInterval(pingInterval);
      if (ws) ws.close();
      activeWs = null;
    };
  }, []);

  const onReady = (event: DockviewReadyEvent) => {
    setApi(event.api);

    // Initial layout: 2 side-by-side agents (Python Dev + React Dev)
    const pythonDev = AGENT_PERSONAS.find(a => a.id === 'python-dev')!;
    const reactDev = AGENT_PERSONAS.find(a => a.id === 'react-dev')!;

    const panel1 = event.api.addPanel({
      id: 'panel_python_dev',
      component: 'agentChat',
      title: `${pythonDev.emoji} ${pythonDev.name}`,
      params: { agent: pythonDev },
    });

    event.api.addPanel({
      id: 'panel_react_dev',
      component: 'agentChat',
      title: `${reactDev.emoji} ${reactDev.name}`,
      params: { agent: reactDev },
      position: { referencePanel: panel1, direction: 'right' },
    });
  };

  const handleAddAgent = (agent: AgentPersona, direction: 'right' | 'below' | 'within' = 'right') => {
    if (!api) return;
    const panelId = `panel_${agent.id}_${Date.now()}`;
    const activePanel = api.activePanel;

    api.addPanel({
      id: panelId,
      component: 'agentChat',
      title: `${agent.emoji} ${agent.name}`,
      params: { agent },
      position: activePanel
        ? { referencePanel: activePanel, direction }
        : undefined,
    });
  };

  const applyPreset = (preset: 'dual' | 'triple' | 'quad') => {
    if (!api) return;
    api.clear();
    setActiveLayout(preset);

    const python = AGENT_PERSONAS.find(a => a.id === 'python-dev')!;
    const react = AGENT_PERSONAS.find(a => a.id === 'react-dev')!;
    const devops = AGENT_PERSONAS.find(a => a.id === 'devops-lead')!;
    const core = AGENT_PERSONAS.find(a => a.id === 'core-eng')!;

    const p1 = api.addPanel({
      id: 'p_py',
      component: 'agentChat',
      title: `${python.emoji} ${python.name}`,
      params: { agent: python },
    });

    const p2 = api.addPanel({
      id: 'p_react',
      component: 'agentChat',
      title: `${react.emoji} ${react.name}`,
      params: { agent: react },
      position: { referencePanel: p1, direction: 'right' },
    });

    if (preset === 'triple' || preset === 'quad') {
      api.addPanel({
        id: 'p_devops',
        component: 'agentChat',
        title: `${devops.emoji} ${devops.name}`,
        params: { agent: devops },
        position: { referencePanel: p1, direction: 'below' },
      });

      if (preset === 'quad') {
        api.addPanel({
          id: 'p_core',
          component: 'agentChat',
          title: `${core.emoji} ${core.name}`,
          params: { agent: core },
          position: { referencePanel: p2, direction: 'below' },
        });
      }
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--bg-primary, #0f131c)',
      }}
    >
      {/* Top Workspace Command Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          borderBottom: '1px solid var(--border-color, #232c3d)',
          backgroundColor: 'var(--bg-secondary, #0b0e15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <LayoutGrid size={16} color="var(--accent-color, #6e5cff)" />
            <span style={{ fontWeight: 600, fontSize: '14px' }}>Multi-Agent Workspace</span>
            <Badge variant="seam" size="sm">VSCode Dock</Badge>
          </div>

          <StatusPill
            status={wsStatus === 'connected' ? 'online' : wsStatus === 'connecting' ? 'pending' : 'idle'}
            label={wsStatus === 'connected' ? '⚡ Live WebSocket Bus' : wsStatus === 'connecting' ? 'Connecting...' : 'Offline Fallback'}
          />

          <span style={{ color: 'var(--border-strong, #303b50)' }}>|</span>

          {/* Preset Buttons */}
          <div style={{ display: 'flex', gap: '4px' }}>
            <Button
              size="sm"
              variant={activeLayout === 'dual' ? 'primary' : 'ghost'}
              onClick={() => applyPreset('dual')}
            >
              2-Split
            </Button>
            <Button
              size="sm"
              variant={activeLayout === 'triple' ? 'primary' : 'ghost'}
              onClick={() => applyPreset('triple')}
            >
              3-Split
            </Button>
            <Button
              size="sm"
              variant={activeLayout === 'quad' ? 'primary' : 'ghost'}
              onClick={() => applyPreset('quad')}
            >
              4-Grid
            </Button>
          </div>
        </div>

        {/* Quick Add Agent Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary, #66718a)' }}>Open Agent:</span>
          {AGENT_PERSONAS.map(agent => (
            <button
              key={agent.id}
              onClick={() => handleAddAgent(agent, 'right')}
              title={`Open ${agent.name} chat`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '4px 8px',
                backgroundColor: 'var(--bg-quaternary, #1c2433)',
                border: '1px solid var(--border-color, #232c3d)',
                borderRadius: 'var(--radius-sm, 4px)',
                color: 'var(--text-primary, #e7ecf5)',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: 500,
              }}
            >
              <span>{agent.emoji}</span>
              <span>{agent.name.split(' ')[0]}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Dockview Workspace Canvas */}
      <div style={{ flex: 1, position: 'relative' }} className="dockview-theme-dark">
        <DockviewReact
          onReady={onReady}
          components={{
            agentChat: AgentChatPanel,
          }}
        />
      </div>
    </div>
  );
};
