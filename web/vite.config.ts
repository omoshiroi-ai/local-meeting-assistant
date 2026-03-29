import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
        // Long-lived SSE (chat) and slow local LLM loads — avoid proxy socket hang-up
        timeout: 0,
        proxyTimeout: 0,
      },
    },
  },
});
