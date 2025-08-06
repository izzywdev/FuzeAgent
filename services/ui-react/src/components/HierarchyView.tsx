import React, { useCallback, useMemo } from 'react'
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  ConnectionMode,
  MarkerType,
  Position,
} from '@xyflow/react'
import type { Node, Edge, Connection } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { FiUsers, FiCpu, FiHome } from 'react-icons/fi'
import type { Organization, Team, Agent } from '../types'

interface HierarchyViewProps {
  organizations: Organization[]
  teams: Team[]
  agents: Agent[]
  currentOrganization: Organization | null
  onSelectOrganization?: (org: Organization) => void
  onSelectTeam?: (team: Team) => void
}

const nodeTypes = {
  organization: ({ data }: { data: any }) => (
    <div 
      className={`px-4 py-3 shadow-lg rounded-lg border-2 cursor-pointer transition-all hover:shadow-xl ${
        data.isSelected 
          ? 'bg-blue-100 border-blue-500' 
          : 'bg-white border-gray-300 hover:border-blue-400'
      }`}
      onClick={() => data.onSelect && data.onSelect(data.organization)}
    >
      <div className="flex items-center gap-2">
        <FiHome className="text-blue-600 text-lg" />
        <div>
          <div className="font-semibold text-gray-900">{data.label}</div>
          <div className="text-xs text-gray-500">{data.teamsCount} teams</div>
        </div>
      </div>
    </div>
  ),
  team: ({ data }: { data: any }) => (
    <div 
      className={`px-3 py-2 shadow-md rounded-lg border cursor-pointer transition-all hover:shadow-lg ${
        data.isSelected
          ? 'bg-green-100 border-green-500'
          : 'bg-white border-gray-200 hover:border-green-400'
      }`}
      onClick={() => data.onSelect && data.onSelect(data.team)}
    >
      <div className="flex items-center gap-2">
        <FiUsers className="text-green-600" />
        <div>
          <div className="font-medium text-gray-900 text-sm">{data.label}</div>
          <div className="text-xs text-gray-500">{data.agentsCount} agents</div>
        </div>
      </div>
    </div>
  ),
  agent: ({ data }: { data: any }) => (
    <div className="px-2 py-1 shadow-sm rounded border bg-white border-gray-200 hover:shadow-md transition-all">
      <div className="flex items-center gap-1">
        <FiCpu className="text-purple-600 text-sm" />
        <div>
          <div className="font-medium text-gray-900 text-xs">{data.label}</div>
          <div className="text-xs text-gray-500">{data.type}</div>
        </div>
      </div>
    </div>
  ),
}

const HierarchyView: React.FC<HierarchyViewProps> = ({
  organizations,
  teams,
  agents,
  currentOrganization,
  onSelectOrganization,
  onSelectTeam,
}) => {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const nodes: Node[] = []
    const edges: Edge[] = []
    
    let yOffset = 0
    const levelHeight = 200
    const nodeSpacing = 250
    
    // Add organization nodes
    organizations.forEach((org, orgIndex) => {
      const orgTeams = teams.filter(team => team.organization_id === org.id)
      // Count agents for this organization (unused but kept for future use)
      // const agentCount = agents.filter(agent => 
      //   orgTeams.some(team => team.id === agent.team_id)
      // ).length
      
      nodes.push({
        id: `org-${org.id}`,
        type: 'organization',
        position: { x: orgIndex * nodeSpacing, y: yOffset },
        data: {
          label: org.name,
          organization: org,
          teamsCount: orgTeams.length,
          isSelected: currentOrganization?.id === org.id,
          onSelect: onSelectOrganization,
        },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
      })
      
      // Add team nodes for this organization
      orgTeams.forEach((team, teamIndex) => {
        const teamAgents = agents.filter(agent => agent.team_id === team.id)
        const teamYOffset = yOffset + levelHeight
        const teamXOffset = orgIndex * nodeSpacing + (teamIndex - orgTeams.length / 2) * 150
        
        nodes.push({
          id: `team-${team.id}`,
          type: 'team',
          position: { x: teamXOffset, y: teamYOffset },
          data: {
            label: team.name,
            team: team,
            agentsCount: teamAgents.length,
            isSelected: false, // Could track selected team
            onSelect: onSelectTeam,
          },
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
        })
        
        // Add edge from organization to team
        edges.push({
          id: `org-${org.id}-team-${team.id}`,
          source: `org-${org.id}`,
          target: `team-${team.id}`,
          type: 'smoothstep',
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#6366f1',
          },
          style: { stroke: '#6366f1', strokeWidth: 2 },
        })
        
        // Add agent nodes for this team
        teamAgents.forEach((agent, agentIndex) => {
          const agentYOffset = teamYOffset + levelHeight
          const agentXOffset = teamXOffset + (agentIndex - teamAgents.length / 2) * 100
          
          nodes.push({
            id: `agent-${agent.id}`,
            type: 'agent',
            position: { x: agentXOffset, y: agentYOffset },
            data: {
              label: agent.name,
              agent: agent,
              type: agent.type,
            },
            targetPosition: Position.Top,
          })
          
          // Add edge from team to agent
          edges.push({
            id: `team-${team.id}-agent-${agent.id}`,
            source: `team-${team.id}`,
            target: `agent-${agent.id}`,
            type: 'smoothstep',
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: '#10b981',
            },
            style: { stroke: '#10b981', strokeWidth: 1 },
          })
        })
      })
    })
    
    return { nodes, edges }
  }, [organizations, teams, agents, currentOrganization, onSelectOrganization, onSelectTeam])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  // Update nodes when data changes
  React.useEffect(() => {
    setNodes(initialNodes)
    setEdges(initialEdges)
  }, [initialNodes, initialEdges, setNodes, setEdges])

  if (organizations.length === 0) {
    return (
      <div className="h-96 flex items-center justify-center bg-gray-50 rounded-lg">
        <div className="text-center">
          <FiHome className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Organizations</h3>
          <p className="text-gray-600">Create an organization to view the hierarchy</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-4">
      <div className="mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <FiHome />
          Organization Hierarchy
        </h2>
        <p className="text-gray-600 text-sm mt-1">
          Interactive view of organizations, teams, and agents
        </p>
      </div>
      
      <div style={{ height: '600px' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          connectionMode={ConnectionMode.Loose}
          fitView
          fitViewOptions={{
            padding: 0.1,
            includeHiddenNodes: false,
          }}
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
      
      <div className="mt-4 flex gap-4 text-sm">
        <div className="flex items-center gap-2">
          <FiHome className="text-blue-600" />
          <span>Organizations</span>
        </div>
        <div className="flex items-center gap-2">
          <FiUsers className="text-green-600" />
          <span>Teams</span>
        </div>
        <div className="flex items-center gap-2">
          <FiCpu className="text-purple-600" />
          <span>Agents</span>
        </div>
      </div>
    </div>
  )
}

export default HierarchyView