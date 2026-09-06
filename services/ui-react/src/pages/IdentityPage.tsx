/**
 * IdentityOrgPage — renders the @fuzefront/identity-ui IdentityPage.
 *
 * `@fuzefront/identity-ui` is the platform's ORG-MEMBER / ROLE / API-TOKEN management
 * surface (members table, invitations, roles & permissions, API tokens). It is not a
 * sign-in screen — sign-in lives in `components/auth/SignIn.tsx` and redirects to
 * FuzeFront's own server-brokered start endpoint.
 *
 * Two defects are fixed here:
 *
 *   1. `baseUrl: '/api/identity'`. The identity client's own paths already begin with
 *      `/api/organizations/...`, so every request went to
 *      `/api/identity/api/organizations/...` and 404'd. The correct base is `''` —
 *      same origin, which is also what the host contract requires (never an absolute
 *      API host: that is mixed content under TLS).
 *   2. No `getToken`. Requests carried no Authorization header, so even a
 *      correctly-routed call would have been rejected. The token now comes from the
 *      FuzeFront session — the shell's when embedded, ours when standalone.
 *
 * The org id defaults to the caller's real tenant from the platform identity rather
 * than the literal string 'default', so the page addresses the org the user is in.
 *
 * The package stays optionally `require`d: it publishes to the private GitHub Packages
 * registry, which this workspace's CI has no credentials for.
 */

/* eslint-disable @typescript-eslint/no-require-imports */
import React from 'react'
import { getToken } from '../lib/security/client'
import { useSecurity } from '../lib/security/SecurityProvider'

// ---------------------------------------------------------------------------
// Try to import identity-ui at module level
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type IdentityClient = any

type IdentityComponents = {
  IdentityPage: React.ComponentType<{ client: IdentityClient; orgId: string }>
  IdentityI18nProvider: React.ComponentType<{ children: React.ReactNode }>
  createIdentityClient: (options: {
    baseUrl?: string
    getToken?: () => string | null | undefined
  }) => IdentityClient
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
//
// `baseUrl: ''` = same origin. `getToken` is read lazily on every request, so a
// sign-in or sign-out that happens after mount is picked up without rebuilding
// the client.
// ---------------------------------------------------------------------------

const identityClient: IdentityClient = identityPkg?.createIdentityClient
  ? identityPkg.createIdentityClient({ baseUrl: '', getToken })
  : null

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface IdentityOrgPageProps {
  /** Organisation to render identity settings for. Defaults to the caller's tenant. */
  orgId?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function IdentityOrgPage({ orgId }: IdentityOrgPageProps): React.ReactElement {
  const { identity } = useSecurity()
  const resolvedOrgId = orgId ?? identity?.tenantId ?? null

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

  // No tenant means no org-scoped page is addressable. Say so rather than requesting
  // a made-up 'default' org and rendering someone else's members list or an error.
  if (!resolvedOrgId) {
    return (
      <div style={{ padding: '2rem' }}>
        <h1>Identity</h1>
        <p style={{ color: '#888', marginTop: '1rem' }}>
          No organization is associated with your session yet.
        </p>
      </div>
    )
  }

  const { IdentityI18nProvider, IdentityPage: IdentityPageComponent } = identityPkg

  return (
    <IdentityI18nProvider>
      <IdentityPageComponent client={identityClient} orgId={resolvedOrgId} />
    </IdentityI18nProvider>
  )
}

export default IdentityOrgPage
