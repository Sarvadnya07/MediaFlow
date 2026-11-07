import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // @ts-expect-error vitest config extension
  test: {
    globals: true,
    environment: 'jsdom',
  },
})
