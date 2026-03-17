/**
 * Cloudflare Worker: builder.crewhubai.com → Langflow pool Space proxy
 *
 * Proxies all requests to the Langflow HF Space, preserving cookies
 * on the crewhubai.com domain so auto-login works inside iframes.
 *
 * Setup in Cloudflare Dashboard:
 * 1. Workers & Pages → Create Worker → paste this code
 * 2. Settings → Triggers → Add Route: builder.crewhubai.com/*
 * 3. DNS: Add AAAA record for "builder" → 100:: (dummy, Worker handles it)
 */

const POOL_SPACES = [
  "https://arimatch1-crewhub-langflow-pool-02.hf.space",
  "https://arimatch1-crewhub-langflow-pool-03.hf.space",
];

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // Round-robin pool selection based on client IP hash
    const clientIP = request.headers.get("CF-Connecting-IP") || "0.0.0.0";
    const hash = Array.from(clientIP).reduce((h, c) => h + c.charCodeAt(0), 0);
    const poolIndex = hash % POOL_SPACES.length;
    const targetBase = POOL_SPACES[poolIndex];

    // Build target URL preserving path and query
    const targetUrl = `${targetBase}${url.pathname}${url.search}`;

    // Forward the request
    const headers = new Headers(request.headers);
    headers.set("Host", new URL(targetBase).host);
    // Remove headers that cause issues with HF Spaces
    headers.delete("cf-connecting-ip");
    headers.delete("cf-ipcountry");
    headers.delete("cf-ray");
    headers.delete("cf-visitor");

    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.method !== "GET" && request.method !== "HEAD"
        ? request.body
        : undefined,
      redirect: "manual",
    });

    // Clone response and modify headers
    const newHeaders = new Headers(response.headers);

    // Allow iframe embedding from crewhubai.com
    newHeaders.set(
      "Content-Security-Policy",
      "frame-ancestors https://crewhubai.com https://staging.crewhubai.com https://*.crewhubai.com"
    );
    newHeaders.delete("X-Frame-Options");

    // Fix Set-Cookie domain — rewrite HF Space domain to crewhubai.com
    const cookies = response.headers.getAll
      ? response.headers.getAll("Set-Cookie")
      : [response.headers.get("Set-Cookie")].filter(Boolean);

    if (cookies.length > 0) {
      newHeaders.delete("Set-Cookie");
      for (const cookie of cookies) {
        // Rewrite domain to crewhubai.com and set SameSite=None for cross-origin
        const rewritten = cookie
          .replace(/domain=[^;]*/gi, "domain=.crewhubai.com")
          .replace(/samesite=[^;]*/gi, "SameSite=None; Secure");
        newHeaders.append("Set-Cookie", rewritten);
      }
    }

    // Handle redirects — rewrite Location header to builder.crewhubai.com
    const location = newHeaders.get("Location");
    if (location) {
      for (const space of POOL_SPACES) {
        if (location.includes(new URL(space).host)) {
          newHeaders.set(
            "Location",
            location.replace(new URL(space).origin, url.origin)
          );
          break;
        }
      }
    }

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders,
    });
  },
};
