import React, { useState, useEffect } from 'react';
import {
  Send,
  Plus,
  Maximize2,
  Sliders,
  Sparkles,
  Bot,
  Terminal,
  Activity,
  Trash2,
  Clock,
  Compass,
  Cpu
} from 'lucide-react';
import {
  TimeInZoneCard,
  TerminalLogWindow,
  SandboxStatusBadge,
  StreamingThoughtIndicator,
} from '../design-system';

interface ChatThread {
  id: string;
  title: string;
  updatedAt: string;
  model: string;
}

interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  thought?: { title: string; duration: string; details: string };
  cards?: Array<
    | { type: 'time_in_zone'; data: { timeString: string; zone: string } }
    | { type: 'terminal_log'; data: { title: string; logs: string[] } }
    | { type: 'sandbox_badge'; data: { status: 'running' | 'idle' | 'failed'; pod: string } }
  >;
}

export const StandaloneChatPage: React.FC = () => {
  const [threads, setThreads] = useState<ChatThread[]>([
    {
      id: 'thread-today-1',
      title: 'Current Time & World Clock Stream',
      updatedAt: 'Just now',
      model: 'FuzeAgent Multi-Agent',
    },
    {
      id: 'thread-today-2',
      title: 'Argocd PostSync & Pod Rollouts',
      updatedAt: '2 hours ago',
      model: 'Claude 3.5 Sonnet',
    },
    {
      id: 'thread-prev-1',
      title: 'PostgreSQL DB Migration & RAG Schema',
      updatedAt: '3 days ago',
      model: 'GPT-4o',
    },
  ]);

  const [activeThreadId, setActiveThreadId] = useState<string>('thread-today-1');
  const [selectedModel, setSelectedModel] = useState<string>('fuzeagent-multi-agent');
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const [telemetryOpen, setTelemetryOpen] = useState<boolean>(false);
  const [input, setInput] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [thoughtExpanded, setThoughtExpanded] = useState<boolean>(true);

  // Time in LA live clock
  const [laTime, setLaTime] = useState<string>(() => {
    return new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/Los_Angeles',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      timeZoneName: 'short',
    }).format(new Date());
  });

  useEffect(() => {
    const timer = setInterval(() => {
      setLaTime(
        new Intl.DateTimeFormat('en-US', {
          timeZone: 'America/Los_Angeles',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: true,
          timeZoneName: 'short',
        }).format(new Date())
      );
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: 'm1',
      role: 'user',
      content: 'What is the current local time in Los Angeles, California right now?',
      timestamp: '12:04 PM',
    },
    {
      id: 'm2',
      role: 'assistant',
      content:
        'I queried the system time broker with timezone `America/Los_Angeles` (Pacific Daylight Time). Here is the verified real-time stream:',
      timestamp: '12:04 PM',
      thought: {
        title: 'Querying world time relay & verifying timezone offset',
        duration: '1.2s',
        details:
          '1. Identified target timezone: America/Los_Angeles\n2. Resolved UTC offset: UTC-7 (PDT daylight saving observed)\n3. Invoked live time provider and bound streaming card.\n4. Sandbox container sandbox-agent-7f92 confirmed heartbeat.',
      },
      cards: [
        {
          type: 'time_in_zone',
          data: {
            timeString: `Los Angeles: ${laTime}`,
            zone: 'America/Los_Angeles (PDT)',
          },
        },
        {
          type: 'sandbox_badge',
          data: {
            status: 'running',
            pod: 'pod/sandbox-agent-7f92-la',
          },
        },
      ],
    },
  ]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    const userText = input.trim();
    setInput('');

    const newMsg: MessageItem = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: userText,
      timestamp: 'Just now',
    };

    setMessages((prev) => [...prev, newMsg]);
    setIsStreaming(true);

    setTimeout(() => {
      const isTimeQuery =
        userText.toLowerCase().includes('time') ||
        userText.toLowerCase().includes('la') ||
        userText.toLowerCase().includes('los angeles');

      const assistantMsg: MessageItem = {
        id: `ast_${Date.now()}`,
        role: 'assistant',
        content: isTimeQuery
          ? `Here is the current updated live time in Los Angeles:`
          : `I have processed your request for "${userText}". Here is the verified sandbox output:`,
        timestamp: 'Just now',
        thought: {
          title: 'Orchestrating agent sub-routine',
          duration: '0.8s',
          details: `Processed instruction via model ${selectedModel}. Executed isolated container commands.`,
        },
        cards: isTimeQuery
          ? [
              {
                type: 'time_in_zone',
                data: {
                  timeString: `Los Angeles: ${laTime}`,
                  zone: 'America/Los_Angeles (PDT)',
                },
              },
            ]
          : [
              {
                type: 'terminal_log',
                data: {
                  title: 'Task Execution Logs',
                  logs: [
                    'Initialized sandbox worker pod...',
                    `Executed instruction: ${userText}`,
                    'Exit code: 0 (Success)',
                  ],
                },
              },
            ],
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setIsStreaming(false);
    }, 1200);
  };

  const handlePopOut = () => {
    const popoutUrl = `${window.location.origin}/chat/window`;
    window.open(popoutUrl, '_blank', 'width=1280,height=860,menubar=no,toolbar=no,status=no');
  };

  const handleNewChat = () => {
    const newId = `thread_${Date.now()}`;
    const newThread: ChatThread = {
      id: newId,
      title: 'New Conversation',
      updatedAt: 'Just now',
      model: selectedModel,
    };
    setThreads([newThread, ...threads]);
    setActiveThreadId(newId);
    setMessages([
      {
        id: `welcome_${Date.now()}`,
        role: 'assistant',
        content:
          "Welcome to your standalone FuzeAgent workspace! I'm ready to orchestrate Kubernetes clusters, check live timezones, or analyze code.",
        timestamp: 'Just now',
      },
    ]);
  };

  return (
    <div
      className="flex w-screen h-screen overflow-hidden text-[var(--text-primary)] font-sans select-none"
      style={{
        backgroundColor: 'var(--bg-primary, #0b0e15)',
        color: 'var(--text-primary, #f0f4f8)',
      }}
    >
      {/* 1. Left Sidebar: Threads History & Models */}
      <aside
        className={`flex flex-col border-r transition-all duration-300 relative z-20 ${
          sidebarOpen ? 'w-64 min-w-[16rem]' : 'w-0 min-w-0 -translate-x-full overflow-hidden'
        }`}
        style={{
          backgroundColor: 'var(--bg-secondary, #0f131c)',
          borderColor: 'var(--border-color, #232c3d)',
        }}
      >
        {/* Brand & New Chat */}
        <div
          className="p-3 border-b flex items-center justify-between"
          style={{ borderColor: 'var(--border-color, #232c3d)' }}
        >
          <div className="flex items-center gap-2 font-bold text-sm tracking-wide">
            <span
              className="w-7 h-7 rounded-lg flex items-center justify-center text-white"
              style={{ background: 'var(--seam, linear-gradient(135deg, #6e5cff, #29d3e6))' }}
            >
              <Bot className="w-4 h-4" />
            </span>
            <span className="font-display">FuzeAgent</span>
          </div>

          <button
            onClick={handleNewChat}
            className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border font-medium transition-colors hover:border-cyan-400"
            style={{
              backgroundColor: 'var(--bg-tertiary, #141a26)',
              borderColor: 'var(--border-color, #232c3d)',
            }}
            title="Start new chat (⌘K)"
          >
            <Plus className="w-3.5 h-3.5 text-cyan-400" />
            <span>New Chat</span>
          </button>
        </div>

        {/* Model Selector */}
        <div
          className="p-3 border-b flex flex-col gap-1.5"
          style={{ borderColor: 'var(--border-color, #232c3d)' }}
        >
          <label className="text-[10px] font-mono uppercase text-[var(--text-tertiary)] flex items-center gap-1">
            <Sliders className="w-3 h-3 text-cyan-400" />
            <span>Active Model</span>
          </label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full text-xs py-1.5 px-2 rounded-lg border bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-primary)] outline-none focus:border-cyan-400 cursor-pointer"
          >
            <option value="fuzeagent-multi-agent">🤖 FuzeAgent Multi-Agent</option>
            <option value="claude-3-5-sonnet">⚡ Claude 3.5 Sonnet</option>
            <option value="gpt-4o">🧠 OpenAI GPT-4o</option>
          </select>
        </div>

        {/* Threads List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <div className="text-[10px] font-mono uppercase text-[var(--text-tertiary)] px-2 py-1">
            Recent Conversations
          </div>
          {threads.map((thread) => {
            const isActive = thread.id === activeThreadId;
            return (
              <div
                key={thread.id}
                onClick={() => setActiveThreadId(thread.id)}
                className={`group flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition-colors ${
                  isActive
                    ? 'border border-cyan-500/40 bg-[var(--bg-tertiary)] text-cyan-300 font-semibold'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="w-2 h-2 rounded-full bg-cyan-400/80" />
                  <span className="truncate">{thread.title}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setThreads(threads.filter((t) => t.id !== thread.id));
                  }}
                  className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-rose-400 transition-opacity p-0.5"
                  title="Delete chat"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            );
          })}
        </div>

        {/* User / Pod Info Footer */}
        <div
          className="p-3 border-t text-[11px] flex items-center justify-between text-[var(--text-tertiary)]"
          style={{ borderColor: 'var(--border-color, #232c3d)' }}
        >
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-mono">Cluster: contabo-prod</span>
          </div>
          <span className="font-mono">v1.2.3</span>
        </div>
      </aside>

      {/* 2. Main Center Canvas: OpenWebUI/Claude-style Standalone Window */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Navigation Bar */}
        <header
          className="h-12 border-b px-4 flex items-center justify-between z-10"
          style={{
            backgroundColor: 'var(--bg-secondary, #0f131c)',
            borderColor: 'var(--border-color, #232c3d)',
          }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 rounded-lg border text-[var(--text-secondary)] hover:text-white transition-colors"
              style={{
                backgroundColor: 'var(--bg-tertiary, #141a26)',
                borderColor: 'var(--border-color, #232c3d)',
              }}
              title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
            >
              ☰
            </button>

            <div>
              <h1 className="text-sm font-bold flex items-center gap-2">
                <span>Standalone Chat Window</span>
                <span
                  className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-cyan-500/30 text-cyan-300"
                  style={{ backgroundColor: 'rgba(41, 211, 230, 0.1)' }}
                >
                  {selectedModel}
                </span>
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Pop-out standalone window button */}
            <button
              onClick={handlePopOut}
              className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border text-[var(--text-secondary)] hover:text-cyan-300 transition-colors"
              style={{
                backgroundColor: 'var(--bg-tertiary, #141a26)',
                borderColor: 'var(--border-color, #232c3d)',
              }}
              title="Open standalone window"
            >
              <Maximize2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Pop Out</span>
            </button>

            {/* Telemetry drawer toggle */}
            <button
              onClick={() => setTelemetryOpen(!telemetryOpen)}
              className={`p-1.5 rounded-lg border transition-colors ${
                telemetryOpen
                  ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40'
                  : 'text-[var(--text-secondary)] hover:text-white'
              }`}
              style={{
                backgroundColor: telemetryOpen ? undefined : 'var(--bg-tertiary, #141a26)',
                borderColor: telemetryOpen ? undefined : 'var(--border-color, #232c3d)',
              }}
              title="Toggle Telemetry Drawer"
            >
              <Activity className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Message Feed Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg) => {
              const isAssistant = msg.role === 'assistant';
              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isAssistant ? 'items-start' : 'items-end'}`}
                >
                  {/* Meta tag */}
                  <div className="flex items-center gap-2 mb-1.5 px-1 text-[11px] text-[var(--text-tertiary)]">
                    <span className="font-semibold text-[var(--text-secondary)]">
                      {isAssistant ? 'FuzeAgent' : 'You'}
                    </span>
                    <span>·</span>
                    <span>{msg.timestamp}</span>
                  </div>

                  {/* Thought accordion if present */}
                  {msg.thought && (
                    <div
                      className="w-full mb-3 rounded-xl border overflow-hidden transition-all text-xs"
                      style={{
                        backgroundColor: 'var(--bg-secondary, #0f131c)',
                        borderColor: 'var(--border-color, #232c3d)',
                      }}
                    >
                      <button
                        onClick={() => setThoughtExpanded(!thoughtExpanded)}
                        className="w-full px-3 py-2 flex items-center justify-between text-cyan-300 font-medium hover:bg-slate-800/40 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Sparkles className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
                          <span>
                            Thought process ({msg.thought.duration})
                          </span>
                        </div>
                        <span className="text-gray-400 text-xs">
                          {thoughtExpanded ? 'Hide ▲' : 'Show ▼'}
                        </span>
                      </button>

                      {thoughtExpanded && (
                        <div
                          className="px-3 py-2.5 font-mono text-[11px] border-t leading-relaxed text-[var(--text-secondary)] whitespace-pre-wrap"
                          style={{
                            backgroundColor: 'var(--bg-primary, #0b0e15)',
                            borderColor: 'var(--border-color, #232c3d)',
                          }}
                        >
                          {msg.thought.details}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Bubble Content */}
                  <div
                    className={`rounded-2xl p-4 text-sm leading-relaxed max-w-2xl relative ${
                      isAssistant
                        ? 'border shadow-lg text-[var(--text-primary)]'
                        : 'bg-cyan-600 text-white font-medium shadow-md'
                    }`}
                    style={
                      isAssistant
                        ? {
                            backgroundColor: 'var(--bg-secondary, #0f131c)',
                            borderColor: 'var(--border-color, #232c3d)',
                          }
                        : undefined
                    }
                  >
                    {/* Assistant fuse seam */}
                    {isAssistant && (
                      <div
                        className="absolute top-0 left-0 right-0 h-[2px] rounded-t-2xl"
                        style={{
                          background: 'var(--seam, linear-gradient(90deg, #6e5cff, #29d3e6))',
                        }}
                      />
                    )}
                    <p>{msg.content}</p>
                  </div>

                  {/* Custom Tool Cards */}
                  {msg.cards && msg.cards.length > 0 && (
                    <div className="w-full max-w-2xl mt-3 space-y-3">
                      {msg.cards.map((card, idx) => {
                        if (card.type === 'time_in_zone') {
                          return (
                            <TimeInZoneCard
                              key={idx}
                              timeString={laTime}
                              zone={card.data.zone}
                            />
                          );
                        }
                        if (card.type === 'terminal_log') {
                          return (
                            <TerminalLogWindow
                              key={idx}
                              title={card.data.title}
                              logs={card.data.logs}
                            />
                          );
                        }
                        if (card.type === 'sandbox_badge') {
                          return (
                            <div key={idx} className="flex items-center gap-2">
                              <SandboxStatusBadge
                                status={card.data.status}
                                label={card.data.pod}
                              />
                            </div>
                          );
                        }
                        return null;
                      })}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Streaming indicator */}
            {isStreaming && (
              <div className="flex flex-col items-start space-y-2">
                <StreamingThoughtIndicator
                  agentName="FuzeAgent"
                  thought="Thinking and executing tool calls..."
                />
              </div>
            )}
          </div>
        </div>

        {/* Floating Composer */}
        <div
          className="p-4 border-t z-10"
          style={{
            backgroundColor: 'var(--bg-secondary, #0f131c)',
            borderColor: 'var(--border-color, #232c3d)',
          }}
        >
          <div className="max-w-3xl mx-auto space-y-2.5">
            {/* Quick Action Pills */}
            <div className="flex items-center gap-2 overflow-x-auto text-[11px] font-medium text-[var(--text-secondary)]">
              <button
                onClick={() => setInput('@agent ')}
                className="px-2.5 py-1 rounded-full border border-cyan-500/30 text-cyan-300 hover:border-cyan-400 transition-colors flex items-center gap-1"
                style={{ backgroundColor: 'rgba(41, 211, 230, 0.08)' }}
              >
                <span>@ Agent Mention</span>
              </button>
              <button
                onClick={() => setInput('What is the current time in Los Angeles, CA?')}
                className="px-2.5 py-1 rounded-full border border-slate-700 hover:border-slate-500 transition-colors flex items-center gap-1"
                style={{ backgroundColor: 'var(--bg-tertiary, #141a26)' }}
              >
                <Clock className="w-3 h-3 text-cyan-400" />
                <span>Time in LA</span>
              </button>
              <button
                onClick={() => setInput('Run kubectl get pods in namespace fuzeagent')}
                className="px-2.5 py-1 rounded-full border border-slate-700 hover:border-slate-500 transition-colors flex items-center gap-1"
                style={{ backgroundColor: 'var(--bg-tertiary, #141a26)' }}
              >
                <Terminal className="w-3 h-3 text-emerald-400" />
                <span>K8s Pod Status</span>
              </button>
            </div>

            {/* Input Row */}
            <div
              className="flex items-center gap-2 p-2 rounded-2xl border shadow-inner transition-colors focus-within:border-cyan-400"
              style={{
                backgroundColor: 'var(--bg-primary, #0b0e15)',
                borderColor: 'var(--border-color, #232c3d)',
              }}
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask FuzeAgent anything, or trigger actions with @agent or /cmd..."
                className="flex-1 bg-transparent border-none outline-none text-sm px-2 text-[var(--text-primary)] placeholder-[var(--text-tertiary)]"
              />

              <button
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                className="w-8 h-8 rounded-xl flex items-center justify-center text-white transition-opacity disabled:opacity-40"
                style={{
                  background: 'var(--seam, linear-gradient(135deg, #6e5cff, #29d3e6))',
                }}
                aria-label="Send message"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-center justify-between text-[10px] text-[var(--text-tertiary)] px-1">
              <span>Enter to send · Shift+Enter for new line</span>
              <span className="font-mono">Pod sandbox: secure & isolated</span>
            </div>
          </div>
        </div>
      </main>

      {/* 3. Optional Right Inspector Drawer: Diagnostics & Sandbox Pod Telemetry */}
      {telemetryOpen && (
        <aside
          className="w-80 min-w-[20rem] border-l flex flex-col h-full overflow-y-auto"
          style={{
            backgroundColor: 'var(--bg-secondary, #0f131c)',
            borderColor: 'var(--border-color, #232c3d)',
          }}
        >
          <div
            className="p-3 border-b flex items-center justify-between"
            style={{ borderColor: 'var(--border-color, #232c3d)' }}
          >
            <div className="flex items-center gap-2 text-xs font-bold font-display">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>Telemetry & Cluster Sandbox</span>
            </div>
            <button
              onClick={() => setTelemetryOpen(false)}
              className="text-gray-400 hover:text-white text-sm p-1"
            >
              ×
            </button>
          </div>

          <div className="p-4 space-y-4 text-xs">
            {/* Live Timezone Monitor */}
            <div
              className="p-3 rounded-xl border space-y-2"
              style={{
                backgroundColor: 'var(--bg-tertiary, #141a26)',
                borderColor: 'var(--border-color, #232c3d)',
              }}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold flex items-center gap-1.5 text-cyan-300">
                  <Compass className="w-3.5 h-3.5" />
                  <span>Timezone Stream</span>
                </span>
                <span className="text-[10px] font-mono text-emerald-400">ACTIVE</span>
              </div>
              <div className="font-mono text-sm font-semibold">{laTime}</div>
              <div className="text-[10px] text-[var(--text-tertiary)]">
                Offset: UTC-7 · America/Los_Angeles (Pacific Time)
              </div>
            </div>

            {/* Sandbox Metrics */}
            <div
              className="p-3 rounded-xl border space-y-2"
              style={{
                backgroundColor: 'var(--bg-tertiary, #141a26)',
                borderColor: 'var(--border-color, #232c3d)',
              }}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Sandbox Pod Metrics</span>
                </span>
                <span className="text-[10px] font-mono text-emerald-400">1/1 RUNNING</span>
              </div>
              <div className="space-y-1 font-mono text-[11px] text-[var(--text-secondary)]">
                <div className="flex justify-between">
                  <span>CPU Usage:</span>
                  <span className="text-cyan-300">14m (2.8%)</span>
                </div>
                <div className="flex justify-between">
                  <span>Memory RSS:</span>
                  <span className="text-cyan-300">128 MiB</span>
                </div>
                <div className="flex justify-between">
                  <span>Token Stream:</span>
                  <span className="text-cyan-300">42 tokens/sec</span>
                </div>
              </div>
            </div>

            {/* Security Isolation Notice */}
            <div
              className="p-3 rounded-xl border text-[11px] text-[var(--text-secondary)] leading-relaxed"
              style={{
                backgroundColor: 'rgba(110, 92, 255, 0.08)',
                borderColor: 'rgba(110, 92, 255, 0.25)',
              }}
            >
              <span className="font-bold text-violet-300 block mb-1">
                Security Sandbox Active
              </span>
              Container runs unprivileged with gVisor / AppArmor confinement. Mutating tools require confirmation.
            </div>
          </div>
        </aside>
      )}
    </div>
  );
};
