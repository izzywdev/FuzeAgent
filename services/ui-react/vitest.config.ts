/// <reference types="vitest" />
/// <reference types="@testing-library/jest-dom" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/coverage/**',
        'dist/',
        'build/',
        '.next/',
        '.nuxt/',
        '.vscode/',
        '**/*.test.*',
        '**/*.spec.*',
      ],
      thresholds: {
        global: {
          branches: 60,
          functions: 60,
          lines: 60,
          statements: 60,
        },
        // Higher thresholds for critical components
        'src/components/pages/CreateAgentPage.tsx': {
          branches: 70,
          functions: 70,
          lines: 70,
          statements: 70,
        },
        'src/components/pages/FixedAgentsPage.tsx': {
          branches: 65,
          functions: 65,
          lines: 65,
          statements: 65,
        },
      },
    },
    include: ['src/**/*.{test,spec}.{js,ts,jsx,tsx}'],
    exclude: [
      'node_modules',
      'dist',
      '.idea',
      '.git',
      '.cache',
    ],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/test': path.resolve(__dirname, './src/test'),
    },
  },
})