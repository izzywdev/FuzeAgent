import React, { useState, useEffect } from 'react';
import { Button, Badge, Card, StatusPill, Input } from '../design-system';
import { apiClient } from '../services/api';
import {
  Rocket,
  Terminal,
  ExternalLink,
  CheckCircle2,
  Clock,
  Plus,
  Search,
  RefreshCw,
  Cpu,
  Layers,
} from 'lucide-react';

export interface AppBuildSession {
  buildSessionId: string;
  name: string;
  brief: string;
  organizationId: string;
  status: 'queued' | 'building' | 'testing' | 'deploying' | 'deployed' | 'failed' | 'cancelled';
  createdAt: string;
  deployedUrl?: string;
  slug?: string;
}

const SAMPLE_BUILDS: AppBuildSession[] = [
  {
    buildSessionId: 'bld_7a2f190',
    name: 'Inventory Operations Portal',
    brief: 'Real-time warehouse inventory tracker with stock level heatmaps, barcode scanner input, and automated PO generation.',
    organizationId: 'org_enterprise_core',
    status: 'deployed',
    createdAt: '10 minutes ago',
    deployedUrl: 'https://app.fuzefront.com/apps/inventory-operations-portal/',
    slug: 'inventory-operations-portal',
  },
  {
    buildSessionId: 'bld_91f3e82',
    name: 'Customer Health Analytics',
    brief: 'Multi-tenant customer churn prediction dashboard with ML feature importance cards and SLA breach alerts.',
    organizationId: 'org_enterprise_core',
    status: 'building',
    createdAt: 'Just now',
    slug: 'customer-health-analytics',
  },
];

export const AppBuildsStudio: React.FC = () => {
  const [builds, setBuilds] = useState<AppBuildSession[]>(SAMPLE_BUILDS);
  const [selectedBuildId, setSelectedBuildId] = useState<string>(SAMPLE_BUILDS[0].buildSessionId);
  const [searchQuery, setSearchQuery] = useState('');
  const [logs, setLogs] = useState<string[]>([
    '[1/6] 🚀 Initiating autonomous app build for "Inventory Operations Portal"',
    '[2/6] 📋 Brief: Real-time warehouse inventory tracker with stock level heatmaps...',
    '[3/6] 🔒 Tenant isolation: Organization ID org_enterprise_core',
    '[4/6] 📦 Scaffolding Vite + React 19 MFE template with FuzeFront DS tokens',
    '[5/6] 🛡️ Spawning ephemeral build runner pod in "fuzeagent" namespace',
    '   ✓ Pod spawned: sbx-runner-node20-7a2f190 (status: Running)',
    '[6/6] ✅ Compilation, linting, and Module Federation chunk generation passed (0 errors)',
    '🌐 Registering microfrontend with FuzeFront portal registry...',
    '   ✓ Manifest: slug="inventory-operations-portal", orgId="org_enterprise_core"',
    '🎉 Application deployment complete and active at https://app.fuzefront.com/apps/inventory-operations-portal/',
  ]);
  const [isLaunchingModal, setIsLaunchingModal] = useState(false);
  const [appName, setAppName] = useState('');
  const [appBrief, setAppBrief] = useState('');
  const [isDeploying, setIsDeploying] = useState(false);

  const selectedBuild = builds.find(b => b.buildSessionId === selectedBuildId) || builds[0];

  // Refresh builds from API
  const refreshBuilds = async () => {
    try {
      const remote = await apiClient.listAppBuilds();
      if (Array.isArray(remote) && remote.length > 0) {
        setBuilds(remote);
      }
    } catch {
      // fallback
    }
  };

  useEffect(() => {
    refreshBuilds();
    const interval = setInterval(refreshBuilds, 5000);
    return () => clearInterval(interval);
  }, []);

  // Poll logs for selected session
  useEffect(() => {
    let timer: any = null;
    const fetchLogs = async () => {
      if (!selectedBuildId) return;
      try {
        const liveLogs = await apiClient.getAppBuildLogs(selectedBuildId);
        if (liveLogs && liveLogs.length > 0) {
          setLogs(liveLogs);
        }
      } catch {
        // keep current
      }
    };
    fetchLogs();
    timer = setInterval(fetchLogs, 2500);
    return () => clearInterval(timer);
  }, [selectedBuildId]);

  const handleLaunchBuild = async () => {
    if (!appName.trim() || !appBrief.trim() || isDeploying) return;
    setIsDeploying(true);

    try {
      const res = await apiClient.launchAppBuild({
        name: appName,
        brief: appBrief,
        organizationId: 'org_enterprise_core',
        context: 'autonomous-mfe',
      });

      const newSession: AppBuildSession = res || {
        buildSessionId: `bld_${Date.now()}`,
        name: appName,
        brief: appBrief,
        organizationId: 'org_enterprise_core',
        status: 'building',
        createdAt: 'Just now',
        slug: appName.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      };

      setBuilds(prev => [newSession, ...prev]);
      setSelectedBuildId(newSession.buildSessionId);
      setIsLaunchingModal(false);
      setAppName('');
      setAppBrief('');

      // Add starter logs
      setLogs([
        `[1/6] 🚀 Initiating autonomous build for "${newSession.name}"`,
        `[2/6] 📋 Brief: ${newSession.brief.slice(0, 100)}...`,
        `[3/6] 🔒 Tenant isolation: Organization ID ${newSession.organizationId}`,
        `[4/6] 📦 Scaffolding Vite + React 19 MFE template with FuzeFront DS tokens`,
        `[5/6] 🛡️ Spawning ephemeral build runner pod in "fuzeagent" namespace...`,
      ]);
    } catch (err) {
      console.error('Build launch error:', err);
    } finally {
      setIsDeploying(false);
    }
  };

  const filteredBuilds = builds.filter(b =>
    b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    b.brief.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--bg-primary, #0f131c)',
        color: 'var(--text-primary, #e7ecf5)',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 20px',
          borderBottom: '1px solid var(--border-color, #232c3d)',
          backgroundColor: 'var(--bg-secondary, #0b0e15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: 'var(--radius-md, 6px)',
              background: 'var(--seam, linear-gradient(90deg, #6e5cff 0%, #29d3e6 100%))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
            }}
          >
            <Rocket size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>App Builds & Autonomous Deployer</h2>
              <Badge variant="seam" size="sm">Kubernetes Runner</Badge>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary, #9fa9bc)', marginTop: '2px' }}>
              FuzeFront "Build your application" execution engine with sandbox pod compilation
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Button size="sm" variant="ghost" onClick={refreshBuilds} icon={<RefreshCw size={13} />}>
            Refresh
          </Button>
          <Button size="sm" variant="seam" onClick={() => setIsLaunchingModal(true)} icon={<Plus size={14} />}>
            Build New Application
          </Button>
        </div>
      </div>

      {/* Main Grid */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Side: Sessions List */}
        <div
          style={{
            width: '360px',
            borderRight: '1px solid var(--border-color, #232c3d)',
            backgroundColor: 'var(--bg-tertiary, #141a26)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ padding: '12px', borderBottom: '1px solid var(--border-color, #232c3d)' }}>
            <Input
              placeholder="Search builds by name or brief..."
              icon={<Search size={14} />}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
            {filteredBuilds.map(b => {
              const isSelected = b.buildSessionId === selectedBuildId;
              const isDone = b.status === 'deployed';
              const isBuilding = b.status === 'building' || b.status === 'queued';
              return (
                <div
                  key={b.buildSessionId}
                  onClick={() => setSelectedBuildId(b.buildSessionId)}
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-md, 6px)',
                    cursor: 'pointer',
                    backgroundColor: isSelected ? 'var(--bg-quaternary, #1c2433)' : 'transparent',
                    border: isSelected
                      ? '1px solid var(--accent-color, #6e5cff)'
                      : '1px solid var(--border-color, #232c3d)',
                    marginBottom: '8px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#ffffff' }}>
                      {b.name}
                    </span>
                    <StatusPill
                      status={isDone ? 'online' : isBuilding ? 'running' : 'failed'}
                      label={b.status}
                    />
                  </div>

                  <p
                    style={{
                      fontSize: '11px',
                      color: 'var(--text-secondary, #9fa9bc)',
                      margin: '0 0 8px 0',
                      lineHeight: '1.4',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {b.brief}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-tertiary, #66718a)' }}>
                    <span>ID: {b.buildSessionId}</span>
                    <span>{b.createdAt}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Side: Build Inspector & Terminal */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '24px' }}>
          {selectedBuild ? (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '16px' }}>
              {/* Build Meta Banner */}
              <Card seamAccent style={{ padding: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <h1 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>{selectedBuild.name}</h1>
                      <StatusPill
                        status={selectedBuild.status === 'deployed' ? 'online' : selectedBuild.status === 'failed' ? 'failed' : 'running'}
                        label={selectedBuild.status.toUpperCase()}
                      />
                    </div>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary, #9fa9bc)', margin: '0 0 12px 0' }}>
                      {selectedBuild.brief}
                    </p>
                    <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: 'var(--text-tertiary, #66718a)' }}>
                      <span>Session ID: <strong style={{ color: 'var(--text-primary)' }}>{selectedBuild.buildSessionId}</strong></span>
                      <span>Tenant Org: <strong style={{ color: 'var(--text-primary)' }}>{selectedBuild.organizationId}</strong></span>
                      <span>Slug: <strong style={{ color: 'var(--accent-2, #29d3e6)' }}>{selectedBuild.slug || 'autonomous-app'}</strong></span>
                    </div>
                  </div>

                  {selectedBuild.status === 'deployed' && (
                    <a
                      href={selectedBuild.deployedUrl || `https://app.fuzefront.com/apps/${selectedBuild.slug}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ textDecoration: 'none' }}
                    >
                      <Button variant="seam" icon={<ExternalLink size={14} />}>
                        Open in FuzeFront
                      </Button>
                    </a>
                  )}
                </div>

                {/* Pipeline Step Progress */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '8px', marginTop: '20px' }}>
                  {[
                    { label: '1. Brief Spec', icon: <Clock size={12} />, done: true },
                    { label: '2. Scaffold MFE', icon: <Layers size={12} />, done: true },
                    { label: '3. Pod Sandbox', icon: <Cpu size={12} />, done: true },
                    { label: '4. Compilation', icon: <Terminal size={12} />, done: true },
                    { label: '5. K8s Deploy', icon: <Rocket size={12} />, done: selectedBuild.status === 'deployed' },
                    { label: '6. Portal Live', icon: <CheckCircle2 size={12} />, done: selectedBuild.status === 'deployed' },
                  ].map((step, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '8px 10px',
                        backgroundColor: step.done ? 'rgba(41, 211, 230, 0.1)' : 'var(--bg-tertiary, #141a26)',
                        border: step.done ? '1px solid var(--accent-2, #29d3e6)' : '1px solid var(--border-color, #232c3d)',
                        borderRadius: 'var(--radius-sm, 4px)',
                        fontSize: '11px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        color: step.done ? '#ffffff' : 'var(--text-tertiary, #66718a)',
                      }}
                    >
                      {step.icon}
                      <span style={{ fontWeight: 500 }}>{step.label}</span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Streaming Terminal Output */}
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  backgroundColor: '#05070a',
                  borderRadius: 'var(--radius-lg, 8px)',
                  border: '1px solid var(--border-color, #232c3d)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    padding: '8px 14px',
                    backgroundColor: '#090d14',
                    borderBottom: '1px solid var(--border-color, #232c3d)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                    <Terminal size={14} color="var(--accent-2, #29d3e6)" />
                    <span>Build & Pod Execution Console: {selectedBuild.buildSessionId}</span>
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--text-tertiary, #66718a)' }}>
                    {logs.length} lines logged
                  </span>
                </div>

                <div
                  style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '14px',
                    fontFamily: 'var(--font-mono, monospace)',
                    fontSize: '12px',
                    lineHeight: '1.6',
                    color: '#9fa9bc',
                  }}
                >
                  {logs.map((line, idx) => (
                    <div
                      key={idx}
                      style={{
                        color: line.includes('✅') || line.includes('🎉')
                          ? 'var(--success-color, #34d399)'
                          : line.includes('🚀') || line.includes('✓')
                          ? 'var(--accent-2, #29d3e6)'
                          : line.includes('Error') || line.includes('failed')
                          ? 'var(--danger-color, #f87171)'
                          : '#c7d2e5',
                      }}
                    >
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', marginTop: '100px', color: 'var(--text-secondary)' }}>
              Select a build session from the left to view logs
            </div>
          )}
        </div>
      </div>

      {/* Modal: Build New Application */}
      {isLaunchingModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
          }}
        >
          <Card seamAccent style={{ width: '540px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>Launch Autonomous App Build</h3>
            <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary, #9fa9bc)' }}>
              Provide the requirements for your application. FuzeAgent will spin up an isolated Kubernetes sandbox pod, compile the React 19 MFE bundle, and register it directly into the FuzeFront portal.
            </p>

            <div>
              <label style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary, #66718a)', fontWeight: 600 }}>
                Application Name
              </label>
              <Input
                placeholder="e.g. Mendys Logistics Dashboard"
                value={appName}
                onChange={e => setAppName(e.target.value)}
                style={{ marginTop: '4px' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary, #66718a)', fontWeight: 600 }}>
                Application Brief & Specifications
              </label>
              <textarea
                rows={5}
                placeholder="Describe features, views, data requirements, and user interactions..."
                value={appBrief}
                onChange={e => setAppBrief(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: '4px',
                  backgroundColor: 'var(--bg-quaternary, #1c2433)',
                  border: '1px solid var(--border-color, #232c3d)',
                  borderRadius: 'var(--radius-md, 6px)',
                  color: 'var(--text-primary, #e7ecf5)',
                  padding: '8px 12px',
                  fontSize: '13px',
                  fontFamily: 'inherit',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px' }}>
              <Button variant="ghost" onClick={() => setIsLaunchingModal(false)} disabled={isDeploying}>
                Cancel
              </Button>
              <Button
                variant="seam"
                onClick={handleLaunchBuild}
                disabled={isDeploying || !appName.trim() || !appBrief.trim()}
                icon={<Rocket size={14} />}
              >
                {isDeploying ? 'Spawning Sandbox Runner...' : 'Launch Build Pod'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
