/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const proxyTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";
// The local mail catcher, read by the demo login to fill the code (PLAN.md D25). Never a real mail server.
const mailpitTarget = process.env.MAILPIT_PROXY_TARGET ?? "http://localhost:8025";
const usePolling = process.env.VITE_USE_POLLING === "1";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
  },
  server: {
    host: true,
    port: 5173,
    watch: usePolling ? { usePolling: true } : undefined,
    proxy: {
      "/api": {
        target: proxyTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/mailpit": {
        target: mailpitTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/mailpit/, ""),
      },
    },
  },
});
