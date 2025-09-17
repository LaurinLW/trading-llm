import { defineConfig } from 'vite';
import dotenv from 'dotenv';

dotenv.config();

export default defineConfig({
  root: 'website',
  base: '/trading/',
  define: {
    'process.env.BACKEND_URL': JSON.stringify(process.env.BACKEND_URL),
    'process.env.WEBSOCKET_URL': JSON.stringify(process.env.WEBSOCKET_URL),
  },
});
