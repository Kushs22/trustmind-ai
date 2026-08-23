import type { NextConfig } from "next";

/**
 * Launch security headers for Vercel / Next.
 * CSP allows Next inline bootstrapping, mic/blob media, and API connect.
 * Tighten further once a nonce-based CSP is adopted.
 */
const apiConnectSources = [
  "'self'",
  "http://127.0.0.1:8000",
  "http://localhost:8000",
  "https://trustmind-ai.onrender.com",
  // Allow the configured public API URL when set at build time.
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "",
]
  .filter(Boolean)
  .join(" ");

const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  // Next.js still relies on inline/eval for some runtime chunks in App Router.
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  `connect-src ${apiConnectSources}`,
  "media-src 'self' blob:",
  "worker-src 'self' blob:",
  "manifest-src 'self'",
].join("; ");

const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), geolocation=(), microphone=(self), payment=()",
  },
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
];

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
