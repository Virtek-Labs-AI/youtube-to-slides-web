import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// Headers that must not be forwarded upstream or downstream
const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  // Content-encoding is handled by fetch automatically
  "content-encoding",
]);

async function proxy(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  const pathname = path.join("/");
  const search = req.nextUrl.search;
  const url = `${BACKEND_URL}/api/${pathname}${search}`;

  // Forward request headers (strip hop-by-hop and rewrite host)
  const reqHeaders = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase()) && key.toLowerCase() !== "host") {
      reqHeaders.set(key, value);
    }
  });

  const hasBody = req.method !== "GET" && req.method !== "HEAD";

  const backendRes = await fetch(url, {
    method: req.method,
    headers: reqHeaders,
    body: hasBody ? req.body : undefined,
    redirect: "manual", // handle redirects ourselves so Set-Cookie is preserved
    // @ts-ignore — duplex required when streaming a request body
    duplex: "half",
  });

  // Build response headers, forwarding Set-Cookie intact
  const resHeaders = new Headers();
  backendRes.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      resHeaders.set(key, value);
    }
  });

  // Preserve multiple Set-Cookie headers (Headers.set() would collapse them)
  const cookies = backendRes.headers.getSetCookie?.() ?? [];
  if (cookies.length > 0) {
    resHeaders.delete("set-cookie");
    cookies.forEach((c) => resHeaders.append("set-cookie", c));
  }

  // Pass redirects through to the browser unchanged
  if (backendRes.status >= 300 && backendRes.status < 400) {
    return new NextResponse(null, {
      status: backendRes.status,
      headers: resHeaders,
    });
  }

  return new NextResponse(backendRes.body, {
    status: backendRes.status,
    headers: resHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
