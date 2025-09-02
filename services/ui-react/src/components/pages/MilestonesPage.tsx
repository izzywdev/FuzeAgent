/**
 * Milestones Page Component
 *
 * Comprehensive milestone management page with:
 * - Search and filtering capabilities
 * - Pagination support
 * - CRUD operations
 * - Task assignment management
 * - Progress tracking across all goals
 */

import React, { useState, useEffect } from 'react'
import { useApiService } from '../../hooks/useApiService'
import type { Milestone, Goal, MilestoneDisplay, MilestoneFilters } from '../../types'
import { MilestoneList, MilestoneFormModal } from '../milestones'
import { milestonesToDisplay } from '../milestones/utils'
import type { MilestoneFormData } from '../milestones/types'

export function MilestonesPage(): React.ReactElement {
  // API service
  const apiService = useApiService()

  // State management
  const [milestones, setMilestones] = useState<MilestoneDisplay[]>([])
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [pageSize] = useState(12)
  const [totalItems, setTotalItems] = useState(0)

  // Filters state
  const [filters, setFilters] = useState<MilestoneFilters>({
    sort_by: 'created_at',
    sort_order: 'desc'
  })

  // Modal states
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingMilestone, setEditingMilestone] = useState<Milestone | null>(null)
  const [selectedMilestone, setSelectedMilestone] = useState<MilestoneDisplay | null>(null)

  // Load data on mount and when filters change
  useEffect(() => {
    loadMilestones()
  }, [currentPage, filters])

  // Load goals for filter dropdown
  useEffect(() => {
    loadGoals()
  }, [])

  /**
   * Load milestones with current filters and pagination
   */
  const loadMilestones = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await apiService.getMilestones({
        ...filters,
        page: currentPage,
        page_size: pageSize
      })

      if (response.ok && response.data) {
        const displayMilestones = milestonesToDisplay(response.data.milestones)
        setMilestones(displayMilestones)
        setTotalItems(response.data.total)
        setTotalPages(response.data.total_pages)
      } else {
        setError(`Failed to load milestones: ${response.status}`)
        setMilestones([])
      }
    } catch (err) {
      console.error('Error loading milestones:', err)
      setError('Failed to load milestones. Please try again.')
      setMilestones([])
    } finally {
      setLoading(false)
    }
  }

  /**
   * Load goals for filtering
   */
  const loadGoals = async () => {
    try {
      const response = await apiService.getGoals('1') // Organization ID
      if (response.ok && Array.isArray(response.data)) {
        setGoals(response.data)
      }
    } catch (err) {
      console.error('Error loading goals:', err)
    }
  }

  /**
   * Handle milestone creation
   */
  const handleCreateMilestone = async (data: MilestoneFormData) => {
    try {
      const milestoneData = {
        goal_id: data.goal_id || '',
        title: data.title,
        description: data.description,
        priority: data.priority,
        target_date: data.target_date
      }

      const response = await apiService.createMilestone(milestoneData)
      if (response.ok) {
        await loadMilestones() // Refresh the list
        setShowCreateForm(false)
      } else {
        throw new Error(`Failed to create milestone: ${response.status}`)
      }
    } catch (error) {
      console.error('Error creating milestone:', error)
      throw error // Let the modal handle the error display
    }
  }

  /**
   * Handle milestone editing
   */
  const handleEditMilestone = (milestone: Milestone) => {
    setEditingMilestone(milestone)
  }

  /**
   * Handle milestone update
   */
  const handleUpdateMilestone = async (data: MilestoneFormData) => {
    if (!editingMilestone) return

    try {
      const response = await apiService.updateMilestone(editingMilestone.id, {
        title: data.title,
        description: data.description,
        priority: data.priority,
        target_date: data.target_date
      })

      if (response.ok) {
        await loadMilestones() // Refresh the list
        setEditingMilestone(null)
      } else {
        throw new Error(`Failed to update milestone: ${response.status}`)
      }
    } catch (error) {
      console.error('Error updating milestone:', error)
      throw error
    }
  }

  /**
   * Handle milestone deletion
   */
  const handleDeleteMilestone = async (milestone: Milestone) => {
    try {
      const response = await apiService.deleteMilestone(milestone.id)
      if (response.ok) {
        await loadMilestones() // Refresh the list
      } else {
        throw new Error(`Failed to delete milestone: ${response.status}`)
      }
    } catch (error) {
      console.error('Error deleting milestone:', error)
      // Error already handled by confirmation dialog
    }
  }

  /**
   * Handle milestone task viewing
   */
  const handleViewTasks = (milestone: Milestone) => {
    // Navigate to milestone tasks or open modal
    console.log('View tasks for milestone:', milestone.title)
    setSelectedMilestone(milestone)
  }

  /**
   * Handle task creation for milestone
   */
  const handleCreateTask = (milestone: Milestone) => {
    // Navigate to create task page or open modal
    console.log('Create task for milestone:', milestone.title)
  }

  /**
   * Handle filter changes
   */
  const handleFiltersChange = (newFilters: MilestoneFilters) => {
    setFilters(newFilters)
    setCurrentPage(1) // Reset to first page when filters change
  }

  /**
   * Handle page changes
   */
  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
      {/* Header */}
      <div style={{
        backgroundColor: 'white',
        borderBottom: '1px solid #e5e7eb',
        boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        padding: '1.5rem 0'
      }}>
        <div style={{ maxWidth: '80rem', margin: '0 auto', padding: '0 1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h1 style={{
                fontSize: '2rem',
                fontWeight: 'bold',
                color: '#111827',
                marginBottom: '0.5rem'
              }}>
                Milestones
              </h1>
              <p style={{ color: '#6b7280' }}>
                Track progress and manage milestones across all your goals
              </p>
            </div>

            <button
              onClick={() => setShowCreateForm(true)}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
              }}
            >
              ➕ Create Milestone
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main style={{ maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem' }}>
        {/* Filters Section */}
        <div style={{
          backgroundColor: 'white',
          borderRadius: '0.75rem',
          padding: '1.5rem',
          marginBottom: '2rem',
          boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
        }}>
          <h3 style={{
            fontSize: '1rem',
            fontWeight: '600',
            color: '#111827',
            marginBottom: '1rem'
          }}>
            Filters & Search
          </h3>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem'
          }}>
            {/* Status Filter */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '0.5rem'
              }}>
                Status
              </label>
              <select
                value={filters.status?.[0] || ''}
                onChange={(e) => {
                  const value = e.target.value
                  handleFiltersChange({
                    ...filters,
                    status: value ? [value as any] : undefined
                  })
                }}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem'
                }}
              >
                <option value="">All Status</option>
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="blocked">Blocked</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>

            {/* Priority Filter */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '0.5rem'
              }}>
                Priority
              </label>
              <select
                value={filters.priority?.[0] || ''}
                onChange={(e) => {
                  const value = e.target.value
                  handleFiltersChange({
                    ...filters,
                    priority: value ? [value as any] : undefined
                  })
                }}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem'
                }}
              >
                <option value="">All Priorities</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            {/* Goal Filter */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '0.5rem'
              }}>
                Goal
              </label>
              <select
                value={filters.goal_id || ''}
                onChange={(e) => {
                  handleFiltersChange({
                    ...filters,
                    goal_id: e.target.value || undefined
                  })
                }}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem'
                }}
              >
                <option value="">All Goals</option>
                {goals.map((goal) => (
                  <option key={goal.id} value={goal.id}>
                    {goal.title}
                  </option>
                ))}
              </select>
            </div>

            {/* Search */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '0.5rem'
              }}>
                Search
              </label>
              <input
                type="text"
                placeholder="Search milestones..."
                value={filters.search || ''}
                onChange={(e) => {
                  handleFiltersChange({
                    ...filters,
                    search: e.target.value || undefined
                  })
                }}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem'
                }}
              />
            </div>
          </div>
        </div>

        {/* Milestones List */}
        <MilestoneList
          milestones={milestones}
          loading={loading}
          error={error}
          onEdit={handleEditMilestone}
          onDelete={handleDeleteMilestone}
          onViewTasks={handleViewTasks}
          onCreateTask={handleCreateTask}
        />

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '1rem',
            marginTop: '2rem',
            padding: '1rem'
          }}>
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              style={{
                padding: '0.5rem 1rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                backgroundColor: currentPage === 1 ? '#f3f4f6' : 'white',
                color: currentPage === 1 ? '#9ca3af' : '#374151',
                cursor: currentPage === 1 ? 'not-allowed' : 'pointer'
              }}
            >
              Previous
            </button>

            <span style={{
              fontSize: '0.875rem',
              color: '#6b7280'
            }}>
              Page {currentPage} of {totalPages} ({totalItems} total)
            </span>

            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              style={{
                padding: '0.5rem 1rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                backgroundColor: currentPage === totalPages ? '#f3f4f6' : 'white',
                color: currentPage === totalPages ? '#9ca3af' : '#374151',
                cursor: currentPage === totalPages ? 'not-allowed' : 'pointer'
              }}
            >
              Next
            </button>
          </div>
        )}
      </main>

      {/* Create Milestone Modal */}
      {showCreateForm && (
        <MilestoneFormModal
          isOpen={showCreateForm}
          onClose={() => setShowCreateForm(false)}
          onSubmit={handleCreateMilestone}
          title="Create Milestone"
          submitButtonText="Create Milestone"
          loading={false}
          goals={goals}
          mode="create"
        />
      )}

      {/* Edit Milestone Modal */}
      {editingMilestone && (
        <MilestoneFormModal
          isOpen={!!editingMilestone}
          onClose={() => setEditingMilestone(null)}
          onSubmit={handleUpdateMilestone}
          initialData={{
            title: editingMilestone.title,
            description: editingMilestone.description,
            priority: editingMilestone.priority,
            target_date: editingMilestone.target_date,
            goal_id: editingMilestone.goal_id
          }}
          title="Edit Milestone"
          submitButtonText="Update Milestone"
          loading={false}
          goals={goals}
          mode="edit"
        />
      )}
    </div>
  )
}
