import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the API runs on :8000. In Docker and Kubernetes the browser
// only ever talks to /api on the same origin (nginx or the Ingress route it).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: process.env.API_URL || "http://localhost:8000", changeOrigin: true },
    },
  },
  build: { sourcemap: false, chunkSizeWarningLimit: 700 },
});
