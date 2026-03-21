import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8686',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8686',
        ws: true,
      },
      '/discover.json': 'http://localhost:8686',
      '/lineup.json': 'http://localhost:8686',
      '/lineup_status.json': 'http://localhost:8686',
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
