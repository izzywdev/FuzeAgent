/* eslint-disable @typescript-eslint/no-require-imports */
import { StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import AppRouter from './components/AppRouter.tsx'
import { SecurityProvider } from './lib/security/SecurityProvider'
import AuthGate from './components/auth/AuthGate'
import { initBrowserRum, initBrowserTelemetry } from '@izzywdev/fuzefront-telemetry/browser'

// ---------------------------------------------------------------------------
// Observability (docs: FuzeFront governance/observability-standard.md P29-P36)
// ---------------------------------------------------------------------------
// As early as possible, before any fetch/XHR, so API calls carry `traceparent`
// and continue the server trace. Same-origin OTLP and RUM ingest by default;
// set VITE_TELEMETRY_ENABLED=false to turn both off.
if (import.meta.env.VITE_TELEMETRY_ENABLED !== 'false') {
  initBrowserTelemetry({
    serviceName: 'fuzeagent-ui',
    serviceVersion: import.meta.env.VITE_APP_RELEASE,
    otlpEndpoint: import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT,
  })
  initBrowserRum({
    serviceName: 'fuzeagent-ui',
    release: import.meta.env.VITE_APP_RELEASE || import.meta.env.MODE,
    sampleRate: Number(import.meta.env.VITE_RUM_SAMPLE_RATE ?? 1),
  })
}

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
  const sdk = require('@izzywdev/fuzefront-sdk-react')
  PlatformProvider = sdk.PlatformProvider ?? null
  sdkIsInPlatform = sdk.isInPlatform ?? null
} catch {
  PlatformProvider = null
  sdkIsInPlatform = null
}

function inPlatform(): boolean {
  if (typeof window === 'undefined') return false
  if (window.parent === window) return false
  if ((window as unknown as Record<string, unknown>).__FUZEFRONT__) return true
  if (sdkIsInPlatform) {
    try { return sdkIsInPlatform() } catch { return false }
  }
  return false
}

function AppWithPlatform(): React.ReactElement {
  // Identity + permissions come from the FuzeFront Security API (or, when embedded,
  // from the shell). AuthGate shows the sign-in redirect surface only when the
  // platform actually advertises sign-in methods — see AuthGate for why.
  const app = (
    <SecurityProvider>
      <AuthGate>
        <AppRouter />
      </AuthGate>
    </SecurityProvider>
  )

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
