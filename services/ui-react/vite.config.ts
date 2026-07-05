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
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      shared: ['react', 'react-dom'] as any,
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
