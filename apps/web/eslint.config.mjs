import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
export default defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    ".next-e2e/**",
    ".next-practice/**",
    ".next-p3/**",
    ".next-p3-e2e/**",
    "next-env.d.ts",
    "playwright-report/**",
    "test-results/**",
  ]),
]);
