import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";

const python = `"${resolve(__dirname, process.platform === "win32" ? "../../.venv/Scripts/python.exe" : "../../.venv/bin/python")}"`;
const api = resolve(__dirname, "../../services/api");

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3110",
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
      command: `${python} scripts/e2e_server.py --port 8011`,
      cwd: api,
      url: "http://127.0.0.1:8011/api/v1/ready",
      reuseExistingServer: false,
      timeout: 120000,
    },
    {
      command: `${python} scripts/e2e_cfd_server.py --port 8013`,
      cwd: api,
      port: 8013,
      reuseExistingServer: false,
      timeout: 120000,
    },
    {
      command: `${python} scripts/e2e_personal_server.py`,
      cwd: api,
      port: 8014,
      reuseExistingServer: false,
      timeout: 180000,
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3110",
      url: "http://127.0.0.1:3110",
      reuseExistingServer: false,
      timeout: 120000,
      env: {
        API_BASE_URL: "http://127.0.0.1:8011",
        CFD_API_BASE_URL: "http://127.0.0.1:8013",
        CFD_JOURNAL_API_BASE_URL: "http://127.0.0.1:8014",
        AVA_E2E: "1",
        AVA_CFD_P3: "1",
      },
    },
  ],
});
