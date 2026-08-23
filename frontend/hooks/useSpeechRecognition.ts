"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean; length: number }>;
};

function getSpeechRecognitionCtor():
  | (new () => SpeechRecognitionLike)
  | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export function useSpeechRecognition() {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [finalTranscript, setFinalTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  /** Always-current spoken text — React state alone races with stop/cancel. */
  const finalRef = useRef("");
  const interimRef = useRef("");

  useEffect(() => {
    setSupported(Boolean(getSpeechRecognitionCtor()));
  }, []);

  const clearTranscript = useCallback(() => {
    finalRef.current = "";
    interimRef.current = "";
    setFinalTranscript("");
    setInterim("");
  }, []);

  const getSpokenText = useCallback(() => {
    return `${finalRef.current} ${interimRef.current}`.trim();
  }, []);

  const stop = useCallback(() => {
    // Keep listening true until onend so final onresult chunks after stop()
    // are still captured in refs before the composer flushes.
    try {
      recognitionRef.current?.stop();
    } catch {
      setListening(false);
    }
  }, []);

  const cancel = useCallback(() => {
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    setListening(false);
    clearTranscript();
    setError(null);
  }, [clearTranscript]);

  const start = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setError("Speech recognition is not supported in this browser.");
      return;
    }
    setError(null);
    clearTranscript();
    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-GB";
    recognition.onresult = (event) => {
      let interimText = "";
      let finalChunk = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const piece = result[0]?.transcript || "";
        if (result.isFinal) finalChunk += piece;
        else interimText += piece;
      }
      if (finalChunk) {
        finalRef.current = `${finalRef.current} ${finalChunk}`.trim();
        setFinalTranscript(finalRef.current);
      }
      interimRef.current = interimText;
      setInterim(interimText);
    };
    recognition.onerror = (event) => {
      if (event.error === "not-allowed") {
        setError("Microphone permission denied.");
      } else if (event.error !== "aborted") {
        setError(`Speech recognition error: ${event.error}`);
      }
      setListening(false);
    };
    recognition.onend = () => {
      setListening(false);
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
      setListening(true);
    } catch {
      setError("Unable to start speech recognition.");
      setListening(false);
    }
  }, [clearTranscript]);

  return {
    supported,
    listening,
    interim,
    finalTranscript,
    setFinalTranscript,
    getSpokenText,
    clearTranscript,
    error,
    start,
    stop,
    cancel,
  };
}
