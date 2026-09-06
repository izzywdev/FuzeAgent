/**
 * FuzeFront Security client — contract adherence and fail-closed behaviour.
 *
 * These pin the two properties the migration exists for:
 *   1. Only published FuzeFront Security paths are called, same-origin under `/api`.
 *      No identity or policy vendor host is ever contacted.
 *   2. Every authorization answer fails CLOSED — errors, non-2xx, and misaligned
 *      bulk responses all deny.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  API_BASE,
  SECURITY_BASE,
  TOKEN_STORAGE_KEY,
  authHeader,
  authzBulkCheck,
  authzCheck,
  exchangeCode,
  getAuthMethods,
  getPermissions,
  getSession,
  getToken,
  logout,
  setToken,
  socialStartUrl,
} from './client'
import type { AuthzCheckRequest } from './contract'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  window.localStorage.clear()
  delete (window as unknown as Record<string, unknown>).__FUZEFRONT__
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('same-origin base', () => {
  it('is relative, never an absolute host (mixed content under TLS)', () => {
    expect(API_BASE).toBe('/api')
    expect(SECURITY_BASE).toBe('/api/v1/security')
    expect(SECURITY_BASE.startsWith('http')).toBe(false)
  })

  it('builds the social start URL from the contract path', () => {
    const url = socialStartUrl('google', 'https://app.example/agents')
    expect(url).toBe(
      '/api/v1/security/social/google/start?returnTo=https%3A%2F%2Fapp.example%2Fagents'
    )
  })
})

describe('token storage', () => {
  it('prefers the FuzeFront shell token when embedded', () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, 'standalone-token')
    ;(window as unknown as Record<string, unknown>).__FUZEFRONT__ = {
      token: 'shell-token',
    }
    expect(getToken()).toBe('shell-token')
  })

  it('falls back to its own stored token when standalone', () => {
    setToken('standalone-token')
    expect(getToken()).toBe('standalone-token')
    expect(authHeader()).toEqual({ Authorization: 'Bearer standalone-token' })
  })

  it('sends no Authorization header when signed out', () => {
    expect(authHeader()).toEqual({})
  })
})

describe('getSession', () => {
  it('does not call the API at all when there is no token', async () => {
    const fetchImpl = vi.fn()
    await expect(getSession(fetchImpl as unknown as typeof fetch)).resolves.toBeNull()
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it('calls GET /api/v1/security/session with the bearer token', async () => {
    setToken('tok')
    const identity = {
      userId: 'u1',
      tenantId: 't1',
      roles: ['operator'],
      authMode: 'federated-jwks' as const,
    }
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse({ identity, user: { id: 'u1', email: 'u@x', roles: [] } })
    )

    const session = await getSession(fetchImpl as unknown as typeof fetch)

    expect(session?.identity.userId).toBe('u1')
    const [url, init] = fetchImpl.mock.calls[0]
    expect(url).toBe('/api/v1/security/session')
    expect(init.method).toBe('GET')
    expect(init.headers.Authorization).toBe('Bearer tok')
  })

  it('treats 401 as "signed out", not as an error', async () => {
    setToken('expired')
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ error: 'nope' }, 401))
    await expect(getSession(fetchImpl as unknown as typeof fetch)).resolves.toBeNull()
  })
})

describe('exchangeCode', () => {
  it('POSTs the broker code to /session/exchange and stores the token', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse({ status: 'authenticated', token: 'new-token', user: {} })
    )

    const result = await exchangeCode('abc123', fetchImpl as unknown as typeof fetch)

    expect(result.status).toBe('authenticated')
    expect(getToken()).toBe('new-token')
    const [url, init] = fetchImpl.mock.calls[0]
    expect(url).toBe('/api/v1/security/session/exchange')
    expect(JSON.parse(init.body)).toEqual({ code: 'abc123' })
  })

  it('does not store a token for an mfa_required result', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse({ status: 'mfa_required', challengeId: 'c1', factors: [] })
    )
    const result = await exchangeCode('abc', fetchImpl as unknown as typeof fetch)
    expect(result.status).toBe('mfa_required')
    expect(getToken()).toBeNull()
  })
})

describe('logout', () => {
  it('revokes server-side and clears the local token', async () => {
    setToken('tok')
    const fetchImpl = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    await logout(fetchImpl as unknown as typeof fetch)
    expect(fetchImpl.mock.calls[0][0]).toBe('/api/v1/security/session')
    expect(fetchImpl.mock.calls[0][1].method).toBe('DELETE')
    expect(getToken()).toBeNull()
  })

  it('still clears the local token when the server call fails', async () => {
    setToken('tok')
    const fetchImpl = vi.fn().mockRejectedValue(new Error('offline'))
    await expect(logout(fetchImpl as unknown as typeof fetch)).rejects.toThrow()
    expect(getToken()).toBeNull()
  })
})

describe('getAuthMethods', () => {
  it('reads the advertised methods rather than hard-coding providers', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse({
        password: false,
        social: ['google'],
        mfa: { enabled: true, types: ['totp'] },
        verification: { email: true, sms: false },
      })
    )
    const methods = await getAuthMethods(fetchImpl as unknown as typeof fetch)
    expect(fetchImpl.mock.calls[0][0]).toBe('/api/v1/security/methods')
    expect(methods.social).toEqual(['google'])
  })
})

describe('authzCheck — fail closed', () => {
  it('sends the bare policy keys from registration/policy.json', async () => {
    setToken('tok')
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ allow: true }))

    const allowed = await authzCheck(
      {
        subject: 'u1',
        tenant: 't1',
        resource: { type: 'Agent', key: 'agent-7' },
        action: 'deploy',
      },
      fetchImpl as unknown as typeof fetch
    )

    expect(allowed).toBe(true)
    const [url, init] = fetchImpl.mock.calls[0]
    expect(url).toBe('/api/v1/security/authz/check')
    expect(JSON.parse(init.body)).toEqual({
      subject: 'u1',
      tenant: 't1',
      resource: { type: 'Agent', key: 'agent-7' },
      action: 'deploy',
    })
  })

  it('denies when the platform says allow:false', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ allow: false }))
    await expect(
      authzCheck(
        { subject: 'u1', tenant: 't1', resource: { type: 'Task' }, action: 'assign' },
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toBe(false)
  })

  it('denies on a transport error', async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error('network down'))
    await expect(
      authzCheck(
        { subject: 'u1', tenant: 't1', resource: { type: 'Task' }, action: 'assign' },
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toBe(false)
  })

  it('denies on a 5xx', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ error: 'boom' }, 503))
    await expect(
      authzCheck(
        { subject: 'u1', tenant: 't1', resource: { type: 'Task' }, action: 'assign' },
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toBe(false)
  })

  it('denies with no tenant scope — a null tenant is never "unrestricted"', async () => {
    const fetchImpl = vi.fn()
    await expect(
      authzCheck(
        { subject: 'u1', tenant: '', resource: { type: 'Task' }, action: 'read' },
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toBe(false)
    expect(fetchImpl).not.toHaveBeenCalled()
  })
})

describe('authzBulkCheck — fail closed', () => {
  const checks: AuthzCheckRequest[] = [
    { subject: 'u1', tenant: 't1', resource: { type: 'Agent' }, action: 'read' },
    { subject: 'u1', tenant: 't1', resource: { type: 'Agent' }, action: 'delete' },
  ]

  it('returns decisions index-aligned with the request', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(jsonResponse({ decisions: [{ allow: true }, { allow: false }] }))
    await expect(
      authzBulkCheck(checks, fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual([true, false])
  })

  it('denies everything when the decision list is misaligned', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ decisions: [{ allow: true }] }))
    await expect(
      authzBulkCheck(checks, fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual([false, false])
  })

  it('denies everything on error', async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error('offline'))
    await expect(
      authzBulkCheck(checks, fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual([false, false])
  })
})

describe('getPermissions — fail closed', () => {
  it('requests the effective grants for subject + tenant', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse({ subject: 'u1', tenant: 't1', permissions: ['Agent:read'] })
    )
    await expect(
      getPermissions('u1', 't1', fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual(['Agent:read'])
    expect(fetchImpl.mock.calls[0][0]).toBe(
      '/api/v1/security/authz/permissions?subject=u1&tenant=t1'
    )
  })

  it('returns [] on failure — "no permissions known", never "unrestricted"', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ error: 'down' }, 500))
    await expect(
      getPermissions('u1', 't1', fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual([])
  })
})
