"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * The backend sets the JWT as an httpOnly cookie and redirects here.
 * Nothing to read from the URL — just redirect to the dashboard.
 */
export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="flex flex-col items-center gap-4">
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
        <p className="text-gray-400">Signing you in...</p>
      </div>
    </div>
  );
}
