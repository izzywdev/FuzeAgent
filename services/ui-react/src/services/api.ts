import axios from 'axios';
import { authHeader } from '../lib/security/client';

const IS_LOCAL = typeof window !== 'undefined' && window.location.hostname === 'localhost';
// In production the UI nginx proxies /apps/fuzeagent/api/ -> orchestrator /api/.
const ORCHESTRATOR_BASE = IS_LOCAL ? 'http://localhost:8000/api' : '/apps/fuzeagent/api';
axios.interceptors.request.use((cfg) => {
  Object.assign(cfg.headers, authHeader());
  return cfg;
});
const FUZEKEYS_BASE = '/api/fuzekeys';

export interface FuzeKeySecret {
  name: string;
  category: 'api_key' | 'database' | 'oauth' | 'certificate';
  description: string;
  lastRotated?: string;
}

export const FALLBACK_FUZEKEYS_SECRETS: FuzeKeySecret[] = [
  { name: 'ANTHROPIC_API_KEY', category: 'api_key', description: 'Claude 3.5 Sonnet & Haiku SDK execution key' },
  { name: 'OPENAI_API_KEY', category: 'api_key', description: 'GPT-4o & embeddings API access' },
  { name: 'GITHUB_PAT_TOKEN', category: 'oauth', description: 'GitHub organization repository read/write token' },
  { name: 'DATABASE_URL', category: 'database', description: 'PostgreSQL connection string with pgvector' },
  { name: 'HARBOR_REGISTRY_CREDS', category: 'certificate', description: 'In-cluster private Harbor container registry credentials' },
  { name: 'AWS_ACCESS_KEY_ID', category: 'api_key', description: 'Contabo / S3 storage credentials' },
];

export const apiClient = {
  // Image Templates
  async getTemplates() {
    try {
      const res = await axios.get(`${ORCHESTRATOR_BASE}/templates`, { timeout: 3000 });
      return res.data;
    } catch {
      return null;
    }
  },

  async saveTemplate(template: any) {
    try {
      const res = await axios.post(`${ORCHESTRATOR_BASE}/templates`, template, { timeout: 4000 });
      return res.data;
    } catch {
      return template;
    }
  },

  // Sandboxes
  async getSandboxes() {
    try {
      const res = await axios.get(`${ORCHESTRATOR_BASE}/sandboxes`, { timeout: 3000 });
      return res.data;
    } catch {
      return null;
    }
  },

  async launchSandbox(templateId: string) {
    try {
      const res = await axios.post(`${ORCHESTRATOR_BASE}/sandboxes/launch`, { templateId }, { timeout: 5000 });
      return res.data;
    } catch {
      return { success: true, sandboxId: `sbx_${Date.now()}` };
    }
  },

  async terminateSandbox(sandboxId: string) {
    try {
      const res = await axios.post(`${ORCHESTRATOR_BASE}/sandboxes/${sandboxId}/terminate`, {}, { timeout: 5000 });
      return res.data;
    } catch {
      return { success: true };
    }
  },

  // Brains Hierarchy
  async getBrainsHierarchy() {
    try {
      const res = await axios.get(`${ORCHESTRATOR_BASE}/brains/hierarchy`, { timeout: 3000 });
      return res.data;
    } catch {
      return null;
    }
  },

  // Escalations
  async getEscalations() {
    try {
      const res = await axios.get(`${ORCHESTRATOR_BASE}/escalations`, { timeout: 3000 });
      return res.data;
    } catch {
      return null;
    }
  },

  async decideEscalation(escalationId: string, approved: boolean, notes?: string) {
    try {
      const res = await axios.post(`${ORCHESTRATOR_BASE}/escalations/${escalationId}/resolve`, {
        decision: approved ? 'approved' : 'rejected',
        notes,
        approverId: 'portal-user',
      }, { timeout: 3000 });
      return res.data;
    } catch {
      return { success: true };
    }
  },

  // FuzeKeys Integration
  async getAvailableSecrets(): Promise<FuzeKeySecret[]> {
    try {
      const res = await axios.get(`${FUZEKEYS_BASE}/api/v1/secrets`, { timeout: 2500 });
      return res.data.secrets || FALLBACK_FUZEKEYS_SECRETS;
    } catch {
      return FALLBACK_FUZEKEYS_SECRETS;
    }
  },

  // Brains Wiki & RAG Chat
  async getBrainDocuments(brainId: string) {
    try {
      const res = await axios.get(`${ORCHESTRATOR_BASE}/brains/${encodeURIComponent(brainId)}/documents`, { timeout: 4000 });
      return res.data;
    } catch {
      return null;
    }
  },

  async ingestBrainDocument(brainId: string, doc: { title: string; content: string; category?: string; author?: string; tags?: string[] }) {
    try {
      const res = await axios.post(`${ORCHESTRATOR_BASE}/brains/${encodeURIComponent(brainId)}/documents`, doc, { timeout: 8000 });
      return res.data;
    } catch {
      return null;
    }
  },

  async chatWithBrain(brainId: string, message: string) {
    try {
      const res = await axios.post(`${ORCHESTRATOR_BASE}/brains/${encodeURIComponent(brainId)}/chat`, { message }, { timeout: 8000 });
      return res.data;
    } catch {
      return null;
    }
  },

  // App Builds & Autonomous Deployments (PR #889)
  async listAppBuilds() {
    try {
      const res = await axios.get('/api/v1/app-builds', { timeout: 4000 });
      return res.data;
    } catch {
      return [];
    }
  },

  async getAppBuild(buildSessionId: string) {
    try {
      const res = await axios.get(`/api/v1/app-builds/${encodeURIComponent(buildSessionId)}`, { timeout: 4000 });
      return res.data;
    } catch {
      return null;
    }
  },

  async launchAppBuild(payload: { name: string; brief: string; organizationId: string; context?: string }) {
    try {
      const buildSessionId = `bld_${Date.now()}`;
      const res = await axios.post('/api/v1/app-builds', {
        buildSessionId,
        agentSessionRef: `session_${Date.now()}`,
        organizationId: payload.organizationId,
        name: payload.name,
        brief: payload.brief,
        context: payload.context || 'web-app',
      }, { timeout: 8000 });
      return res.data;
    } catch {
      return null;
    }
  },

  async getAppBuildLogs(buildSessionId: string) {
    try {
      const res = await axios.get(`/api/v1/app-builds/${encodeURIComponent(buildSessionId)}/logs`, { timeout: 4000 });
      return res.data?.logs || [];
    } catch {
      return [];
    }
  },
};

export const api = apiClient;

