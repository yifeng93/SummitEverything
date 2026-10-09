import react from '@vitejs/plugin-react'
import type { ProxyOptions } from 'vite'
import { defineConfig } from 'vitest/config'

const apiProxy: ProxyOptions = {
  target: process.env.SUMMIT_API_TARGET ?? 'http://127.0.0.1:8793',
  changeOrigin: false,
  configure(proxy) {
    proxy.on('proxyReq', (request) => {
      const token = process.env.SUMMIT_SESSION_TOKEN
      if (token) request.setHeader('Authorization', `Bearer ${token}`)
    })
  },
}

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    restoreMocks: true,
  },
  server: {
    host: '127.0.0.1',
    port: Number(process.env.SUMMIT_WEB_PORT ?? 5173),
    strictPort: true,
    proxy: { '/api': apiProxy },
  },
})
