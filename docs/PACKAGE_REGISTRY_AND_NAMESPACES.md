# FuzeFront Ecosystem Package Registry & Namespace Guide

## 1. Registry Architecture & Scope Mapping

All shared packages built across the **FuzeFront** ecosystem are published to the **GitHub Packages Registry** under the account scope:

> **`@izzywdev/`** (NOT `@fuzefront/`)

### Why `@izzywdev/`?
GitHub Packages enforces that package scopes must match the owning personal or organization account on GitHub (`izzywdev`). 
Inside the `FuzeFront` monorepo (`izzywdev/FuzeFront`), internal workspace packages are named `@fuzefront/<package-name>`. When published via GitHub Actions, each package is automatically renamed to:

$$\text{@fuzefront/<name>} \longrightarrow \mathbf{@izzywdev/fuzefront-<name>}$$

Attempting to install `@fuzefront/<name>` from GitHub Packages will fail with:
```
npm error 404 Not Found - GET https://npm.pkg.github.com/@fuzefront%2f<name>
npm error 404 npm package "<name>" does not exist under owner "fuzefront"
```

---

## 2. Package Name Resolution Table

| Internal Monorepo Name (`FuzeFront`) | Published GitHub Package Name | Current Version | Usage in Consuming Apps (`FuzeAgent`, `FuzeX`, etc.) |
|---|---|---|---|
| `@fuzefront/design-system` | **`@izzywdev/fuzefront-design-system`** | `^1.2.0` | Token-driven "fuse seam" React component library & core styling |
| `@fuzefront/identity` | **`@izzywdev/fuzefront-identity`** | `^1.0.0` | Identity contracts, session models, and tenant context |
| `@fuzefront/identity-ui` | **`@izzywdev/fuzefront-identity-ui`** | `^0.1.0` | Org members, roles, and API token administration UI |
| `@fuzefront/security-client` | **`@izzywdev/fuzefront-security-client`** | `^0.9.0` | Security API client generated from FuzeFront OpenAPI spec |
| `@fuzefront/billing-ui` | **`@izzywdev/fuzefront-billing-ui`** | `^1.0.0` | Subscription, invoice, and payment method checkout panel |
| `@fuzefront/chat-ui` | **`@izzywdev/fuzefront-chat-ui`** | `^1.2.3` | Real-time chat interface components |
| `@fuzefront/chat-client` | **`@izzywdev/fuzefront-chat-client`** | `^1.1.0` | WebSocket chat client library |
| `@fuzefront/telemetry` | **`@izzywdev/fuzefront-telemetry`** | `^0.1.0` | Distributed OpenTelemetry tracing & structured logging |
| `@fuzefront/feature-flags` | **`@izzywdev/fuzefront-feature-flags`** | `^1.0.1` | Feature flag evaluation and Unleash client |
| `@fuzefront/portal-branding-ui` | **`@izzywdev/fuzefront-portal-branding-ui`** | `^0.1.0` | White-label branding and theme customization |
| `@fuzefront/core` | **`@izzywdev/fuzefront-core`** | `^1.0.0` | Core shared utilities and event buses |

---

## 3. Configuration in Consuming Applications

In any consuming application (e.g. `FuzeAgent/services/ui-react`), configure `.npmrc` at the directory containing `package.json`:

```ini
# Scope -> registry mapping
@izzywdev:registry=https://npm.pkg.github.com
@fuzefront:registry=https://npm.pkg.github.com

# Authenticate using GITHUB_TOKEN
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
always-auth=true
```

In `package.json`, specify the dependency with the `@izzywdev/` prefix:
```json
{
  "dependencies": {
    "@izzywdev/fuzefront-design-system": "^1.2.0",
    "@izzywdev/fuzefront-identity": "^1.0.0"
  }
}
```

In local development with Vite (`vite.config.ts`), aliases allow resolving either scope directly from the local monorepo when checked out side-by-side:
```typescript
resolve: {
  alias: {
    "@": path.resolve(__dirname, "./src"),
    "@izzywdev/fuzefront-design-system": path.resolve(__dirname, "../../../FuzeFront/design-system"),
    "@fuzefront/design-system": path.resolve(__dirname, "../../../FuzeFront/design-system"),
  },
}
```
