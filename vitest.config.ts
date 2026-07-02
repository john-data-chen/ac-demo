import path from "path";

import { defineConfig } from "vitest/config";

// apps/api is Python (FastAPI + pytest) since the NestJS migration — vitest only covers web.
export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["apps/web/__tests__/**/*.test.{ts,tsx}"],
    exclude: ["**/node_modules/**", "apps/web/__tests__/e2e/**", "packages"],
    setupFiles: ["./vitest.setup.ts"],
    alias: {
      "@web": path.resolve(__dirname, "./apps/web/src")
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html", "lcov"],
      include: ["apps/web/src/**/*.{ts,tsx}"],
      exclude: [
        "**/node_modules/**",
        "**/__tests__/**",
        "**/dist/**",
        "**/.turbo/**",
        "**/.next/**",
        "**/coverage/**",
        "**/packages/**"
      ]
    }
  },
  resolve: {
    alias: {
      "@web": path.resolve(__dirname, "./apps/web/src")
    }
  }
});
