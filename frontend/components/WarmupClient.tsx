"use client";

import { useEffect } from "react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

/** Ping /warmup on first paint so Render is less likely to sleep before a check-in. */
export function WarmupClient() {
  useEffect(() => {
    const ctrl = new AbortController();
    void fetch(`${API_URL}/warmup`, { signal: ctrl.signal, cache: "no-store" }).catch(
      () => undefined,
    );
    return () => ctrl.abort();
  }, []);
  return null;
}
