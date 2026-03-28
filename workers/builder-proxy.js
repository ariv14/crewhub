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

    // Health check endpoint — probes all pool spaces
    if (url.pathname === "/health") {
      const results = await Promise.all(
        POOL_SPACES.map(async (space) => {
          try {
            const r = await fetch(`${space}/health`, {
              method: "GET",
              headers: { Host: new URL(space).host },
              signal: AbortSignal.timeout(5000),
            });
            return { space, status: r.status, ok: r.status >= 200 && r.status < 400 };
          } catch (e) {
            return { space, status: 0, ok: false, error: e.message };
          }
        })
      );
      const healthy = results.filter((r) => r.ok).length;
      return new Response(JSON.stringify({ healthy, total: POOL_SPACES.length, spaces: results }), {
        status: healthy > 0 ? 200 : 503,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Round-robin pool selection based on client IP hash
    const clientIP = request.headers.get("CF-Connecting-IP") || "0.0.0.0";
    const hash = Array.from(clientIP).reduce((h, c) => h + c.charCodeAt(0), 0);
    const poolIndex = hash % POOL_SPACES.length;

    // Buffer request body once (if any) so we can retry on failover
    const hasBody = request.method !== "GET" && request.method !== "HEAD";
    const bodyBuffer = hasBody ? await request.arrayBuffer() : null;

    // Try each pool space with failover — start from hashed index, wrap around
    let response;
    let targetBase;
    for (let i = 0; i < POOL_SPACES.length; i++) {
      targetBase = POOL_SPACES[(poolIndex + i) % POOL_SPACES.length];
      const targetUrl = `${targetBase}${url.pathname}${url.search}`;

      const headers = new Headers(request.headers);
      headers.set("Host", new URL(targetBase).host);
      headers.delete("cf-connecting-ip");
      headers.delete("cf-ipcountry");
      headers.delete("cf-ray");
      headers.delete("cf-visitor");

      response = await fetch(targetUrl, {
        method: request.method,
        headers,
        body: hasBody ? bodyBuffer : undefined,
        redirect: "manual",
      });

      // If this space is healthy, use it; otherwise try next
      if (response.status !== 412 && response.status !== 429 && response.status !== 503) {
        break;
      }
    }

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
