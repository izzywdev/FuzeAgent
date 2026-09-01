import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import mdx from '@mdx-js/rollup'
import federation from '@originjs/vite-plugin-federation'
import path from 'path'

// Module Federation contract (must match registration/manifest.json — slug: "fuzeagent"):
//   scope  = "fuzeagentApp"        (federation `name`)
//   module = "./FuzeAgentApp"      (exposed module)
//   remoteEntry served SAME-ORIGIN under the FuzeFront portal shell at
//   https://app.fuzefront.com/apps/fuzeagent/remoteEntry.js — NOT the old
//   cross-origin https://fuzeagent.prod.fuzefront.com/remoteEntry.js. That host
//   sits behind the Cloudflare Access wall, so the browser's fetch of it (no
//   Access session) got an HTML login page back instead of JS and Module
//   Federation failed with "Failed to fetch dynamically imported module".
//   Slug is 'fuzeagent' per registration/manifest.json and FuzeFront's builtin
//   registry entry (app-registry/builtins.ts:35) — do not change it.
// React / react-dom are shared singletons so FuzeFront's React instance is reused.
export default defineConfig({
  plugins: [
    { enforce: 'pre', ...mdx() },
    react(),
    federation({
      name: 'fuzeagentApp',
      filename: 'remoteEntry.js',
      exposes: {
        './FuzeAgentApp': './src/App',
      },
      // Explicit singleton config, byte-matching the FuzeFront host
      // (frontend/vite.config.ts: react/react-dom singletons at ^19.0.0).
      // The previous bare-array `shared: ['react', 'react-dom']` shorthand
      // bundles this remote's OWN React copy rather than declaring a real
      // singleton, so it worked only by accident (no runtime version check
      // against the host at all). Declaring requiredVersion here is what
      // makes a genuine host/remote mismatch fail loudly instead of silently
      // shipping two React copies. See FuzeFront's MF-singleton-mismatch fix.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      shared: {
        react: { singleton: true, requiredVersion: '^19.0.0' },
        'react-dom': { singleton: true, requiredVersion: '^19.0.0' },
      } as any,
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // MUST match deploy/helm/fuzeagent/values.yaml's federatedMount.path AND the
  // vendored registration/manifest.json's integration.remoteEntry exactly, or
  // remoteEntry.js 200s while every chunk it references 404s (blank portal
  // panel, green healthcheck) -- see federated-mount-ingress.yaml's comment.
  // This same build is ALSO served at the root of this app's own admin-console
  // host (fuzeagent.prod.fuzefront.com/) -- nginx.conf aliases the
  // /apps/fuzeagent/ prefix straight back to the flat docroot, so index.html's
  // own asset references (also under this base) resolve there too.
  base: '/apps/fuzeagent/',
  build: {
    target: 'esnext',
    minify: false,
    cssCodeSplit: false,
    // Flat output (no nested assets/ subdir): the Dockerfile copies dist/
    // straight to the nginx docroot and nginx.conf aliases /apps/fuzeagent/
    // to that docroot, so every asset path under the base above must resolve
    // one level down, not under an extra assets/ segment.
    assetsDir: '',
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    cors: true,
  },
})
