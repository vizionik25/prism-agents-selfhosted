import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const isDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone',
  ...(isDemoMode && {
    async headers() {
      return [
        {
          source: "/(.*)",
          headers: [
            // Allow iframe embedding from any origin in demo mode
            { key: "X-Frame-Options", value: "ALLOWALL" },
            { key: "Content-Security-Policy", value: "frame-ancestors *" },
          ],
        },
      ];
    },
  }),
};

export default withSentryConfig(nextConfig, {
  org: "vizionik-media",
  project: "prism-agents-frontend",

  // Source map upload; set SENTRY_AUTH_TOKEN in .env.sentry-build-plugin
  // (gitignored) or as a Vercel env var.
  authToken: process.env.SENTRY_AUTH_TOKEN,

  // Upload a wider set of client source files for better stack trace resolution.
  widenClientFileUpload: true,

  // Proxy API route to bypass ad-blockers.
  tunnelRoute: "/monitoring",

  // Suppress non-CI output.
  silent: !process.env.CI,
});
