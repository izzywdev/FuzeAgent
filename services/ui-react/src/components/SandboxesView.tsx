import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Clock, 
  Cpu, 
  Square, 
  Radio, 
  CheckCircle2
} from 'lucide-react';
import { Button, Badge } from '../design-system';

interface ActiveSandbox {
  id: string;
  podName: string;
  agentName: string;
  templateId: string;
  team: string;
  status: 'running' | 'idle' | 'terminating';
  uptimeSeconds: number;
  timeoutSeconds: number;
  cpuPercent: number;
  memoryMb: number;
  memoryLimitMb: number;
  lastEvent: string;
  logs: string[];
}

const INITIAL_SANDBOXES: ActiveSandbox[] = [
  {
    id: 'sbx-py-7721',
    podName: 'fuzeagent-runner-py-9df82',
    agentName: 'Python Dev #1',
    templateId: 'python-dev',
    team: 'Core Engineering',
    status: 'running',
    uptimeSeconds: 420,
    timeoutSeconds: 1800,
    cpuPercent: 34.2,
    memoryMb: 412,
    memoryLimitMb: 4096,
    lastEvent: 'Running pytest tests/test_fuzekeys_bridge.py',
    logs: [
      '[session-relay] Agent Python Dev #1 starting, relay: wss://fuzeagent.prod.fuzefront.com/ws/stream',
      '[init] Starting Python sandbox container...',
      '[init] Synchronizing zero-exposure secrets from FuzeKeys API...',
      '[runner] Received task: "Implement zero-exposure credential relay"',
      '[claude] Inspecting tests/test_fuzekeys_bridge.py...',
      '[tool_call] exec: pytest -v tests/test_fuzekeys_bridge.py',
      '[output] ================= 4 passed in 0.42s ================='
    ]
  },
  {
    id: 'sbx-react-3190',
    podName: 'fuzeagent-runner-react-4aa12',
    agentName: 'React Developer #2',
    templateId: 'react-dev',
    team: 'Core Engineering',
    status: 'idle',
    uptimeSeconds: 980,
    timeoutSeconds: 1800,
    cpuPercent: 4.1,
    memoryMb: 528,
    memoryLimitMb: 4096,
    lastEvent: 'Idle: waiting for next prompt on centralized bus',
    logs: [
      '[session-relay] Connected to centralized event bus',
      '[init] React & TypeScript Agent sandbox ready',
      '[runner] Vite build succeeded with 0 errors in 1.4s',
      '[stream] Waiting for user input via FuzeFront portal chat...'
    ]
  }
];

export const SandboxesView: React.FC = () => {
  const [sandboxes, setSandboxes] = useState<ActiveSandbox[]>(INITIAL_SANDBOXES);
  const [selectedSandbox, setSelectedSandbox] = useState<ActiveSandbox>(INITIAL_SANDBOXES[0]);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Live timer tick
  useEffect(() => {
    const timer = setInterval(() => {
      setSandboxes(prev => prev.map(sb => {
        if (sb.status === 'running' || sb.status === 'idle') {
          return { ...sb, uptimeSeconds: sb.uptimeSeconds + 1 };
        }
        return sb;
      }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleTerminate = (id: string) => {
    setSandboxes(prev => prev.filter(sb => sb.id !== id));
    if (selectedSandbox?.id === id) {
      setSelectedSandbox(sandboxes.find(s => s.id !== id) || INITIAL_SANDBOXES[0]);
    }
    setActionNotice(`Terminated sandbox ${id} and reclaimed cluster pod resources.`);
    setTimeout(() => setActionNotice(null), 4000);
  };

  const handleExtend = (id: string) => {
    setSandboxes(prev => prev.map(sb => {
      if (sb.id === id) {
        return { ...sb, timeoutSeconds: sb.timeoutSeconds + 900 };
      }
      return sb;
    }));
    setActionNotice(`Extended sandbox timeout by +15 minutes (900s).`);
    setTimeout(() => setActionNotice(null), 4000);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s < 10 ? '0' : ''}${s}s`;
  };

  return (
    <div className="space-y-6">
      {/* Toast Notice */}
      {actionNotice && (
        <div 
          className="p-3.5 rounded-xl border flex items-center justify-between text-xs animate-in fade-in shadow-lg"
          style={{
            backgroundColor: 'var(--bg-tertiary, #141a26)',
            borderColor: 'var(--accent-color, #6e5cff)',
            color: 'var(--text-primary, #e7ecf5)',
          }}
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{actionNotice}</span>
          </div>
          <button onClick={() => setActionNotice(null)} className="opacity-60 hover:opacity-100">✕</button>
        </div>
      )}

      {/* Top Banner (FuzeFront Dark Seam) */}
      <div 
        className="p-6 rounded-2xl border relative overflow-hidden shadow-2xl"
        style={{
          background: 'linear-gradient(135deg, rgba(20, 26, 38, 0.95) 0%, rgba(11, 14, 21, 0.98) 100%)',
          borderColor: 'var(--border-color, #232c3d)',
        }}
      >
        <div 
          className="absolute top-0 left-0 right-0 h-[2px]"
          style={{ background: 'var(--seam, linear-gradient(90deg, #6e5cff 0%, #29d3e6 100%))' }}
        />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span 
                className="p-2 rounded-xl border flex items-center justify-center text-emerald-400"
                style={{
                  backgroundColor: 'rgba(52, 211, 153, 0.12)',
                  borderColor: 'rgba(52, 211, 153, 0.3)',
                }}
              >
                <Shield className="w-5 h-5" />
              </span>
              <div>
                <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary, #e7ecf5)' }}>
                  Active Agents & Isolation Monitor
                </h2>
                <p className="text-xs" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                  Live Kubernetes pods executing containerized agent runtimes with strict resource boundaries and auto-shutdown timers.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span 
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-mono"
              style={{
                backgroundColor: 'rgba(52, 211, 153, 0.12)',
                borderColor: 'rgba(52, 211, 153, 0.3)',
                color: 'var(--success-color, #34d399)',
              }}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-semibold">{sandboxes.length} Active Pods</span>
            </span>
          </div>
        </div>
      </div>

      {/* Grid: Active Pods List + Live Stream Console */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Active Pods Roster */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Active Sandboxed Runtimes ({sandboxes.length})
            </span>
          </div>

          {sandboxes.length === 0 ? (
            <div 
              className="p-8 text-center rounded-2xl border text-xs"
              style={{
                backgroundColor: 'var(--bg-tertiary, #141a26)',
                borderColor: 'var(--border-color, #232c3d)',
                color: 'var(--text-secondary, #9fa9bc)',
              }}
            >
              No active agent sandboxes running. Launch a new container from the Image Registry or deploy an Agent Blueprint.
            </div>
          ) : (
            sandboxes.map(sb => {
              const isSelected = selectedSandbox?.id === sb.id;
              const remaining = Math.max(0, sb.timeoutSeconds - sb.uptimeSeconds);
              return (
                <div
                  key={sb.id}
                  onClick={() => setSelectedSandbox(sb)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    isSelected ? 'ring-1 ring-emerald-500/50 shadow-lg' : 'hover:border-slate-700'
                  }`}
                  style={{
                    backgroundColor: isSelected ? 'rgba(52, 211, 153, 0.08)' : 'var(--bg-tertiary, #141a26)',
                    borderColor: isSelected ? 'var(--success-color, #34d399)' : 'var(--border-color, #232c3d)',
                    color: 'var(--text-primary, #e7ecf5)',
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span 
                          className="w-2 h-2 rounded-full"
                          style={{
                            backgroundColor: sb.status === 'running' ? 'var(--success-color, #34d399)' : '#9fa9bc',
                            boxShadow: sb.status === 'running' ? '0 0 6px var(--success-color, #34d399)' : 'none',
                          }}
                        />
                        <h4 className="text-xs font-bold leading-tight" style={{ color: 'var(--text-primary)' }}>
                          {sb.agentName}
                        </h4>
                      </div>
                      <p className="text-[11px] font-mono mt-1 opacity-70" style={{ color: 'var(--text-secondary)' }}>
                        {sb.podName}
                      </p>
                    </div>

                    <Badge variant={sb.status === 'running' ? 'success' : 'default'} size="sm">
                      {sb.team}
                    </Badge>
                  </div>

                  <div className="mt-3.5 pt-2.5 border-t grid grid-cols-2 gap-2 text-xs" style={{ borderColor: 'var(--border-color)' }}>
                    <div className="flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                      <Clock className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                      <span className="text-[11px]">Shutdown: <strong className="text-amber-300 font-mono">{formatTime(remaining)}</strong></span>
                    </div>

                    <div className="flex items-center gap-1.5 font-mono text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                      <Cpu className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                      <span>{sb.cpuPercent}% | {sb.memoryMb}MB</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Live Stream Console */}
        {selectedSandbox && (
          <div 
            className="lg:col-span-7 rounded-2xl border shadow-2xl overflow-hidden flex flex-col"
            style={{
              backgroundColor: 'var(--bg-tertiary, #141a26)',
              borderColor: 'var(--border-color, #232c3d)',
            }}
          >
            {/* Console Header */}
            <div 
              className="p-4 border-b flex items-center justify-between"
              style={{
                backgroundColor: 'var(--bg-secondary, #0b0e15)',
                borderColor: 'var(--border-color, #232c3d)',
              }}
            >
              <div className="flex items-center gap-2.5">
                <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
                <span className="text-xs font-bold font-mono text-slate-200">{selectedSandbox.podName}</span>
                <span className="text-[11px] opacity-70 font-mono" style={{ color: 'var(--text-secondary)' }}>
                  ({selectedSandbox.templateId})
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleExtend(selectedSandbox.id)}
                  title="Add 15m to shutdown timer"
                >
                  +15m Timeout
                </Button>

                <Button
                  variant="danger"
                  size="sm"
                  icon={<Square className="w-3 h-3" />}
                  onClick={() => handleTerminate(selectedSandbox.id)}
                >
                  Stop Container
                </Button>
              </div>
            </div>

            {/* Terminal Body */}
            <div 
              className="p-4 flex-1 overflow-y-auto font-mono text-xs space-y-1.5 min-h-[340px]"
              style={{
                backgroundColor: '#080b11',
                color: '#e2e8f0',
              }}
            >
              <div 
                className="text-[11px] pb-2 border-b flex items-center justify-between font-mono"
                style={{ borderColor: '#1c2433', color: 'var(--success-color, #34d399)' }}
              >
                <span>[Centralized Bus Relay Stream Connected — ws://orchestrator:8000/ws]</span>
                <span className="text-slate-500">Namespace: fuzeagent</span>
              </div>

              {selectedSandbox.logs.map((log, idx) => (
                <div key={idx} className="leading-relaxed flex items-start gap-2">
                  <span className="text-slate-600 select-none text-[10px] w-5 text-right">{idx + 1}</span>
                  <span 
                    className={
                      log.includes('error') || log.includes('fail')
                        ? 'text-rose-400 font-semibold'
                        : log.includes('passed') || log.includes('success')
                        ? 'text-emerald-400 font-bold'
                        : log.includes('[init]') || log.includes('[runner]')
                        ? 'text-indigo-400'
                        : 'text-slate-300'
                    }
                  >
                    {log}
                  </span>
                </div>
              ))}
            </div>

            {/* Console Footer */}
            <div 
              className="p-3 border-t text-[11px] flex items-center justify-between"
              style={{
                backgroundColor: 'var(--bg-secondary, #0b0e15)',
                borderColor: 'var(--border-color, #232c3d)',
                color: 'var(--text-secondary)',
              }}
            >
              <span>Streaming active stdout/stderr over WebSocket bridge</span>
              <span className="font-mono text-emerald-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                Heartbeat OK (ping 29s)
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
export default SandboxesView;
