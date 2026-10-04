import { useState } from 'react';
import { 
  Brain, 
  User, 
  Building2, 
  Users, 
  Bot, 
  Sparkles, 
  Database, 
  Shield, 
  Eye, 
  Edit3, 
  Search, 
  Plus,
  BookOpen
} from 'lucide-react';
import { BrainWikiExplorer } from './BrainWikiExplorer';

export interface BrainItem {
  id: string;
  name: string;
  scope: 'user_profile' | 'org_global' | 'team_level' | 'agent_persona' | 'session' | 'custom';
  description: string;
  itemCount: number;
  lastUpdated: string;
  isPersistent: boolean;
  consultAccess: {
    teams: string[];
    agents: string[];
    allTeams?: boolean;
    allAgents?: boolean;
  };
  updateAccess: {
    teams: string[];
    agents: string[];
    allTeams?: boolean;
    allAgents?: boolean;
  };
}

const INITIAL_BRAINS: BrainItem[] = [
  {
    id: 'brain-user-profile',
    name: 'User Personal Profile Brain',
    scope: 'user_profile',
    description: 'Personalized user context, preferred communication tone, coding style conventions, and identity mapping (e.g. fuzefront/izzy.weinberg@gmail.com).',
    itemCount: 42,
    lastUpdated: 'Just now',
    isPersistent: true,
    consultAccess: { teams: ['all'], agents: ['all'], allTeams: true, allAgents: true },
    updateAccess: { teams: ['Personal'], agents: ['CEO Assistant'], allTeams: false, allAgents: false }
  },
  {
    id: 'brain-org-global',
    name: 'FuzeOne Enterprise Global Brain',
    scope: 'org_global',
    description: 'Organization-wide architectural patterns, FuzeSDLC standards, Zero-Exposure FuzeKeys security policies, and brand guidelines.',
    itemCount: 1540,
    lastUpdated: '12m ago',
    isPersistent: true,
    consultAccess: { teams: ['all'], agents: ['all'], allTeams: true, allAgents: true },
    updateAccess: { teams: ['Architecture', 'Executive'], agents: ['IzzyAI'], allTeams: false, allAgents: false }
  },
  {
    id: 'brain-team-dev',
    name: 'Core Engineering Team Brain',
    scope: 'team_level',
    description: 'Shared microservice APIs, database schema migration standards, and repository context across backend and frontend repositories.',
    itemCount: 680,
    lastUpdated: '1h ago',
    isPersistent: true,
    consultAccess: { teams: ['Core Engineering', 'DevOps'], agents: ['Python Dev', 'React Dev'], allTeams: false, allAgents: false },
    updateAccess: { teams: ['Core Engineering'], agents: ['Lead Architect'], allTeams: false, allAgents: false }
  },
  {
    id: 'brain-agent-persona-python',
    name: 'Python Dev Persona Long-Term Memory',
    scope: 'agent_persona',
    description: 'Agent persona accumulated learning, past debugging reflections, optimized library patterns, and task performance feedback. Persists across all sessions.',
    itemCount: 312,
    lastUpdated: '2h ago',
    isPersistent: true,
    consultAccess: { teams: ['Core Engineering'], agents: ['Python Dev #1', 'Python Dev #2'], allTeams: false, allAgents: false },
    updateAccess: { teams: ['Core Engineering'], agents: ['Python Dev #1'], allTeams: false, allAgents: false }
  },
  {
    id: 'brain-session-ephemeral',
    name: 'Active Chat Session Memory',
    scope: 'session',
    description: 'Ephemeral conversational buffer, scratchpad variables, tool call stack, and context tokens for current active chat. Destroyed on session close.',
    itemCount: 18,
    lastUpdated: 'Active streaming',
    isPersistent: false,
    consultAccess: { teams: ['Current Session'], agents: ['Assigned Agent'], allTeams: false, allAgents: false },
    updateAccess: { teams: ['Current Session'], agents: ['Assigned Agent'], allTeams: false, allAgents: false }
  },
  {
    id: 'brain-custom-finance-specs',
    name: 'Banking & Financial Protocols (Custom)',
    scope: 'custom',
    description: 'Specialized regulatory banking documentation, scraping session state schemas, and ledger reconciliation protocols.',
    itemCount: 89,
    lastUpdated: '1d ago',
    isPersistent: true,
    consultAccess: { teams: ['Finance', 'Core Engineering'], agents: ['Python Dev', 'Finance Agent'], allTeams: false, allAgents: false },
    updateAccess: { teams: ['Finance'], agents: ['Finance Lead'], allTeams: false, allAgents: false }
  }
];

export function BrainsMemoryHierarchy() {
  const [brains, setBrains] = useState<BrainItem[]>(INITIAL_BRAINS);
  const [selectedBrain, setSelectedBrain] = useState<BrainItem>(INITIAL_BRAINS[0]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [querySimulation, setQuerySimulation] = useState('How do we authenticate with FuzeKeys in the bank scraper?');
  const [isSimulating, setIsSimulating] = useState(false);
  const [activeMode, setActiveMode] = useState<'wiki' | 'hierarchy'>('wiki');
  const [simulationResult, setSimulationResult] = useState<string | null>(null);

  // New Custom Brain form state
  const [newBrainName, setNewBrainName] = useState('');
  const [newBrainDesc, setNewBrainDesc] = useState('');
  const [newBrainConsultTeams, setNewBrainConsultTeams] = useState('Core Engineering, Product');
  const [newBrainUpdateTeams, setNewBrainUpdateTeams] = useState('Core Engineering');

  const handleCreateBrain = () => {
    if (!newBrainName) return;
    const newBrain: BrainItem = {
      id: `brain-custom-${Date.now()}`,
      name: newBrainName,
      scope: 'custom',
      description: newBrainDesc || 'Custom organization knowledge store',
      itemCount: 0,
      lastUpdated: 'Just created',
      isPersistent: true,
      consultAccess: {
        teams: newBrainConsultTeams.split(',').map(s => s.trim()),
        agents: ['Assigned Specialists'],
        allTeams: false,
        allAgents: false
      },
      updateAccess: {
        teams: newBrainUpdateTeams.split(',').map(s => s.trim()),
        agents: ['Authorized Leads'],
        allTeams: false,
        allAgents: false
      }
    };
    setBrains([...brains, newBrain]);
    setSelectedBrain(newBrain);
    setShowCreateModal(false);
    setNewBrainName('');
    setNewBrainDesc('');
  };

  const handleSimulateRag = () => {
    setIsSimulating(true);
    setSimulationResult(null);
    setTimeout(() => {
      setIsSimulating(false);
      setSimulationResult(`[RAG Retrieval across 5-Tier Memory Hierarchy]
1. User Profile Memory: Identified user 'izzy.weinberg@gmail.com' (developer/admin role)
2. Org Global Memory: Found FuzeKeys Zero-Exposure rule (CLAUDE.md: raw creds never persisted on disk)
3. Team Brain (Core Eng): Retrieved fuzekeysBridge.js specifications (storeBankCredentials returning opaque ref)
4. Agent Persona Memory: Recalled previous successful OTP session manager implementation for Bank Hapoalim
5. Session Memory: Integrated current prompt parameters into execution context.
-> Consolidated Context: Ready to stream synthesized response to centralized bus.`);
    }, 1000);
  };

  const getScopeBadge = (scope: BrainItem['scope']) => {
    switch (scope) {
      case 'user_profile':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"><User className="w-3 h-3" /> User Profile</span>;
      case 'org_global':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300"><Building2 className="w-3 h-3" /> Org Global</span>;
      case 'team_level':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"><Users className="w-3 h-3" /> Team Level</span>;
      case 'agent_persona':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"><Bot className="w-3 h-3" /> Persona Memory</span>;
      case 'session':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"><Sparkles className="w-3 h-3" /> Session Memory</span>;
      case 'custom':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300"><Database className="w-3 h-3" /> Custom Brain</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gradient-to-r from-purple-950 via-slate-900 to-indigo-950 p-6 rounded-xl border border-purple-800/40 text-white shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 bg-purple-500/20 text-purple-400 rounded-md border border-purple-500/30">
              <Brain className="w-5 h-5" />
            </span>
            <h2 className="text-xl font-bold tracking-tight">Brains & Memory Hierarchy (RAG)</h2>
          </div>
          <p className="text-sm text-slate-300 max-w-2xl">
            Hierarchical RAG architecture providing multi-level memory isolation: from User Profile and Org Global standards, 
            down to Team domain knowledge, Agent Persona persistent long-term learning, and ephemeral session memory.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium text-sm transition-all shadow-md active:scale-95"
          >
            <Plus className="w-4 h-4" />
            Create Knowledge Brain
          </button>
        </div>
      </div>

      {/* Mode Switcher */}
      <div className="flex items-center gap-2 border-b pb-3" style={{ borderColor: 'var(--border-color, #232c3d)' }}>
        <button
          onClick={() => setActiveMode('wiki')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            activeMode === 'wiki'
              ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
              : 'hover:opacity-100 opacity-70'
          }`}
          style={{
            backgroundColor: activeMode === 'wiki' ? undefined : 'var(--bg-tertiary, #141a26)',
            border: activeMode === 'wiki' ? 'none' : '1px solid var(--border-color, #232c3d)',
            color: activeMode === 'wiki' ? '#fff' : 'var(--text-secondary, #9fa9bc)'
          }}
        >
          <BookOpen className="w-4 h-4" />
          <span>Wiki Documents & RAG Chat Explorer</span>
        </button>

        <button
          onClick={() => setActiveMode('hierarchy')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            activeMode === 'hierarchy'
              ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
              : 'hover:opacity-100 opacity-70'
          }`}
          style={{
            backgroundColor: activeMode === 'hierarchy' ? undefined : 'var(--bg-tertiary, #141a26)',
            border: activeMode === 'hierarchy' ? 'none' : '1px solid var(--border-color, #232c3d)',
            color: activeMode === 'hierarchy' ? '#fff' : 'var(--text-secondary, #9fa9bc)'
          }}
        >
          <Brain className="w-4 h-4" />
          <span>5-Tier Memory Architecture & Access Control</span>
        </button>
      </div>

      {activeMode === 'wiki' && (
        <div className="h-[750px] rounded-xl border border-slate-800 overflow-hidden shadow-xl">
          <BrainWikiExplorer
            brainId={selectedBrain.id}
            brainName={selectedBrain.name}
            brainTier={selectedBrain.scope.toUpperCase()}
            onClose={() => setActiveMode('hierarchy')}
          />
        </div>
      )}

      {activeMode === 'hierarchy' && (
        <>

      {/* Memory Distinction Banner */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/60 rounded-xl">
          <div className="flex items-center gap-2 text-amber-900 dark:text-amber-300 font-semibold text-sm mb-1">
            <Bot className="w-4 h-4 text-amber-600" />
            Agent Persona Long-Term Memory
          </div>
          <p className="text-xs text-amber-800/90 dark:text-amber-400/90 leading-relaxed">
            Persistent across all executions. Stores an agent persona's accumulated reflections, successful task patterns, 
            tool mastery scores, and specialized instincts. Never wiped on container shutdown.
          </p>
        </div>

        <div className="p-4 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/60 rounded-xl">
          <div className="flex items-center gap-2 text-rose-900 dark:text-rose-300 font-semibold text-sm mb-1">
            <Sparkles className="w-4 h-4 text-rose-600" />
            Ephemeral Session Memory
          </div>
          <p className="text-xs text-rose-800/90 dark:text-rose-400/90 leading-relaxed">
            Scoped strictly to the current active chat or task thread. Holds transient token window context, scratchpad files, 
            and intermediate tool call returns. Cleaned up immediately upon session closure.
          </p>
        </div>
      </div>

      {/* Main Grid: Brains List + Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Brains List */}
        <div className="lg:col-span-5 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-1">
            Memory Stores & RAG Brains ({brains.length})
          </div>
          {brains.map(brain => {
            const isSelected = selectedBrain.id === brain.id;
            return (
              <div 
                key={brain.id}
                onClick={() => setSelectedBrain(brain)}
                className={`p-4 rounded-xl border transition-all cursor-pointer ${
                  isSelected 
                    ? 'shadow-md' 
                    : 'hover:border-slate-600'
                }`}
                style={{
                  backgroundColor: isSelected ? 'rgba(110, 92, 255, 0.15)' : 'var(--bg-tertiary, #141a26)',
                  borderColor: isSelected ? 'var(--accent-color, #6e5cff)' : 'var(--border-color, #232c3d)',
                  color: 'var(--text-primary, #e7ecf5)'
                }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="p-2 rounded-lg text-purple-400 border" style={{ backgroundColor: 'rgba(168, 85, 247, 0.15)', borderColor: 'rgba(168, 85, 247, 0.3)' }}>
                      <Brain className="w-4 h-4" />
                    </span>
                    <div>
                      <h3 className="text-sm font-bold text-white">{brain.name}</h3>
                      <div className="mt-1">{getScopeBadge(brain.scope)}</div>
                    </div>
                  </div>
                  <span className="text-xs font-mono" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                    {brain.itemCount} items
                  </span>
                </div>
                <p className="text-xs mt-2 line-clamp-2" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>{brain.description}</p>
              </div>
            );
          })}
        </div>

        {/* Selected Brain Detail & Access Control */}
        <div 
          className="lg:col-span-7 rounded-xl border shadow-sm p-6 space-y-6"
          style={{
            backgroundColor: 'var(--bg-tertiary, #141a26)',
            borderColor: 'var(--border-color, #232c3d)',
            color: 'var(--text-primary, #e7ecf5)'
          }}
        >
          <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                {selectedBrain.name}
              </h3>
              {getScopeBadge(selectedBrain.scope)}
            </div>
            <p className="text-xs text-slate-500 mt-1">{selectedBrain.description}</p>
            <div className="mt-3 flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-4 text-xs text-slate-600 dark:text-slate-400">
                <span>Indexed Items: <strong>{selectedBrain.itemCount}</strong></span>
                <span>Persistence: <strong>{selectedBrain.isPersistent ? 'Permanent DB (pgvector)' : 'Ephemeral In-Memory'}</strong></span>
                <span>Updated: <strong>{selectedBrain.lastUpdated}</strong></span>
              </div>
              <button
                onClick={() => setActiveMode('wiki')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-cyan-500 hover:from-purple-500 hover:to-cyan-400 text-white text-xs font-semibold shadow-sm transition-all active:scale-95"
              >
                <BookOpen className="w-3.5 h-3.5" />
                Explore Wiki & Chat
              </button>
            </div>
          </div>

          {/* Granular Access Control (Consult vs Update) */}
          <div className="space-y-4">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-indigo-500" />
              Granular Brain Access Permissions
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Consult / Read-Only Access */}
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/60 space-y-2.5">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
                  <Eye className="w-4 h-4 text-blue-500" />
                  Consult Access (Read-Only)
                </div>
                <p className="text-xs text-slate-500">
                  Agents and teams authorized to query and retrieve context from this brain during reasoning.
                </p>
                <div className="space-y-1.5 pt-1">
                  <div className="text-xs">
                    <span className="text-slate-500">Teams: </span>
                    <strong className="text-slate-700 dark:text-slate-300 font-mono">
                      {selectedBrain.consultAccess.allTeams ? 'All Teams (Global)' : selectedBrain.consultAccess.teams.join(', ')}
                    </strong>
                  </div>
                  <div className="text-xs">
                    <span className="text-slate-500">Agents: </span>
                    <strong className="text-slate-700 dark:text-slate-300 font-mono">
                      {selectedBrain.consultAccess.allAgents ? 'All Personas' : selectedBrain.consultAccess.agents.join(', ')}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Update / Read-Write Access */}
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/60 space-y-2.5">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
                  <Edit3 className="w-4 h-4 text-purple-500" />
                  Update Access (Read-Write)
                </div>
                <p className="text-xs text-slate-500">
                  Only designated agents and teams can write new knowledge, edit embeddings, or prune entries.
                </p>
                <div className="space-y-1.5 pt-1">
                  <div className="text-xs">
                    <span className="text-slate-500">Teams: </span>
                    <strong className="text-slate-700 dark:text-slate-300 font-mono">
                      {selectedBrain.updateAccess.allTeams ? 'All Teams' : selectedBrain.updateAccess.teams.join(', ')}
                    </strong>
                  </div>
                  <div className="text-xs">
                    <span className="text-slate-500">Agents: </span>
                    <strong className="text-slate-700 dark:text-slate-300 font-mono">
                      {selectedBrain.updateAccess.allAgents ? 'All Personas' : selectedBrain.updateAccess.agents.join(', ')}
                    </strong>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* RAG Query Simulator across Hierarchy */}
          <div className="p-4 rounded-xl border border-purple-200 dark:border-purple-900/60 bg-purple-50/30 dark:bg-purple-950/20 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-purple-900 dark:text-purple-300 uppercase tracking-wider flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5 text-purple-600" />
                Multi-Tier RAG Context Retrieval Test
              </span>
              <button 
                onClick={handleSimulateRag}
                disabled={isSimulating}
                className="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white rounded text-xs font-medium transition-all shadow-sm active:scale-95 disabled:opacity-50"
              >
                {isSimulating ? 'Querying Hierarchy...' : 'Simulate Query'}
              </button>
            </div>
            <input 
              type="text"
              value={querySimulation}
              onChange={(e) => setQuerySimulation(e.target.value)}
              className="w-full text-xs font-mono p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Enter test user or agent query..."
            />
            {simulationResult && (
              <pre className="p-3 rounded bg-slate-950 text-slate-300 text-xs font-mono overflow-x-auto leading-relaxed border border-slate-800 animate-in fade-in duration-200">
                {simulationResult}
              </pre>
            )}
          </div>
        </div>
      </div>
      </>
      )}

      {/* Modal: Create Custom Brain */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Brain className="w-5 h-5 text-purple-600" />
                Create New Custom Knowledge Brain
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Brain Name</label>
                <input 
                  type="text"
                  value={newBrainName}
                  onChange={(e) => setNewBrainName(e.target.value)}
                  placeholder="e.g. Legal & Compliance Docs, Payments Engine"
                  className="w-full p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Description & Scope</label>
                <textarea 
                  value={newBrainDesc}
                  onChange={(e) => setNewBrainDesc(e.target.value)}
                  placeholder="Define the knowledge domain and intended use..."
                  rows={2}
                  className="w-full p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Consult Teams (Read-Only ACL, comma-separated)</label>
                <input 
                  type="text"
                  value={newBrainConsultTeams}
                  onChange={(e) => setNewBrainConsultTeams(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">Update Teams (Read-Write ACL, comma-separated)</label>
                <input 
                  type="text"
                  value={newBrainUpdateTeams}
                  onChange={(e) => setNewBrainUpdateTeams(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button 
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-medium"
              >
                Cancel
              </button>
              <button 
                onClick={handleCreateBrain}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-medium shadow-sm active:scale-95"
              >
                Save Brain
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default BrainsMemoryHierarchy;
