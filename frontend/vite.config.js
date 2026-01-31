import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // SSE requires these settings
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            // Ensure proper headers for SSE
            proxyReq.setHeader('Accept', 'text/event-stream');
          });
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Optimize chunk size
    chunkSizeWarningLimit: 1000,
  },
})
