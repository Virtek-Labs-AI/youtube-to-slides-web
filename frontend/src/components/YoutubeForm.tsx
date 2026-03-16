"use client";

import { useState, FormEvent } from "react";
import { Plus, Loader2 } from "lucide-react";

interface YoutubeFormProps {
  onSubmit: (url: string) => Promise<void>;
}

const YOUTUBE_REGEX =
  /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)[A-Za-z0-9_-]+/;

export default function YoutubeForm({ onSubmit }: YoutubeFormProps) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (!YOUTUBE_REGEX.test(url.trim())) {
      setError("Please enter a valid YouTube URL.");
      return;
    }

    setLoading(true);
    try {
      await onSubmit(url.trim());
      setUrl("");
    } catch {
      setError("Failed to submit. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-3">
        <input
          type="text"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setError("");
          }}
          placeholder="Paste a YouTube URL..."
          className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-white placeholder-gray-500 outline-none transition focus:border-red-500 focus:ring-1 focus:ring-red-500"
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-5 py-3 font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Plus className="h-5 w-5" />
          )}
          Generate
        </button>
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}
    </form>
  );
}
