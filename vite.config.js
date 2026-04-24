import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [tailwindcss(),react()],
  server: {
    proxy: {
      // Forward /api/* to FastAPI on 8000
      // anything starting with /api goes to FastAPI at :8000
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        // /api/ask  ->  /ask
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  
})
