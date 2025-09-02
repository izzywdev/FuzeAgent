import { useState } from 'react'
import { useApiService } from '../hooks/useApiService'
import { FiPlay, FiCopy, FiChevronDown, FiChevronRight } from 'react-icons/fi'
import { CopyToClipboard } from 'react-copy-to-clipboard'
import CodeBlock from './CodeBlock'

interface ApiEndpoint {
  id: string
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  path: string
  title: string
  description: string
  parameters?: {
    name: string
    type: string
    required: boolean
    description: string
    default?: any
  }[]
  requestBody?: {
    type: string
    properties: Record<string, any>
    example: any
  }
  responses: {
    status: number
    description: string
    example: any
  }[]
}

const apiEndpoints: ApiEndpoint[] = [
  {
    id: 'list-organizations',
    method: 'GET',
    path: '/organizations',
    title: 'List Organizations',
    description: 'Retrieve all organizations',
    responses: [
      {
        status: 200,
        description: 'Success',
        example: [
          {
            id: "org_123",
            name: "ACME Corporation",
            description: "Main development organization",
            created_at: "2024-01-15T10:30:00Z"
          }
        ]
      }
    ]
  },
  {
    id: 'create-organization',
    method: 'POST',
    path: '/organizations',
    title: 'Create Organization',
    description: 'Create a new organization',
    requestBody: {
      type: 'object',
      properties: {
        name: { type: 'string', required: true },
        description: { type: 'string', required: false }
      },
      example: {
        name: "New Organization",
        description: "Organization description"
      }
    },
    responses: [
      {
        status: 201,
        description: 'Created',
        example: {
          id: "org_124",
          name: "New Organization", 
          description: "Organization description",
          created_at: "2024-01-15T11:00:00Z"
        }
      }
    ]
  },
  {
    id: 'list-agents',
    method: 'GET',
    path: '/agents',
    title: 'List Agents',
    description: 'Retrieve agents, optionally filtered by team',
    parameters: [
      {
        name: 'team_id',
        type: 'string',
        required: false,
        description: 'Filter agents by team ID'
      }
    ],
    responses: [
      {
        status: 200,
        description: 'Success',
        example: [
          {
            id: "agent_789",
            name: "React Developer",
            role: "Senior Frontend Developer",
            type: "developer",
            status: "active",
            team_id: "team_456",
            config: {
              model: "claude-sonnet-4-20250514",
              skills: ["react", "typescript", "tailwind"],
              tools: ["code_generation", "code_review"]
            },
            created_at: "2024-01-15T11:15:00Z"
          }
        ]
      }
    ]
  },
  {
    id: 'create-agent-from-template',
    method: 'POST',
    path: '/agents/from-template',
    title: 'Create Agent from Template',
    description: 'Deploy a new agent using a pre-built template',
    requestBody: {
      type: 'object',
      properties: {
        template_id: { type: 'string', required: true },
        name: { type: 'string', required: true },
        team_id: { type: 'string', required: true },
        overrides: { type: 'object', required: false }
      },
      example: {
        template_id: "react_developer",
        name: "Frontend Dev 1",
        team_id: "team_456",
        overrides: {
          skills: ["react", "typescript", "next.js"],
          model: "claude-sonnet-4-20250514"
        }
      }
    },
    responses: [
      {
        status: 201,
        description: 'Agent created',
        example: {
          id: "agent_890",
          name: "Frontend Dev 1",
          role: "React Developer",
          type: "developer",
          status: "active",
          team_id: "team_456"
        }
      }
    ]
  }
]

export default function ApiPlayground() {
  const [selectedEndpoint, setSelectedEndpoint] = useState<string>(apiEndpoints[0].id)
  // const [requestData, setRequestData] = useState<string>('')
  const [response, setResponse] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['request']))

  const currentEndpoint = apiEndpoints.find(ep => ep.id === selectedEndpoint)!

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(section)) {
      newExpanded.delete(section)
    } else {
      newExpanded.add(section)
    }
    setExpandedSections(newExpanded)
  }

  const executeRequest = async () => {
    setLoading(true)
    setResponse(null)

    try {
      // Simulate API request
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Make actual API request
      const response = await fetch(`${currentEndpoint.path}`, {
        method: currentEndpoint.method,
        headers: {
          'Content-Type': 'application/json'
        },
        body: currentEndpoint.method !== 'GET' && currentEndpoint.requestBody 
          ? JSON.stringify(currentEndpoint.requestBody.example) 
          : undefined
      })
      
      const responseData = await response.json()
      setResponse({
        status: response.status,
        data: responseData
      })
    } catch (error) {
      setResponse({
        status: 500,
        error: 'Request failed',
        message: error instanceof Error ? error.message : 'Unknown error'
      })
    } finally {
      setLoading(false)
    }
  }

  const generateCurlCommand = () => {
    const baseUrl = 'http://localhost:8006'
    let curl = `curl -X ${currentEndpoint.method} "${baseUrl}${currentEndpoint.path}"`
    
    if (currentEndpoint.method !== 'GET' && currentEndpoint.requestBody) {
      curl += ` \\\n  -H "Content-Type: application/json" \\\n  -d '${JSON.stringify(currentEndpoint.requestBody.example, null, 2)}'`
    }
    
    return curl
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">API Playground</h1>
        <p className="text-gray-600">
          Explore and test FuzeAgent API endpoints interactively. Select an endpoint, 
          customize the request, and see live responses.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Endpoint Selection */}
        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">API Endpoints</h2>
          {apiEndpoints.map((endpoint) => (
            <button
              key={endpoint.id}
              onClick={() => setSelectedEndpoint(endpoint.id)}
              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                selectedEndpoint === endpoint.id
                  ? 'border-blue-500 bg-blue-50 text-blue-900'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={`px-2 py-1 text-xs font-medium rounded ${
                  endpoint.method === 'GET' ? 'bg-green-100 text-green-800' :
                  endpoint.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                  endpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                  endpoint.method === 'PATCH' ? 'bg-purple-100 text-purple-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {endpoint.method}
                </span>
                <span className="font-mono text-sm">{endpoint.path}</span>
              </div>
              <div className="text-sm text-gray-600">{endpoint.title}</div>
            </button>
          ))}
        </div>

        {/* Request Configuration */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white border border-gray-200 rounded-lg">
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 text-sm font-medium rounded ${
                  currentEndpoint.method === 'GET' ? 'bg-green-100 text-green-800' :
                  currentEndpoint.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                  currentEndpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                  currentEndpoint.method === 'PATCH' ? 'bg-purple-100 text-purple-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {currentEndpoint.method}
                </span>
                <span className="font-mono text-lg">{currentEndpoint.path}</span>
              </div>
              <p className="text-gray-600 mt-2">{currentEndpoint.description}</p>
            </div>

            {/* Parameters */}
            {currentEndpoint.parameters && (
              <div className="p-4 border-b border-gray-200">
                <button
                  onClick={() => toggleSection('parameters')}
                  className="flex items-center gap-2 text-lg font-semibold text-gray-900 mb-3"
                >
                  {expandedSections.has('parameters') ? <FiChevronDown /> : <FiChevronRight />}
                  Parameters
                </button>
                {expandedSections.has('parameters') && (
                  <div className="space-y-3">
                    {currentEndpoint.parameters.map((param) => (
                      <div key={param.name} className="flex items-start gap-4 p-3 bg-gray-50 rounded">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-medium">{param.name}</span>
                            <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">
                              {param.type}
                            </span>
                            {param.required && (
                              <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                                required
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mt-1">{param.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Request Body */}
            {currentEndpoint.requestBody && (
              <div className="p-4 border-b border-gray-200">
                <button
                  onClick={() => toggleSection('request')}
                  className="flex items-center gap-2 text-lg font-semibold text-gray-900 mb-3"
                >
                  {expandedSections.has('request') ? <FiChevronDown /> : <FiChevronRight />}
                  Request Body
                </button>
                {expandedSections.has('request') && (
                  <div>
                    <CodeBlock language="json">
                      {JSON.stringify(currentEndpoint.requestBody.example, null, 2)}
                    </CodeBlock>
                  </div>
                )}
              </div>
            )}

            {/* Try It Out */}
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Try it out</h3>
                <button
                  onClick={executeRequest}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <FiPlay className="w-4 h-4" />
                  {loading ? 'Executing...' : 'Execute'}
                </button>
              </div>

              {/* cURL Command */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">cURL Command</label>
                  <CopyToClipboard text={generateCurlCommand()}>
                    <button className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
                      <FiCopy className="w-3 h-3" />
                      Copy
                    </button>
                  </CopyToClipboard>
                </div>
                <CodeBlock language="bash" showLineNumbers={false}>
                  {generateCurlCommand()}
                </CodeBlock>
              </div>

              {/* Response */}
              {(response || loading) && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Response</h4>
                  {loading ? (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 text-gray-600">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                        Executing request...
                      </div>
                    </div>
                  ) : response ? (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${
                          response.status >= 200 && response.status < 300
                            ? 'bg-green-100 text-green-800'
                            : response.status >= 400
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {response.status}
                        </span>
                        <span className="text-sm text-gray-600">
                          {response.status >= 200 && response.status < 300 ? 'Success' :
                           response.status >= 400 ? 'Error' : 'Info'}
                        </span>
                      </div>
                      <CodeBlock language="json">
                        {JSON.stringify(response.data || response, null, 2)}
                      </CodeBlock>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}