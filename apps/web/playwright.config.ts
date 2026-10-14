import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    reducedMotion: "reduce",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
  webServer: [
    {
      command:
        process.platform === "win32"
          ? `"${resolve(__dirname, "../../.venv/Scripts/python.exe")}" scripts/e2e_server.py`
          : `"${resolve(__dirname, "../../.venv/bin/python")}" scripts/e2e_server.py`,
      cwd: resolve(__dirname, "../../services/api"),
      url: "http://127.0.0.1:8001/api/v1/ready",
      reuseExistingServer: false,
      timeout: 120000,
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3100",
      url: "http://127.0.0.1:3100",
      env: { API_BASE_URL: "http://127.0.0.1:8001", AVA_E2E: "1" },
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
});
