/**
 * SecurityProvider / AuthGate — identity resolution and fail-closed UI gating.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { SecurityProvider, useSecurity } from './SecurityProvider'
import { TOKEN_STORAGE_KEY } from './client'
import AuthGate from '../../components/auth/AuthGate'

function Probe() {
  const { status, identity, can } = useSecurity()
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="user">{identity?.userId ?? '-'}</span>
      <span data-testid="can-read-agent">{String(can('Agent', 'read'))}</span>
      <span data-testid="can-delete-agent">{String(can('Agent', 'delete'))}</span>
    </div>
  )
}

const IDENTITY = {
  userId: 'u1',
  tenantId: 't1',
  roles: ['operator'],
  authMode: 'federated-jwks' as const,
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/** Route by URL so each test only declares the endpoints it cares about. */
function routeFetch(routes: Record<string, () => Response | Promise<Response>>) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    for (const [prefix, responder] of Object.entries(routes)) {
      if (url.startsWith(prefix)) return responder()
    }
    return jsonResponse({ error: 'not found' }, 404)
  })
}

beforeEach(() => {
  window.localStorage.clear()
  delete (window as unknown as Record<string, unknown>).__FUZEFRONT__
  window.history.replaceState({}, '', '/')
  vi.restoreAllMocks()
})

describe('identity resolution', () => {
  it('is anonymous with no token and no shell', async () => {
    vi.stubGlobal('fetch', routeFetch({}))
    render(
      <SecurityProvider>
        <Probe />
      </SecurityProvider>
    )
    await waitFor(() =>
      expect(screen.getByTestId('status').textContent).toBe('anonymous')
    )
    expect(screen.getByTestId('can-read-agent').textContent).toBe('false')
  })

  it('takes the identity from the FuzeFront shell when embedded', async () => {
    ;(window as unknown as Record<string, unknown>).__FUZEFRONT__ = {
      token: 'shell-token',
      user: { userId: 'shell-user', tenantId: 't1', roles: ['admin'] },
    }
    const fetchImpl = routeFetch({
      '/api/v1/security/authz/permissions': () =>
        jsonResponse({ subject: 'shell-user', tenant: 't1', permissions: ['Agent:read'] }),
    })
    vi.stubGlobal('fetch', fetchImpl)

    render(
      <SecurityProvider>
        <Probe />
      </SecurityProvider>
    )

    await waitFor(() =>
      expect(screen.getByTestId('status').textContent).toBe('authenticated')
    )
    expect(screen.getByTestId('user').textContent).toBe('shell-user')
    // The shell identity is used as-is; no /session round trip is needed.
    expect(
      fetchImpl.mock.calls.some((c) => String(c[0]).includes('/security/session'))
    ).toBe(false)
  })

  it('resolves the identity from GET /session when standalone', async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, 'tok')
    vi.stubGlobal(
      'fetch',
      routeFetch({
        '/api/v1/security/session': () =>
          jsonResponse({ identity: IDENTITY, user: { id: 'u1' } }),
        '/api/v1/security/authz/permissions': () =>
          jsonResponse({ subject: 'u1', tenant: 't1', permissions: ['Agent:read'] }),
      })
    )

    render(
      <SecurityProvider>
        <Probe />
      </SecurityProvider>
    )

    await waitFor(() =>
      expect(screen.getByTestId('status').textContent).toBe('authenticated')
    )
    expect(screen.getByTestId('user').textContent).toBe('u1')
  })
})

describe('can() is fail closed', () => {
  it('grants only what the platform actually returned', async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, 'tok')
    vi.stubGlobal(
      'fetch',
      routeFetch({
        '/api/v1/security/session': () =>
          jsonResponse({ identity: IDENTITY, user: { id: 'u1' } }),
        '/api/v1/security/authz/permissions': () =>
          jsonResponse({ subject: 'u1', tenant: 't1', permissions: ['Agent:read'] }),
      })
    )

    render(
      <SecurityProvider>
        <Probe />
      </SecurityProvider>
    )

    await waitFor(() =>
      expect(screen.getByTestId('can-read-agent').textContent).toBe('true')
    )
    expect(screen.getByTestId('can-delete-agent').textContent).toBe('false')
  })

  it('grants nothing when the permissions call fails', async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, 'tok')
    vi.stubGlobal(
      'fetch',
      routeFetch({
        '/api/v1/security/session': () =>
          jsonResponse({ identity: IDENTITY, user: { id: 'u1' } }),
        '/api/v1/security/authz/permissions': () => jsonResponse({ error: 'down' }, 503),
      })
    )

    render(
      <SecurityProvider>
        <Probe />
      </SecurityProvider>
    )

    await waitFor(() =>
      expect(screen.getByTestId('status').textContent).toBe('authenticated')
    )
    expect(screen.getByTestId('can-read-agent').textContent).toBe('false')
  })

  it('grants nothing when the identity has no tenant scope', async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, 'tok')
    const fetchImpl = routeFetch({
      '/api/v1/security/session': () =>
        jsonResponse({ identity: { ...IDENTITY, tenantId: null }, user: { id: 'u1' } }),
    })
    vi.stubGlobal('fetch', fetchImpl)

    render(
      <SecurityProvider>
        <Probe />
      </SecurityProvider>
    )

    await waitFor(() =>
      expect(screen.getByTestId('status').textContent).toBe('authenticated')
    )
    expect(screen.getByTestId('can-read-agent').textContent).toBe('false')
    // No tenant means no tenant-scoped decision is even attempted.
    expect(
      fetchImpl.mock.calls.some((c) => String(c[0]).includes('/authz/permissions'))
    ).toBe(false)
  })
})

describe('broker code exchange', () => {
  it('exchanges a ?code= from the social callback and scrubs the URL', async () => {
    window.history.replaceState({}, '', '/agents?code=broker-code-1')
    vi.stubGlobal(
      'fetch',
      routeFetch({
        '/api/v1/security/session/exchange': () =>
          jsonResponse({ status: 'authenticated', token: 'fresh', user: {} }),
        '/api/v1/security/session': () =>
          jsonResponse({ identity: IDENTITY, user: { id: 'u1' } }),
        '/api/v1/security/authz/permissions': () =>
          jsonResponse({ subject: 'u1', tenant: 't1', permissions: [] }),
      })
    )

    render(
      <SecurityProvider>
        <Probe />
      </SecurityProvider>
    )

    await waitFor(() =>
      expect(screen.getByTestId('status').textContent).toBe('authenticated')
    )
    // Single-use code must not survive a refresh.
    expect(window.location.search).not.toContain('code=')
  })
})

describe('AuthGate', () => {
  it('shows sign-in when anonymous AND the platform advertises methods', async () => {
    vi.stubGlobal(
      'fetch',
      routeFetch({
        '/api/v1/security/methods': () =>
          jsonResponse({
            password: false,
            social: ['google'],
            mfa: { enabled: false, types: [] },
            verification: { email: false, sms: false },
          }),
      })
    )

    render(
      <SecurityProvider>
        <AuthGate>
          <div>protected content</div>
        </AuthGate>
      </SecurityProvider>
    )

    expect(await screen.findByText('Continue with Google')).toBeTruthy()
    expect(screen.queryByText('protected content')).toBeNull()
  })

  it('renders the app when no security surface exists (standalone/offline)', async () => {
    // /methods 404s -> there is no sign-in to offer. Blocking here would be a
    // self-inflicted dead end; the server still fails closed on every API call.
    vi.stubGlobal('fetch', routeFetch({}))

    render(
      <SecurityProvider>
        <AuthGate>
          <div>protected content</div>
        </AuthGate>
      </SecurityProvider>
    )

    expect(await screen.findByText('protected content')).toBeTruthy()
  })

  it('renders the app for an authenticated user', async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, 'tok')
    vi.stubGlobal(
      'fetch',
      routeFetch({
        '/api/v1/security/session': () =>
          jsonResponse({ identity: IDENTITY, user: { id: 'u1' } }),
        '/api/v1/security/authz/permissions': () =>
          jsonResponse({ subject: 'u1', tenant: 't1', permissions: [] }),
      })
    )

    render(
      <SecurityProvider>
        <AuthGate>
          <div>protected content</div>
        </AuthGate>
      </SecurityProvider>
    )

    expect(await screen.findByText('protected content')).toBeTruthy()
  })
})

describe('useSecurity outside a provider', () => {
  it('degrades to anonymous with no permissions, never to "permitted"', () => {
    render(<Probe />)
    expect(screen.getByTestId('status').textContent).toBe('anonymous')
    expect(screen.getByTestId('can-read-agent').textContent).toBe('false')
  })
})
