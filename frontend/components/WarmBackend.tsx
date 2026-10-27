"use client";

import { useEffect } from "react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

/** Fire-and-forget ping so a sleeping backend starts waking as soon as any page loads. */
export function WarmBackend() {
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/health`, { method: "GET", signal: controller.signal }).catch(
      () => {
        /* best effort */
      },
    );
    return () => controller.abort();
  }, []);
  return null;
}
