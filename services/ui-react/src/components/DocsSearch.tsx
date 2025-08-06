import { useState, useEffect, useMemo } from 'react'
import Fuse from 'fuse.js'
import { FiSearch, FiBook, FiArrowRight } from 'react-icons/fi'
import { Link } from 'react-router-dom'

interface SearchableContent {
  id: string
  title: string
  content: string
  path: string
  section?: string
  type: 'page' | 'section' | 'api'
}

// Mock search data - in a real app, this would come from your documentation content
const searchableContent: SearchableContent[] = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    content: 'Quick start guide for FuzeAgent AI team orchestration platform. Set up your first agents and teams.',
    path: '/docs/getting-started',
    type: 'page'
  },
  {
    id: 'api-organizations',
    title: 'Organizations API',
    content: 'Create and manage organizations. List, create, update, and delete organizations.',
    path: '/docs/api-reference#organizations',
    section: 'API Reference',
    type: 'api'
  },
  {
    id: 'api-agents',
    title: 'Agents API',
    content: 'Manage AI agents. Create agents from templates, assign tasks, monitor performance.',
    path: '/docs/api-reference#agents',
    section: 'API Reference',
    type: 'api'
  },
  {
    id: 'creating-agents',
    title: 'Creating Agents',
    content: 'Learn how to create and configure AI agents. Agent types, templates, custom configurations.',
    path: '/docs/creating-agents',
    type: 'page'
  },
  {
    id: 'task-management',
    title: 'Task Management',
    content: 'Assign and manage tasks across your AI team. Task distribution, monitoring, and completion.',
    path: '/docs/task-management',
    type: 'page'
  }
]

interface DocsSearchProps {
  query: string
  onQueryChange: (query: string) => void
  className?: string
}

export default function DocsSearch({ query, onQueryChange, className = '' }: DocsSearchProps) {
  const [isOpen, setIsOpen] = useState(false)
  
  // Initialize Fuse.js for fuzzy search
  const fuse = useMemo(() => new Fuse(searchableContent, {
    keys: [
      { name: 'title', weight: 3 },
      { name: 'content', weight: 2 },
      { name: 'section', weight: 1 }
    ],
    threshold: 0.3,
    includeScore: true,
    includeMatches: true
  }), [])

  // Search results
  const searchResults = useMemo(() => {
    if (!query.trim()) return []
    return fuse.search(query).slice(0, 8) // Limit to 8 results
  }, [query, fuse])

  // Close search on escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
        onQueryChange('')
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onQueryChange])

  const handleResultClick = () => {
    setIsOpen(false)
    onQueryChange('')
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'api':
        return '🔌'
      case 'section':
        return '📋'
      default:
        return '📖'
    }
  }

  const highlightMatch = (text: string, matches: readonly any[] = []) => {
    if (!matches.length) return text

    let result: string | React.ReactElement = text
    const match = matches[0]
    
    if (match && match.indices && match.indices.length > 0) {
      const [start, end] = match.indices[0]
      result = (
        <>
          {text.slice(0, start)}
          <mark className="bg-yellow-200 text-yellow-900 px-1 rounded">
            {text.slice(start, end + 1)}
          </mark>
          {text.slice(end + 1)}
        </>
      )
    }

    return result
  }

  return (
    <div className={`relative ${className}`}>
      {/* Search Input */}
      <div className="relative">
        <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
        <input
          type="text"
          placeholder="Search documentation..."
          value={query}
          onChange={(e) => {
            onQueryChange(e.target.value)
            setIsOpen(true)
          }}
          onFocus={() => setIsOpen(true)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
        />
      </div>

      {/* Search Results */}
      {isOpen && query.trim() && (
        <>
          {/* Overlay */}
          <div 
            className="fixed inset-0 z-40 bg-gray-600 bg-opacity-50"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Results Panel */}
          <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-lg shadow-lg border border-gray-200 z-50 max-h-96 overflow-y-auto">
            {searchResults.length > 0 ? (
              <div className="p-2">
                <div className="text-xs text-gray-500 px-3 py-2 border-b border-gray-100">
                  {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} for "{query}"
                </div>
                <div className="space-y-1 mt-2">
                  {searchResults.map((result) => {
                    const item = result.item
                    const titleMatch = result.matches?.find(m => m.key === 'title')
                    const contentMatch = result.matches?.find(m => m.key === 'content')
                    
                    return (
                      <Link
                        key={item.id}
                        to={item.path}
                        onClick={handleResultClick}
                        className="block p-3 rounded-md hover:bg-gray-50 transition-colors group"
                      >
                        <div className="flex items-start gap-3">
                          <span className="text-lg mt-0.5">{getTypeIcon(item.type)}</span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h4 className="text-sm font-medium text-gray-900 truncate">
                                {highlightMatch(item.title, titleMatch?.indices ? [...titleMatch.indices] : [])}
                              </h4>
                              {item.section && (
                                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                                  {item.section}
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                              {highlightMatch(item.content, contentMatch?.indices ? [...contentMatch.indices] : [])}
                            </p>
                          </div>
                          <FiArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 mt-1" />
                        </div>
                      </Link>
                    )
                  })}
                </div>
              </div>
            ) : (
              <div className="p-4 text-center text-gray-500">
                <FiBook className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">No results found for "{query}"</p>
                <p className="text-xs mt-1">Try different keywords or browse our documentation</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}