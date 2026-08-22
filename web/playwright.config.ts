import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  use: {
    baseURL: "http://127.0.0.1:3200",
    trace: "on-first-retry",
  },
  webServer: {
    command: "node ./node_modules/next/dist/bin/next dev",
    env: {
      ...process.env,
      PORT: "3200",
      NEXT_PUBLIC_API_URL: "http://127.0.0.1:4010",
      NEXT_PUBLIC_COGNITO_REGION: "us-east-1",
      NEXT_PUBLIC_COGNITO_USER_POOL_ID: "us-east-1_tracevault",
      NEXT_PUBLIC_COGNITO_CLIENT_ID: "tracevault-client",
      NEXT_PUBLIC_COGNITO_DOMAIN: "tracevault.auth.us-east-1.amazoncognito.com",
    },
    url: "http://127.0.0.1:3200",
    reuseExistingServer: !process.env.CI,
  },
});
