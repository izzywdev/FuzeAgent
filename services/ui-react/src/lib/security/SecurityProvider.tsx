/**
 * SecurityProvider — the single source of "who is the user, and what may they do".
 *
 * Identity comes from the FuzeFront platform, in this order:
 *
 *   1. Embedded in the FuzeFront shell → the host's `window.__FUZEFRONT__` sentinel.
 *      The shell already authenticated the user; we do not re-authenticate.
 *   2. Standalone → `GET /api/v1/security/session` with the stored session token.
 *
 * Permissions come from `GET /api/v1/security/authz/permissions` as a single
 * `Resource:action` set, so a screen can gate many controls without N round trips.
 * `can()` is FAIL-CLOSED: unknown, unloaded, or errored means "not permitted".
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { ActionKey, Identity, ResourceKey } from './contract'
import {
  BROKER_CODE_PARAM,
  exchangeCode,
  getPermissions,
  getSession,
  getToken,
  hostedIdentity,
  logout as revokeSession,
} from './client'

export type SecurityStatus = 'loading' | 'authenticated' | 'anonymous' | 'error'

export interface SecurityContextValue {
  status: SecurityStatus
  identity: Identity | null
  /** Effective `Resource:action` grants for the current tenant. Empty until loaded. */
  permissions: string[]
  error: string | null
  /** Fail-closed capability check for UI gating. Server-side authz still decides. */
  can: (resource: ResourceKey | string, action: ActionKey | string) => boolean
  signOut: () => Promise<void>
  refresh: () => Promise<void>
}

const SecurityContext = createContext<SecurityContextValue | null>(null)

/**
 * Consume a single-use broker `code` from the URL if the social callback returned one,
 * exchanging it for a session and cleaning the address bar so a refresh cannot replay
 * an already-spent code.
 */
async function consumeBrokerCode(): Promise<void> {
  if (typeof window === 'undefined') return
  const url = new URL(window.location.href)
  const code = url.searchParams.get(BROKER_CODE_PARAM)
  if (!code) return
  try {
    await exchangeCode(code)
  } finally {
    url.searchParams.delete(BROKER_CODE_PARAM)
    window.history.replaceState({}, '', url.toString())
  }
}

export function SecurityProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SecurityStatus>('loading')
  const [identity, setIdentity] = useState<Identity | null>(null)
  const [permissions, setPermissions] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      await consumeBrokerCode()

      // 1. Embedded in the FuzeFront shell — the host owns the session.
      const hosted = hostedIdentity()
      let resolved: Identity | null = hosted

      // 2. Standalone — ask the platform who we are.
      if (!resolved && getToken()) {
        const session = await getSession()
        resolved = session?.identity ?? null
      }

      if (!resolved) {
        setIdentity(null)
        setPermissions([])
        setStatus('anonymous')
        return
      }

      setIdentity(resolved)
      setStatus('authenticated')

      // Effective grants for the tenant. A null tenant means no tenant-scoped
      // decision is possible — the contract says fail closed, so: no permissions.
      if (resolved.tenantId) {
        setPermissions(await getPermissions(resolved.userId, resolved.tenantId))
      } else {
        setPermissions([])
      }
    } catch (err) {
      setIdentity(null)
      setPermissions([])
      setError(err instanceof Error ? err.message : 'Sign-in failed')
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const signOut = useCallback(async () => {
    await revokeSession()
    setIdentity(null)
    setPermissions([])
    setStatus('anonymous')
  }, [])

  const can = useCallback(
    (resource: ResourceKey | string, action: ActionKey | string) => {
      if (status !== 'authenticated') return false
      return permissions.includes(`${resource}:${action}`)
    },
    [permissions, status]
  )

  const value = useMemo<SecurityContextValue>(
    () => ({ status, identity, permissions, error, can, signOut, refresh: load }),
    [status, identity, permissions, error, can, signOut, load]
  )

  return <SecurityContext.Provider value={value}>{children}</SecurityContext.Provider>
}

/**
 * Access the current security state.
 *
 * Returns a fail-closed anonymous state when no provider is mounted, so a component
 * rendered outside the tree degrades to "no identity, no permissions" rather than
 * throwing or — far worse — appearing permitted.
 */
export function useSecurity(): SecurityContextValue {
  const ctx = useContext(SecurityContext)
  if (ctx) return ctx
  return {
    status: 'anonymous',
    identity: null,
    permissions: [],
    error: null,
    can: () => false,
    signOut: async () => {},
    refresh: async () => {},
  }
}
