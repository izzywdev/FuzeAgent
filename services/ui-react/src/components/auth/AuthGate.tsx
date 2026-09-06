/**
 * AuthGate — decides whether to show the app or the sign-in surface.
 *
 * The rule, and why it is not simply "no identity => sign-in":
 *
 *   authenticated                  -> render the app.
 *   anonymous, platform PRESENT    -> render <SignIn/>. The platform advertises real
 *                                     sign-in methods, so there is something to do.
 *   anonymous, platform ABSENT     -> render the app. `GET /v1/security/methods` did
 *                                     not answer, so no sign-in exists to offer;
 *                                     blocking here would lock a standalone/offline
 *                                     deployment out of a UI it used to be able to
 *                                     open, and would replace a working screen with a
 *                                     dead end.
 *
 * That is NOT a security downgrade. The gate is cosmetic; the orchestrator enforces
 * authentication and authorization server-side and fails closed on every request
 * (`services/orchestrator/auth.py`). A UI that renders without a session simply gets
 * 401s from the API — which is the correct, honest failure — rather than a
 * self-inflicted white screen when the platform is not deployed.
 */

import { useEffect, useState, type ReactNode } from 'react'
import type { AuthMethods } from '../../lib/security/contract'
import { getAuthMethods } from '../../lib/security/client'
import { useSecurity } from '../../lib/security/SecurityProvider'
import { SignIn } from './SignIn'

type Probe =
  | { state: 'probing' }
  | { state: 'present'; methods: AuthMethods }
  | { state: 'absent' }

export function AuthGate({ children }: { children: ReactNode }) {
  const { status, error } = useSecurity()
  const [probe, setProbe] = useState<Probe>({ state: 'probing' })

  const needsProbe = status === 'anonymous' || status === 'error'

  useEffect(() => {
    if (!needsProbe) return
    let cancelled = false
    getAuthMethods()
      .then((methods) => {
        if (!cancelled) setProbe({ state: 'present', methods })
      })
      .catch(() => {
        // No security surface on this origin — standalone/offline deployment.
        if (!cancelled) setProbe({ state: 'absent' })
      })
    return () => {
      cancelled = true
    }
  }, [needsProbe])

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center" role="status">
        <p className="text-sm text-muted-foreground">Signing in…</p>
      </div>
    )
  }

  if (status === 'authenticated') return <>{children}</>

  if (probe.state === 'probing') {
    return (
      <div className="min-h-screen flex items-center justify-center" role="status">
        <p className="text-sm text-muted-foreground">Checking sign-in…</p>
      </div>
    )
  }

  if (probe.state === 'present') {
    return <SignIn methods={probe.methods} error={error} />
  }

  return <>{children}</>
}

export default AuthGate
