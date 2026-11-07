import { NextRequest, NextResponse } from "next/server";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

export function backendOrigin(): string {
  const fromEnv = (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    ""
  ).replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (process.env.NODE_ENV === "development") return "http://127.0.0.1:8000";
  return "https://trustmind-ai.onrender.com";
}

function isPausedHost(status: number, body: string): boolean {
  return (
    status === 503 &&
    /service has been suspended|service suspended/i.test(body)
  );
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function proxyToBackend(
  req: NextRequest,
  backendPath: string,
): Promise<NextResponse> {
  const target = `${backendOrigin()}${backendPath}${req.nextUrl.search}`;
  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });

  let body: Uint8Array | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = new Uint8Array(await req.arrayBuffer());
  }

  const attempts = req.method === "GET" || req.method === "HEAD" ? 4 : 3;
  const delays = [0, 2500, 5000, 8000];
  let lastNetworkError = false;

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (attempt > 0) await sleep(delays[attempt] ?? 3000);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 25_000);
    try {
      const response = await fetch(target, {
        method: req.method,
        headers,
        body,
        cache: "no-store",
        redirect: "manual",
        signal: controller.signal,
      });
      const bytes = new Uint8Array(await response.arrayBuffer());
      const text = new TextDecoder().decode(bytes);

      if (isPausedHost(response.status, text)) {
        return NextResponse.json(
          {
            detail:
              "The check-in service is paused right now. Get help now is still available — try again once the API is back online.",
          },
          { status: 503 },
        );
      }

      const retryable =
        response.status === 502 ||
        response.status === 503 ||
        response.status === 504;
      if (retryable && attempt < attempts - 1) continue;

      const out = new Headers();
      const contentType = response.headers.get("content-type");
      if (contentType) out.set("content-type", contentType);
      return new NextResponse(bytes, {
        status: response.status,
        headers: out,
      });
    } catch {
      lastNetworkError = true;
      if (attempt === attempts - 1) break;
    } finally {
      clearTimeout(timer);
    }
  }

  return NextResponse.json(
    {
      detail: lastNetworkError
        ? "Unable to reach the check-in service. It may still be starting — wait a few seconds and try again."
        : "The check-in service is unavailable right now. Get help now is still available.",
    },
    { status: 503 },
  );
}
