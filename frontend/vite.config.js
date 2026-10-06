import { defineConfig } from 'vite';

export default defineConfig({
  base: '/',
  build: {
    outDir: '../apk_audit/web_assets',
    emptyOutDir: false,
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        entryFileNames: 'app.js',
        assetFileNames: 'app.css',
      },
    },
  },
});
