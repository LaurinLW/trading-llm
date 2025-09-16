import { defineConfig } from 'vite';
import dotenv from 'dotenv';

dotenv.config();

export default defineConfig({
  root: 'website',
  base: '/trading/',
  define: {
    'process.env': process.env,
  },
});
