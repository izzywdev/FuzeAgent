import React from 'react';
import { Sparkles } from 'lucide-react';

export interface StreamingThoughtIndicatorProps {
  agentName: string;
  thought?: string;
  agentEmoji?: string;
}

export const StreamingThoughtIndicator: React.FC<StreamingThoughtIndicatorProps> = ({
  agentName,
  thought = 'Consulting knowledge hierarchy and executing in sandbox...',
  agentEmoji = '🤖',
}) => {
  return (
    <div className="flex gap-2.5 items-start animate-in fade-in my-2">
      <div 
        className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-base shadow-sm border"
        style={{
          backgroundColor: 'var(--bg-tertiary, #141a26)',
          borderColor: 'var(--border-color, #232c3d)',
        }}
      >
        {agentEmoji}
      </div>

      <div 
        className="rounded-2xl rounded-tl-none px-4 py-2.5 border text-xs shadow-md flex items-center gap-2.5 max-w-lg"
        style={{
          backgroundColor: 'var(--bg-tertiary, #141a26)',
          borderColor: 'var(--border-color, #232c3d)',
          color: 'var(--text-secondary, #9fa9bc)',
        }}
      >
        <Sparkles className="w-4 h-4 text-cyan-400 animate-spin" />
        <span className="font-sans leading-snug">
          <strong className="text-[var(--text-primary)] font-semibold">{agentName}</strong> {thought}
        </span>
      </div>
    </div>
  );
};
