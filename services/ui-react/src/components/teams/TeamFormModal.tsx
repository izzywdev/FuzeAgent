/**
 * Team Form Modal Component
 *
 * Modal dialog for creating and editing teams.
 * Includes form validation, loading states, and error handling.
 *
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import React, { useState, useEffect } from 'react'
import type { TeamFormModalProps, TeamFormErrors } from './types'
import { validateTeamCreate, validateTeamUpdate, createDefaultTeamCreate, createTeamUpdateFromTeam } from './utils'

const TEAM_TYPES = [
  { value: 'development', label: 'Development' },
  { value: 'operations', label: 'Operations' },
  { value: 'management', label: 'Management' },
  { value: 'research', label: 'Research' }
] as const

const TEAM_COLORS = [
  '#2563eb', // Blue
  '#dc2626', // Red
  '#16a34a', // Green
  '#ca8a04', // Yellow
  '#9333ea', // Purple
  '#c2410c', // Orange
  '#0891b2', // Cyan
  '#be185d'  // Pink
] as const

const TeamFormModal: React.FC<TeamFormModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  mode,
  loading = false,
  error = null
}) => {
  const [formData, setFormData] = useState(
    mode === 'edit' && initialData
      ? createTeamUpdateFromTeam(initialData)
      : createDefaultTeamCreate()
  )
  const [errors, setErrors] = useState<TeamFormErrors>({})
  const [touched, setTouched] = useState<Record<string, boolean>>({})

  // Reset form when modal opens/closes or mode changes
  useEffect(() => {
    if (isOpen) {
      const newFormData = mode === 'edit' && initialData
        ? createTeamUpdateFromTeam(initialData)
        : createDefaultTeamCreate()
      setFormData(newFormData)
      setErrors({})
      setTouched({})
    }
  }, [isOpen, mode, initialData])

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))

    // Clear error when user starts typing
    if (errors[field as keyof TeamFormErrors]) {
      setErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }

  const handleBlur = (field: string) => {
    setTouched(prev => ({ ...prev, [field]: true }))

    // Validate field on blur
    const validationErrors = mode === 'create'
      ? validateTeamCreate(formData as any)
      : validateTeamUpdate(formData as any)

    if (validationErrors[field as keyof TeamFormErrors]) {
      setErrors(prev => ({
        ...prev,
        [field]: validationErrors[field as keyof TeamFormErrors]
      }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validate all fields
    const validationErrors = mode === 'create'
      ? validateTeamCreate(formData as any)
      : validateTeamUpdate(formData as any)

    setErrors(validationErrors)
    setTouched({
      name: true,
      description: true,
      team_type: true,
      color: true
    })

    // If no errors, submit
    if (Object.keys(validationErrors).length === 0) {
      try {
        await onSubmit(formData)
        onClose()
      } catch (error) {
        // Error handling is done by parent component
      }
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {mode === 'create' ? 'Create Team' : 'Edit Team'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={loading}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* General Error */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
              Team Name *
            </label>
            <input
              type="text"
              id="name"
              value={formData.name || ''}
              onChange={(e) => handleInputChange('name', e.target.value)}
              onBlur={() => handleBlur('name')}
              className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.name && touched.name
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-gray-300 focus:border-blue-500'
              }`}
              placeholder="Enter team name"
              disabled={loading}
            />
            {errors.name && touched.name && (
              <p className="mt-1 text-sm text-red-600">{errors.name}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              id="description"
              value={formData.description || ''}
              onChange={(e) => handleInputChange('description', e.target.value)}
              onBlur={() => handleBlur('description')}
              rows={3}
              className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.description && touched.description
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-gray-300 focus:border-blue-500'
              }`}
              placeholder="Enter team description"
              disabled={loading}
            />
            {errors.description && touched.description && (
              <p className="mt-1 text-sm text-red-600">{errors.description}</p>
            )}
          </div>

          {/* Team Type */}
          <div>
            <label htmlFor="team_type" className="block text-sm font-medium text-gray-700 mb-2">
              Team Type
            </label>
            <select
              id="team_type"
              value={formData.team_type || 'development'}
              onChange={(e) => handleInputChange('team_type', e.target.value)}
              onBlur={() => handleBlur('team_type')}
              className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.team_type && touched.team_type
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-gray-300 focus:border-blue-500'
              }`}
              disabled={loading}
            >
              {TEAM_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
            {errors.team_type && touched.team_type && (
              <p className="mt-1 text-sm text-red-600">{errors.team_type}</p>
            )}
          </div>

          {/* Color Picker */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Team Color
            </label>
            <div className="flex flex-wrap gap-2">
              {TEAM_COLORS.map((color) => (
                <button
                  key={color}
                  type="button"
                  onClick={() => handleInputChange('color', color)}
                  className={`w-8 h-8 rounded-full border-2 ${
                    formData.color === color
                      ? 'border-gray-800'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                  style={{ backgroundColor: color }}
                  disabled={loading}
                />
              ))}
            </div>
            <input
              type="text"
              value={formData.color || '#2563eb'}
              onChange={(e) => handleInputChange('color', e.target.value)}
              onBlur={() => handleBlur('color')}
              className={`mt-2 w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.color && touched.color
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-gray-300 focus:border-blue-500'
              }`}
              placeholder="#2563eb"
              disabled={loading}
            />
            {errors.color && touched.color && (
              <p className="mt-1 text-sm text-red-600">{errors.color}</p>
            )}
          </div>

          {/* Status (Edit mode only) */}
          {mode === 'edit' && (
            <div>
              <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-2">
                Status
              </label>
              <select
                id="status"
                value={formData.status || 'active'}
                onChange={(e) => handleInputChange('status', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={loading}
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {mode === 'create' ? 'Creating...' : 'Updating...'}
              </div>
            ) : (
              mode === 'create' ? 'Create Team' : 'Update Team'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default TeamFormModal
