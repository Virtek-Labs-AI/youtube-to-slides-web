"use client";

import { useState } from "react";
import {
  Download,
  ExternalLink,
  Loader2,
  AlertCircle,
  Clock,
  CheckCircle2,
} from "lucide-react";
import api from "@/lib/api";

export interface Presentation {
  id: string;
  youtube_url: string;
  title?: string;
  status: "pending" | "processing" | "done" | "failed";
  error_message?: string;
  created_at: string;
  google_slides_url?: string;
}

interface PresentationCardProps {
  presentation: Presentation;
}

const STATUS_CONFIG = {
  pending: {
    label: "Pending",
    color: "bg-yellow-900 text-yellow-300",
    icon: Clock,
  },
  processing: {
    label: "Processing",
    color: "bg-blue-900 text-blue-300",
    icon: Loader2,
  },
  done: {
    label: "Done",
    color: "bg-green-900 text-green-300",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    color: "bg-red-900 text-red-300",
    icon: AlertCircle,
  },
};

export default function PresentationCard({
  presentation,
}: PresentationCardProps) {
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");

  const status = STATUS_CONFIG[presentation.status];
  const StatusIcon = status.icon;

  const handleDownload = async () => {
    try {
      const response = await api.get(
        `/api/presentations/${presentation.id}/download`,
        { responseType: "blob" }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.download = `${presentation.title || "presentation"}.pptx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      // download failed silently
    }
  };

  const handleImportToSlides = async () => {
    setImporting(true);
    setImportError("");
    try {
      const { data } = await api.post(
        `/api/presentations/${presentation.id}/import-google-slides`
      );
      if (data.google_slides_url) {
        window.open(data.google_slides_url, "_blank");
      }
    } catch {
      setImportError("Failed to import to Google Slides.");
    } finally {
      setImporting(false);
    }
  };

  const displayTitle =
    presentation.title || presentation.youtube_url;
  const createdAt = new Date(presentation.created_at).toLocaleDateString(
    undefined,
    {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }
  );

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-5 transition hover:border-gray-700">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-medium text-white">
            {displayTitle}
          </h3>
          <p className="mt-1 text-sm text-gray-500">{createdAt}</p>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${status.color}`}
        >
          <StatusIcon
            className={`h-3.5 w-3.5 ${
              presentation.status === "processing" ? "animate-spin" : ""
            }`}
          />
          {status.label}
        </span>
      </div>

      {presentation.status === "failed" && presentation.error_message && (
        <p className="mt-3 rounded-lg bg-red-950 px-3 py-2 text-sm text-red-400">
          {presentation.error_message}
        </p>
      )}

      {presentation.status === "done" && (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={handleDownload}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-700"
          >
            <Download className="h-4 w-4" />
            Download PPTX
          </button>
          <button
            onClick={handleImportToSlides}
            disabled={importing}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
          >
            {importing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ExternalLink className="h-4 w-4" />
            )}
            Import to Google Slides
          </button>
        </div>
      )}

      {importError && (
        <p className="mt-2 text-sm text-red-400">{importError}</p>
      )}
    </div>
  );
}
