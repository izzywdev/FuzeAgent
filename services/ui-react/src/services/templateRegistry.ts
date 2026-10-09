/**
 * FuzeAgent Template & Blueprint Registry
 * 
 * Provides two-tiered template architecture:
 * Level 1: Foundation Image Templates (container image, Dockerfile, setup script, env, secrets, sandboxing)
 * Level 2: Agent Blueprints / Templates (built on an Image Template + Network Policy + Connectors + Brains)
 */

export interface FuzeKeysSecretBinding {
  keyName: string;
  secretRef: string;
  description: string;
}

export interface SandboxingConfig {
  defaultTimeoutSeconds: number;
  cpuLimit: string;
  memoryLimit: string;
  networkIsolation: 'strict' | 'outbound-only' | 'full';
  autoShutdownOnIdle: boolean;
}

export interface EventBusConfig {
  enabled: boolean;
  channel: string;
  streamLlmChunks: boolean;
  wsRelayUrl: string;
}

export interface EscalationConfig {
  requiresApprovalForDestructive: boolean;
  costThresholdUsd: number;
  escalateTo: 'human' | 'orchestrator' | 'both';
}

export interface ImageTemplate {
  id: string;
  name: string;
  category: 'development' | 'devops' | 'marketing' | 'qa' | 'security' | 'management';
  role: string;
  image: string;
  description: string;
  dockerfile: string;
  envVars: Record<string, string>;
  fuzeKeysSecrets: FuzeKeysSecretBinding[];
  setupScript: string;
  sandboxing: SandboxingConfig;
  eventBus: EventBusConfig;
  escalation: EscalationConfig;
  status: 'active' | 'building' | 'ready';
  created_at?: string;
}

export interface ConnectorBinding {
  id: string;
  name: string;
  type: 'github' | 'postgres' | 'slack' | 'jira' | 'redis';
  description?: string;
  scope?: string;
}

export interface BrainBinding {
  id: string;
  name: string;
  category: 'engineering' | 'architecture' | 'product' | 'database';
  documentCount?: number;
}

export interface AgentBlueprintTemplate {
  id: string;
  name: string;
  role: string;
  category: 'development' | 'devops' | 'marketing' | 'qa' | 'security' | 'management';
  description: string;
  imageTemplateId: string;
  imageTemplateName?: string;
  networkPolicy: 'strict-isolated' | 'fuzefront-internal' | 'egress-allowlisted' | 'full-access';
  connectors: ConnectorBinding[];
  brains: BrainBinding[];
  defaultGoal: string;
  defaultBackstory: string;
  systemPrompt: string;
  tools: string[];
  skills: string[];
  defaultModel: string;
  defaultTemperature: number;
  created_at?: string;
}

// -------------------------------------------------------------
// Default Foundation Image Templates
// -------------------------------------------------------------
export const DEFAULT_IMAGE_TEMPLATES: ImageTemplate[] = [
  {
    id: 'python-dev',
    name: 'Python Developer Runtime',
    category: 'development',
    role: 'Backend & Data Specialist',
    image: 'ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest',
    description: 'Isolated Python 3.12 environment with FastAPI, SQLAlchemy, Pytest, Black, Ruff, Poetry, asyncpg, and LLM streaming relay.',
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
      DEFAULT_TIMEOUT: '1800',
    },
    fuzeKeysSecrets: [
      { keyName: 'ANTHROPIC_API_KEY', secretRef: 'fk_sec_anthropic_prod', description: 'Zero-exposure Anthropic token via FuzeKeys' },
      { keyName: 'GITHUB_TOKEN', secretRef: 'fk_sec_github_agent_pat', description: 'Agent scoped GitHub PAT' },
      { keyName: 'DATABASE_URL', secretRef: 'fk_sec_pg_vector_ai', description: 'Encrypted db connection credential' },
    ],
    setupScript: `#!/bin/bash
set -e
echo "[init] Starting Python sandbox container..."
if [ -n "$WS_RELAY_URL" ]; then
  echo "[init] Connected to centralized event bus: $WS_RELAY_URL"
fi
exec /usr/local/bin/session-relay "$@"`,
    sandboxing: {
      defaultTimeoutSeconds: 1800,
      cpuLimit: '2.0',
      memoryLimit: '4Gi',
      networkIsolation: 'outbound-only',
      autoShutdownOnIdle: true,
    },
    eventBus: {
      enabled: true,
      channel: 'agent.stream.python-dev',
      streamLlmChunks: true,
      wsRelayUrl: 'wss://fuzeagent.prod.fuzefront.com/ws/stream',
    },
    escalation: {
      requiresApprovalForDestructive: true,
      costThresholdUsd: 5.0,
      escalateTo: 'human',
    },
    status: 'ready',
  },
  {
    id: 'react-dev',
    name: 'React & UI Developer Runtime',
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
      FORCE_COLOR: '1',
    },
    fuzeKeysSecrets: [
      { keyName: 'ANTHROPIC_API_KEY', secretRef: 'fk_sec_anthropic_prod', description: 'Anthropic Claude Code token' },
      { keyName: 'NPM_TOKEN', secretRef: 'fk_sec_npm_pkg_registry', description: 'Internal FuzeFront scoped registry token' },
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
      autoShutdownOnIdle: true,
    },
    eventBus: {
      enabled: true,
      channel: 'agent.stream.react-dev',
      streamLlmChunks: true,
      wsRelayUrl: 'wss://fuzeagent.prod.fuzefront.com/ws/stream',
    },
    escalation: {
      requiresApprovalForDestructive: true,
      costThresholdUsd: 5.0,
      escalateTo: 'human',
    },
    status: 'ready',
  },
  {
    id: 'devops-k8s',
    name: 'DevOps & Kubernetes Runtime',
    category: 'devops',
    role: 'Infrastructure & GitOps Specialist',
    image: 'ghcr.io/izzywdev/fuzeagent/claude-runner-devops:latest',
    description: 'Cloud-native ops container with kubectl, helm, k9s, git, terraform, and cluster RBAC introspection tools.',
    dockerfile: `# syntax=docker/dockerfile:1
FROM alpine/k8s:1.30.2
RUN apk add --no-cache bash curl git jq yq helm openssl
USER agent
CMD ["/usr/local/bin/session-relay"]`,
    envVars: {
      KUBECONFIG_INCLUSTER: 'true',
      HELM_CACHE_HOME: '/tmp/helm-cache',
    },
    fuzeKeysSecrets: [
      { keyName: 'KUBE_BEARER_TOKEN', secretRef: 'fk_sec_k8s_orchestrator_token', description: 'Restricted In-Cluster ServiceAccount Token' },
      { keyName: 'ARGO_AUTH_TOKEN', secretRef: 'fk_sec_argocd_sync_token', description: 'GitOps ArgoCD deployment trigger key' },
    ],
    setupScript: `#!/bin/bash
set -e
echo "[init] DevOps Runner online. Verifying in-cluster RBAC..."
kubectl auth can-i get pods --namespace fuzeagent
exec /usr/local/bin/session-relay "$@"`,
    sandboxing: {
      defaultTimeoutSeconds: 2400,
      cpuLimit: '1.5',
      memoryLimit: '2Gi',
      networkIsolation: 'strict',
      autoShutdownOnIdle: true,
    },
    eventBus: {
      enabled: true,
      channel: 'agent.stream.devops',
      streamLlmChunks: true,
      wsRelayUrl: 'wss://fuzeagent.prod.fuzefront.com/ws/stream',
    },
    escalation: {
      requiresApprovalForDestructive: true,
      costThresholdUsd: 10.0,
      escalateTo: 'human',
    },
    status: 'ready',
  },
];

// -------------------------------------------------------------
// Default Agent Blueprint Templates (Level 2: Image + Policies + Connectors + Brains)
// -------------------------------------------------------------
export const DEFAULT_AGENT_TEMPLATES: AgentBlueprintTemplate[] = [
  {
    id: 'tmpl-fullstack-dev',
    name: 'Full-Stack Feature Engineer',
    role: 'Senior Software Engineer',
    category: 'development',
    description: 'Autonomous builder that writes Python backend services, wires React 19 UI with FuzeFront DS, and validates integration test suites.',
    imageTemplateId: 'python-dev',
    imageTemplateName: 'Python Developer Runtime',
    networkPolicy: 'fuzefront-internal',
    connectors: [
      { id: 'conn-github', name: 'GitHub Enterprise', type: 'github', description: 'Push PRs & branch automation' },
      { id: 'conn-postgres', name: 'Primary PostgreSQL', type: 'postgres', description: 'Query & schema migration inspection' },
    ],
    brains: [
      { id: 'brain-wiki', name: 'Engineering Wiki & Architecture Docs', category: 'engineering', documentCount: 42 },
      { id: 'brain-rfcs', name: 'FuzeFront Design System Standards', category: 'architecture', documentCount: 18 },
    ],
    defaultGoal: 'Implement end-to-end full-stack features conforming strictly to FuzeFront DS tokens and zero-downtime microfrontends.',
    defaultBackstory: 'You are a staff engineer who writes clean, idiomatic code with robust test coverage and beautiful frontend aesthetics.',
    systemPrompt: 'You are the Full-Stack Feature Engineer in FuzeAgent. Always use proper design tokens and run test verification before completing tasks.',
    tools: ['code_generation', 'code_review', 'unit_testing', 'git_workflow', 'vector_search'],
    skills: ['Python 3.12', 'FastAPI', 'React 19', 'Vite', 'Asyncpg', 'PostgreSQL'],
    defaultModel: 'claude-sonnet-4-20250514',
    defaultTemperature: 0.2,
  },
  {
    id: 'tmpl-k8s-sre',
    name: 'Kubernetes Platform & SRE Lead',
    role: 'Site Reliability Engineer',
    category: 'devops',
    description: 'Monitors pod health, validates Helm charts, detects container restart loops, and safeguards cluster stability.',
    imageTemplateId: 'devops-k8s',
    imageTemplateName: 'DevOps & Kubernetes Runtime',
    networkPolicy: 'strict-isolated',
    connectors: [
      { id: 'conn-github', name: 'GitHub Helm Repo', type: 'github', description: 'Chart repository access' },
      { id: 'conn-slack', name: 'Slack Alerts (#ops-alerts)', type: 'slack', description: 'Deployment notification channel' },
    ],
    brains: [
      { id: 'brain-infra', name: 'Infrastructure Runbooks & Alerts', category: 'architecture', documentCount: 35 },
    ],
    defaultGoal: 'Safeguard cluster reliability, automate rollouts, and ensure zero unhandled pod terminations.',
    defaultBackstory: 'You are an SRE specialist dedicated to infrastructure resiliency, declarative GitOps, and rapid fault diagnosis.',
    systemPrompt: 'You are the Kubernetes Platform SRE in FuzeAgent. Analyze telemetry, inspect events, and maintain cluster uptime.',
    tools: ['helm_lint', 'kubectl_inspect', 'log_streaming', 'health_check'],
    skills: ['Kubernetes', 'Helm', 'ArgoCD', 'Prometheus', 'NetworkPolicies'],
    defaultModel: 'claude-sonnet-4-20250514',
    defaultTemperature: 0.1,
  },
  {
    id: 'tmpl-growth-strategist',
    name: 'Growth & Content Campaign Strategist',
    role: 'Marketing Strategist',
    category: 'marketing',
    description: 'Generates omnichannel marketing campaigns, drafts product announcements, and monitors engagement analytics.',
    imageTemplateId: 'react-dev',
    imageTemplateName: 'React & UI Developer Runtime',
    networkPolicy: 'egress-allowlisted',
    connectors: [
      { id: 'conn-slack', name: 'Marketing Slack Hub', type: 'slack', description: 'Campaign coordination' },
    ],
    brains: [
      { id: 'brain-product', name: 'Product Marketing & Personas', category: 'product', documentCount: 24 },
    ],
    defaultGoal: 'Draft compelling marketing copy, design landing pages, and optimize user acquisition funnels.',
    defaultBackstory: 'You are a data-driven growth strategist who crafts viral content and analyzes product positioning.',
    systemPrompt: 'You are the Growth Strategist in FuzeAgent. Write high-converting copy and design engaging interactive experiences.',
    tools: ['copywriting', 'analytics_query', 'campaign_design'],
    skills: ['Growth Hacking', 'FuzeSocial', 'Content Strategy', 'SEO'],
    defaultModel: 'claude-sonnet-4-20250514',
    defaultTemperature: 0.7,
  },
  {
    id: 'tmpl-qa-automation',
    name: 'QA & Test Automation Specialist',
    role: 'Quality Assurance Engineer',
    category: 'qa',
    description: 'Executes automated end-to-end regression tests, generates integration test suites, and audits API contracts.',
    imageTemplateId: 'python-dev',
    imageTemplateName: 'Python Developer Runtime',
    networkPolicy: 'fuzefront-internal',
    connectors: [
      { id: 'conn-github', name: 'GitHub CI Pipeline', type: 'github', description: 'Trigger test suites & annotate PRs' },
      { id: 'conn-jira', name: 'Jira Bug Tracker', type: 'jira', description: 'File bug reports with trace logs' },
    ],
    brains: [
      { id: 'brain-wiki', name: 'Engineering Wiki & API Specs', category: 'engineering', documentCount: 42 },
    ],
    defaultGoal: 'Maintain zero-defect releases with comprehensive automated unit, integration, and E2E coverage.',
    defaultBackstory: 'You are a meticulous QA engineer who tests edge cases and ensures resilient systems.',
    systemPrompt: 'You are the QA Automation Specialist in FuzeAgent. Find defects early and write rock-solid test suites.',
    tools: ['pytest', 'playwright', 'api_contract_test', 'bug_reporter'],
    skills: ['Pytest', 'Playwright', 'Vitest', 'Postman', 'Contract Testing'],
    defaultModel: 'claude-sonnet-4-20250514',
    defaultTemperature: 0.1,
  },
];

// -------------------------------------------------------------
// Persistence Helpers (localStorage + Memory cache)
// -------------------------------------------------------------
const STORAGE_KEY_IMAGES = 'fuzeagent_image_templates_v2';
const STORAGE_KEY_AGENTS = 'fuzeagent_agent_blueprints_v2';

export const templateRegistry = {
  // Image Templates
  getImageTemplates(): ImageTemplate[] {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_IMAGES);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch {
      // fallback to memory
    }
    return DEFAULT_IMAGE_TEMPLATES;
  },

  saveImageTemplate(template: ImageTemplate): void {
    const list = this.getImageTemplates();
    const idx = list.findIndex(t => t.id === template.id);
    if (idx >= 0) {
      list[idx] = template;
    } else {
      list.unshift(template);
    }
    try {
      localStorage.setItem(STORAGE_KEY_IMAGES, JSON.stringify(list));
    } catch {
      // ignore
    }
  },

  deleteImageTemplate(id: string): void {
    const list = this.getImageTemplates().filter(t => t.id !== id);
    try {
      localStorage.setItem(STORAGE_KEY_IMAGES, JSON.stringify(list));
    } catch {
      // ignore
    }
  },

  // Agent Blueprint Templates
  getAgentTemplates(): AgentBlueprintTemplate[] {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_AGENTS);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch {
      // fallback
    }
    return DEFAULT_AGENT_TEMPLATES;
  },

  saveAgentTemplate(blueprint: AgentBlueprintTemplate): void {
    const list = this.getAgentTemplates();
    const idx = list.findIndex(t => t.id === blueprint.id);
    if (idx >= 0) {
      list[idx] = blueprint;
    } else {
      list.unshift(blueprint);
    }
    try {
      localStorage.setItem(STORAGE_KEY_AGENTS, JSON.stringify(list));
    } catch {
      // ignore
    }
  },

  deleteAgentTemplate(id: string): void {
    const list = this.getAgentTemplates().filter(t => t.id !== id);
    try {
      localStorage.setItem(STORAGE_KEY_AGENTS, JSON.stringify(list));
    } catch {
      // ignore
    }
  },
};
