"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import api from "@/lib/api";
import { Presentation, LogIn } from "lucide-react";

export default function LandingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    isAuthenticated().then((authed) => {
      if (authed) router.replace("/dashboard");
    });
  }, [router]);

  const handleLogin = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/api/auth/login");
      window.location.href = data.url;
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="w-full max-w-md space-y-8 text-center">
        <div className="flex flex-col items-center gap-4">
          <div className="rounded-2xl bg-red-600 p-4">
            <Presentation className="h-10 w-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-white">
            YouTube to Slides
          </h1>
          <p className="text-lg text-gray-400">
            Turn any YouTube video into a professional presentation in seconds.
          </p>
        </div>

        <button
          onClick={handleLogin}
          disabled={loading}
          className="inline-flex w-full items-center justify-center gap-3 rounded-lg bg-white px-6 py-3 text-base font-semibold text-gray-900 shadow-sm transition hover:bg-gray-100 disabled:opacity-60"
        >
          {loading ? (
            <svg
              className="h-5 w-5 animate-spin text-gray-600"
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
          ) : (
            <LogIn className="h-5 w-5" />
          )}
          Sign in with Google
        </button>
      </div>
    </div>
  );
}
