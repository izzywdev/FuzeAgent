import React from 'react';
import { User, Sparkles, Terminal, Copy, Check } from 'lucide-react';
import { TimeInZoneCard } from './TimeInZoneCard';

export interface AgentChatBubbleProps {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: string;
  agentName?: string;
  agentEmoji?: string;
  thought?: string;
  toolCall?: { tool: string; output: string };
  isStreaming?: boolean;
}

export const AgentChatBubble: React.FC<AgentChatBubbleProps> = ({
  role,
  content,
  timestamp,
  agentName = 'Agent',
  agentEmoji = '🤖',
  thought,
  toolCall,
  isStreaming = false,
}) => {
  const isUser = role === 'user';
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Check if message is a time response
  const isTimeResponse = !isUser && content.toLowerCase().includes('time in');

  return (
    <div className={`flex flex-col gap-1.5 my-2 ${isUser ? 'items-end' : 'items-start'}`}>
      {/* Sender Header */}
      <div className="flex items-center gap-2 px-1 text-[11px] text-[var(--text-tertiary)]">
        {!isUser ? (
          <>
            <span className="font-semibold text-[var(--text-primary)] flex items-center gap-1">
              <span>{agentEmoji}</span>
              <span>{agentName}</span>
            </span>
            <span>•</span>
          </>
        ) : (
          <span className="font-semibold text-indigo-400">You</span>
        )}
        <span>{timestamp}</span>
      </div>

      {/* Thought reasoning process banner if present */}
      {thought && !isUser && (
        <div 
          className="max-w-xl text-xs rounded-xl px-3.5 py-2 border flex items-center gap-2.5 animate-in fade-in"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-secondary)',
          }}
        >
          <Sparkles className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 animate-spin" />
          <span className="font-mono text-[11px] leading-tight">{thought}</span>
        </div>
      )}

      {/* Main Bubble */}
      <div className="flex gap-2.5 max-w-2xl group">
        {!isUser && (
          <div 
            className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-base shadow-sm border"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              borderColor: 'var(--border-color)',
            }}
          >
            {agentEmoji}
          </div>
        )}

        <div className="flex-1 space-y-2">
          {isTimeResponse ? (
            <TimeInZoneCard timeString={content} />
          ) : (
            <div
              className={`rounded-2xl px-4 py-3 text-xs leading-relaxed border shadow-md relative transition-all ${
                isUser ? 'rounded-tr-none text-white' : 'rounded-tl-none'
              }`}
              style={{
                backgroundColor: isUser ? 'var(--accent-color, #6e5cff)' : 'var(--bg-tertiary, #141a26)',
                borderColor: isUser ? 'rgba(110, 92, 255, 0.5)' : 'var(--border-color, #232c3d)',
                color: isUser ? '#ffffff' : 'var(--text-primary, #e7ecf5)',
              }}
            >
              {/* Fuse seam glowing bar on agent bubbles */}
              {!isUser && (
                <div 
                  className="absolute top-0 left-0 right-0 h-[2px] rounded-t-2xl opacity-80"
                  style={{ background: 'var(--seam, linear-gradient(90deg, #6e5cff, #29d3e6))' }}
                />
              )}

              <div className="whitespace-pre-wrap font-sans">
                {content}
                {isStreaming && (
                  <span className="inline-block w-1.5 h-3.5 ml-1 bg-cyan-400 animate-pulse align-middle" />
                )}
              </div>

              {!isUser && content && (
                <button
                  onClick={handleCopy}
                  className="absolute bottom-2 right-2 p-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-slate-700/40 text-[var(--text-tertiary)]"
                  title="Copy response"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              )}
            </div>
          )}

          {/* Tool call / execution output block if present */}
          {toolCall && (
            <div 
              className="rounded-xl p-3 border font-mono text-[11px] shadow-inner"
              style={{
                backgroundColor: 'var(--bg-primary, #0b0e15)',
                borderColor: 'var(--border-color, #232c3d)',
              }}
            >
              <div className="flex items-center gap-1.5 text-indigo-400 font-bold mb-1">
                <Terminal className="w-3.5 h-3.5" />
                <span>{toolCall.tool}</span>
              </div>
              <div className="text-[var(--text-secondary)] pl-5 whitespace-pre-wrap border-l border-slate-700/50">
                {toolCall.output}
              </div>
            </div>
          )}
        </div>

        {isUser && (
          <div 
            className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-sm shadow-sm border"
            style={{
              backgroundColor: 'var(--bg-quaternary)',
              borderColor: 'var(--border-color)',
            }}
          >
            <User className="w-4 h-4 text-indigo-300" />
          </div>
        )}
      </div>
    </div>
  );
};
