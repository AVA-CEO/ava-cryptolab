import type { NextConfig } from "next";

const config: NextConfig = {
  devIndicators:
    process.env.AVA_E2E === "1" ? false : { position: "bottom-right" },
  distDir:
    process.env.AVA_PRACTICE === "1"
      ? ".next-practice"
      : process.env.AVA_E2E === "1"
        ? ".next-e2e"
        : ".next",
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
};
export default config;
