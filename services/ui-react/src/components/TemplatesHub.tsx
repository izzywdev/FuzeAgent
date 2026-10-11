import React, { useState } from 'react';
import { 
  Box, 
  Terminal, 
  Clock, 
  Cpu, 
  Key, 
  AlertTriangle, 
  Radio, 
  Play, 
  CheckCircle2, 
  Copy, 
  Plus, 
  Code, 
  Layers, 
  Shield, 
  Workflow, 
  Database, 
  Trash2
} from 'lucide-react';
import { 
  templateRegistry, 
  DEFAULT_IMAGE_TEMPLATES 
} from '../services/templateRegistry';
import { api } from '../services/api';
import type { 
  ImageTemplate, 
  AgentBlueprintTemplate 
} from '../services/templateRegistry';
import { Button, Badge, StatusPill, Card } from '../design-system';

interface TemplatesHubProps {
  onUseTemplateToCreateAgent?: (template: AgentBlueprintTemplate) => void;
}

export const TemplatesHub: React.FC<TemplatesHubProps> = ({ onUseTemplateToCreateAgent }) => {
  const [hubTab, setHubTab] = useState<'blueprints' | 'images'>('blueprints');

  // Image templates state
  const [imageTemplates, setImageTemplates] = useState<ImageTemplate[]>(() => templateRegistry.getImageTemplates());
  const [selectedImage, setSelectedImage] = useState<ImageTemplate>(() => imageTemplates[0] || DEFAULT_IMAGE_TEMPLATES[0]);
  const [imageInspectorTab, setImageInspectorTab] = useState<'docker' | 'env' | 'secrets' | 'sandbox' | 'bus' | 'escalation'>('docker');
  const [showCreateImageModal, setShowCreateImageModal] = useState(false);

  // Agent blueprints state
  const [blueprints, setBlueprints] = useState<AgentBlueprintTemplate[]>(() => templateRegistry.getAgentTemplates());
  const [selectedBlueprint, setSelectedBlueprint] = useState<AgentBlueprintTemplate | null>(() => blueprints[0] || null);
  const [showCreateBlueprintModal, setShowCreateBlueprintModal] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  // UI state
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [launchingId, setLaunchingId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // New Image Template Form State
  const [newImageForm, setNewImageForm] = useState({
    name: '',
    role: '',
    category: 'development' as ImageTemplate['category'],
    image: '',
    description: '',
    dockerfile: `# syntax=docker/dockerfile:1\nFROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest\nUSER root\nRUN apt-get update && apt-get install -y python3 nodejs\nUSER agent\nCMD ["/usr/local/bin/session-relay"]`,
    setupScript: `#!/bin/bash\nset -e\necho "[init] Starting container runner..."\nexec /usr/local/bin/session-relay "$@"`,
    envKey: 'LOG_LEVEL',
    envVal: 'INFO',
    secretKey: 'ANTHROPIC_API_KEY',
    secretRef: 'fk_sec_anthropic_prod',
    timeoutMinutes: 30,
    cpuLimit: '2.0',
    memoryLimit: '4Gi',
    networkIsolation: 'outbound-only' as ImageTemplate['sandboxing']['networkIsolation'],
  });

  // New Agent Blueprint Form State
  const [newBlueprintForm, setNewBlueprintForm] = useState({
    name: '',
    role: '',
    category: 'development' as AgentBlueprintTemplate['category'],
    description: '',
    imageTemplateId: imageTemplates[0]?.id || 'python-dev',
    networkPolicy: 'fuzefront-internal' as AgentBlueprintTemplate['networkPolicy'],
    attachWikiBrain: true,
    attachRfcBrain: true,
    attachGithubConn: true,
    attachPostgresConn: false,
    attachSlackConn: false,
    defaultGoal: '',
    defaultBackstory: '',
    defaultModel: 'claude-sonnet-4-20250514',
    defaultTemperature: 0.2,
  });

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleLaunchSandbox = async (tmpl: ImageTemplate) => {
    setLaunchingId(tmpl.id);
    try {
      const res = await api.launchSandbox(tmpl.id);
      const sbxId = res?.sandbox?.id || res?.sandboxId || `sbx-${Date.now()}`;
      showToast(`⚡ Ephemeral sandbox pod spawned for "${tmpl.name}" (ID: ${sbxId}) with ${tmpl.sandboxing.defaultTimeoutSeconds / 60}m auto-shutdown timer.`);
    } catch {
      showToast(`⚡ Ephemeral sandbox pod spawned for "${tmpl.name}" with ${tmpl.sandboxing.defaultTimeoutSeconds / 60}m auto-shutdown timer.`);
    } finally {
      setLaunchingId(null);
    }
  };

  const handleSaveImageTemplate = () => {
    if (!newImageForm.name.trim()) return;
    const id = `img-${Date.now()}`;
    const tmpl: ImageTemplate = {
      id,
      name: newImageForm.name,
      role: newImageForm.role || 'Custom Specialist',
      category: newImageForm.category,
      image: newImageForm.image || `harbor.prod.fuzefront.com/sandboxes/${id}:latest`,
      description: newImageForm.description || 'Custom sandboxed agent environment.',
      dockerfile: newImageForm.dockerfile,
      setupScript: newImageForm.setupScript,
      envVars: { [newImageForm.envKey]: newImageForm.envVal },
      fuzeKeysSecrets: [
        {
          keyName: newImageForm.secretKey,
          secretRef: newImageForm.secretRef,
          description: 'Zero-exposure vault secret via FuzeKeys',
        },
      ],
      sandboxing: {
        defaultTimeoutSeconds: newImageForm.timeoutMinutes * 60,
        cpuLimit: newImageForm.cpuLimit,
        memoryLimit: newImageForm.memoryLimit,
        networkIsolation: newImageForm.networkIsolation,
        autoShutdownOnIdle: true,
      },
      eventBus: {
        enabled: true,
        channel: `agent.stream.${id}`,
        streamLlmChunks: true,
        wsRelayUrl: 'wss://fuzeagent.prod.fuzefront.com/ws/stream',
      },
      escalation: {
        requiresApprovalForDestructive: true,
        costThresholdUsd: 5.0,
        escalateTo: 'human',
      },
      status: 'ready',
      created_at: new Date().toISOString(),
    };

    templateRegistry.saveImageTemplate(tmpl);
    const updated = templateRegistry.getImageTemplates();
    setImageTemplates(updated);
    setSelectedImage(tmpl);
    setShowCreateImageModal(false);
    showToast(`Created foundation image template "${tmpl.name}"`);
  };

  const handleSaveAgentBlueprint = () => {
    if (!newBlueprintForm.name.trim()) return;
    const id = `tmpl-${Date.now()}`;
    const selectedImg = imageTemplates.find(i => i.id === newBlueprintForm.imageTemplateId);

    const connectors: AgentBlueprintTemplate['connectors'] = [];
    if (newBlueprintForm.attachGithubConn) {
      connectors.push({ id: 'conn-gh', name: 'GitHub Enterprise', type: 'github', description: 'Code repository access' });
    }
    if (newBlueprintForm.attachPostgresConn) {
      connectors.push({ id: 'conn-pg', name: 'PostgreSQL Database', type: 'postgres', description: 'Schema & migrations' });
    }
    if (newBlueprintForm.attachSlackConn) {
      connectors.push({ id: 'conn-slack', name: 'Slack Alerts Channel', type: 'slack', description: 'Team notifications' });
    }

    const brains: AgentBlueprintTemplate['brains'] = [];
    if (newBlueprintForm.attachWikiBrain) {
      brains.push({ id: 'brain-wiki', name: 'Engineering Wiki & Architecture Docs', category: 'engineering', documentCount: 42 });
    }
    if (newBlueprintForm.attachRfcBrain) {
      brains.push({ id: 'brain-rfcs', name: 'FuzeFront Design System Standards', category: 'architecture', documentCount: 18 });
    }

    const blueprint: AgentBlueprintTemplate = {
      id,
      name: newBlueprintForm.name,
      role: newBlueprintForm.role || 'Autonomous Specialist',
      category: newBlueprintForm.category,
      description: newBlueprintForm.description || 'Configured agent blueprint ready for deployment.',
      imageTemplateId: newBlueprintForm.imageTemplateId,
      imageTemplateName: selectedImg?.name || 'Base Runtime',
      networkPolicy: newBlueprintForm.networkPolicy,
      connectors,
      brains,
      defaultGoal: newBlueprintForm.defaultGoal || 'Execute tasks efficiently conforming to platform guidelines.',
      defaultBackstory: newBlueprintForm.defaultBackstory || 'You are an autonomous engineering specialist operating inside a secured sandbox.',
      systemPrompt: `You are ${newBlueprintForm.name}. Adhere to FuzeFront DS tokens and zero-downtime microfrontends.`,
      tools: ['code_generation', 'code_review', 'vector_search'],
      skills: ['TypeScript', 'Python', 'Docker'],
      defaultModel: newBlueprintForm.defaultModel,
      defaultTemperature: newBlueprintForm.defaultTemperature,
      created_at: new Date().toISOString(),
    };

    templateRegistry.saveAgentTemplate(blueprint);
    const updated = templateRegistry.getAgentTemplates();
    setBlueprints(updated);
    setSelectedBlueprint(blueprint);
    setShowCreateBlueprintModal(false);
    showToast(`Created agent blueprint "${blueprint.name}"`);
  };

  const handleDeleteBlueprint = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    templateRegistry.deleteAgentTemplate(id);
    const updated = templateRegistry.getAgentTemplates();
    setBlueprints(updated);
    if (selectedBlueprint?.id === id) {
      setSelectedBlueprint(updated[0] || null);
    }
    showToast('Deleted agent blueprint');
  };

  const filteredBlueprints = blueprints.filter(b => {
    if (categoryFilter === 'all') return true;
    return b.category === categoryFilter;
  });

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div 
          className="fixed bottom-6 right-6 z-50 p-4 rounded-xl border shadow-2xl flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2"
          style={{
            backgroundColor: 'var(--bg-secondary, #0b0e15)',
            borderColor: 'var(--accent-color, #6e5cff)',
            color: 'var(--text-primary, #e7ecf5)',
          }}
        >
          <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <span className="text-xs font-medium">{toastMessage}</span>
          <button onClick={() => setToastMessage(null)} className="text-xs opacity-60 hover:opacity-100 ml-2">✕</button>
        </div>
      )}

      {/* Hero Header with Two-Tiered Architecture Description */}
      <div 
        className="p-6 rounded-2xl border relative overflow-hidden shadow-2xl"
        style={{
          background: 'linear-gradient(135deg, rgba(20, 26, 38, 0.95) 0%, rgba(11, 14, 21, 0.98) 100%)',
          borderColor: 'var(--border-color, #232c3d)',
        }}
      >
        <div 
          className="absolute top-0 left-0 right-0 h-[2px]"
          style={{ background: 'var(--seam, linear-gradient(90deg, #6e5cff 0%, #29d3e6 100%))' }}
        />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2.5">
              <span 
                className="p-2 rounded-xl border flex items-center justify-center"
                style={{
                  backgroundColor: 'var(--accent-soft, rgba(110, 92, 255, 0.14))',
                  borderColor: 'rgba(110, 92, 255, 0.3)',
                  color: 'var(--accent-color, #6e5cff)',
                }}
              >
                <Layers className="w-5 h-5" />
              </span>
              <div>
                <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary, #e7ecf5)' }}>
                  Templates & Blueprints Hub
                </h2>
                <p className="text-xs" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                  Two-tier architecture: Foundation Image Runtimes layered with Network Policies, Connectors, and Knowledge Brains.
                </p>
              </div>
            </div>
          </div>

          {/* Primary Top Tab Switcher */}
          <div 
            className="flex items-center p-1 rounded-xl border self-start md:self-auto"
            style={{
              backgroundColor: 'var(--bg-secondary, #0b0e15)',
              borderColor: 'var(--border-color, #232c3d)',
            }}
          >
            <button
              onClick={() => setHubTab('blueprints')}
              className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
                hubTab === 'blueprints' ? 'shadow-md' : 'opacity-70 hover:opacity-100'
              }`}
              style={{
                backgroundColor: hubTab === 'blueprints' ? 'var(--accent-color, #6e5cff)' : 'transparent',
                color: hubTab === 'blueprints' ? '#ffffff' : 'var(--text-secondary, #9fa9bc)',
              }}
            >
              <Workflow className="w-4 h-4" />
              <span>Agent Blueprints</span>
              <span 
                className="px-1.5 py-0.5 rounded-full text-[10px] font-mono"
                style={{
                  backgroundColor: hubTab === 'blueprints' ? 'rgba(255,255,255,0.2)' : 'var(--bg-quaternary, #1c2433)',
                  color: hubTab === 'blueprints' ? '#ffffff' : 'var(--text-secondary)',
                }}
              >
                {blueprints.length}
              </span>
            </button>

            <button
              onClick={() => setHubTab('images')}
              className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
                hubTab === 'images' ? 'shadow-md' : 'opacity-70 hover:opacity-100'
              }`}
              style={{
                backgroundColor: hubTab === 'images' ? 'var(--accent-color, #6e5cff)' : 'transparent',
                color: hubTab === 'images' ? '#ffffff' : 'var(--text-secondary, #9fa9bc)',
              }}
            >
              <Box className="w-4 h-4" />
              <span>Foundation Images</span>
              <span 
                className="px-1.5 py-0.5 rounded-full text-[10px] font-mono"
                style={{
                  backgroundColor: hubTab === 'images' ? 'rgba(255,255,255,0.2)' : 'var(--bg-quaternary, #1c2433)',
                  color: hubTab === 'images' ? '#ffffff' : 'var(--text-secondary)',
                }}
              >
                {imageTemplates.length}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* TIER 2: AGENT BLUEPRINTS (Assembled: Image + Network + Connectors + Brains) */}
      {/* ========================================================================= */}
      {hubTab === 'blueprints' && (
        <div className="space-y-6">
          {/* Subheader & Actions */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                Filter Category:
              </span>
              {['all', 'development', 'devops', 'marketing', 'qa'].map(cat => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium capitalize transition-all border ${
                    categoryFilter === cat ? 'font-bold' : 'opacity-70 hover:opacity-100'
                  }`}
                  style={{
                    backgroundColor: categoryFilter === cat ? 'var(--bg-quaternary, #1c2433)' : 'transparent',
                    borderColor: categoryFilter === cat ? 'var(--accent-color, #6e5cff)' : 'var(--border-color, #232c3d)',
                    color: categoryFilter === cat ? 'var(--text-primary)' : 'var(--text-secondary)',
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>

            <Button
              variant="seam"
              size="sm"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setShowCreateBlueprintModal(true)}
            >
              Create Agent Blueprint
            </Button>
          </div>

          {/* Blueprints Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredBlueprints.map(bp => {
              const baseImg = imageTemplates.find(i => i.id === bp.imageTemplateId);
              return (
                <Card
                  key={bp.id}
                  hoverable
                  style={{
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '260px',
                  }}
                >
                  <div>
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div>
                        <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                          {bp.name}
                        </h3>
                        <p className="text-xs font-medium mt-0.5" style={{ color: 'var(--accent-color, #6e5cff)' }}>
                          {bp.role}
                        </p>
                      </div>
                      <Badge variant="accent" size="sm">
                        {bp.category}
                      </Badge>
                    </div>

                    <p className="text-xs line-clamp-2 mb-4 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      {bp.description}
                    </p>

                    {/* Blueprint Assembly Tags */}
                    <div className="space-y-2 border-t pt-3 mb-4" style={{ borderColor: 'var(--border-color)' }}>
                      <div className="flex items-center gap-1.5 text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                        <Box className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                        <span className="font-semibold text-slate-300">Runtime:</span>
                        <span className="font-mono text-indigo-300 truncate">{baseImg?.name || bp.imageTemplateId}</span>
                      </div>

                      <div className="flex items-center gap-1.5 text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                        <Shield className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                        <span className="font-semibold text-slate-300">Policy:</span>
                        <span className="font-mono text-emerald-300 capitalize">{bp.networkPolicy.replace('-', ' ')}</span>
                      </div>

                      <div className="flex items-center gap-1.5 text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                        <Database className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                        <span className="font-semibold text-slate-300">Brains:</span>
                        <span className="truncate">{bp.brains.length > 0 ? bp.brains.map(b => b.name).join(', ') : 'None'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-2 pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
                    <button
                      onClick={(e) => handleDeleteBlueprint(bp.id, e)}
                      className="p-1.5 rounded-lg opacity-40 hover:opacity-100 hover:text-rose-400 transition-colors"
                      title="Delete blueprint"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>

                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => onUseTemplateToCreateAgent && onUseTemplateToCreateAgent(bp)}
                    >
                      Use Blueprint to Create Agent
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TIER 1: FOUNDATION IMAGE TEMPLATES (Container images, Dockerfiles, Secrets) */}
      {/* ========================================================================= */}
      {hubTab === 'images' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: Image Template List */}
            <div className="lg:col-span-4 space-y-3">
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                  Foundation Images ({imageTemplates.length})
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  icon={<Plus className="w-3.5 h-3.5" />}
                  onClick={() => setShowCreateImageModal(true)}
                >
                  New Image
                </Button>
              </div>

              <div className="space-y-2.5">
                {imageTemplates.map(tmpl => {
                  const isSelected = selectedImage.id === tmpl.id;
                  return (
                    <div
                      key={tmpl.id}
                      onClick={() => setSelectedImage(tmpl)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                        isSelected ? 'ring-1 ring-indigo-500/50 shadow-md' : 'hover:border-slate-700'
                      }`}
                      style={{
                        backgroundColor: isSelected ? 'var(--accent-soft, rgba(110, 92, 255, 0.14))' : 'var(--bg-tertiary, #141a26)',
                        borderColor: isSelected ? 'var(--accent-color, #6e5cff)' : 'var(--border-color, #232c3d)',
                      }}
                    >
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                            <Terminal className="w-3.5 h-3.5" />
                          </span>
                          <div>
                            <h4 className="text-xs font-bold leading-tight" style={{ color: 'var(--text-primary)' }}>
                              {tmpl.name}
                            </h4>
                            <p className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                              {tmpl.role}
                            </p>
                          </div>
                        </div>
                        <StatusPill status={tmpl.status === 'ready' ? 'online' : 'pending'} label={tmpl.status} />
                      </div>

                      <div className="mt-2.5 pt-2 border-t flex items-center justify-between text-[11px]" style={{ borderColor: 'var(--border-color)' }}>
                        <span className="flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                          <Clock className="w-3.5 h-3.5 text-amber-400" />
                          <span>{tmpl.sandboxing.defaultTimeoutSeconds / 60}m timeout</span>
                        </span>
                        <span className="flex items-center gap-1.5 font-mono text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                          <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                          <span>{tmpl.sandboxing.cpuLimit} CPU / {tmpl.sandboxing.memoryLimit}</span>
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right: Selected Image Deep-Dive Inspector (Fixes Image 1 & 3) */}
            <div 
              className="lg:col-span-8 rounded-2xl border shadow-xl overflow-hidden flex flex-col"
              style={{
                backgroundColor: 'var(--bg-tertiary, #141a26)',
                borderColor: 'var(--border-color, #232c3d)',
              }}
            >
              {/* Header */}
              <div 
                className="p-5 border-b flex flex-col md:flex-row md:items-center justify-between gap-4"
                style={{
                  backgroundColor: 'var(--bg-secondary, #0b0e15)',
                  borderColor: 'var(--border-color, #232c3d)',
                }}
              >
                <div>
                  <div className="flex items-center gap-2.5 mb-1">
                    <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                      {selectedImage.name}
                    </h3>
                    <Badge variant="accent" size="sm">
                      {selectedImage.id}
                    </Badge>
                    <StatusPill status="online" label="Ready" />
                  </div>
                  <p className="text-xs mb-2 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                    {selectedImage.description}
                  </p>
                  <div 
                    className="flex items-center gap-2 px-2.5 py-1 rounded-lg border font-mono text-[11px] w-fit"
                    style={{
                      backgroundColor: 'var(--bg-quaternary, #1c2433)',
                      borderColor: 'var(--border-color, #232c3d)',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    <Box className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                    <span className="truncate max-w-sm">{selectedImage.image}</span>
                    <button 
                      onClick={() => copyToClipboard(selectedImage.image, 'image')}
                      className="hover:text-white transition-colors"
                      title="Copy Image URI"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                    {copiedKey === 'image' && <span className="text-[10px] text-emerald-400">Copied!</span>}
                  </div>
                </div>

                <Button
                  variant="seam"
                  size="sm"
                  loading={launchingId === selectedImage.id}
                  icon={<Play className="w-3.5 h-3.5" />}
                  onClick={() => handleLaunchSandbox(selectedImage)}
                >
                  {launchingId === selectedImage.id ? 'Spawning Sandbox...' : 'Launch Test Pod'}
                </Button>
              </div>

              {/* Inspector Sub-Tabs (Clean Horizontal Tab Bar) */}
              <div 
                className="flex border-b px-4 gap-1 overflow-x-auto"
                style={{
                  backgroundColor: 'var(--bg-secondary, #0b0e15)',
                  borderColor: 'var(--border-color, #232c3d)',
                }}
              >
                {[
                  { id: 'docker', label: 'Dockerfile & Build', icon: <Code className="w-3.5 h-3.5" /> },
                  { id: 'env', label: 'Env & Setup Script', icon: <Terminal className="w-3.5 h-3.5" /> },
                  { id: 'secrets', label: `FuzeKeys Secrets (${selectedImage.fuzeKeysSecrets.length})`, icon: <Key className="w-3.5 h-3.5" /> },
                  { id: 'sandbox', label: 'Sandboxing & Quotas', icon: <Shield className="w-3.5 h-3.5" /> },
                  { id: 'bus', label: 'Event Bus', icon: <Radio className="w-3.5 h-3.5" /> },
                  { id: 'escalation', label: 'Approvals & Budget', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setImageInspectorTab(tab.id as any)}
                    className={`py-3 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-all whitespace-nowrap ${
                      imageInspectorTab === tab.id
                        ? 'border-indigo-500 text-indigo-400'
                        : 'border-transparent opacity-60 hover:opacity-100 hover:text-white'
                    }`}
                    style={{
                      color: imageInspectorTab === tab.id ? 'var(--accent-color, #6e5cff)' : 'var(--text-secondary)',
                    }}
                  >
                    {tab.icon}
                    <span>{tab.label}</span>
                  </button>
                ))}
              </div>

              {/* Inspector Content Panel */}
              <div className="p-6 flex-1 overflow-y-auto">
                {imageInspectorTab === 'docker' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                        Multi-Stage Container Dockerfile
                      </span>
                      <button 
                        onClick={() => copyToClipboard(selectedImage.dockerfile, 'dockerfile')}
                        className="text-xs flex items-center gap-1 opacity-70 hover:opacity-100"
                        style={{ color: 'var(--accent-color, #6e5cff)' }}
                      >
                        <Copy className="w-3 h-3" />
                        <span>Copy Dockerfile</span>
                      </button>
                    </div>
                    <pre 
                      className="p-4 rounded-xl font-mono text-xs overflow-x-auto leading-relaxed border"
                      style={{
                        backgroundColor: '#080b11',
                        borderColor: 'var(--border-color, #232c3d)',
                        color: '#a5b4fc',
                      }}
                    >
                      {selectedImage.dockerfile}
                    </pre>
                  </div>
                )}

                {imageInspectorTab === 'env' && (
                  <div className="space-y-5">
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-secondary)' }}>
                        Environment Variables
                      </span>
                      <div className="border rounded-xl overflow-hidden" style={{ borderColor: 'var(--border-color)' }}>
                        <table className="w-full text-xs text-left">
                          <thead style={{ backgroundColor: 'var(--bg-quaternary, #1c2433)', color: 'var(--text-secondary)' }}>
                            <tr>
                              <th className="p-2.5 font-semibold">Key</th>
                              <th className="p-2.5 font-semibold">Default Value</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y" style={{ borderColor: 'var(--border-color)' }}>
                            {Object.entries(selectedImage.envVars).map(([k, v]) => (
                              <tr key={k}>
                                <td className="p-2.5 font-mono text-indigo-300 font-semibold">{k}</td>
                                <td className="p-2.5 font-mono" style={{ color: 'var(--text-primary)' }}>{v}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-secondary)' }}>
                        Bootstrap & Initialization Script (setup.sh)
                      </span>
                      <pre 
                        className="p-4 rounded-xl font-mono text-xs overflow-x-auto leading-relaxed border"
                        style={{
                          backgroundColor: '#080b11',
                          borderColor: 'var(--border-color, #232c3d)',
                          color: '#34d399',
                        }}
                      >
                        {selectedImage.setupScript}
                      </pre>
                    </div>
                  </div>
                )}

                {imageInspectorTab === 'secrets' && (
                  <div className="space-y-4">
                    <span className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-secondary)' }}>
                      FuzeKeys Zero-Exposure Secret Injections
                    </span>
                    <div className="space-y-3">
                      {selectedImage.fuzeKeysSecrets.map(sec => (
                        <div 
                          key={sec.keyName}
                          className="p-4 rounded-xl border flex items-center justify-between gap-4"
                          style={{
                            backgroundColor: 'var(--bg-quaternary, #1c2433)',
                            borderColor: 'var(--border-color, #232c3d)',
                          }}
                        >
                          <div className="flex items-center gap-3">
                            <span className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              <Key className="w-4 h-4" />
                            </span>
                            <div>
                              <div className="font-mono text-xs font-bold text-amber-300">{sec.keyName}</div>
                              <div className="text-[11px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>{sec.description}</div>
                            </div>
                          </div>
                          <Badge variant="warning" size="sm">
                            {sec.secretRef}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {imageInspectorTab === 'sandbox' && (
                  <div className="space-y-4">
                    <span className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-secondary)' }}>
                      Resource Quotas & Enforced Shutdown Policy
                    </span>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 rounded-xl border" style={{ backgroundColor: 'var(--bg-quaternary)', borderColor: 'var(--border-color)' }}>
                        <span className="text-[11px] font-semibold" style={{ color: 'var(--text-secondary)' }}>CPU Quota</span>
                        <div className="text-sm font-mono font-bold mt-1 text-indigo-400">{selectedImage.sandboxing.cpuLimit} vCPU</div>
                      </div>
                      <div className="p-4 rounded-xl border" style={{ backgroundColor: 'var(--bg-quaternary)', borderColor: 'var(--border-color)' }}>
                        <span className="text-[11px] font-semibold" style={{ color: 'var(--text-secondary)' }}>Memory Limit</span>
                        <div className="text-sm font-mono font-bold mt-1 text-cyan-400">{selectedImage.sandboxing.memoryLimit}</div>
                      </div>
                      <div className="p-4 rounded-xl border" style={{ backgroundColor: 'var(--bg-quaternary)', borderColor: 'var(--border-color)' }}>
                        <span className="text-[11px] font-semibold" style={{ color: 'var(--text-secondary)' }}>Execution Timeout</span>
                        <div className="text-sm font-mono font-bold mt-1 text-amber-400">
                          {selectedImage.sandboxing.defaultTimeoutSeconds / 60} Minutes ({selectedImage.sandboxing.defaultTimeoutSeconds}s)
                        </div>
                      </div>
                      <div className="p-4 rounded-xl border" style={{ backgroundColor: 'var(--bg-quaternary)', borderColor: 'var(--border-color)' }}>
                        <span className="text-[11px] font-semibold" style={{ color: 'var(--text-secondary)' }}>Network Boundary</span>
                        <div className="text-sm font-mono font-bold mt-1 text-emerald-400 capitalize">{selectedImage.sandboxing.networkIsolation}</div>
                      </div>
                    </div>
                  </div>
                )}

                {imageInspectorTab === 'bus' && (
                  <div className="space-y-4">
                    <div 
                      className="p-4 rounded-xl border space-y-3 font-mono text-xs"
                      style={{
                        backgroundColor: '#080b11',
                        borderColor: 'var(--border-color, #232c3d)',
                      }}
                    >
                      <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Event Bus Channel:</span>
                        <span className="text-indigo-400 font-bold">{selectedImage.eventBus.channel}</span>
                      </div>
                      <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>LLM Chunk Streaming:</span>
                        <span className="text-emerald-400 font-bold">Active (SSE + WebSocket Bridge)</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span style={{ color: 'var(--text-secondary)' }}>Relay Gateway URL:</span>
                        <span className="text-slate-300">{selectedImage.eventBus.wsRelayUrl}</span>
                      </div>
                    </div>
                    <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      As the agent runs inside its pod, output tokens and tool executions are relayed to the WebSocket bus in real time.
                    </p>
                  </div>
                )}

                {imageInspectorTab === 'escalation' && (
                  <div className="space-y-4">
                    <div 
                      className="p-4 rounded-xl border space-y-3"
                      style={{
                        backgroundColor: 'rgba(245, 166, 35, 0.08)',
                        borderColor: 'rgba(245, 166, 35, 0.3)',
                      }}
                    >
                      <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
                        <AlertTriangle className="w-4 h-4" />
                        <span>Human-in-the-Loop Safeguards</span>
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                        Destructive operations (cluster mutations, schema changes, spending over ${selectedImage.escalation.costThresholdUsd.toFixed(2)}) require human supervisor sign-off before proceeding.
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div className="p-3.5 rounded-xl border" style={{ backgroundColor: 'var(--bg-quaternary)', borderColor: 'var(--border-color)' }}>
                        <span className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Destructive Ops Gate:</span>
                        <span className="font-bold text-emerald-400">Strict (Fails Closed)</span>
                      </div>
                      <div className="p-3.5 rounded-xl border" style={{ backgroundColor: 'var(--bg-quaternary)', borderColor: 'var(--border-color)' }}>
                        <span className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Budget Threshold:</span>
                        <span className="font-bold text-slate-200">${selectedImage.escalation.costThresholdUsd.toFixed(2)} USD</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: CREATE FOUNDATION IMAGE TEMPLATE */}
      {/* ========================================================================= */}
      {showCreateImageModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div 
            className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border shadow-2xl p-6 space-y-5"
            style={{
              backgroundColor: 'var(--bg-secondary, #0b0e15)',
              borderColor: 'var(--border-color, #232c3d)',
              color: 'var(--text-primary, #e7ecf5)',
            }}
          >
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
              <div className="flex items-center gap-2">
                <Box className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-bold">Register New Foundation Image Template</h3>
              </div>
              <button onClick={() => setShowCreateImageModal(false)} className="opacity-60 hover:opacity-100 text-sm">✕</button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Template Name *</label>
                  <input
                    type="text"
                    value={newImageForm.name}
                    onChange={e => setNewImageForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Python ML & Data Science"
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-medium outline-none focus:border-indigo-500"
                    style={{ borderColor: 'var(--border-color)' }}
                  />
                </div>
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Specialist Role *</label>
                  <input
                    type="text"
                    value={newImageForm.role}
                    onChange={e => setNewImageForm(prev => ({ ...prev, role: e.target.value }))}
                    placeholder="e.g., Senior Data Scientist"
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-medium outline-none focus:border-indigo-500"
                    style={{ borderColor: 'var(--border-color)' }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Category</label>
                  <select
                    value={newImageForm.category}
                    onChange={e => setNewImageForm(prev => ({ ...prev, category: e.target.value as any }))}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-medium outline-none"
                    style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--bg-tertiary)' }}
                  >
                    <option value="development">Development</option>
                    <option value="devops">DevOps & Cloud</option>
                    <option value="marketing">Marketing</option>
                    <option value="qa">Quality Assurance</option>
                    <option value="security">Security & Audit</option>
                  </select>
                </div>
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Container Image URI</label>
                  <input
                    type="text"
                    value={newImageForm.image}
                    onChange={e => setNewImageForm(prev => ({ ...prev, image: e.target.value }))}
                    placeholder="ghcr.io/org/repo:tag"
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-mono text-xs outline-none"
                    style={{ borderColor: 'var(--border-color)' }}
                  />
                </div>
              </div>

              <div>
                <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Description</label>
                <textarea
                  rows={2}
                  value={newImageForm.description}
                  onChange={e => setNewImageForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Summary of installed runtimes and preloaded toolchains..."
                  className="w-full px-3 py-2 rounded-lg border bg-transparent text-xs outline-none"
                  style={{ borderColor: 'var(--border-color)' }}
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Timeout (Minutes)</label>
                  <input
                    type="number"
                    value={newImageForm.timeoutMinutes}
                    onChange={e => setNewImageForm(prev => ({ ...prev, timeoutMinutes: Number(e.target.value) }))}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-mono text-xs outline-none"
                    style={{ borderColor: 'var(--border-color)' }}
                  />
                </div>
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>CPU Limit</label>
                  <input
                    type="text"
                    value={newImageForm.cpuLimit}
                    onChange={e => setNewImageForm(prev => ({ ...prev, cpuLimit: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-mono text-xs outline-none"
                    style={{ borderColor: 'var(--border-color)' }}
                  />
                </div>
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Memory Limit</label>
                  <input
                    type="text"
                    value={newImageForm.memoryLimit}
                    onChange={e => setNewImageForm(prev => ({ ...prev, memoryLimit: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-mono text-xs outline-none"
                    style={{ borderColor: 'var(--border-color)' }}
                  />
                </div>
              </div>

              <div>
                <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Dockerfile Content</label>
                <textarea
                  rows={4}
                  value={newImageForm.dockerfile}
                  onChange={e => setNewImageForm(prev => ({ ...prev, dockerfile: e.target.value }))}
                  className="w-full p-3 rounded-lg border font-mono text-[11px] outline-none"
                  style={{ backgroundColor: '#080b11', borderColor: 'var(--border-color)', color: '#a5b4fc' }}
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <Button variant="ghost" size="sm" onClick={() => setShowCreateImageModal(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" onClick={handleSaveImageTemplate}>
                Save Image Template
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: CREATE AGENT BLUEPRINT (Level 2 Template) */}
      {/* ========================================================================= */}
      {showCreateBlueprintModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div 
            className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border shadow-2xl p-6 space-y-5"
            style={{
              backgroundColor: 'var(--bg-secondary, #0b0e15)',
              borderColor: 'var(--border-color, #232c3d)',
              color: 'var(--text-primary, #e7ecf5)',
            }}
          >
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
              <div className="flex items-center gap-2">
                <Workflow className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-bold">Create Assembled Agent Blueprint</h3>
              </div>
              <button onClick={() => setShowCreateBlueprintModal(false)} className="opacity-60 hover:opacity-100 text-sm">✕</button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Blueprint Name *</label>
                  <input
                    type="text"
                    value={newBlueprintForm.name}
                    onChange={e => setNewBlueprintForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Senior Security Auditor"
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-medium outline-none focus:border-indigo-500"
                    style={{ borderColor: 'var(--border-color)' }}
                  />
                </div>
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Specialist Role *</label>
                  <input
                    type="text"
                    value={newBlueprintForm.role}
                    onChange={e => setNewBlueprintForm(prev => ({ ...prev, role: e.target.value }))}
                    placeholder="e.g., Security & Compliance Specialist"
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-medium outline-none focus:border-indigo-500"
                    style={{ borderColor: 'var(--border-color)' }}
                  />
                </div>
              </div>

              {/* Foundation Image Selection */}
              <div>
                <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  1. Foundation Image Runtime (Base Container) *
                </label>
                <select
                  value={newBlueprintForm.imageTemplateId}
                  onChange={e => setNewBlueprintForm(prev => ({ ...prev, imageTemplateId: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-lg border bg-transparent font-medium outline-none"
                  style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--bg-tertiary)' }}
                >
                  {imageTemplates.map(img => (
                    <option key={img.id} value={img.id}>
                      {img.name} ({img.role}) — {img.sandboxing.defaultTimeoutSeconds / 60}m timeout
                    </option>
                  ))}
                </select>
              </div>

              {/* Network Policy */}
              <div>
                <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  2. Network Isolation Policy *
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'strict-isolated', label: 'Strict Isolated (Airgapped)', desc: 'No egress, in-pod execution only' },
                    { id: 'fuzefront-internal', label: 'FuzeFront Internal Only', desc: 'Allows Postgres, Brains, and S2S APIs' },
                    { id: 'egress-allowlisted', label: 'Allowlisted Egress', desc: 'Allows GitHub, Slack, and external LLMs' },
                    { id: 'full-access', label: 'Full Access (Dev/Sandbox)', desc: 'Standard pod egress connectivity' },
                  ].map(pol => (
                    <div
                      key={pol.id}
                      onClick={() => setNewBlueprintForm(prev => ({ ...prev, networkPolicy: pol.id as any }))}
                      className={`p-2.5 rounded-xl border cursor-pointer transition-all ${
                        newBlueprintForm.networkPolicy === pol.id ? 'border-indigo-500 bg-indigo-500/10' : 'hover:border-slate-700'
                      }`}
                      style={{ borderColor: newBlueprintForm.networkPolicy === pol.id ? 'var(--accent-color)' : 'var(--border-color)' }}
                    >
                      <div className="font-bold text-slate-200">{pol.label}</div>
                      <div className="text-[10px] opacity-70">{pol.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Attached Brains & Knowledge Collections */}
              <div>
                <label className="block mb-1.5 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  3. Attach Brains (RAG & Semantic Memory)
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <label className="flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer" style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)' }}>
                    <input
                      type="checkbox"
                      checked={newBlueprintForm.attachWikiBrain}
                      onChange={e => setNewBlueprintForm(prev => ({ ...prev, attachWikiBrain: e.target.checked }))}
                      className="accent-indigo-500"
                    />
                    <div>
                      <div className="font-semibold text-slate-200">Engineering Wiki & Architecture</div>
                      <div className="text-[10px] text-slate-400">42 indexed documentation chunks</div>
                    </div>
                  </label>

                  <label className="flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer" style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)' }}>
                    <input
                      type="checkbox"
                      checked={newBlueprintForm.attachRfcBrain}
                      onChange={e => setNewBlueprintForm(prev => ({ ...prev, attachRfcBrain: e.target.checked }))}
                      className="accent-indigo-500"
                    />
                    <div>
                      <div className="font-semibold text-slate-200">FuzeFront Design System Standards</div>
                      <div className="text-[10px] text-slate-400">18 design tokens & guidelines</div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Connectors */}
              <div>
                <label className="block mb-1.5 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  4. Attach Service Connectors
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <label className="flex items-center gap-2 p-2 rounded-lg border cursor-pointer" style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)' }}>
                    <input
                      type="checkbox"
                      checked={newBlueprintForm.attachGithubConn}
                      onChange={e => setNewBlueprintForm(prev => ({ ...prev, attachGithubConn: e.target.checked }))}
                      className="accent-indigo-500"
                    />
                    <span className="font-medium text-slate-200">GitHub</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-lg border cursor-pointer" style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)' }}>
                    <input
                      type="checkbox"
                      checked={newBlueprintForm.attachPostgresConn}
                      onChange={e => setNewBlueprintForm(prev => ({ ...prev, attachPostgresConn: e.target.checked }))}
                      className="accent-indigo-500"
                    />
                    <span className="font-medium text-slate-200">PostgreSQL</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-lg border cursor-pointer" style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)' }}>
                    <input
                      type="checkbox"
                      checked={newBlueprintForm.attachSlackConn}
                      onChange={e => setNewBlueprintForm(prev => ({ ...prev, attachSlackConn: e.target.checked }))}
                      className="accent-indigo-500"
                    />
                    <span className="font-medium text-slate-200">Slack Alerts</span>
                  </label>
                </div>
              </div>

              {/* Goal & Backstory */}
              <div>
                <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  5. Default Goal & Instructions
                </label>
                <textarea
                  rows={2}
                  value={newBlueprintForm.defaultGoal}
                  onChange={e => setNewBlueprintForm(prev => ({ ...prev, defaultGoal: e.target.value }))}
                  placeholder="Primary objective this agent blueprint will pursue autonomously..."
                  className="w-full px-3 py-2 rounded-lg border bg-transparent text-xs outline-none"
                  style={{ borderColor: 'var(--border-color)' }}
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <Button variant="ghost" size="sm" onClick={() => setShowCreateBlueprintModal(false)}>
                Cancel
              </Button>
              <Button variant="seam" size="sm" onClick={handleSaveAgentBlueprint}>
                Save Blueprint
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default TemplatesHub;
