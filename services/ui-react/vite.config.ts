import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import mdx from '@mdx-js/rollup'
import federation from '@originjs/vite-plugin-federation'
import path from 'path'

// Module Federation contract (must match the FuzeFront app-registry builtin manifest,
// registration/manifest.json):
//   scope  = "fuzeagentApp"        (federation `name`)
//   module = "./FuzeAgentApp"      (exposed module)
//   remoteEntry served SAME-ORIGIN at app.fuzefront.com/apps/fuzeagent/remoteEntry.js
//   (registration/manifest.json integration.remoteEntry) -- also reachable at
//   https://fuzeagent.prod.fuzefront.com/apps/fuzeagent/remoteEntry.js on the
//   standalone admin-console host, since this repo has ONE build for both
//   surfaces (see services/ui-react/nginx.conf's `^~ /apps/fuzeagent/` alias,
//   which maps the prefix back onto the flat docroot for both hosts).
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
  // MUST match deploy/helm/fuzeagent/values.yaml federatedMount.path exactly
  // ("/apps/fuzeagent") and registration/manifest.json's integration.remoteEntry
  // ("/apps/fuzeagent/remoteEntry.js") -- a mismatch 200s remoteEntry.js and
  // then 404s every chunk it imports. Was '/', stale from before this repo's
  // remote was mounted same-origin under the FuzeFront portal; nginx.conf's
  // `^~ /apps/fuzeagent/` alias already assumed this value.
  base: '/apps/fuzeagent/',
  build: {
    target: 'esnext',
    minify: false,
    cssCodeSplit: false,
    // Without this, @originjs/vite-plugin-federation emits remoteEntry.js at
    // `${assetsDir}/${filename}` (plugin default for assetsDir is "assets")
    // -> /apps/fuzeagent/assets/remoteEntry.js, one segment deeper than
    // registration/manifest.json's declared /apps/fuzeagent/remoteEntry.js.
    assetsDir: '',
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    cors: true,
  },
})
