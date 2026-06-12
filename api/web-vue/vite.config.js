import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/web/',
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://localhost:8765',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'https://localhost:8765',
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
})
