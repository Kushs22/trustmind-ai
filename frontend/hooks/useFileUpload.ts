"use client";

import { useCallback, useState } from "react";
import {
  ApiError,
  processImageFile,
  processPdfFile,
  type ImageProcessResult,
  type PdfProcessResult,
} from "@/lib/api";

export type PendingImage = {
  id: string;
  file: File;
  previewUrl: string;
  status: "pending" | "uploading" | "processed" | "error";
  progress: number;
  error?: string;
  result?: ImageProcessResult;
  extractedText: string;
  included: boolean;
};

export type PendingPdf = {
  id: string;
  file: File;
  status: "pending" | "uploading" | "processed" | "error";
  progress: number;
  error?: string;
  result?: PdfProcessResult;
  extractedText: string;
  included: boolean;
};

const MAX_IMAGE_COUNT = 5;
const MAX_IMAGE_SIZE_MB = 8;
const MAX_PDF_COUNT = 3;
const MAX_PDF_SIZE_MB = 15;
const ALLOWED_IMAGES = new Set(["image/jpeg", "image/png", "image/webp"]);
const ALLOWED_PDFS = new Set(["application/pdf"]);

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useFileUpload() {
  const [images, setImages] = useState<PendingImage[]>([]);
  const [pdfs, setPdfs] = useState<PendingPdf[]>([]);
  const [error, setError] = useState<string | null>(null);

  const removeImage = useCallback((id: string) => {
    setImages((prev) => {
      const target = prev.find((i) => i.id === id);
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((i) => i.id !== id);
    });
  }, []);

  const removePdf = useCallback((id: string) => {
    setPdfs((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const updateImageText = useCallback((id: string, text: string) => {
    setImages((prev) =>
      prev.map((i) => (i.id === id ? { ...i, extractedText: text } : i)),
    );
  }, []);

  const updatePdfText = useCallback((id: string, text: string) => {
    setPdfs((prev) =>
      prev.map((p) => (p.id === id ? { ...p, extractedText: text } : p)),
    );
  }, []);

  const toggleImageIncluded = useCallback((id: string, included: boolean) => {
    setImages((prev) =>
      prev.map((i) => (i.id === id ? { ...i, included } : i)),
    );
  }, []);

  const togglePdfIncluded = useCallback((id: string, included: boolean) => {
    setPdfs((prev) =>
      prev.map((p) => (p.id === id ? { ...p, included } : p)),
    );
  }, []);

  const addFiles = useCallback(
    async (fileList: FileList | File[]) => {
      setError(null);
      const files = Array.from(fileList);
      for (const file of files) {
        if (ALLOWED_IMAGES.has(file.type)) {
          if (images.length >= MAX_IMAGE_COUNT) {
            setError(`Maximum ${MAX_IMAGE_COUNT} images allowed.`);
            continue;
          }
          if (file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024) {
            setError(`Image ${file.name} exceeds ${MAX_IMAGE_SIZE_MB} MB.`);
            continue;
          }
          const id = uid();
          const previewUrl = URL.createObjectURL(file);
          const item: PendingImage = {
            id,
            file,
            previewUrl,
            status: "uploading",
            progress: 30,
            extractedText: "",
            included: true,
          };
          setImages((prev) => [...prev, item]);
          try {
            const result = await processImageFile(file);
            setImages((prev) =>
              prev.map((i) =>
                i.id === id
                  ? {
                      ...i,
                      status: "processed",
                      progress: 100,
                      result,
                      extractedText: result.extracted_text || "",
                      included: Boolean(
                        result.extracted_text || result.useful_context,
                      ),
                    }
                  : i,
              ),
            );
          } catch (err) {
            const message =
              err instanceof ApiError ? err.message : "Image processing failed.";
            setImages((prev) =>
              prev.map((i) =>
                i.id === id
                  ? { ...i, status: "error", progress: 100, error: message }
                  : i,
              ),
            );
          }
        } else if (ALLOWED_PDFS.has(file.type) || file.name.toLowerCase().endsWith(".pdf")) {
          if (pdfs.length >= MAX_PDF_COUNT) {
            setError(`Maximum ${MAX_PDF_COUNT} PDFs allowed.`);
            continue;
          }
          if (file.size > MAX_PDF_SIZE_MB * 1024 * 1024) {
            setError(`PDF ${file.name} exceeds ${MAX_PDF_SIZE_MB} MB.`);
            continue;
          }
          const id = uid();
          const item: PendingPdf = {
            id,
            file,
            status: "uploading",
            progress: 30,
            extractedText: "",
            included: true,
          };
          setPdfs((prev) => [...prev, item]);
          try {
            const result = await processPdfFile(file);
            setPdfs((prev) =>
              prev.map((p) =>
                p.id === id
                  ? {
                      ...p,
                      status: "processed",
                      progress: 100,
                      result,
                      extractedText: result.extracted_text || "",
                      included: Boolean(result.extracted_text?.trim()),
                    }
                  : p,
              ),
            );
          } catch (err) {
            const message =
              err instanceof ApiError ? err.message : "PDF processing failed.";
            setPdfs((prev) =>
              prev.map((p) =>
                p.id === id
                  ? { ...p, status: "error", progress: 100, error: message }
                  : p,
              ),
            );
          }
        } else {
          setError(
            `Unsupported file: ${file.name}. Use JPEG/PNG/WEBP images or PDF.`,
          );
        }
      }
    },
    [images.length, pdfs.length],
  );

  const clearAll = useCallback(() => {
    images.forEach((i) => {
      if (i.previewUrl) URL.revokeObjectURL(i.previewUrl);
    });
    setImages([]);
    setPdfs([]);
    setError(null);
  }, [images]);

  return {
    images,
    pdfs,
    error,
    setError,
    addFiles,
    removeImage,
    removePdf,
    updateImageText,
    updatePdfText,
    toggleImageIncluded,
    togglePdfIncluded,
    clearAll,
    limits: {
      maxImageCount: MAX_IMAGE_COUNT,
      maxPdfCount: MAX_PDF_COUNT,
      maxImageSizeMb: MAX_IMAGE_SIZE_MB,
      maxPdfSizeMb: MAX_PDF_SIZE_MB,
    },
  };
}
