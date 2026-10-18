import { useState } from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Bot, 
  Lock
} from 'lucide-react';

interface EscalationItem {
  id: string;
  agentName: string;
  team: string;
  taskTitle: string;
  actionType: 'destructive_op' | 'budget_threshold' | 'security_elevation' | 'api_publish';
  summary: string;
  proposedCommand: string;
  costEstimateUsd?: number;
  requestedAt: string;
  status: 'pending' | 'approved' | 'rejected';
}

const INITIAL_ESCALATIONS: EscalationItem[] = [
  {
    id: 'esc-901',
    agentName: 'DevOps & Cloud Engineer',
    team: 'Core Engineering',
    taskTitle: 'Deploy production ingress & federated mount',
    actionType: 'security_elevation',
    summary: 'Agent requested apply permissions for cluster-wide Ingress resource under app.fuzefront.com domain.',
    proposedCommand: 'kubectl apply -f deploy/helm/fuzeagent/templates/federated-mount-ingress.yaml -n fuzeagent',
    requestedAt: '3m ago',
    status: 'pending'
  },
  {
    id: 'esc-902',
    agentName: 'Python Dev #1',
    team: 'Core Engineering',
    taskTitle: 'Execute Bank Hapoalim credential sync via FuzeKeys',
    actionType: 'destructive_op',
    summary: 'Agent requests retrieval of zero-exposure banking token from FuzeKeys vault for scraper validation.',
    proposedCommand: 'curl -X POST $FUZEKEYS_API_URL/vault/retrieve -H "Authorization: Bearer $AGENT_TOKEN" -d \'{"ref": "fk_sec_hapoalim_cred"}\'',
    requestedAt: '12m ago',
    status: 'pending'
  },
  {
    id: 'esc-899',
    agentName: 'Growth & Marketing Agent',
    team: 'Marketing',
    taskTitle: 'Auto-publish multi-channel product announcement',
    actionType: 'api_publish',
    summary: 'Scheduled publish of 4 campaign posts to LinkedIn, X, and Reddit via FuzeSocial API.',
    proposedCommand: 'fuzesocial-cli publish --batch announcement_2026.json --dry-run=false',
    costEstimateUsd: 1.25,
    requestedAt: '1h ago',
    status: 'approved'
  }
];

export function EscalationsView() {
  const [escalations, setEscalations] = useState<EscalationItem[]>(INITIAL_ESCALATIONS);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const handleDecision = (id: string, decision: 'approved' | 'rejected') => {
    setEscalations(prev => prev.map(item => {
      if (item.id === id) {
        return { ...item, status: decision };
      }
      return item;
    }));
    setActionNotice(`Escalation ${id} has been ${decision}. The agent sandbox has been notified.`);
    setTimeout(() => setActionNotice(null), 4000);
  };

  const getActionBadge = (type: EscalationItem['actionType']) => {
    switch (type) {
      case 'destructive_op':
        return <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300">Destructive Operation</span>;
      case 'security_elevation':
        return <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">Security Elevation</span>;
      case 'budget_threshold':
        return <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">Budget Exceeded</span>;
      case 'api_publish':
        return <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">External API Write</span>;
    }
  };

  const pendingCount = escalations.filter(e => e.status === 'pending').length;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gradient-to-r from-amber-950 via-slate-900 to-slate-950 p-6 rounded-xl border border-amber-800/40 text-white shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 bg-amber-500/20 text-amber-400 rounded-md border border-amber-500/30">
              <AlertTriangle className="w-5 h-5" />
            </span>
            <h2 className="text-xl font-bold tracking-tight">Decision Escalation & Human Oversight</h2>
          </div>
          <p className="text-sm text-slate-300 max-w-2xl">
            Autonomous agent safeguards: actions that modify production infrastructure, access encrypted vaults, 
            or exceed budgetary allowances are held in safe escrow until approved by a human lead or managing agent.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-950 text-amber-300 border border-amber-500/40 rounded-lg text-xs font-mono">
            <Clock className="w-4 h-4 text-amber-400 animate-pulse" />
            {pendingCount} Pending Approvals
          </span>
        </div>
      </div>

      {actionNotice && (
        <div className="p-3 bg-emerald-950/40 border border-emerald-500/40 rounded-lg text-xs text-emerald-200 flex items-center justify-between animate-in fade-in duration-200">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-emerald-400 hover:underline">Dismiss</button>
        </div>
      )}

      {/* Escalation Cards */}
      <div className="space-y-4">
        {escalations.map(item => {
          const isPending = item.status === 'pending';
          return (
            <div 
              key={item.id}
              className={`p-6 rounded-xl border transition-all ${
                isPending 
                  ? 'bg-white dark:bg-slate-900 border-amber-300/80 dark:border-amber-800/80 shadow-md' 
                  : 'bg-slate-50 dark:bg-slate-950/60 border-slate-200 dark:border-slate-800 opacity-75'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-3">
                  <span className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400">
                    <Bot className="w-5 h-5" />
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-bold text-slate-900 dark:text-white">{item.agentName}</h4>
                      <span className="text-xs text-slate-500 font-mono">({item.team})</span>
                    </div>
                    <p className="text-xs text-slate-500">{item.taskTitle}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {getActionBadge(item.actionType)}
                  <span className="text-xs text-slate-400 font-mono">{item.requestedAt}</span>
                </div>
              </div>

              <div className="py-4 space-y-3">
                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                  {item.summary}
                </p>

                <div className="space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Proposed Action Payload</span>
                  <pre className="p-3 rounded-lg bg-slate-950 text-slate-200 font-mono text-xs overflow-x-auto border border-slate-800">
                    {item.proposedCommand}
                  </pre>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
                <span className="text-xs text-slate-500 flex items-center gap-1">
                  <Lock className="w-3.5 h-3.5" />
                  Escalation Target: <strong>Human Supervisor or IzzyAI Orchestrator</strong>
                </span>

                <div className="flex items-center gap-2">
                  {isPending ? (
                    <>
                      <button 
                        onClick={() => handleDecision(item.id, 'rejected')}
                        className="flex items-center gap-1.5 px-3 py-1.5 border border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg text-xs font-semibold transition-all active:scale-95"
                      >
                        <XCircle className="w-4 h-4" /> Reject & Abort
                      </button>
                      <button 
                        onClick={() => handleDecision(item.id, 'approved')}
                        className="flex items-center gap-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition-all shadow-sm active:scale-95"
                      >
                        <CheckCircle2 className="w-4 h-4" /> Approve Action
                      </button>
                    </>
                  ) : (
                    <span className={`flex items-center gap-1.5 text-xs font-bold font-mono uppercase ${
                      item.status === 'approved' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
                    }`}>
                      {item.status === 'approved' ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                      {item.status}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default EscalationsView;
