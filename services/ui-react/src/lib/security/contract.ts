/**
 * FuzeFront Security contract — types.
 *
 * These mirror `@izzywdev/fuzefront-security-client` (published under `@izzywdev/` on GitHub Packages,
 * generated from FuzeFront's `packages/security/openapi.yaml`) one-for-one.
 *
 * Package Scope Convention:
 * GitHub Packages mandates that published package scopes match the owning account (`@izzywdev/`).
 * Internal workspace packages named `@fuzefront/<pkg>` publish as `@izzywdev/fuzefront-<pkg>`.
 *
 * When the private registry is wired up for this repo, replace imports with:
 *
 *     import type { Identity, AuthMethods, SessionResult } from '@izzywdev/fuzefront-security-client'
 *
 * Contract: FuzeFront Security API v0.4.0 / `@izzywdev/fuzefront-security-client` v0.2.0.
 */

/** Which verifier produced an identity. Provider-neutral by contract. */
export type AuthMode = 'legacy-hs256' | 'federated-jwks'

/**
 * The stable, normalized identity every consumer receives regardless of which verifier
 * produced it. The contract's keystone — invariant across token-format migrations.
 */
export interface Identity {
  /** Stable subject identifier. Always present. */
  userId: string
  /**
   * Tenant/organization scope. `null` when unknown; consumers fail closed on
   * tenant-scoped decisions when this is null.
   */
  tenantId: string | null
  /** Role slugs. Always an array; empty means "no roles known". */
  roles: string[]
  email?: string
  authMode: AuthMode
  issuedAt?: number
  expiresAt?: number
  issuer?: string
}

/** Hydrated user record returned alongside the identity by `GET /session`. */
export interface SecurityUser {
  id: string
  email: string
  roles: string[]
  [key: string]: unknown
}

/** `GET /v1/security/session` response. */
export interface SessionInfo {
  identity: Identity
  user: SecurityUser
}

/** Supported social provider slugs. Extensible; `google` is first. */
export type SocialProvider = 'google'

/** Neutral MFA factor type. */
export type MfaFactorType = 'totp' | 'sms' | 'email' | 'webauthn'

/**
 * Neutral capability descriptor for the auth surface — what sign-in methods this
 * deployment actually offers. Read it; never hard-code a provider list.
 */
export interface AuthMethods {
  password: boolean
  social: SocialProvider[]
  mfa: { enabled: boolean; types: MfaFactorType[] }
  verification: { email: boolean; sms: boolean }
}

/**
 * Discriminated login/exchange outcome: an authenticated session, or an MFA-required
 * challenge. Narrow on `status` before reading variant fields.
 */
export type SessionResult =
  | { status: 'authenticated'; token: string; sessionId?: string; user: unknown }
  | {
      status: 'mfa_required'
      challengeId: string
      factors: { factorId: string; type: MfaFactorType }[]
    }

/** A resource-instance reference for a (possibly ReBAC-scoped) decision. */
export interface ResourceRef {
  type: string
  key?: string
}

/** `POST /v1/security/authz/check` request. */
export interface AuthzCheckRequest {
  subject: string
  tenant: string
  resource: ResourceRef
  action: string
  context?: Record<string, unknown>
}

/** `POST /v1/security/authz/check` response. */
export interface AuthzDecision {
  allow: boolean
}

/** `POST /v1/security/authz/bulk-check` response — index-aligned with the request. */
export interface AuthzBulkDecision {
  decisions: AuthzDecision[]
}

/** `GET /v1/security/authz/permissions` response. Effective `Resource:action` grants. */
export interface PermissionSet {
  subject: string
  tenant: string
  permissions: string[]
}

/** Stable, provider-neutral error codes. Fail-closed. */
export type SecurityErrorCode =
  | 'NO_TOKEN'
  | 'MALFORMED'
  | 'INVALID_SIGNATURE'
  | 'EXPIRED'
  | 'NOT_ACTIVE'
  | 'INVALID_ISSUER'
  | 'INVALID_AUDIENCE'
  | 'MISSING_CLAIM'
  | 'JWKS_UNAVAILABLE'
  | 'VERIFIER_UNAVAILABLE'
  | 'INVALID_CREDENTIALS'
  | 'INVALID_CODE'
  | 'CONFLICT'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'PROVIDER_UNAVAILABLE'
  | 'UNKNOWN'

// ---------------------------------------------------------------------------
// FuzeAgent's own policy vocabulary — the BARE keys registered in
// registration/policy.json. These are what we send as `resource.type` / `action`.
// They are FuzeAgent's vocabulary; the engine that evaluates them is the platform's
// business and is never named here.
// ---------------------------------------------------------------------------

export const RESOURCE = {
  Organization: 'Organization',
  Team: 'Team',
  Agent: 'Agent',
  Task: 'Task',
  Goal: 'Goal',
} as const

export const ACTION = {
  read: 'read',
  create: 'create',
  update: 'update',
  delete: 'delete',
  deploy: 'deploy',
  assign: 'assign',
} as const

export type ResourceKey = (typeof RESOURCE)[keyof typeof RESOURCE]
export type ActionKey = (typeof ACTION)[keyof typeof ACTION]
