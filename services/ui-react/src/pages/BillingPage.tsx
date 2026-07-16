/**
 * BillingPage — renders the @fuzefront/billing-ui panel.
 * Degrades gracefully to a plain message when the package is absent.
 */

import React from 'react'

// ---------------------------------------------------------------------------
// Try to import billing-ui at module level (safe when package is absent)
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type BillingComponents = {
  UsagePanel: React.ComponentType<Record<string, unknown>>
  SubscriptionManager: React.ComponentType<{
    subscription: Subscription
    onUpgrade?: (priceId: string) => void
    onCancel?: () => void
    onReactivate?: () => void
  }>
  BillingI18nProvider: React.ComponentType<{ children: React.ReactNode }>
}

interface Subscription {
  id: string
  status: string
  priceId: string
  currentPeriodEnd: string
}

let billing: BillingComponents | null = null

try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  billing = require('@fuzefront/billing-ui')
  // Styles — import via require so the try/catch covers the CSS too.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  require('@fuzefront/billing-ui/styles.css')
} catch {
  billing = null
}

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_SUBSCRIPTION: Subscription = {
  id: 'sub_1',
  status: 'active',
  priceId: 'price_starter',
  currentPeriodEnd: new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString(),
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BillingPage(): React.ReactElement {
  if (!billing) {
    return (
      <div style={{ padding: '2rem' }}>
        <h1>Billing &amp; Usage</h1>
        <p style={{ color: '#888', marginTop: '1rem' }}>
          Billing UI is not available in this environment.
        </p>
      </div>
    )
  }

  const { BillingI18nProvider, SubscriptionManager, UsagePanel } = billing

  const handleUpgrade = (priceId: string) => {
    console.info('[BillingPage] upgrade requested for', priceId)
  }

  const handleCancel = () => {
    console.info('[BillingPage] cancel requested')
  }

  const handleReactivate = () => {
    console.info('[BillingPage] reactivate requested')
  }

  return (
    <BillingI18nProvider>
      <div style={{ padding: '2rem', maxWidth: '900px' }}>
        <h1 style={{ marginBottom: '1.5rem', fontSize: '1.5rem', fontWeight: 600 }}>
          Billing &amp; Usage
        </h1>

        <SubscriptionManager
          subscription={MOCK_SUBSCRIPTION}
          onUpgrade={handleUpgrade}
          onCancel={handleCancel}
          onReactivate={handleReactivate}
        />

        <div style={{ marginTop: '2rem' }}>
          <UsagePanel />
        </div>
      </div>
    </BillingI18nProvider>
  )
}
