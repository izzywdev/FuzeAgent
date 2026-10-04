import axios from 'axios';

const ORCHESTRATOR_BASE = '/api/orchestrator/image-registry';
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

  // Brains Hierarchy
  async getBrainsHierarchy() {
    try {
      const res = await axios.get(`${ORCHESTRATOR_BASE}/brains`, { timeout: 3000 });
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
      const res = await axios.post(`${ORCHESTRATOR_BASE}/escalations/${escalationId}/decision`, {
        approved,
        notes,
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
};
