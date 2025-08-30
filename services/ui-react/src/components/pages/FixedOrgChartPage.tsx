import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useMemo, useRef, useState, useLayoutEffect } from 'react'

// Lazy-load GoJS from CDN to avoid bundler dependency issues
async function loadGoJs(): Promise<any> {
  // Try ESM module first (faster and avoids global)
  try {
    const mod: any = await import(/* @vite-ignore */ 'https://unpkg.com/gojs/release/go-module.js')
    if (mod && (mod as any).Diagram) return mod
  } catch {}
  return new Promise((resolve, reject) => {
    const w = window as any
    if (w.go) return resolve(w.go)
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/gojs/release/go.js'
    script.crossOrigin = 'anonymous'
    script.referrerPolicy = 'no-referrer'
    script.async = true
    script.onload = () => resolve((window as any).go)
    script.onerror = (e) => reject(e)
    document.head.appendChild(script)
  })
}

// Default fallback structure when no API data is available
const defaultOrgStructure = {
  organization: 'No Organization',
  ceo: 'No CEO',
  departments: [
    {
      name: 'No Departments',
      head: 'No Head',
      color: '#6b7280',
      teams: [
        {
          name: 'No Teams',
          lead: 'No Lead',
          members: ['No members found']
        }
      ]
    }
  ]
}

type Org = { id: string; name: string }
type Team = { id: string; organization_id: string; name: string; description?: string; team_type?: string }
type Agent = { id: string; team_id?: string; name: string; type?: string }

export function FixedOrgChartPage() {
  const navigate = useNavigate()
  const [org, setOrg] = useState<Org | null>(null)
  const [teams, setTeams] = useState<Team[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [quickItem, setQuickItem] = useState<{ type: 'org' | 'team' | 'agent'; id?: string } | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const [orgsRes, teamsRes, agentsRes] = await Promise.all([
          fetch('/organizations'),
          fetch('/teams'),
          fetch('/agents'),
        ])
        const orgs: Org[] = await orgsRes.json()
        setOrg(orgs[0] || null)
        setTeams(await teamsRes.json())
        setAgents(await agentsRes.json())
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const orgChart = useMemo(() => {
    if (!org) return defaultOrgStructure
    const grouped: Record<string, Agent[]> = {}
    for (const ag of agents) {
      const key = ag.team_id || 'unassigned'
      grouped[key] = grouped[key] || []
      grouped[key].push(ag)
    }
    
    // Create departments based on team types
    const departmentMap: Record<string, {name: string, color: string, teams: any[]}> = {
      'development': { name: 'Engineering', color: '#2563eb', teams: [] },
      'qa': { name: 'Quality Assurance', color: '#16a34a', teams: [] },
      'devops': { name: 'DevOps', color: '#7c3aed', teams: [] },
      'business': { name: 'Business Operations', color: '#dc2626', teams: [] },
      'design': { name: 'Design', color: '#f59e0b', teams: [] },
      'executive': { name: 'Executive Leadership', color: '#8b5cf6', teams: [] }
    }
    
    // Group teams by type
    for (const team of teams) {
      const dept = departmentMap[team.team_type || 'development'] || departmentMap['development']
      dept.teams.push({
        name: team.name,
        lead: 'Team Lead',
        members: (grouped[team.id] || []).map(a => a.name || 'Agent')
      })
    }
    
    // Convert to array and filter out empty departments
    const departments = Object.values(departmentMap)
      .filter(dept => dept.teams.length > 0)
      .map(dept => ({
        name: dept.name,
        head: 'Department Head',
        color: dept.color,
        teams: dept.teams
      }))
    
    return {
      organization: org.name,
      ceo: 'Organization Leader',
      departments: departments.length > 0 ? departments : defaultOrgStructure.departments
    }
  }, [org, teams, agents])

  const view = orgChart

  // No external graph library – render our own SVG-based chart

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading organization chart…</div>
  }

  return (
    <div style={{minHeight: '100vh', backgroundColor: '#f9fafb'}}>
      {/* Navigation */}
      <nav style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
        <div style={{maxWidth: '80rem', margin: '0 auto', padding: '0 1rem'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '4rem'}}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <Link to="/" style={{display: 'flex', alignItems: 'center', textDecoration: 'none'}}>
                <div style={{
                  width: '2rem', 
                  height: '2rem', 
                  backgroundColor: '#2563eb', 
                  borderRadius: '0.5rem', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  marginRight: '0.75rem'
                }}>
                  <span style={{color: 'white', fontWeight: 'bold'}}>F</span>
                </div>
                <h1 style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#111827'}}>FuzeAgent</h1>
              </Link>
              
              {/* Navigation Links */}
              <div style={{display: 'flex', marginLeft: '1.5rem', gap: '2rem'}}>
                <Link to="/" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
                  Dashboard
                </Link>
                <Link to="/agents" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
                  Agents
                </Link>
                <Link to="/teams" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
                  Teams
                </Link>
                <Link to="/goals" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
                  Goals
                </Link>
                <Link to="/organization-chart" style={{color: '#2563eb', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none', borderBottom: '2px solid #2563eb', paddingBottom: '1rem'}}>
                  Organization Chart
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main style={{maxWidth: '80rem', margin: '0 auto', padding: '1.5rem 1rem'}}>
        {/* Header */}
        <div style={{textAlign: 'center', marginBottom: '2rem'}}>
          <h2 style={{fontSize: '2rem', fontWeight: 'bold', color: '#111827'}}>{view.organization}</h2>
          <p style={{marginTop: '0.5rem', fontSize: '0.875rem', color: '#6b7280'}}>
            AI Team Organizational Structure
          </p>
        </div>

        <OrganizationGraph
          orgName={view.organization}
          teams={teams}
          agents={agents}
          onNodeClick={(node) => {
            if (node.type === 'org') setQuickItem({ type: 'org' })
            if (node.type === 'team') setQuickItem({ type: 'team', id: node.dataId })
            if (node.type === 'agent') setQuickItem({ type: 'agent', id: node.dataId })
          }}
        />

        {/* Organization Stats */}
        <div style={{marginTop: '3rem', backgroundColor: 'white', borderRadius: '1rem', padding: '2rem', border: '1px solid #e5e7eb'}}>
          <h3 style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#111827', marginBottom: '1.5rem', textAlign: 'center'}}>
            Organization Overview
          </h3>
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem'}}>
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>🏢</div>
              <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827'}}>{view.departments.length}</div>
              <div style={{fontSize: '0.875rem', color: '#6b7280'}}>Departments</div>
            </div>
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>👥</div>
              <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827'}}>
                {view.departments.reduce((acc, dept) => acc + dept.teams.length, 0)}
              </div>
              <div style={{fontSize: '0.875rem', color: '#6b7280'}}>Teams</div>
            </div>
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>🤖</div>
              <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827'}}>
                {view.departments.reduce((acc, dept) => 
                  acc + dept.teams.reduce((teamAcc, team) => teamAcc + team.members.length, 0), 0
                )}
              </div>
              <div style={{fontSize: '0.875rem', color: '#6b7280'}}>AI Agents</div>
            </div>
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>⚡</div>
              <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#16a34a'}}>Active</div>
              <div style={{fontSize: '0.875rem', color: '#6b7280'}}>Status</div>
            </div>
          </div>
        </div>

        {quickItem && (
          <IframePreviewModal type={quickItem.type} id={quickItem.id} onClose={() => setQuickItem(null)} />
        )}
      </main>
    </div>
  )
}

function OrganizationGraph({ orgName, teams, agents, onNodeClick }: { orgName: string; teams: Team[]; agents: Agent[]; onNodeClick: (node: { type: 'org'|'team'|'agent'; dataId?: string }) => void }) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [width, setWidth] = useState<number>(1024)
  useLayoutEffect(() => {
    const el = containerRef.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth || 1024)
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    window.addEventListener('resize', measure)
    return () => { ro.disconnect(); window.removeEventListener('resize', measure) }
  }, [])

  const layout = useMemo(() => {
    const orgW = 220, orgH = 80
    const teamW = 200, teamH = 70
    const agentW = 160, agentH = 44
    const vGap = 60, hGap = 24
    const padding = 32
    const countTeams = Math.max(teams.length, 1)
    const segment = Math.max((width - padding * 2) / countTeams, teamW + hGap)

    const orgX = padding + (width - padding * 2) / 2 - orgW / 2
    const orgY = padding

    type NodePos = { id: string; label: string; x: number; y: number; w: number; h: number; color?: string; type: 'org'|'team'|'agent'; dataId?: string }
    const nodes: NodePos[] = [{ id: 'org', label: orgName, x: orgX, y: orgY, w: orgW, h: orgH, type: 'org' }]

    const teamTypeColor: Record<string,string> = { development:'#2563eb', qa:'#16a34a', devops:'#7c3aed', business:'#dc2626', design:'#f59e0b', executive:'#8b5cf6' }
    const teamCenters: Record<string, number> = {}
    teams.forEach((t, i) => {
      const cx = padding + segment * i + segment / 2
      const x = cx - teamW / 2
      const y = orgY + orgH + vGap
      teamCenters[t.id] = cx
      nodes.push({ id: `team-${t.id}`, label: t.name, x, y, w: teamW, h: teamH, type: 'team', color: teamTypeColor[t.team_type || 'development'], dataId: t.id })
    })

    const agentsByTeam: Record<string, Agent[]> = {}
    agents.forEach(a => {
      const key = a.team_id || 'unassigned'
      if (!agentsByTeam[key]) agentsByTeam[key] = []
      agentsByTeam[key].push(a)
    })

    let maxAgentsInRow = 0
    teams.forEach(t => { maxAgentsInRow = Math.max(maxAgentsInRow, (agentsByTeam[t.id] || []).length) })

    teams.forEach(t => {
      const list = agentsByTeam[t.id] || []
      const n = list.length
      if (n === 0) return
      const cx = teamCenters[t.id]
      const totalW = n * agentW + (n - 1) * hGap
      const startX = cx - totalW / 2
      const y = orgY + orgH + vGap + teamH + vGap
      list.forEach((a, idx) => {
        const x = startX + idx * (agentW + hGap)
        nodes.push({ id: `agent-${a.id}`, label: a.name || 'Agent', x, y, w: agentW, h: agentH, type: 'agent', dataId: a.id })
      })
    })

    const svgHeight = padding + orgH + vGap + teamH + (maxAgentsInRow > 0 ? vGap + agentH : 0) + padding

    const links: Array<{ from: NodePos; to: NodePos }> = []
    teams.forEach(t => {
      const teamNode = nodes.find(n => n.id === `team-${t.id}`)
      if (!teamNode) return
      links.push({ from: nodes[0], to: teamNode })
      const list = agentsByTeam[t.id] || []
      list.forEach(a => {
        const agentNode = nodes.find(n => n.id === `agent-${a.id}`)
        if (agentNode) links.push({ from: teamNode, to: agentNode })
      })
    })

    return { nodes, links, width, height: svgHeight, padding }
  }, [width, orgName, teams, agents])

  return (
    <div ref={containerRef} style={{ height: `${layout.height}px`, position: 'relative', border: '1px solid #e5e7eb', borderRadius: '8px', background: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '2rem' }}>
      <svg width={layout.width} height={layout.height} style={{ position: 'absolute', inset: 0 }}>
        {layout.links.map((l, i) => {
          const x1 = l.from.x + l.from.w / 2, y1 = l.from.y + l.from.h
          const x2 = l.to.x + l.to.w / 2, y2 = l.to.y
          const path = `M ${x1} ${y1} C ${x1} ${y1 + 40}, ${x2} ${y2 - 40}, ${x2} ${y2}`
          return <path key={i} d={path} stroke="#cbd5e1" strokeWidth="2" fill="none" />
        })}
      </svg>
      {layout.nodes.map(node => (
        <div
          key={node.id}
          onClick={() => onNodeClick({ type: node.type, dataId: node.dataId })}
          style={{ position: 'absolute', left: node.x, top: node.y, width: node.w, height: node.h, borderRadius: 12, border: node.type==='org' ? '2px solid #6366f1' : '1px solid #e5e7eb', background: node.type==='org' ? '#eef2ff' : '#ffffff', boxShadow: node.type==='org' ? '0 4px 12px rgba(99,102,241,0.15)' : '0 2px 8px rgba(0,0,0,0.06)', padding: node.type==='agent' ? 10 : 14, display: 'flex', flexDirection: 'column', alignItems: node.type==='agent' ? 'flex-start' : 'center', justifyContent: 'center', cursor: 'pointer', transition: 'transform 120ms ease' }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)' }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)' }}
        >
          {node.type === 'team' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, width: '100%' }}>
              <span style={{ width: 10, height: 10, borderRadius: 9999, background: node.color || '#9ca3af' }} />
              <span style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{node.label}</span>
            </div>
          )}
          {node.type === 'org' && (
            <>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#111827' }}>{node.label}</div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>Organization</div>
            </>
          )}
          {node.type === 'team' && (
            <div style={{ fontSize: 11, color: '#6b7280' }}>TEAM</div>
          )}
          {node.type === 'agent' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 24, height: 24, borderRadius: 9999, background: '#e2e8f0', border: '1px solid #cbd5e1' }} />
              <span style={{ fontSize: 12, color: '#374151' }}>{node.label}</span>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

type QuickEditModalProps = {
  type: 'org' | 'team' | 'agent'
  id?: string
  org: Org | null
  teams: Team[]
  agents: Agent[]
  onClose: () => void
  onSaved: (res: { kind: 'org'|'team'|'agent'; item: any }) => void
  onOpenFullPage: () => void
}

function QuickEditModal({ type, id, org, teams, agents, onClose, onSaved, onOpenFullPage }: QuickEditModalProps) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const entity = type === 'org' ? org : type === 'team' ? teams.find(t => t.id === id) : agents.find(a => a.id === id)
  const [form, setForm] = useState<{ name: string; description?: string; team_type?: string; color?: string }>(() => ({
    name: (entity as any)?.name || '',
    description: (entity as any)?.description || '',
    team_type: (entity as any)?.team_type || 'development',
    color: (entity as any)?.color || '#2563eb'
  }))

  const handleSave = async () => {
    setSaving(true); setError('')
    try {
      if (type === 'org' && org) {
        const res = await fetch(`/organizations/${org.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: form.name, description: form.description }) })
        if (res.ok) onSaved({ kind: 'org', item: await res.json() }); else onSaved({ kind: 'org', item: { ...org, name: form.name, description: form.description } })
      } else if (type === 'team' && id) {
        const res = await fetch(`/teams/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: form.name, description: form.description, team_type: form.team_type, color: form.color }) })
        if (res.ok) onSaved({ kind: 'team', item: await res.json() })
      } else if (type === 'agent' && id) {
        const res = await fetch(`/agents/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: form.name }) })
        if (res.ok) onSaved({ kind: 'agent', item: await res.json() })
      }
    } catch (e) {
      setError('Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  if (!entity) return null

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
      <div style={{ width: '560px', maxWidth: '92vw', background: 'white', borderRadius: 12, border: '1px solid #e5e7eb', boxShadow: '0 20px 40px rgba(0,0,0,0.25)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid #eef2f7' }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#111827' }}>{type === 'org' ? 'Edit Organization' : type === 'team' ? 'Edit Team' : 'Edit Agent'}</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={onOpenFullPage} style={{ padding: '6px 10px', fontSize: 12, border: '1px solid #d1d5db', borderRadius: 8, background: 'white', cursor: 'pointer' }}>Open full page</button>
            <button onClick={onClose} style={{ padding: '6px 10px', fontSize: 12, border: '1px solid #d1d5db', borderRadius: 8, background: 'white', cursor: 'pointer' }}>Close</button>
          </div>
        </div>
        <div style={{ padding: 20 }}>
          {error && <div style={{ marginBottom: 12, color: '#dc2626', fontSize: 12 }}>{error}</div>}
          <div style={{ display: 'grid', gap: 12 }}>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: 12, color: '#374151' }}>Name</span>
              <input value={form.name} onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))} style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14 }} />
            </label>
            {(type === 'org' || type === 'team') && (
              <label style={{ display: 'grid', gap: 6 }}>
                <span style={{ fontSize: 12, color: '#374151' }}>Description</span>
                <textarea value={form.description} onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))} rows={3} style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, resize: 'vertical' }} />
              </label>
            )}
            {type === 'team' && (
              <div style={{ display: 'grid', gap: 12, gridTemplateColumns: '1fr 1fr' }}>
                <label style={{ display: 'grid', gap: 6 }}>
                  <span style={{ fontSize: 12, color: '#374151' }}>Team Type</span>
                  <select value={form.team_type} onChange={e => setForm(prev => ({ ...prev, team_type: e.target.value }))} style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14 }}>
                    <option value="development">Development</option>
                    <option value="qa">QA</option>
                    <option value="devops">DevOps</option>
                    <option value="business">Business</option>
                    <option value="design">Design</option>
                    <option value="executive">Executive</option>
                  </select>
                </label>
                <label style={{ display: 'grid', gap: 6 }}>
                  <span style={{ fontSize: 12, color: '#374151' }}>Color</span>
                  <input type="color" value={form.color} onChange={e => setForm(prev => ({ ...prev, color: e.target.value }))} style={{ height: 40, border: '1px solid #d1d5db', borderRadius: 8 }} />
                </label>
              </div>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: 16, borderTop: '1px solid #eef2f7' }}>
          <button onClick={onClose} style={{ padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 8, background: 'white', cursor: 'pointer' }}>Cancel</button>
          <button onClick={handleSave} disabled={saving} style={{ padding: '10px 14px', borderRadius: 8, background: saving ? '#9ca3af' : '#2563eb', color: 'white', border: 'none', cursor: saving ? 'not-allowed' : 'pointer' }}>{saving ? 'Saving…' : 'Save'}</button>
        </div>
      </div>
    </div>
  )
}

function IframePreviewModal({ type, id, onClose }: { type: 'org'|'team'|'agent'; id?: string; onClose: () => void }) {
  const path = type === 'org' ? '/organization/profile' : type === 'team' ? `/teams/${id}` : `/agents/${id}`
  const url = path
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
      <div style={{ width: '90vw', height: '85vh', background: 'white', borderRadius: 12, overflow: 'hidden', boxShadow: '0 25px 50px rgba(0,0,0,0.35)', border: '1px solid #e5e7eb' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: '1px solid #eef2f7', background: '#f9fafb' }}>
          <div style={{ fontSize: 14, color: '#374151' }}>{url}</div>
          <button onClick={onClose} style={{ padding: '6px 10px', fontSize: 12, border: '1px solid #d1d5db', borderRadius: 8, background: 'white', cursor: 'pointer' }}>Close</button>
        </div>
        <iframe src={url} style={{ width: '100%', height: 'calc(85vh - 44px)', border: 'none' }} />
      </div>
    </div>
  )
}