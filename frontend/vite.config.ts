import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Forward API calls to the FastAPI dev server so the browser sees one origin.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
