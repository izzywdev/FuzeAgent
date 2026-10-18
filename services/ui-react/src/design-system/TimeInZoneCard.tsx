import React from 'react';
import { Clock, Globe, Sparkles } from 'lucide-react';

export interface TimeInZoneCardProps {
  timeString: string;
  zone?: string;
}

export const TimeInZoneCard: React.FC<TimeInZoneCardProps> = ({
  timeString,
  zone = 'America/Los_Angeles',
}) => {
  const isLA = timeString.toLowerCase().includes('los angeles') || timeString.toLowerCase().includes('la');
  
  return (
    <div 
      className="rounded-2xl p-4 border shadow-xl relative overflow-hidden transition-all hover:border-cyan-500/50"
      style={{
        backgroundColor: 'var(--bg-tertiary, #141a26)',
        borderColor: 'var(--border-color, #232c3d)',
      }}
    >
      {/* Top glowing Fuse Seam */}
      <div 
        className="absolute top-0 left-0 right-0 h-[2.5px]"
        style={{ background: 'var(--seam, linear-gradient(90deg, #6e5cff, #29d3e6))' }}
      />

      <div className="flex items-start justify-between gap-3 mb-2.5">
        <div className="flex items-center gap-2">
          <span 
            className="p-1.5 rounded-lg border flex items-center justify-center text-cyan-400"
            style={{
              backgroundColor: 'rgba(41, 211, 230, 0.1)',
              borderColor: 'rgba(41, 211, 230, 0.3)',
            }}
          >
            <Clock className="w-4 h-4 animate-pulse" />
          </span>
          <div>
            <h4 className="text-xs font-bold font-display" style={{ color: 'var(--text-primary)' }}>
              {isLA ? 'Los Angeles, California (PDT)' : 'World Clock Time Stream'}
            </h4>
            <span className="text-[10px] font-mono text-[var(--text-tertiary)] flex items-center gap-1">
              <Globe className="w-3 h-3" />
              <span>{isLA ? 'UTC-7 (Pacific Time Zone)' : zone}</span>
            </span>
          </div>
        </div>

        <span 
          className="text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded-md border"
          style={{
            backgroundColor: 'rgba(110, 92, 255, 0.15)',
            borderColor: 'rgba(110, 92, 255, 0.35)',
            color: '#a78bfa',
          }}
        >
          ⚡ Live Stream
        </span>
      </div>

      {/* Formatted time display */}
      <div 
        className="p-3 rounded-xl border text-sm font-semibold flex items-center justify-between shadow-inner"
        style={{
          backgroundColor: 'var(--bg-primary, #0b0e15)',
          borderColor: 'var(--border-color, #232c3d)',
          color: 'var(--text-primary)',
        }}
      >
        <span className="font-mono text-cyan-300 font-bold tracking-wide">
          {timeString}
        </span>
        <Sparkles className="w-4 h-4 text-cyan-400" />
      </div>

      <div className="mt-2.5 flex items-center justify-between text-[10px] text-[var(--text-tertiary)]">
        <span>Verified via orchestrator sandbox relay</span>
        <span className="font-mono">Zone: {isLA ? 'America/Los_Angeles' : zone}</span>
      </div>
    </div>
  );
};
