import { StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import AppRouter from './components/AppRouter.tsx'

// ---------------------------------------------------------------------------
// Optional FuzeFront platform integration
// ---------------------------------------------------------------------------
// We attempt to load PlatformProvider from @izzywdev/fuzefront-sdk-react.
// When the package is absent (standalone dev, CI) we fall back to a plain
// passthrough wrapper — nothing breaks.
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let PlatformProvider: React.ComponentType<{ children: ReactNode }> | null = null
let sdkIsInPlatform: (() => boolean) | null = null

try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const sdk = require('@izzywdev/fuzefront-sdk-react')
  PlatformProvider = sdk.PlatformProvider ?? null
  sdkIsInPlatform = sdk.isInPlatform ?? null
} catch {
  PlatformProvider = null
  sdkIsInPlatform = null
}

function inPlatform(): boolean {
  if (typeof window === 'undefined') return false
  if ((window as Record<string, unknown>).__FUZEFRONT__) return true
  if (sdkIsInPlatform) {
    try { return sdkIsInPlatform() } catch { return false }
  }
  return false
}

function AppWithPlatform(): React.ReactElement {
  const app = <AppRouter />

  if (PlatformProvider && inPlatform()) {
    return <PlatformProvider>{app}</PlatformProvider>
  }

  return app
}

// ---------------------------------------------------------------------------
// Mount
// ---------------------------------------------------------------------------

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppWithPlatform />
  </StrictMode>,
)
