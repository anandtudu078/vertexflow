import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const BACKEND_URL = process.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // The FastAPI backend does not send CORS headers, so the browser cannot call
    // it directly from the dev server. Proxy the same-origin paths through Vite.
    proxy: {
      '/api': { target: BACKEND_URL, changeOrigin: true },
      '/health': {
        target: BACKEND_URL,
        changeOrigin: true,
        rewrite: () => '/',
      },
    },
  },
})
