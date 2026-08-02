/**
 * SignIn — the sign-in surface, rendered only in STANDALONE mode by `AuthGate`.
 *
 * FuzeAgent does not authenticate anybody. This screen is a redirect surface: it
 * renders whatever methods the platform advertises (`GET /api/v1/security/methods`,
 * fetched by `AuthGate`) and hands the browser to FuzeFront's own server-brokered
 * start endpoint (`/api/v1/security/social/{provider}/start`). FuzeFront brokers
 * onward and returns a single-use `code`, which `SecurityProvider` exchanges for a
 * session.
 *
 * There is deliberately NO password form here. `POST /v1/security/session` (password
 * login) exists in the contract, but a product-side password form would mean FuzeAgent
 * handling user credentials — precisely what delegating identity is meant to prevent,
 * and what `.semgrep/fuze-authz.yml` forbids. Password sign-in belongs on FuzeFront's
 * own surface; when the deployment advertises `password: true` we say so and point
 * there instead of collecting the password ourselves.
 *
 * Embedded in the FuzeFront shell this never renders: the host has already
 * authenticated the user and `SecurityProvider` picks the identity up from the shell.
 */

import type { AuthMethods } from '../../lib/security/contract'
import { socialStartUrl } from '../../lib/security/client'

const PROVIDER_LABELS: Record<string, string> = {
  google: 'Continue with Google',
}

function providerLabel(provider: string): string {
  return PROVIDER_LABELS[provider] ?? `Continue with ${provider}`
}

export interface SignInProps {
  /** What the platform advertises. Never hard-code a provider list. */
  methods: AuthMethods
  /** Non-fatal message from a previous sign-in attempt (e.g. a spent broker code). */
  error?: string | null
}

export function SignIn({ methods, error }: SignInProps) {
  const returnTo = typeof window === 'undefined' ? '/' : window.location.href

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-6 text-center">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Sign in to FuzeAgent</h1>
          <p className="text-sm text-muted-foreground">
            FuzeAgent uses your FuzeFront account.
          </p>
        </div>

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}

        <div className="space-y-3">
          {methods.social.map((provider) => (
            <a
              key={provider}
              href={socialStartUrl(provider, returnTo)}
              className="block w-full rounded-md border px-4 py-2 text-sm font-medium"
            >
              {providerLabel(provider)}
            </a>
          ))}

          {methods.password && (
            <p className="text-sm text-muted-foreground">
              Password sign-in is handled by FuzeFront. Sign in there, then return here.
            </p>
          )}

          {/* Empty state — auth is configured but no method is switched on. */}
          {methods.social.length === 0 && !methods.password && (
            <p className="text-sm text-muted-foreground">
              No sign-in method is enabled for this deployment. Contact your
              administrator.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default SignIn
