/**
 * FuzeFront Security API client (browser).
 *
 * Speaks ONLY the published FuzeFront Security contract, same-origin under `/api`:
 *
 *   GET    /api/v1/security/session                  current identity ("me")
 *   DELETE /api/v1/security/session                  logout
 *   POST   /api/v1/security/session/exchange         broker code -> session
 *   GET    /api/v1/security/methods                  which sign-in methods exist
 *   GET    /api/v1/security/social/{provider}/start  server-brokered social login
 *   POST   /api/v1/security/authz/check              one decision
 *   POST   /api/v1/security/authz/bulk-check         many decisions
 *   GET    /api/v1/security/authz/permissions        effective grants
 *
 * No identity provider and no policy engine is named here, and none is contacted
 * directly: the browser only ever talks to its own origin. Per the contract's boundary
 * guarantee, the sign-in redirect goes to FuzeFront's own `/social/{provider}/start`,
 * which brokers onward — no FuzeFront-internal identity host is ever visible.
 *
 * SAME-ORIGIN ONLY. The base is the relative string `/api`; never an absolute host.
 * An absolute `http://` base is mixed content under TLS and breaks in prod ingress.
 */

import type {
  AuthMethods,
  AuthzBulkDecision,
  AuthzCheckRequest,
  AuthzDecision,
  Identity,
  PermissionSet,
  ResourceRef,
  SessionInfo,
  SessionResult,
} from './contract'

/** Same-origin API base. Deliberately relative — do not make this configurable. */
export const API_BASE = '/api'
export const SECURITY_BASE = `${API_BASE}/v1/security`

/** localStorage key holding the FuzeFront session token for standalone mode. */
export const TOKEN_STORAGE_KEY = 'fuzefront.session.token'

/** Query param FuzeFront's social callback appends when returning to us. */
export const BROKER_CODE_PARAM = 'code'

export class SecurityError extends Error {
  status: number
  body: unknown
  constructor(status: number, message: string, body: unknown) {
    super(message)
    this.name = 'SecurityError'
    this.status = status
    this.body = body
  }
}

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------
//
// When FuzeAgent runs INSIDE the FuzeFront shell the host owns the session and
// exposes it on `window.__FUZEFRONT__`; we read it and never write it. Standalone,
// we hold the token ourselves after a `/session/exchange`.

interface FuzeFrontSentinel {
  token?: string
  user?: { userId?: string; email?: string; tenantId?: string | null; roles?: string[] }
}

function sentinel(): FuzeFrontSentinel | undefined {
  if (typeof window === 'undefined') return undefined
  return (window as unknown as Record<string, unknown>).__FUZEFRONT__ as
    | FuzeFrontSentinel
    | undefined
}

export function getToken(): string | null {
  const hosted = sentinel()?.token
  if (hosted) return hosted
  if (typeof window === 'undefined') return null
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  if (typeof window === 'undefined') return
  try {
    if (token) window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
    else window.localStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch {
    /* storage unavailable (private mode) — the session is then request-scoped only */
  }
}

/** Authorization header for any FuzeAgent API call, or `{}` when unauthenticated. */
export function authHeader(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// ---------------------------------------------------------------------------
// Transport
// ---------------------------------------------------------------------------

type FetchImpl = typeof fetch

async function request<T>(
  method: string,
  path: string,
  init: { body?: unknown; fetchImpl?: FetchImpl } = {}
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json', ...authHeader() }
  let payload: string | undefined
  if (init.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(init.body)
  }
  const doFetch = init.fetchImpl ?? globalThis.fetch
  const response = await doFetch(`${SECURITY_BASE}${path}`, {
    method,
    headers,
    body: payload,
  })

  const text = await response.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : undefined
  } catch {
    data = text
  }

  if (!response.ok) {
    const message =
      data && typeof data === 'object' && 'error' in (data as Record<string, unknown>)
        ? String((data as Record<string, unknown>).error)
        : response.statusText || `Request failed with ${response.status}`
    throw new SecurityError(response.status, message, data)
  }
  return data as T
}

// ---------------------------------------------------------------------------
// AuthN
// ---------------------------------------------------------------------------

/**
 * Current identity. Returns `null` when the caller has no valid session (401) —
 * that is the normal "signed out" answer, not an error.
 */
export async function getSession(fetchImpl?: FetchImpl): Promise<SessionInfo | null> {
  if (!getToken()) return null
  try {
    return await request<SessionInfo>('GET', '/session', { fetchImpl })
  } catch (error) {
    if (error instanceof SecurityError && error.status === 401) return null
    throw error
  }
}

/** Which sign-in methods this deployment offers. Never hard-code a provider list. */
export function getAuthMethods(fetchImpl?: FetchImpl): Promise<AuthMethods> {
  return request<AuthMethods>('GET', '/methods', { fetchImpl })
}

/**
 * URL that begins a server-brokered social sign-in. This is a full-page navigation,
 * not a fetch: FuzeFront redirects the browser onward and back to `returnTo` with a
 * single-use `code`.
 */
export function socialStartUrl(provider: string, returnTo: string): string {
  const params = new URLSearchParams({ returnTo })
  return `${SECURITY_BASE}/social/${encodeURIComponent(provider)}/start?${params.toString()}`
}

/**
 * Exchange the opaque, single-use broker `code` from the callback for a session.
 * On `status: 'authenticated'` the token is stored. An `mfa_required` result is
 * returned as-is for the caller to complete via the contract's `/mfa/*` endpoints.
 */
export async function exchangeCode(
  code: string,
  fetchImpl?: FetchImpl
): Promise<SessionResult> {
  const result = await request<SessionResult>('POST', '/session/exchange', {
    body: { code },
    fetchImpl,
  })
  if (result.status === 'authenticated') setToken(result.token)
  return result
}

/** Revoke the current session server-side and drop the local token. Idempotent. */
export async function logout(fetchImpl?: FetchImpl): Promise<void> {
  try {
    if (getToken()) await request<void>('DELETE', '/session', { fetchImpl })
  } finally {
    setToken(null)
  }
}

// ---------------------------------------------------------------------------
// AuthZ — decisions are the platform's; FuzeAgent ships no policy
// ---------------------------------------------------------------------------

/**
 * One authorization decision. Fail-closed: any error resolves to `false`, so a broken
 * or unreachable security service hides capability rather than exposing it.
 */
export async function authzCheck(
  input: {
    subject: string
    tenant: string
    resource: ResourceRef
    action: string
    context?: Record<string, unknown>
  },
  fetchImpl?: FetchImpl
): Promise<boolean> {
  if (!input.subject || !input.tenant) return false
  try {
    const body: AuthzCheckRequest = input
    const decision = await request<AuthzDecision>('POST', '/authz/check', {
      body,
      fetchImpl,
    })
    return decision?.allow === true
  } catch {
    return false
  }
}

/**
 * Many decisions in one round trip, index-aligned with the input. Fail-closed: any
 * error — including a decision list whose length does not match the request — denies
 * everything rather than letting a short list read as "allowed".
 */
export async function authzBulkCheck(
  checks: AuthzCheckRequest[],
  fetchImpl?: FetchImpl
): Promise<boolean[]> {
  if (checks.length === 0) return []
  const denied = checks.map(() => false)
  try {
    const result = await request<AuthzBulkDecision>('POST', '/authz/bulk-check', {
      body: { checks },
      fetchImpl,
    })
    if (!Array.isArray(result?.decisions) || result.decisions.length !== checks.length) {
      return denied
    }
    return result.decisions.map((d) => d?.allow === true)
  } catch {
    return denied
  }
}

/**
 * Effective `Resource:action` grants for a subject in a tenant — one round trip that
 * lets the UI gate many controls without N checks. Fail-closed: `[]` on any error,
 * which means "no permissions known", never "unrestricted".
 */
export async function getPermissions(
  subject: string,
  tenant: string,
  fetchImpl?: FetchImpl
): Promise<string[]> {
  if (!subject || !tenant) return []
  try {
    const params = new URLSearchParams({ subject, tenant })
    const result = await request<PermissionSet>(
      'GET',
      `/authz/permissions?${params.toString()}`,
      { fetchImpl }
    )
    return Array.isArray(result?.permissions) ? result.permissions : []
  } catch {
    return []
  }
}

/** Identity exposed by the FuzeFront shell, when FuzeAgent is running embedded. */
export function hostedIdentity(): Identity | null {
  const user = sentinel()?.user
  if (!user?.userId) return null
  return {
    userId: user.userId,
    tenantId: user.tenantId ?? null,
    roles: user.roles ?? [],
    email: user.email,
    authMode: 'federated-jwks',
  }
}
