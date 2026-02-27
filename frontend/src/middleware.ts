import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/", "/login", "/register", "/agents"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths and static assets
  if (
    PUBLIC_PATHS.some(
      (p) => pathname === p || (p !== "/" && pathname.startsWith(p))
    ) ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // Check for auth token in cookies (set by client-side auth)
  // Note: actual auth validation happens server-side via API calls.
  // This middleware only handles redirects for UX, not security.
  // The real auth check happens when API calls are made with the token.

  // Protected dashboard routes
  if (pathname.startsWith("/dashboard") || pathname.startsWith("/admin")) {
    // We can't check localStorage from middleware (server-side).
    // Instead, we let the page render and the AuthProvider will redirect
    // client-side if not authenticated. This is the standard pattern
    // for SPA-style auth with Next.js App Router.
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
