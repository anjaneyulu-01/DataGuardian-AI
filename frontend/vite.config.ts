import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// The project keeps ONE .env at the repository root, shared with the backend
// and docker-compose. `envDir` points Vite there instead of at frontend/.
//
// Safe despite that file holding server-side secrets: Vite only inlines
// VITE_-prefixed variables into the browser bundle. XAI_API_KEY and friends
// are visible to this config at build time but never shipped to the client.
const repoRoot = fileURLToPath(new URL('..', import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repoRoot, '')
  const backendUrl = env.VITE_BACKEND_URL ?? 'http://localhost:8000'

  return {
    envDir: repoRoot,
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: 5173,
      // Lets the app call FastAPI as a same-origin `/api/...` path in dev, so
      // there is no CORS pre-flight and no backend host hard-coded in the code.
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
  }
})
