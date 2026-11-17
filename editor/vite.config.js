import {defineConfig} from 'vite';
export default defineConfig({base:'/static/cowork/',build:{target:'es2022',outDir:'../static/cowork',emptyOutDir:true,chunkSizeWarningLimit:6000}});
