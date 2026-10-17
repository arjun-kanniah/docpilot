import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // IPv4 explicitly: "localhost" can bind only ::1, which the dev container's port forwarding misses
    host: '127.0.0.1',
    // Forward API calls to the FastAPI dev server so the browser sees one origin.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
