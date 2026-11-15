import { defineConfig } from 'vite';
export default defineConfig({server: {proxy: {'/api': {target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000', rewrite: path => /^\/api\/(health|disputes|notices)(\/|$)/.test(path) ? path.replace(/^\/api/, '') : path}}}});
