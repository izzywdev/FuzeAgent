import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Clock, 
  Cpu, 
  Terminal,
  Radio, 
  CheckCircle2,
  Trash2,
  PlusCircle,
  ExternalLink
} from 'lucide-react';
import { Button, Badge } from '../design-system';
import { api } from '../services/api';

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
    podName: 'agent-sbx-python-dev-prod',
    agentName: 'Python Developer Agent',
    templateId: 'claude-runner-base:latest',
    team: 'Core Engineering',
    status: 'running',
    uptimeSeconds: 420,
    timeoutSeconds: 1800,
    cpuPercent: 14.2,
    memoryMb: 512,
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
    podName: 'agent-sbx-docker-builder',
    agentName: 'App Builder Sandbox',
    templateId: 'fuzeagent-builder:v1.2',
    team: 'DevOps & SRE',
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
  const [selectedSandboxId, setSelectedSandboxId] = useState<string>(INITIAL_SANDBOXES[0].id);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Sync live sandboxes from orchestrator backend
  useEffect(() => {
    let isMounted = true;
    const fetchLiveSandboxes = async () => {
      try {
        const live = await api.getSandboxes();
        if (Array.isArray(live) && live.length > 0 && isMounted) {
          const mapped: ActiveSandbox[] = live.map((s: any) => ({
            id: s.id,
            podName: s.podName || s.id,
            agentName: s.name || s.templateId,
            templateId: s.templateId,
            team: 'Core Engineering',
            status: s.status === 'running' ? 'running' : 'idle',
            uptimeSeconds: Math.max(1, (s.timeoutSeconds || 1800) - (s.secondsRemaining || 1800)),
            timeoutSeconds: s.timeoutSeconds || 1800,
            cpuPercent: 14.2,
            memoryMb: 512,
            memoryLimitMb: 4096,
            lastEvent: s.currentTask || 'Ready for tasks',
            logs: s.logs || [],
          }));
          setSandboxes(mapped);
        }
      } catch {
        // keep fallback
      }
    };

    fetchLiveSandboxes();
    const interval = setInterval(fetchLiveSandboxes, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

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

  const handleTerminate = async (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await api.terminateSandbox(id);
    } catch {
      // ignore
    }
    setSandboxes(prev => prev.map(sb => sb.id === id ? { ...sb, status: 'terminating' as const } : sb));
    setActionNotice(`Terminating sandbox ${id} and releasing cluster PVC...`);
    setTimeout(() => {
      setSandboxes(prev => prev.filter(sb => sb.id !== id));
    }, 1500);
  };

  const handleExtend = async (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await api.extendSandboxTimeout(id, 900);
    } catch {
      // ignore
    }
    setSandboxes(prev => prev.map(sb => {
      if (sb.id === id) {
        return { ...sb, timeoutSeconds: sb.timeoutSeconds + 900 };
      }
      return sb;
    }));
    setActionNotice(`Added +15m timeout to sandbox ${id}.`);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s.toString().padStart(2, '0')}s`;
  };

  const selectedSandbox = sandboxes.find(s => s.id === selectedSandboxId) || sandboxes[0];

  return (
    <div className="space-y-6" data-frame="03-active-sandboxes-teardown" style={{ color: 'var(--text-primary, #e7ecf5)' }}>
      {/* Action Notification */}
      {actionNotice && (
        <div 
          className="p-3.5 rounded-xl border flex items-center justify-between text-xs animate-in fade-in"
          style={{
            backgroundColor: 'var(--bg-secondary, #0b0e15)',
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

      {/* Top Banner (aligned with 03-active-sandboxes-teardown.html) */}
      <div 
        className="panel p-6 shadow-2xl"
        style={{
          background: 'linear-gradient(135deg, rgba(20, 26, 38, 0.98) 0%, rgba(11, 14, 21, 0.99) 100%)',
          borderColor: 'var(--border-color, #232c3d)',
          color: 'var(--text-primary, #e7ecf5)',
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <span 
                className="p-2.5 rounded-xl border flex items-center justify-center text-emerald-400"
                style={{
                  backgroundColor: 'rgba(52, 211, 153, 0.12)',
                  borderColor: 'rgba(52, 211, 153, 0.3)',
                }}
              >
                <Shield className="w-5 h-5" />
              </span>
              <div>
                <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary, #e7ecf5)' }}>
                  Active Sandboxes & Teardown Flow
                </h1>
                <p className="text-xs" style={{ color: 'var(--text-secondary, #9fa9bc)', marginTop: '2px' }}>
                  Monitors isolated Kubernetes sandbox pods executing agent tasks and Claude runner base sessions with clean cluster deallocation.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="pill running">
              <span className="dot" />
              <span>{sandboxes.length} Active Pods</span>
            </span>
          </div>
        </div>
      </div>

      {/* Main Panel matching 03-active-sandboxes-teardown.html */}
      <div className="panel" data-sandboxes-panel style={{ borderRadius: 'var(--radius-xl, 12px)' }}>
        <div className="table-header">
          <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>
            Running Sandbox Pods ({sandboxes.length} Active)
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)' }}>
            Namespace: fuzeagent
          </div>
        </div>

        {sandboxes.length === 0 ? (
          <div 
            className="p-8 text-center text-xs"
            style={{ color: 'var(--text-secondary, #9fa9bc)' }}
          >
            No active agent sandboxes running. Launch a new container from the Image Registry or deploy an Agent Blueprint.
          </div>
        ) : (
          sandboxes.map(sb => {
            const isSelected = selectedSandbox?.id === sb.id;
            const remaining = Math.max(0, sb.timeoutSeconds - sb.uptimeSeconds);
            const isTerminating = sb.status === 'terminating';

            return (
              <div 
                key={sb.id}
                className="pod-row cursor-pointer"
                onClick={() => setSelectedSandboxId(sb.id)}
                style={{
                  backgroundColor: isSelected ? 'rgba(110, 92, 255, 0.08)' : 'transparent',
                  borderLeft: isSelected ? '3px solid var(--accent-color, #6e5cff)' : '3px solid transparent',
                }}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>
                      {sb.podName}
                    </span>
                    <span className="text-[11px] font-mono opacity-60">({sb.agentName})</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                    Session: {sb.id} · Image: {sb.templateId} · CPU: {sb.cpuPercent}% · Mem: {sb.memoryMb}MB · Timeout: {formatTime(remaining)}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {isTerminating ? (
                    <span className="pill terminating">⏳ Terminating</span>
                  ) : (
                    <span className="pill running">● Running</span>
                  )}

                  {!isTerminating && (
                    <>
                      <button
                        onClick={(e) => handleExtend(sb.id, e)}
                        className="prompt-btn"
                        title="Add 15m timeout"
                      >
                        +15m
                      </button>
                      <button 
                        className="btn-terminate"
                        data-action="terminate-sandbox"
                        onClick={(e) => handleTerminate(sb.id, e)}
                      >
                        Terminate
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Selected Pod Live Stream Terminal Console */}
      {selectedSandbox && (
        <div 
          className="panel shadow-2xl overflow-hidden flex flex-col"
          style={{
            backgroundColor: 'var(--bg-tertiary, #141a26)',
            borderColor: 'var(--border-color, #232c3d)',
            borderRadius: 'var(--radius-xl, 12px)',
          }}
        >
          <div 
            className="p-3.5 border-b flex items-center justify-between"
            style={{
              backgroundColor: 'var(--bg-secondary, #0b0e15)',
              borderColor: 'var(--border-color, #232c3d)',
            }}
          >
            <div className="flex items-center gap-2.5">
              <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
              <span className="text-xs font-bold font-mono text-slate-200">{selectedSandbox.podName}</span>
              <span className="text-[11px] font-mono" style={{ color: 'var(--text-tertiary)' }}>
                stdout/stderr bus relay
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                Heartbeat OK
              </span>
            </div>
          </div>

          <div 
            className="p-4 font-mono text-xs space-y-1.5 min-h-[260px] max-h-[360px] overflow-y-auto"
            style={{
              backgroundColor: '#080b11',
              color: '#e2e8f0',
            }}
          >
            <div 
              className="text-[11px] pb-2 border-b flex items-center justify-between font-mono"
              style={{ borderColor: '#1c2433', color: 'var(--success-color, #34d399)' }}
            >
              <span>[Centralized Bus Relay Stream Connected — wss://orchestrator:8000/ws]</span>
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
        </div>
      )}
    </div>
  );
};
export default SandboxesView;
