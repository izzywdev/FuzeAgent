import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import mdx from '@mdx-js/rollup'
import federation from '@originjs/vite-plugin-federation'
import path from 'path'

// Module Federation contract (must match registration/manifest.json — slug: "fuzeagent"):
//   scope  = "fuzeagentApp"        (federation `name`)
//   module = "./FuzeAgentApp"      (exposed module)
//   remoteEntry served SAME-ORIGIN under the FuzeFront portal shell at
//   https://app.fuzefront.com/apps/fuzeagent/remoteEntry.js
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
  base: '/apps/fuzeagent/',
  build: {
    target: 'esnext',
    minify: false,
    cssCodeSplit: false,
    assetsDir: '',
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    cors: true,
  },
})
