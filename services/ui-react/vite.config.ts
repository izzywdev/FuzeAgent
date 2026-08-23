import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import mdx from '@mdx-js/rollup'
import federation from '@originjs/vite-plugin-federation'
import path from 'path'

// Module Federation contract (must match the FuzeFront app-registry builtin manifest):
//   scope  = "fuzeagentApp"        (federation `name`)
//   module = "./FuzeAgentApp"      (exposed module)
//   remoteEntry served SAME-ORIGIN under the FuzeFront portal shell at
//   https://app.fuzefront.com/apps/fuzeagent/remoteEntry.js — NOT the old
//   cross-origin https://fuzeagent.prod.fuzefront.com/remoteEntry.js. That host
//   sits behind the Cloudflare Access wall, so the browser's fetch of it (no
//   Access session) got an HTML login page back instead of JS and Module
//   Federation failed with "Failed to fetch dynamically imported module".
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
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      shared: ['react', 'react-dom'] as any,
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
