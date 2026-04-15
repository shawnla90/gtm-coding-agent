import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Basic-auth gate for the competitive intel dashboard.
 *
 * Gates all non-static routes with a shared username + password from
 * AUTH_USER / AUTH_PASS env vars. Skip entirely in local dev by leaving
 * the env vars unset.
 *
 * Next.js 16 uses `proxy.ts` instead of the deprecated `middleware.ts`.
 */
export function proxy(request: NextRequest) {
  const user = process.env.AUTH_USER;
  const pass = process.env.AUTH_PASS;

  // If either env var is missing, skip auth (local dev + first deploy check).
  if (!user || !pass) {
    return NextResponse.next();
  }

  const header = request.headers.get("authorization");
  if (header?.startsWith("Basic ")) {
    try {
      const decoded = atob(header.slice(6));
      const [u, p] = decoded.split(":");
      if (u === user && p === pass) {
        return NextResponse.next();
      }
    } catch {
      // fall through to 401
    }
  }

  return new NextResponse("Authentication required.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Apollo Intel", charset="UTF-8"',
    },
  });
}

export const config = {
  // Run on everything except Next internals + common static assets.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
