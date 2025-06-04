import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import path from 'path' // Import path module

// https://vite.dev/config/
export default defineConfig({
  plugins: [tailwindcss(),],
  resolve: { // Add resolve configuration
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
