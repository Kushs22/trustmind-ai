import { proxyToBackend } from "@/lib/backendProxy";
import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 60;

export function GET(req: NextRequest) {
  return proxyToBackend(req, "/warmup");
}
