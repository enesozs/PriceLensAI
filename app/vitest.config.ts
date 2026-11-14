import { defineConfig } from "vitest/config";

// Unit tests only; e2e/ holds the Playwright smoke tests (npm run e2e).
export default defineConfig({ test: { include: ["src/**/*.test.ts"] } });
