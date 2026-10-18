import React from 'react';
import { Terminal, Copy, Check } from 'lucide-react';

export interface TerminalLogWindowProps {
  title?: string;
  logs: string[];
  height?: string;
}

export const TerminalLogWindow: React.FC<TerminalLogWindowProps> = ({
  title = 'Kubernetes Sandbox Runner (/dev/tty)',
  logs,
  height = '240px',
}) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(logs.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div 
      className="rounded-2xl border shadow-2xl overflow-hidden font-mono text-xs flex flex-col"
      style={{
        backgroundColor: 'var(--bg-primary, #0b0e15)',
        borderColor: 'var(--border-color, #232c3d)',
      }}
    >
      {/* Title Bar */}
      <div 
        className="px-4 py-2.5 border-b flex items-center justify-between"
        style={{
          backgroundColor: 'var(--bg-secondary, #0f131c)',
          borderColor: 'var(--border-color, #232c3d)',
        }}
      >
        <div className="flex items-center gap-2 text-[var(--text-secondary)]">
          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
          <span className="font-bold text-[11px] text-[var(--text-primary)]">{title}</span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex gap-1.5 mr-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
          </div>
          <button
            onClick={handleCopy}
            className="p-1 rounded hover:bg-slate-800 text-[var(--text-tertiary)] hover:text-white transition-colors"
            title="Copy logs"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Log Feed */}
      <div 
        className="p-4 overflow-y-auto space-y-1 select-text"
        style={{ maxHeight: height }}
      >
        {logs.length === 0 ? (
          <div className="text-[var(--text-tertiary)] italic">Waiting for container sandbox telemetry...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="flex gap-3 leading-relaxed">
              <span className="text-[var(--text-tertiary)] opacity-50 select-none text-[10px] w-6 text-right">
                {index + 1}
              </span>
              <span className="text-[var(--text-primary)] break-all">{log}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
