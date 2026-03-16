"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { isAuthenticated, removeToken } from "@/lib/auth";
import api from "@/lib/api";
import YoutubeForm from "@/components/YoutubeForm";
import PresentationCard, {
  Presentation,
} from "@/components/PresentationCard";
import { LogOut, Presentation as PresentationIcon } from "lucide-react";

interface User {
  name: string;
  email: string;
  picture?: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [presentations, setPresentations] = useState<Presentation[]>([]);
  const [loadingUser, setLoadingUser] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPresentations = useCallback(async () => {
    try {
      const { data } = await api.get("/api/presentations");
      setPresentations(
        Array.isArray(data) ? data : data.presentations ?? []
      );
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    const fetchUser = async () => {
      try {
        const { data } = await api.get("/api/auth/me");
        setUser(data);
      } catch {
        removeToken();
        router.replace("/");
      } finally {
        setLoadingUser(false);
      }
    };

    fetchUser();
    fetchPresentations();
  }, [router, fetchPresentations]);

  useEffect(() => {
    const hasActive = presentations.some(
      (p) => p.status === "pending" || p.status === "processing"
    );

    if (hasActive) {
      if (!intervalRef.current) {
        intervalRef.current = setInterval(fetchPresentations, 3000);
      }
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [presentations, fetchPresentations]);

  const handleSubmitUrl = async (url: string) => {
    await api.post("/api/presentations", { youtube_url: url });
    await fetchPresentations();
  };

  const handleLogout = () => {
    removeToken();
    router.replace("/");
  };

  if (loadingUser) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <svg
          className="h-8 w-8 animate-spin text-red-500"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* Header */}
      <header className="mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-red-600 p-2">
            <PresentationIcon className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-semibold text-white">
            YouTube to Slides
          </span>
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <div className="flex items-center gap-3">
              {user.picture && (
                <Image
                  src={user.picture}
                  alt={user.name}
                  width={32}
                  height={32}
                  className="rounded-full"
                />
              )}
              <span className="hidden text-sm text-gray-300 sm:inline">
                {user.name}
              </span>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-400 transition hover:bg-gray-800 hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </header>

      {/* Form */}
      <section className="mb-8">
        <h2 className="mb-3 text-xl font-semibold text-white">
          Generate a presentation
        </h2>
        <YoutubeForm onSubmit={handleSubmitUrl} />
      </section>

      {/* Presentations */}
      <section>
        <h2 className="mb-4 text-xl font-semibold text-white">
          Your presentations
        </h2>
        {presentations.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-800 py-12 text-center">
            <PresentationIcon className="mx-auto h-10 w-10 text-gray-700" />
            <p className="mt-3 text-gray-500">
              No presentations yet. Paste a YouTube URL above to get started.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {presentations.map((p) => (
              <PresentationCard key={p.id} presentation={p} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
