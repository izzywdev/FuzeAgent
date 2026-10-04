import { useState, useEffect } from 'react';
import { 
  Shield, 
  Clock, 
  Cpu, 
  Square, 
  Radio
} from 'lucide-react';

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

const MOCK_SANDBOXES: ActiveSandbox[] = [
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

export function SandboxesView() {
  const [sandboxes, setSandboxes] = useState<ActiveSandbox[]>(MOCK_SANDBOXES);
  const [selectedSandbox, setSelectedSandbox] = useState<ActiveSandbox>(MOCK_SANDBOXES[0]);
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
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gradient-to-r from-emerald-950 via-slate-900 to-slate-950 p-6 rounded-xl border border-emerald-800/40 text-white shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 bg-emerald-500/20 text-emerald-400 rounded-md border border-emerald-500/30">
              <Shield className="w-5 h-5" />
            </span>
            <h2 className="text-xl font-bold tracking-tight">Active Sandboxes & Isolation Monitor</h2>
          </div>
          <p className="text-sm text-slate-300 max-w-2xl">
            Live Kubernetes pods executing containerized agent runtimes. Full resource capping, strict network boundaries, 
            and enforced auto-shutdown timers to prevent runaway processes.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-950 text-emerald-300 border border-emerald-500/40 rounded-lg text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            {sandboxes.length} Active Pods
          </span>
        </div>
      </div>

      {actionNotice && (
        <div className="p-3 bg-emerald-950/40 border border-emerald-500/40 rounded-lg text-xs text-emerald-200 flex items-center justify-between animate-in fade-in duration-200">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-emerald-400 hover:underline">Dismiss</button>
        </div>
      )}

      {/* Grid: Sandboxes list + Live Stream console */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Active Pods List */}
        <div className="lg:col-span-5 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-1">
            Active Sandboxed Runtimes
          </div>
          {sandboxes.length === 0 ? (
            <div className="p-8 text-center bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-500 text-xs">
              No active sandboxes running. Launch a new container from the Image Registry.
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
                    isSelected 
                      ? 'bg-emerald-950/20 border-emerald-500/80 shadow-md ring-1 ring-emerald-500/40' 
                      : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                        <h4 className="text-sm font-bold text-slate-900 dark:text-white">{sb.agentName}</h4>
                      </div>
                      <p className="text-xs text-slate-500 font-mono mt-0.5">{sb.podName}</p>
                    </div>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      {sb.team}
                    </span>
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs border-t border-slate-100 dark:border-slate-800 pt-2.5">
                    <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
                      <Clock className="w-3.5 h-3.5 text-amber-500" />
                      <span>Shutdown in: <strong>{formatTime(remaining)}</strong></span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400 font-mono text-[11px]">
                      <Cpu className="w-3.5 h-3.5 text-indigo-500" />
                      <span>{sb.cpuPercent}% | {sb.memoryMb}MB</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Live Container Stream Console */}
        {selectedSandbox && (
          <div className="lg:col-span-7 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-emerald-500 animate-pulse" />
                <span className="text-xs font-bold text-slate-900 dark:text-white font-mono">{selectedSandbox.podName}</span>
                <span className="text-xs text-slate-500">({selectedSandbox.templateId})</span>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => handleExtend(selectedSandbox.id)}
                  className="px-2.5 py-1 text-xs bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded font-medium transition-all"
                  title="Add 15m to shutdown timer"
                >
                  +15m Timeout
                </button>
                <button 
                  onClick={() => handleTerminate(selectedSandbox.id)}
                  className="px-2.5 py-1 text-xs bg-rose-600 hover:bg-rose-500 text-white rounded font-medium transition-all flex items-center gap-1 shadow-sm active:scale-95"
                >
                  <Square className="w-3 h-3" /> Stop
                </button>
              </div>
            </div>

            <div className="p-4 bg-slate-950 flex-1 overflow-y-auto font-mono text-xs text-slate-300 space-y-1.5 min-h-[300px]">
              <div className="text-emerald-400 text-[11px] pb-2 border-b border-slate-800">
                [Centralized Bus Relay Stream Connected — ws://orchestrator:8000/ws]
              </div>
              {selectedSandbox.logs.map((log, idx) => (
                <div key={idx} className="leading-relaxed">
                  <span className="text-slate-600 select-none mr-2">{idx + 1}</span>
                  <span className={log.includes('error') ? 'text-rose-400' : log.includes('passed') ? 'text-emerald-400 font-bold' : log.includes('[init]') ? 'text-indigo-400' : 'text-slate-300'}>
                    {log}
                  </span>
                </div>
              ))}
            </div>

            <div className="p-3 bg-slate-900 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Streaming active stdout/stderr over WebSocket bridge</span>
              <span className="text-emerald-400 font-mono">Heartbeat OK (ping 29s)</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SandboxesView;
