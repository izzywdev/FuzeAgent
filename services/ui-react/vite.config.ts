import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import mdx from '@mdx-js/rollup'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    { enforce: 'pre', ...mdx() },
    react()
  ],
  resolve: {
    alias: {
      "@": "/app/src",
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
})
