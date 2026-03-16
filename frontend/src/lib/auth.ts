/**
 * Auth helpers — the JWT is stored as an httpOnly cookie set by the backend.
 * The browser sends it automatically on every request; JavaScript cannot read it.
 *
 * isAuthenticated() performs a lightweight server check rather than reading a
 * local token, because there is no token accessible to JS.
 */

export async function isAuthenticated(): Promise<boolean> {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/me`,
      { credentials: "include" }
    );
    return res.ok;
  } catch {
    return false;
  }
}
