/**
 * usePlatformBridge — graceful bridge to @izzywdev/fuzefront-sdk-react.
 * Degrades silently when the package is absent (standalone / dev mode).
 *
 * Strategy
 * --------
 * We cannot call SDK hooks (useGlobalMenu) conditionally or inside async
 * callbacks. So we keep two execution paths:
 *
 *  1. Platform present  → import SDK synchronously via a module-level
 *     try/catch wrapper.  The SDK hooks are called unconditionally but
 *     their results are only used when isInPlatform() returns true.
 *
 *  2. Package absent    → sdkReady stays false; all hooks are no-ops.
 */

/* eslint-disable @typescript-eslint/no-require-imports */
import { useEffect } from 'react'

// ---------------------------------------------------------------------------
// Synchronous module-level SDK load (try/catch so missing package is safe)
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SdkModule = any  // typed loosely so missing package doesn't break tsc

let sdk: SdkModule | null = null
let sdkReady = false

try {
  // When the package is present this import is resolved at bundle time.
  // When absent the try/catch catches the module-not-found error.
  sdk = require('@izzywdev/fuzefront-sdk-react')
  sdkReady = true
} catch {
  sdk = null
  sdkReady = false
}

// ---------------------------------------------------------------------------
// Runtime platform sentinel
// ---------------------------------------------------------------------------

export function isInPlatform(): boolean {
  if (typeof window === 'undefined') return false
  if ((window as Record<string, unknown>).__FUZEFRONT__) return true
  if (sdkReady && sdk?.isInPlatform) {
    try {
      return sdk.isInPlatform()
    } catch {
      return false
    }
  }
  return false
}

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface PlatformUser {
  userId: string
  email?: string
  tenantId: string | null
  roles: string[]
}

// ---------------------------------------------------------------------------
// usePlatformUser
// ---------------------------------------------------------------------------

/**
 * Returns the authenticated platform user when running inside FuzeFront,
 * or null in standalone mode.
 */
export function usePlatformUser(): PlatformUser | null {
  // Read from the window sentinel that PlatformProvider populates.
  if (!isInPlatform()) return null
  try {
    const sentinel = (window as Record<string, unknown>).__FUZEFRONT__ as
      | { user?: PlatformUser }
      | undefined
    return sentinel?.user ?? null
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// useMenuRegistrar
// ---------------------------------------------------------------------------

const MENU_ITEMS = [
  { label: 'Dashboard', path: '/' },
  { label: 'Agents', path: '/agents' },
  { label: 'Teams', path: '/teams' },
  { label: 'Hierarchy', path: '/hierarchy' },
  { label: 'Goals', path: '/goals' },
  { label: 'Playground', path: '/playground' },
]

/**
 * Registers FuzeAgent's navigation entries into the FuzeFront global menu.
 *
 * Rules of Hooks requirement: useGlobalMenu() must always be called (not
 * conditionally). We satisfy this by calling it unconditionally when the SDK
 * module loaded, then gating the addAppMenuItems side-effect on isInPlatform().
 */
export function useMenuRegistrar(): void {
  // Call the SDK hook unconditionally (when SDK is present); get a stable
  // menu handle (or a stub when the SDK isn't available).
  const menu: { addAppMenuItems?: (appId: string, items: typeof MENU_ITEMS) => void } =
    sdkReady && sdk?.useGlobalMenu
      ? sdk.useGlobalMenu()          // real hook — always called at hook level
      : {}                            // stub — no SDK, no-op

  useEffect(() => {
    if (!isInPlatform()) return
    if (typeof menu.addAppMenuItems !== 'function') return
    try {
      menu.addAppMenuItems('fuzeagent', MENU_ITEMS)
    } catch {
      // SDK present but API mismatch — degrade silently
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
