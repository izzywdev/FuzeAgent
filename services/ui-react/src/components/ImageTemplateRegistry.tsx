import { useState } from 'react';
import { 
  Box, 
  Shield, 
  Terminal, 
  Clock, 
  Key, 
  AlertTriangle, 
  Radio, 
  Play, 
  CheckCircle2, 
  Copy, 
  Plus, 
  RefreshCw, 
  Cpu, 
  Lock, 
  Code
} from 'lucide-react';

export interface ImageTemplate {
  id: string;
  name: string;
  category: 'development' | 'devops' | 'marketing' | 'quality_assurance' | 'management';
  role: string;
  image: string;
  description: string;
  dockerfile: string;
  envVars: Record<string, string>;
  fuzeKeysSecrets: Array<{ keyName: string; secretRef: string; description: string }>;
  setupScript: string;
  sandboxing: {
    defaultTimeoutSeconds: number;
    cpuLimit: string;
    memoryLimit: string;
    networkIsolation: 'strict' | 'outbound-only' | 'full';
    autoShutdownOnIdle: boolean;
  };
  eventBus: {
    enabled: boolean;
    channel: string;
    streamLlmChunks: boolean;
    wsRelayUrl: string;
  };
  escalation: {
    requiresApprovalForDestructive: boolean;
    costThresholdUsd: number;
    escalateTo: 'human' | 'orchestrator' | 'both';
  };
  status: 'active' | 'building' | 'ready';
}

const DEFAULT_TEMPLATES: ImageTemplate[] = [
  {
    id: 'python-dev',
    name: 'Python Developer Agent',
    category: 'development',
    role: 'Backend & Data Specialist',
    image: 'ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest',
    description: 'Isolated Python 3.12 environment with FastAPI, SQLAlchemy, Pytest, Black, Ruff, Poetry, and LLM streaming relay.',
    dockerfile: `# syntax=docker/dockerfile:1
FROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest
USER root
RUN apt-get update && apt-get install -y python3-pip python3-venv build-essential \\
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages pytest black ruff poetry ipython asyncpg
USER agent
COPY setup.sh /usr/local/bin/init-container.sh
CMD ["/usr/local/bin/session-relay"]`,
    envVars: {
      PYTHONUNBUFFERED: '1',
      PYTHONDONTWRITEBYTECODE: '1',
      LOG_LEVEL: 'INFO',
      DEFAULT_TIMEOUT: '1800'
    },
    fuzeKeysSecrets: [
      { keyName: 'ANTHROPIC_API_KEY', secretRef: 'fk_sec_anthropic_prod', description: 'Zero-exposure Anthropic token via FuzeKeys' },
      { keyName: 'GITHUB_TOKEN', secretRef: 'fk_sec_github_agent_pat', description: 'Agent scoped GitHub PAT' },
      { keyName: 'DATABASE_URL', secretRef: 'fk_sec_pg_vector_ai', description: 'Encrypted db connection credential' }
    ],
    setupScript: `#!/bin/bash
set -e
echo "[init] Starting Python sandbox container..."
if [ -n "$WS_RELAY_URL" ]; then
  echo "[init] Connected to centralized event bus: $WS_RELAY_URL"
fi
# Fetch required JIT secrets from FuzeKeys vault API
if [ -n "$FUZEKEYS_API_URL" ]; then
  echo "[init] Synchronizing zero-exposure secrets from FuzeKeys..."
fi
exec /usr/local/bin/session-relay "$@"`,
    sandboxing: {
      defaultTimeoutSeconds: 1800,
      cpuLimit: '2.0',
      memoryLimit: '4Gi',
      networkIsolation: 'outbound-only',
      autoShutdownOnIdle: true
    },
    eventBus: {
      enabled: true,
      channel: 'agent.stream.python-dev',
      streamLlmChunks: true,
      wsRelayUrl: 'wss://fuzeagent.prod.fuzefront.com/ws/stream'
    },
    escalation: {
      requiresApprovalForDestructive: true,
      costThresholdUsd: 5.0,
      escalateTo: 'human'
    },
    status: 'ready'
  },
  {
    id: 'react-dev',
    name: 'React Developer Agent',
    category: 'development',
    role: 'Frontend & UI Specialist',
    image: 'ghcr.io/izzywdev/fuzeagent/claude-runner-react-dev:latest',
    description: 'Modern Node 22 + React 19 environment with Vite, Tailwind CSS v4, Playwright, Vitest, and FuzeFront Design System tools.',
    dockerfile: `# syntax=docker/dockerfile:1
FROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest
USER root
RUN apt-get update && apt-get install -y nodejs npm git \\
    && npm install -g pnpm vite vitest typescript \\
    && rm -rf /var/lib/apt/lists/*
USER agent
COPY setup.sh /usr/local/bin/init-container.sh
CMD ["/usr/local/bin/session-relay"]`,
    envVars: {
      NODE_ENV: 'development',
      VITE_PORT: '5173',
      FORCE_COLOR: '1'
    },
    fuzeKeysSecrets: [
      { keyName: 'ANTHROPIC_API_KEY', secretRef: 'fk_sec_anthropic_prod', description: 'Anthropic Claude Code token' },
      { keyName: 'NPM_TOKEN', secretRef: 'fk_sec_npm_pkg_registry', description: 'Internal FuzeFront scoped registry token' }
    ],
    setupScript: `#!/bin/bash
set -e
echo "[init] Launching React & TypeScript Agent sandbox"
pnpm config set store-dir /app/.pnpm-store
exec /usr/local/bin/session-relay "$@"`,
    sandboxing: {
      defaultTimeoutSeconds: 1800,
      cpuLimit: '2.0',
      memoryLimit: '4Gi',
      networkIsolation: 'outbound-only',
      autoShutdownOnIdle: true
    },
    eventBus: {
      enabled: true,
      channel: 'agent.stream.react-dev',
      streamLlmChunks: true,
      wsRelayUrl: 'wss://fuzeagent.prod.fuzefront.com/ws/stream'
    },
    escalation: {
      requiresApprovalForDestructive: true,
      costThresholdUsd: 5.0,
      escalateTo: 'human'
    },
    status: 'ready'
  },
  {
    id: 'devops-specialist',
    name: 'DevOps & Cloud Engineer',
    category: 'devops',
    role: 'Infrastructure & Kubernetes Specialist',
    image: 'ghcr.io/izzywdev/fuzeagent/claude-runner-devops:latest',
    description: 'Cloud-native sandbox with kubectl, Helm, Terraform, Cloudflare CLI, Docker-in-Docker client, and GitOps automation.',
    dockerfile: `# syntax=docker/dockerfile:1
FROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest
USER root
RUN apt-get update && apt-get install -y curl gnupg lsb-release jq \\
    && curl -fsSL https://get.helm.sh/helm-v3.15.2-linux-amd64.tar.gz | tar -xz -C /usr/local/bin --strip-components=1 \\
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \\
    && install -m 0755 kubectl /usr/local/bin/kubectl \\
    && rm -f kubectl
USER agent
CMD ["/usr/local/bin/session-relay"]`,
    envVars: {
      KUBECONFIG: '/app/.kube/config',
      HELM_CACHE_HOME: '/tmp/helm-cache'
    },
    fuzeKeysSecrets: [
      { keyName: 'KUBE_CLUSTER_TOKEN', secretRef: 'fk_sec_k3s_service_account', description: 'Namespaced Kubernetes token' },
      { keyName: 'CLOUDFLARE_API_TOKEN', secretRef: 'fk_sec_cf_tunnel_prod', description: 'Cloudflare edge management token' }
    ],
    setupScript: `#!/bin/bash
set -e
echo "[init] Initializing DevOps Agent sandbox..."
kubectl version --client=true
exec /usr/local/bin/session-relay "$@"`,
    sandboxing: {
      defaultTimeoutSeconds: 3600,
      cpuLimit: '2.0',
      memoryLimit: '4Gi',
      networkIsolation: 'strict',
      autoShutdownOnIdle: true
    },
    eventBus: {
      enabled: true,
      channel: 'agent.stream.devops',
      streamLlmChunks: true,
      wsRelayUrl: 'wss://fuzeagent.prod.fuzefront.com/ws/stream'
    },
    escalation: {
      requiresApprovalForDestructive: true,
      costThresholdUsd: 10.0,
      escalateTo: 'both'
    },
    status: 'ready'
  },
  {
    id: 'marketing-marketer',
    name: 'Growth & Marketing Agent',
    category: 'marketing',
    role: 'Content & Campaign Strategist',
    image: 'ghcr.io/izzywdev/fuzeagent/claude-runner-marketer:latest',
    description: 'Marketing analysis & copywriting sandbox with FuzeSocial integration, SEO analyzers, image generation hooks, and brand tone RAG.',
    dockerfile: `# syntax=docker/dockerfile:1
FROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest
USER root
RUN apt-get update && apt-get install -y python3-pip jq curl \\
    && pip3 install --break-system-packages beautifulsoup4 requests markdown \\
    && rm -rf /var/lib/apt/lists/*
USER agent
CMD ["/usr/local/bin/session-relay"]`,
    envVars: {
      CAMPAIGN_DEFAULT_TONE: 'professional-innovative',
      ENABLE_AUTO_IMAGE_GEN: 'true'
    },
    fuzeKeysSecrets: [
      { keyName: 'SOCIAL_API_KEY', secretRef: 'fk_sec_fuzesocial_token', description: 'FuzeSocial publishing API key' },
      { keyName: 'OPENAI_API_KEY', secretRef: 'fk_sec_openai_prod', description: 'DALL-E & GPT-4o creative token' }
    ],
    setupScript: `#!/bin/bash
set -e
echo "[init] Starting Marketing campaign agent..."
exec /usr/local/bin/session-relay "$@"`,
    sandboxing: {
      defaultTimeoutSeconds: 1200,
      cpuLimit: '1.0',
      memoryLimit: '2Gi',
      networkIsolation: 'outbound-only',
      autoShutdownOnIdle: true
    },
    eventBus: {
      enabled: true,
      channel: 'agent.stream.marketing',
      streamLlmChunks: true,
      wsRelayUrl: 'wss://fuzeagent.prod.fuzefront.com/ws/stream'
    },
    escalation: {
      requiresApprovalForDestructive: true,
      costThresholdUsd: 3.0,
      escalateTo: 'human'
    },
    status: 'ready'
  }
];

export function ImageTemplateRegistry() {
  const [templates, setTemplates] = useState<ImageTemplate[]>(DEFAULT_TEMPLATES);
  const [selectedTemplate, setSelectedTemplate] = useState<ImageTemplate>(DEFAULT_TEMPLATES[0]);
  const [activeTab, setActiveTab] = useState<'dockerfile' | 'env' | 'secrets' | 'sandbox' | 'bus' | 'escalation'>('dockerfile');
  const [showAddModal, setShowAddModal] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [launchingId, setLaunchingId] = useState<string | null>(null);
  const [launchMessage, setLaunchMessage] = useState<string | null>(null);

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleLaunchSandbox = (template: ImageTemplate) => {
    setLaunchingId(template.id);
    setTimeout(() => {
      setLaunchingId(null);
      setLaunchMessage(`Spawned secure sandbox container for ${template.name} with ${template.sandboxing.defaultTimeoutSeconds}s timeout!`);
      setTimeout(() => setLaunchMessage(null), 5000);
    }, 1200);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 to-indigo-950 p-6 rounded-xl border border-indigo-800/40 text-white shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 bg-indigo-500/20 text-indigo-400 rounded-md border border-indigo-500/30">
              <Box className="w-5 h-5" />
            </span>
            <h2 className="text-xl font-bold tracking-tight">Agent Image Template Registry</h2>
          </div>
          <p className="text-sm text-slate-300 max-w-2xl">
            Pre-configured container images combining isolated runtime environments, automatic FuzeKeys secret injection, 
            sandboxed timeout auto-shutdown, centralized LLM bus streaming, and human escalation workflows.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium text-sm transition-all shadow-md active:scale-95"
          >
            <Plus className="w-4 h-4" />
            New Image Template
          </button>
        </div>
      </div>

      {launchMessage && (
        <div className="p-4 bg-emerald-950/40 border border-emerald-500/40 rounded-lg text-emerald-200 flex items-center justify-between animate-in fade-in duration-200">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span className="text-sm font-medium">{launchMessage}</span>
          </div>
          <button onClick={() => setLaunchMessage(null)} className="text-xs text-emerald-400 hover:underline">Dismiss</button>
        </div>
      )}

      {/* Grid: Left Template Selector, Right Detail Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Templates List */}
        <div className="lg:col-span-4 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-1">
            Configured Agent Images ({templates.length})
          </div>
          {templates.map(tmpl => {
            const isSelected = selectedTemplate.id === tmpl.id;
            return (
              <div 
                key={tmpl.id}
                onClick={() => setSelectedTemplate(tmpl)}
                className={`p-4 rounded-xl border transition-all cursor-pointer ${
                  isSelected 
                    ? 'bg-indigo-950/20 border-indigo-500/80 shadow-md ring-1 ring-indigo-500/40' 
                    : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
                      <Terminal className="w-4 h-4" />
                    </span>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white">{tmpl.name}</h3>
                      <p className="text-xs text-slate-500">{tmpl.role}</p>
                    </div>
                  </div>
                  <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                    {tmpl.status}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 dark:border-slate-800/80 pt-2.5">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    {tmpl.sandboxing.defaultTimeoutSeconds / 60}m timeout
                  </span>
                  <span className="flex items-center gap-1 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                    <Cpu className="w-3.5 h-3.5 text-slate-400" />
                    {tmpl.sandboxing.cpuLimit} CPU / {tmpl.sandboxing.memoryLimit}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Template Deep-Dive Inspector */}
        <div className="lg:col-span-8 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-50/50 dark:bg-slate-900/50">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">{selectedTemplate.name}</h3>
                <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300 font-mono">
                  {selectedTemplate.id}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">{selectedTemplate.description}</p>
              <div className="mt-2 flex items-center gap-2 font-mono text-xs text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800/80 px-2.5 py-1 rounded w-fit">
                <Box className="w-3.5 h-3.5 text-indigo-500" />
                <span>{selectedTemplate.image}</span>
                <button 
                  onClick={() => copyToClipboard(selectedTemplate.image, 'image')}
                  className="hover:text-indigo-500 ml-1"
                  title="Copy Image URI"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </div>
            </div>
            <button 
              onClick={() => handleLaunchSandbox(selectedTemplate)}
              disabled={launchingId === selectedTemplate.id}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium text-sm transition-all shadow active:scale-95 disabled:opacity-50 self-start md:self-auto"
            >
              {launchingId === selectedTemplate.id ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Spawning Sandbox...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Launch Sandbox
                </>
              )}
            </button>
          </div>

          {/* Sub Navigation Tabs */}
          <div className="flex border-b border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-950/40 px-4 gap-2 overflow-x-auto">
            <button 
              onClick={() => setActiveTab('dockerfile')}
              className={`py-3 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
                activeTab === 'dockerfile' 
                  ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400' 
                  : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <Code className="w-3.5 h-3.5" />
              Dockerfile & Base
            </button>
            <button 
              onClick={() => setActiveTab('env')}
              className={`py-3 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
                activeTab === 'env' 
                  ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400' 
                  : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              Env & Setup Script
            </button>
            <button 
              onClick={() => setActiveTab('secrets')}
              className={`py-3 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
                activeTab === 'secrets' 
                  ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400' 
                  : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <Key className="w-3.5 h-3.5" />
              FuzeKeys Secrets ({selectedTemplate.fuzeKeysSecrets.length})
            </button>
            <button 
              onClick={() => setActiveTab('sandbox')}
              className={`py-3 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
                activeTab === 'sandbox' 
                  ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400' 
                  : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <Shield className="w-3.5 h-3.5" />
              Sandboxing & Timeouts
            </button>
            <button 
              onClick={() => setActiveTab('bus')}
              className={`py-3 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
                activeTab === 'bus' 
                  ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400' 
                  : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <Radio className="w-3.5 h-3.5" />
              Event Bus Streaming
            </button>
            <button 
              onClick={() => setActiveTab('escalation')}
              className={`py-3 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
                activeTab === 'escalation' 
                  ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400' 
                  : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Decision Escalation
            </button>
          </div>

          {/* Tab Content */}
          <div className="p-6 flex-1">
            {/* Dockerfile */}
            {activeTab === 'dockerfile' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Multi-Stage Dockerfile</span>
                  <button 
                    onClick={() => copyToClipboard(selectedTemplate.dockerfile, 'dockerfile')}
                    className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    <Copy className="w-3 h-3" />
                    {copiedKey === 'dockerfile' ? 'Copied!' : 'Copy Dockerfile'}
                  </button>
                </div>
                <pre className="p-4 rounded-lg bg-slate-950 text-slate-200 text-xs font-mono overflow-x-auto leading-relaxed border border-slate-800">
                  {selectedTemplate.dockerfile}
                </pre>
                <div className="p-3 bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-900/60 rounded-lg text-xs text-indigo-800 dark:text-indigo-300">
                  💡 <strong>OCI Multi-Arch Compliant</strong>: Images are pre-built to linux/amd64 and linux/arm64 and pushed to the container registry with rootless container execution (default user: <code>agent</code>).
                </div>
              </div>
            )}

            {/* Env & Setup Script */}
            {activeTab === 'env' && (
              <div className="space-y-6">
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Environment Variables</h4>
                  <div className="bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800 divide-y divide-slate-200 dark:divide-slate-800 font-mono text-xs">
                    {Object.entries(selectedTemplate.envVars).map(([k, v]) => (
                      <div key={k} className="p-2.5 flex items-center justify-between">
                        <span className="text-indigo-600 dark:text-indigo-400 font-medium">{k}</span>
                        <span className="text-slate-600 dark:text-slate-300">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Initialization Hook Script (/usr/local/bin/init-container.sh)</h4>
                  <pre className="p-4 rounded-lg bg-slate-950 text-slate-200 text-xs font-mono overflow-x-auto leading-relaxed border border-slate-800">
                    {selectedTemplate.setupScript}
                  </pre>
                </div>
              </div>
            )}

            {/* FuzeKeys Secrets Integration */}
            {activeTab === 'secrets' && (
              <div className="space-y-4">
                <div className="p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/60 rounded-lg text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2.5">
                  <Lock className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <strong>Zero-Exposure Vault Integration</strong>: Credentials never touch the agent's disk or git repository. 
                    They are dynamically retrieved over the secure <code>FuzeKeys</code> API using opaque tokenized references bound to the active organization context.
                  </div>
                </div>

                <div className="bg-white dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800 overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-900 text-slate-500 uppercase tracking-wider border-b border-slate-200 dark:border-slate-800">
                      <tr>
                        <th className="py-2.5 px-4">Container Env Variable</th>
                        <th className="py-2.5 px-4">FuzeKeys Vault Reference</th>
                        <th className="py-2.5 px-4">Description</th>
                        <th className="py-2.5 px-4 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                      {selectedTemplate.fuzeKeysSecrets.map(sec => (
                        <tr key={sec.keyName} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/40">
                          <td className="py-3 px-4 text-indigo-600 dark:text-indigo-400 font-bold">{sec.keyName}</td>
                          <td className="py-3 px-4 text-slate-600 dark:text-slate-400">{sec.secretRef}</td>
                          <td className="py-3 px-4 font-sans text-slate-500 text-xs">{sec.description}</td>
                          <td className="py-3 px-4 text-right">
                            <span className="inline-flex items-center gap-1 text-[11px] font-sans text-emerald-600 dark:text-emerald-400">
                              <CheckCircle2 className="w-3 h-3" /> Synced
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Sandboxing & Timeout */}
            {activeTab === 'sandbox' && (
              <div className="space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
                    <div className="flex items-center gap-2 mb-2 text-slate-900 dark:text-white font-medium text-sm">
                      <Clock className="w-4 h-4 text-indigo-500" />
                      Execution Timeout & Auto-Shutdown
                    </div>
                    <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                      {selectedTemplate.sandboxing.defaultTimeoutSeconds} seconds
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Container forcefully terminates after {selectedTemplate.sandboxing.defaultTimeoutSeconds / 60} minutes to prevent runaway compute or cost spikes.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
                    <div className="flex items-center gap-2 mb-2 text-slate-900 dark:text-white font-medium text-sm">
                      <Shield className="w-4 h-4 text-emerald-500" />
                      Network Isolation Level
                    </div>
                    <div className="text-lg font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                      {selectedTemplate.sandboxing.networkIsolation}
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Restricts in-cluster lateral movement; allows only external HTTPS package index mirrors and orchestrator WebSocket.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="text-sm font-medium text-slate-900 dark:text-white">Auto-shutdown on task completion or idle</div>
                    <div className="text-xs text-slate-500">Deletes the k8s pod / container when the agent marks task as done</div>
                  </div>
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                    Active
                  </span>
                </div>
              </div>
            )}

            {/* Event Bus Streaming */}
            {activeTab === 'bus' && (
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 space-y-3 font-mono text-xs">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400">Event Bus Channel:</span>
                    <span className="text-indigo-400 font-bold">{selectedTemplate.eventBus.channel}</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400">LLM Token Streaming:</span>
                    <span className="text-emerald-400">Enabled (SSE + WebSocket Chunking)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Relay URL:</span>
                    <span className="text-slate-300">{selectedTemplate.eventBus.wsRelayUrl}</span>
                  </div>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">
                  As the agent executes inside its container, every token, thought step, and tool result is piped through <code>session-relay.sh</code> into the orchestrator message bus and broadcasted to the user's FuzeFront portal chat in real-time.
                </p>
              </div>
            )}

            {/* Decision Escalation */}
            {activeTab === 'escalation' && (
              <div className="space-y-4">
                <div className="p-4 rounded-lg border border-amber-200 dark:border-amber-900/60 bg-amber-50/50 dark:bg-amber-950/20 space-y-3">
                  <div className="flex items-center gap-2 text-amber-900 dark:text-amber-200 font-semibold text-sm">
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                    Human-in-the-Loop Safeguards
                  </div>
                  <p className="text-xs text-amber-800/90 dark:text-amber-300/80 leading-relaxed">
                    When an agent attempts a sensitive operation (e.g. database schema change, package publishing, deletion, or spending over ${selectedTemplate.escalation.costThresholdUsd.toFixed(2)}), 
                    execution is paused and an approval request is dispatched to the managing orchestrator or human supervisor.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div className="p-3 rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
                    <span className="text-slate-500 block mb-1">Destructive Ops Gate:</span>
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">Required (Fails closed)</span>
                  </div>
                  <div className="p-3 rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
                    <span className="text-slate-500 block mb-1">Budget Escalation Threshold:</span>
                    <span className="font-semibold text-slate-900 dark:text-white">${selectedTemplate.escalation.costThresholdUsd.toFixed(2)} USD</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* New Template Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Box className="w-5 h-5 text-indigo-600" />
                Register New Agent Container Image
              </h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
            </div>
            <p className="text-xs text-slate-500">
              Define a new agent container image with customized Dockerfile environment, FuzeKeys secret bindings, and execution timeout.
            </p>
            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button 
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-medium"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  const id = `custom-agent-${Date.now()}`;
                  const created: ImageTemplate = {
                    id,
                    name: 'Custom Polyglot Agent',
                    category: 'development',
                    role: 'FullStack & Automation Specialist',
                    image: `ghcr.io/izzywdev/fuzeagent/${id}:latest`,
                    description: 'Custom sandboxed agent environment.',
                    dockerfile: `# syntax=docker/dockerfile:1\nFROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest\nUSER root\nRUN apt-get update && apt-get install -y python3-pip nodejs\nUSER agent\nCMD ["/usr/local/bin/session-relay"]`,
                    envVars: { LOG_LEVEL: 'INFO' },
                    fuzeKeysSecrets: [{ keyName: 'ANTHROPIC_API_KEY', secretRef: 'fk_sec_anthropic_prod', description: 'Anthropic LLM Token' }],
                    setupScript: '#!/bin/bash\nexec /usr/local/bin/session-relay "$@"',
                    sandboxing: { defaultTimeoutSeconds: 1800, cpuLimit: '2.0', memoryLimit: '4Gi', networkIsolation: 'outbound-only', autoShutdownOnIdle: true },
                    eventBus: { enabled: true, channel: `agent.stream.${id}`, streamLlmChunks: true, wsRelayUrl: 'wss://fuzeagent.prod.fuzefront.com/ws/stream' },
                    escalation: { requiresApprovalForDestructive: true, costThresholdUsd: 5.0, escalateTo: 'human' },
                    status: 'ready'
                  };
                  setTemplates(prev => [...prev, created]);
                  setSelectedTemplate(created);
                  setShowAddModal(false);
                }}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium shadow-sm active:scale-95"
              >
                Add Template
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ImageTemplateRegistry;

