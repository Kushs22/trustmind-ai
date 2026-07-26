"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, transcribeAudio } from "@/lib/api";

const MAX_AUDIO_DURATION_SECONDS = 180;
const MAX_AUDIO_SIZE_MB = 15;

export type RecorderStatus =
  | "idle"
  | "listening"
  | "paused"
  | "processing"
  | "completed";

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

export function useVoiceRecorder() {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const startedAtRef = useRef<number>(0);
  const elapsedOffsetRef = useRef(0);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stopTracks = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => () => {
    clearTimer();
    stopTracks();
    mediaRecorderRef.current?.stop();
  }, [clearTimer, stopTracks]);

  const startTimer = useCallback(() => {
    clearTimer();
    startedAtRef.current = Date.now();
    timerRef.current = window.setInterval(() => {
      const next =
        elapsedOffsetRef.current +
        Math.floor((Date.now() - startedAtRef.current) / 1000);
      setElapsed(next);
      if (next >= MAX_AUDIO_DURATION_SECONDS) {
        void stopAndTranscribe();
      }
    }, 250);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearTimer]);

  const start = useCallback(async () => {
    setError(null);
    setWarnings([]);
    setTranscript("");
    chunksRef.current = [];
    elapsedOffsetRef.current = 0;
    setElapsed(0);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mime = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";
      const recorder = new MediaRecorder(stream, { mimeType: mime });
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.start(500);
      setStatus("listening");
      startTimer();
    } catch {
      setError("Microphone permission denied or unavailable.");
      setStatus("idle");
      stopTracks();
    }
  }, [startTimer, stopTracks]);

  const pause = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state !== "recording") return;
    recorder.pause();
    elapsedOffsetRef.current = elapsed;
    clearTimer();
    setStatus("paused");
  }, [clearTimer, elapsed]);

  const resume = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state !== "paused") return;
    recorder.resume();
    setStatus("listening");
    startTimer();
  }, [startTimer]);

  const cancel = useCallback(() => {
    clearTimer();
    try {
      mediaRecorderRef.current?.stop();
    } catch {
      /* ignore */
    }
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    stopTracks();
    setStatus("idle");
    setElapsed(0);
    elapsedOffsetRef.current = 0;
    setTranscript("");
    setWarnings([]);
    setError(null);
  }, [clearTimer, stopTracks]);

  const stopAndTranscribe = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    clearTimer();
    if (!recorder) return;

    const blob: Blob = await new Promise((resolve) => {
      recorder.onstop = () => {
        const type = recorder.mimeType || "audio/webm";
        resolve(new Blob(chunksRef.current, { type }));
      };
      try {
        recorder.stop();
      } catch {
        resolve(new Blob([], { type: "audio/webm" }));
      }
    });
    stopTracks();
    mediaRecorderRef.current = null;

    if (blob.size === 0) {
      setError("No audio captured.");
      setStatus("idle");
      return;
    }
    if (blob.size > MAX_AUDIO_SIZE_MB * 1024 * 1024) {
      setError(`Recording exceeds ${MAX_AUDIO_SIZE_MB} MB.`);
      setStatus("idle");
      return;
    }

    setStatus("processing");
    try {
      const ext = blob.type.includes("mp4") ? "mp4" : "webm";
      const result = await transcribeAudio(blob, `recording.${ext}`);
      setTranscript(result.transcript || "");
      setWarnings(result.warnings || []);
      if (!result.transcript?.trim()) {
        setError("Empty transcript. Please try again or type your message.");
        setStatus("idle");
        return;
      }
      setStatus("completed");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Transcription failed. Please try again.",
      );
      setStatus("idle");
    }
  }, [clearTimer, stopTracks]);

  return {
    status,
    elapsed,
    elapsedLabel: formatElapsed(elapsed),
    error,
    transcript,
    setTranscript,
    warnings,
    start,
    pause,
    resume,
    cancel,
    stopAndTranscribe,
    maxDurationSeconds: MAX_AUDIO_DURATION_SECONDS,
  };
}
