import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const proxyTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";
const usePolling = process.env.VITE_USE_POLLING === "1";

export default defineConfig({
  plugins: [react()],
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
    },
  },
});
