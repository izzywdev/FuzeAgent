/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Set to 'false' to disable browser tracing + RUM (see main.tsx).
  readonly VITE_TELEMETRY_ENABLED?: string
  // OTLP/HTTP endpoint for browser tracing. Optional; defaults to same-origin '/v1/traces'.
  readonly VITE_OTEL_EXPORTER_OTLP_ENDPOINT?: string
  // App release/version stamped on every RUM payload. Optional; falls back to the Vite MODE.
  readonly VITE_APP_RELEASE?: string
  // Fraction (0..1) of sessions reporting RUM vitals/timing. Optional; defaults to 1.
  readonly VITE_RUM_SAMPLE_RATE?: string
}

declare module '*.mdx' {
  import { ComponentType } from 'react'
  const Component: ComponentType
  export default Component
}

declare module '*.md' {
  import { ComponentType } from 'react'
  const Component: ComponentType
  export default Component
}
