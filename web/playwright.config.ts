import { defineConfig, devices } from "@playwright/test";

import { CYCLE_WAIT_MS, webUrl } from "./e2e/stack";

// The flows share one database and one Mailpit inbox, and a customer's demo code is the newest email: one worker,
// in file order, and no retry that could hide a flow that only passes the second time.
export default defineConfig({
  testDir: "e2e",
  testMatch: "*.e2e.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  timeout: 4 * CYCLE_WAIT_MS,
  expect: { timeout: CYCLE_WAIT_MS },
  outputDir: "e2e-results",
  reporter: [["list"], ["html", { outputFolder: "e2e-report", open: "never" }]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: webUrl(),
    viewport: { width: 1280, height: 800 },
    locale: "es-ES",
    timezoneId: "UTC",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
});
