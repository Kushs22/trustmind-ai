"use client";

import { API_URL } from "@/lib/api";
import { useEffect } from "react";

/** Ping /warmup on first paint so Render is less likely to sleep before a check-in. */
export function WarmupClient() {
  useEffect(() => {
    const ctrl = new AbortController();
    let cancelled = false;

    async function ping(attempt = 0) {
      try {
        await fetch(`${API_URL}/warmup`, {
          signal: ctrl.signal,
          cache: "no-store",
        });
      } catch {
        if (!cancelled && attempt < 2) {
          window.setTimeout(() => {
            void ping(attempt + 1);
          }, 4000 * (attempt + 1));
        }
      }
    }

    void ping();
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, []);
  return null;
}
