import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Static build: relative base so the site works from any folder or static host.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  server: { port: 5174, host: "127.0.0.1" },
  // The main chunk is mostly Observable Plot + d3 (~185 kB gzipped), needed by the landing page;
  // secondary pages and the map geometry are split into their own chunks.
  build: { chunkSizeWarningLimit: 650 },
});
