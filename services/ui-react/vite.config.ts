import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import mdx from '@mdx-js/rollup'
import federation from '@originjs/vite-plugin-federation'
import path from 'path'

// Module Federation contract (must match the FuzeFront app-registry builtin manifest):
//   scope  = "fuzeagentApp"        (federation `name`)
//   module = "./FuzeAgentApp"      (exposed module)
//   remoteEntry served at https://fuzeagent.prod.fuzefront.com/remoteEntry.js
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
  // Served at the root of fuzeagent.prod.fuzefront.com.
  // remoteEntry.js → https://fuzeagent.prod.fuzefront.com/remoteEntry.js
  base: '/',
  build: {
    target: 'esnext',
    minify: false,
    cssCodeSplit: false,
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    cors: true,
  },
})
