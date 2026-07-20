/**
 * IdentityOrgPage — renders the @fuzefront/identity-ui IdentityPage.
 * Degrades gracefully when the package is absent.
 */

/* eslint-disable @typescript-eslint/no-require-imports */
import React from 'react'

// ---------------------------------------------------------------------------
// Try to import identity-ui at module level
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type IdentityClient = any

type IdentityComponents = {
  IdentityPage: React.ComponentType<{ client: IdentityClient; orgId: string }>
  IdentityI18nProvider: React.ComponentType<{ children: React.ReactNode }>
  createIdentityClient: (options: { baseUrl: string }) => IdentityClient
}

let identityPkg: IdentityComponents | null = null

try {
  identityPkg = require('@fuzefront/identity-ui')
} catch {
  identityPkg = null
}

// ---------------------------------------------------------------------------
// Create the client once (outside the component) so it's stable across renders.
// Only constructed when the package is present.
// ---------------------------------------------------------------------------

const identityClient: IdentityClient =
  identityPkg?.createIdentityClient
    ? identityPkg.createIdentityClient({ baseUrl: '/api/identity' })
    : null

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface IdentityOrgPageProps {
  /** Organisation to render identity settings for. Defaults to 'default'. */
  orgId?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function IdentityOrgPage({ orgId = 'default' }: IdentityOrgPageProps): React.ReactElement {
  if (!identityPkg || !identityClient) {
    return (
      <div style={{ padding: '2rem' }}>
        <h1>Identity</h1>
        <p style={{ color: '#888', marginTop: '1rem' }}>
          Identity UI is not available in this environment.
        </p>
      </div>
    )
  }

  const { IdentityI18nProvider, IdentityPage: IdentityPageComponent } = identityPkg

  return (
    <IdentityI18nProvider>
      <IdentityPageComponent client={identityClient} orgId={orgId} />
    </IdentityI18nProvider>
  )
}

export default IdentityOrgPage
