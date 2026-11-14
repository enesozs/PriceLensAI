import { defineConfig, devices } from "@playwright/test";

// Smoke tests against the production build (npm run build first). Locally they use the installed Google Chrome;
// in CI the workflow installs Playwright's Chromium (PW_CHANNEL unset).
export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  use: { baseURL: "http://127.0.0.1:4181", channel: process.env.PW_CHANNEL ?? "chrome" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], channel: process.env.PW_CHANNEL ?? "chrome" } },
    { name: "phone", use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  webServer: { command: "npx vite preview --port 4181 --host 127.0.0.1 --strictPort", url: "http://127.0.0.1:4181", reuseExistingServer: false },
});
