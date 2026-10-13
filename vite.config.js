import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { viteSingleFile } from 'vite-plugin-singlefile';
import path from 'path';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    viteSingleFile(),
  ],
  root: path.resolve(__dirname, 'src/ui/react_src'),
  base: './',
  build: {
    outDir: path.resolve(__dirname, 'src/ui/dist'),
    emptyOutDir: true,
  },
});
