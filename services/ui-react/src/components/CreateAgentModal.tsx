import React, { useState, useCallback, useMemo } from 'react';
import { FiX, FiShield } from 'react-icons/fi';
import { Box, Workflow, Layers } from 'lucide-react';
import type { AgentTemplate, CreateAgentFromTemplate, CreateCustomAgent, Team } from '../types';
import { templateRegistry } from '../services/templateRegistry';
import type { AgentBlueprintTemplate } from '../services/templateRegistry';
import { Button, Badge } from '../design-system';

interface CreateAgentModalProps {
  templates: AgentTemplate[];
  currentTeam: Team | null;
  onClose: () => void;
  onSubmit: (data: CreateAgentFromTemplate | CreateCustomAgent) => Promise<void>;
  initialBlueprint?: AgentBlueprintTemplate | null;
  onOpenTemplatesHub?: () => void;
}

export const CreateAgentModal: React.FC<CreateAgentModalProps> = React.memo(({
  templates: apiTemplates,
  currentTeam,
  onClose,
  onSubmit,
  initialBlueprint,
  onOpenTemplatesHub,
}) => {
  const [activeTab, setActiveTab] = useState<'blueprint' | 'custom'>('blueprint');

  // Load registered blueprints
  const registeredBlueprints = useMemo(() => {
    const list = [...templateRegistry.getAgentTemplates()];
    if (apiTemplates && apiTemplates.length > 0) {
      apiTemplates.forEach(t => {
        if (!list.some(b => b.id === t.template_id)) {
          list.push({
            id: t.template_id,
            name: t.name,
            role: 'Specialist',
            category: (t.category as any) || 'development',
            description: t.description || t.default_goal,
            imageTemplateId: 'python-dev',
            networkPolicy: 'fuzefront-internal',
            connectors: [],
            brains: [],
            defaultGoal: t.default_goal,
            defaultBackstory: t.default_backstory,
            systemPrompt: t.system_prompt,
            tools: t.tools || [],
            skills: t.skills || [],
            defaultModel: t.default_model || 'claude-sonnet-4-20250514',
            defaultTemperature: t.default_temperature || 0.2,
          });
        }
      });
    }
    return list;
  }, [apiTemplates]);

  const registeredImages = useMemo(() => templateRegistry.getImageTemplates(), []);

  // Selected Blueprint state
  const [selectedBlueprintId, setSelectedBlueprintId] = useState<string>(
    initialBlueprint?.id || registeredBlueprints[0]?.id || ''
  );
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const selectedBlueprint = useMemo(() => {
    return registeredBlueprints.find(b => b.id === selectedBlueprintId) || registeredBlueprints[0] || null;
  }, [registeredBlueprints, selectedBlueprintId]);

  // Form overrides
  const [blueprintForm, setBlueprintForm] = useState({
    name: selectedBlueprint ? `${selectedBlueprint.name}` : '',
    goal: selectedBlueprint?.defaultGoal || '',
    backstory: selectedBlueprint?.defaultBackstory || '',
    temperature: selectedBlueprint?.defaultTemperature || 0.2,
  });

  // Custom Form state
  const [selectedImageId, setSelectedImageId] = useState<string>(registeredImages[0]?.id || 'python-dev');
  const [customForm, setCustomForm] = useState({
    name: '',
    role: '',
    type: 'developer',
    goal: '',
    backstory: '',
    networkPolicy: 'fuzefront-internal',
    temperature: 0.2,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelectBlueprint = useCallback((bp: AgentBlueprintTemplate) => {
    setSelectedBlueprintId(bp.id);
    setBlueprintForm({
      name: bp.name,
      goal: bp.defaultGoal,
      backstory: bp.defaultBackstory,
      temperature: bp.defaultTemperature,
    });
  }, []);

  const handleBlueprintSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBlueprint) {
      setError('Please select an agent blueprint template');
      return;
    }
    if (!currentTeam) {
      setError('Please select a team in the top header before creating an agent');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data: CreateAgentFromTemplate = {
        template_id: selectedBlueprint.id,
        overrides: {
          team_id: currentTeam.id,
          name: blueprintForm.name || selectedBlueprint.name,
          role: selectedBlueprint.role,
          goal: blueprintForm.goal || selectedBlueprint.defaultGoal,
          backstory: blueprintForm.backstory || selectedBlueprint.defaultBackstory,
          temperature: blueprintForm.temperature,
          image_template_id: selectedBlueprint.imageTemplateId,
          network_policy: selectedBlueprint.networkPolicy,
          brains: selectedBlueprint.brains.map(b => b.name),
          connectors: selectedBlueprint.connectors.map(c => c.name),
        },
      };
      await onSubmit(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to create agent from blueprint');
    } finally {
      setLoading(false);
    }
  }, [selectedBlueprint, blueprintForm, currentTeam, onSubmit]);

  const handleCustomSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentTeam) {
      setError('Please select a team first');
      return;
    }
    if (!customForm.name.trim()) {
      setError('Please provide an agent name');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data: CreateCustomAgent = {
        team_id: currentTeam.id,
        name: customForm.name,
        role: customForm.role || 'Autonomous Specialist',
        type: customForm.type,
        config: {
          goal: customForm.goal || `Perform ${customForm.role || 'assigned'} tasks in sandbox`,
          tools: ['code_generation', 'code_review', 'vector_search'],
          model: 'claude-sonnet-4-20250514',
          temperature: customForm.temperature,
        },
      };
      await onSubmit(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to create custom agent');
    } finally {
      setLoading(false);
    }
  }, [customForm, currentTeam, onSubmit]);

  const filteredBlueprints = useMemo(() => {
    return registeredBlueprints.filter(bp => {
      const matchesCat = categoryFilter === 'all' || bp.category === categoryFilter;
      const matchesQuery = !searchQuery || 
        bp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        bp.role.toLowerCase().includes(searchQuery.toLowerCase()) ||
        bp.description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCat && matchesQuery;
    });
  }, [registeredBlueprints, categoryFilter, searchQuery]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
      <div 
        className="w-full max-w-4xl max-h-[92vh] overflow-hidden rounded-2xl border shadow-2xl flex flex-col"
        style={{
          backgroundColor: 'var(--bg-secondary, #0b0e15)',
          borderColor: 'var(--border-color, #232c3d)',
          color: 'var(--text-primary, #e7ecf5)',
        }}
      >
        {/* Modal Header */}
        <div 
          className="p-5 border-b flex items-center justify-between"
          style={{
            backgroundColor: 'var(--bg-secondary, #0b0e15)',
            borderColor: 'var(--border-color, #232c3d)',
          }}
        >
          <div className="flex items-center gap-3">
            <span 
              className="p-2 rounded-xl border flex items-center justify-center text-indigo-400"
              style={{
                backgroundColor: 'var(--accent-soft, rgba(110, 92, 255, 0.14))',
                borderColor: 'rgba(110, 92, 255, 0.3)',
              }}
            >
              <Workflow className="w-5 h-5" />
            </span>
            <div>
              <h3 className="text-base font-bold" style={{ color: 'var(--text-primary, #e7ecf5)' }}>
                Deploy New Agent
              </h3>
              <p className="text-xs" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                Select an assembled Agent Blueprint (Image + Policy + Connectors + Brains) or configure a custom agent.
              </p>
            </div>
          </div>

          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg opacity-60 hover:opacity-100 hover:bg-slate-800 transition-colors"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div 
          className="px-6 pt-4 border-b flex items-center justify-between"
          style={{
            backgroundColor: 'var(--bg-tertiary, #141a26)',
            borderColor: 'var(--border-color, #232c3d)',
          }}
        >
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab('blueprint')}
              className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
                activeTab === 'blueprint'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent opacity-60 hover:opacity-100'
              }`}
            >
              <Workflow className="w-3.5 h-3.5" />
              <span>From Agent Blueprint</span>
              <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-indigo-500/20 text-indigo-300 font-mono">
                {registeredBlueprints.length} Available
              </span>
            </button>

            <button
              onClick={() => setActiveTab('custom')}
              className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
                activeTab === 'custom'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent opacity-60 hover:opacity-100'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Custom from Foundation Image</span>
            </button>
          </div>

          {onOpenTemplatesHub && (
            <button
              onClick={() => {
                onClose();
                onOpenTemplatesHub();
              }}
              className="text-xs pb-3 flex items-center gap-1 text-indigo-400 hover:underline"
            >
              <span>Manage & Create Blueprints</span>
              <span>→</span>
            </button>
          )}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => setError(null)} className="text-xs opacity-70 hover:opacity-100">✕</button>
            </div>
          )}

          {/* TAB 1: FROM AGENT BLUEPRINT */}
          {activeTab === 'blueprint' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Blueprint Selector */}
              <div className="lg:col-span-6 space-y-3">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search blueprints by name or role..."
                    className="w-full px-3 py-1.5 rounded-lg border bg-transparent text-xs outline-none focus:border-indigo-500"
                    style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--bg-quaternary)' }}
                  />
                </div>

                <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                  {['all', 'development', 'devops', 'marketing', 'qa'].map(cat => (
                    <button
                      key={cat}
                      onClick={() => setCategoryFilter(cat)}
                      className={`px-2 py-0.5 rounded-lg text-[11px] capitalize border transition-all ${
                        categoryFilter === cat ? 'font-bold' : 'opacity-60 hover:opacity-100'
                      }`}
                      style={{
                        backgroundColor: categoryFilter === cat ? 'var(--bg-quaternary)' : 'transparent',
                        borderColor: categoryFilter === cat ? 'var(--accent-color)' : 'var(--border-color)',
                        color: categoryFilter === cat ? 'var(--text-primary)' : 'var(--text-secondary)',
                      }}
                    >
                      {cat}
                    </button>
                  ))}
                </div>

                <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
                  {filteredBlueprints.length === 0 ? (
                    <div className="p-6 text-center text-xs text-slate-500 border rounded-xl" style={{ borderColor: 'var(--border-color)' }}>
                      No templates match filter. Create one in Templates Hub.
                    </div>
                  ) : (
                    filteredBlueprints.map(bp => {
                      const isSelected = selectedBlueprint?.id === bp.id;
                      return (
                        <div
                          key={bp.id}
                          onClick={() => handleSelectBlueprint(bp)}
                          className={`p-3 rounded-xl border cursor-pointer transition-all ${
                            isSelected ? 'ring-1 ring-indigo-500/50 shadow-md' : 'hover:border-slate-700'
                          }`}
                          style={{
                            backgroundColor: isSelected ? 'var(--accent-soft, rgba(110, 92, 255, 0.14))' : 'var(--bg-tertiary, #141a26)',
                            borderColor: isSelected ? 'var(--accent-color, #6e5cff)' : 'var(--border-color, #232c3d)',
                          }}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <h4 className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>
                                {bp.name}
                              </h4>
                              <p className="text-[11px] font-medium" style={{ color: 'var(--accent-color, #6e5cff)' }}>
                                {bp.role}
                              </p>
                            </div>
                            <Badge variant="accent" size="sm">
                              {bp.category}
                            </Badge>
                          </div>

                          <p className="text-[11px] line-clamp-2 my-2 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                            {bp.description}
                          </p>

                          <div className="flex items-center gap-3 text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                            <span className="flex items-center gap-1">
                              <Box className="w-3 h-3 text-indigo-400" />
                              {bp.imageTemplateName || bp.imageTemplateId}
                            </span>
                            <span className="flex items-center gap-1">
                              <FiShield className="w-3 h-3 text-emerald-400" />
                              {bp.networkPolicy.replace('-', ' ')}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Right Column: Selected Blueprint Form & Deployment Options */}
              <div 
                className="lg:col-span-6 p-4 rounded-xl border flex flex-col justify-between space-y-4"
                style={{
                  backgroundColor: 'var(--bg-tertiary, #141a26)',
                  borderColor: 'var(--border-color, #232c3d)',
                }}
              >
                {selectedBlueprint ? (
                  <form onSubmit={handleBlueprintSubmit} className="space-y-3.5 text-xs">
                    <div>
                      <span className="text-[10px] uppercase font-bold tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                        Selected Blueprint Specifications
                      </span>
                      <div className="p-3 rounded-lg border mt-1 space-y-1.5" style={{ backgroundColor: 'var(--bg-quaternary)', borderColor: 'var(--border-color)' }}>
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-300">Foundation Image:</span>
                          <span className="font-mono text-indigo-300">{selectedBlueprint.imageTemplateName || selectedBlueprint.imageTemplateId}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-300">Network Isolation:</span>
                          <span className="capitalize text-emerald-300">{selectedBlueprint.networkPolicy.replace('-', ' ')}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-300">Attached Brains:</span>
                          <span>{selectedBlueprint.brains.length} Knowledge Collections</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-300">Connectors:</span>
                          <span>{selectedBlueprint.connectors.length > 0 ? selectedBlueprint.connectors.map(c => c.name).join(', ') : 'None'}</span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Agent Instance Name *</label>
                      <input
                        type="text"
                        value={blueprintForm.name}
                        onChange={e => setBlueprintForm(prev => ({ ...prev, name: e.target.value }))}
                        className="w-full px-3 py-2 rounded-lg border bg-transparent font-medium outline-none focus:border-indigo-500"
                        style={{ borderColor: 'var(--border-color)' }}
                        required
                      />
                    </div>

                    <div>
                      <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Primary Goal</label>
                      <textarea
                        rows={2}
                        value={blueprintForm.goal}
                        onChange={e => setBlueprintForm(prev => ({ ...prev, goal: e.target.value }))}
                        className="w-full px-3 py-2 rounded-lg border bg-transparent text-xs outline-none"
                        style={{ borderColor: 'var(--border-color)' }}
                      />
                    </div>

                    <div>
                      <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Target Team Assignment</label>
                      <div className="p-2.5 rounded-lg border flex items-center justify-between" style={{ backgroundColor: 'var(--bg-quaternary)', borderColor: 'var(--border-color)' }}>
                        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                          {currentTeam ? currentTeam.name : 'No team selected (Pick team in header)'}
                        </span>
                        <Badge variant={currentTeam ? 'success' : 'warning'} size="sm">
                          {currentTeam ? currentTeam.team_type : 'Select Team'}
                        </Badge>
                      </div>
                    </div>

                    <div className="pt-2">
                      <Button
                        type="submit"
                        variant="seam"
                        size="md"
                        loading={loading}
                        style={{ width: '100%' }}
                      >
                        Launch Agent from Blueprint
                      </Button>
                    </div>
                  </form>
                ) : (
                  <div className="p-8 text-center text-xs text-slate-500">
                    Select a blueprint on the left to configure launch parameters.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: CUSTOM FROM FOUNDATION IMAGE */}
          {activeTab === 'custom' && (
            <form onSubmit={handleCustomSubmit} className="space-y-4 text-xs max-w-xl mx-auto">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Agent Name *</label>
                  <input
                    type="text"
                    value={customForm.name}
                    onChange={e => setCustomForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Code Reviewer #3"
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-medium outline-none focus:border-indigo-500"
                    style={{ borderColor: 'var(--border-color)' }}
                    required
                  />
                </div>
                <div>
                  <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Role / Specialty</label>
                  <input
                    type="text"
                    value={customForm.role}
                    onChange={e => setCustomForm(prev => ({ ...prev, role: e.target.value }))}
                    placeholder="e.g., Static Analysis Specialist"
                    className="w-full px-3 py-2 rounded-lg border bg-transparent font-medium outline-none focus:border-indigo-500"
                    style={{ borderColor: 'var(--border-color)' }}
                  />
                </div>
              </div>

              <div>
                <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Foundation Container Image</label>
                <select
                  value={selectedImageId}
                  onChange={e => setSelectedImageId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border bg-transparent font-medium outline-none"
                  style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--bg-tertiary)' }}
                >
                  {registeredImages.map(img => (
                    <option key={img.id} value={img.id}>
                      {img.name} ({img.role})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block mb-1 font-semibold" style={{ color: 'var(--text-secondary)' }}>Goal & Autonomous Scope</label>
                <textarea
                  rows={2}
                  value={customForm.goal}
                  onChange={e => setCustomForm(prev => ({ ...prev, goal: e.target.value }))}
                  placeholder="What tasks should this agent execute autonomously?"
                  className="w-full px-3 py-2 rounded-lg border bg-transparent text-xs outline-none"
                  style={{ borderColor: 'var(--border-color)' }}
                />
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  loading={loading}
                  style={{ width: '100%' }}
                >
                  Create & Launch Custom Agent
                </Button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
});
export default CreateAgentModal;