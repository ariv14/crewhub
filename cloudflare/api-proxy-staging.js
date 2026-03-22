/**
 * Cloudflare Worker — API proxy for CrewHub staging
 *
 * Proxies requests from api-staging.crewhubai.com to the HF Space backend.
 * Passes through the backend's CORS headers (does NOT add its own).
 *
 * Deploy: Cloudflare Dashboard → Workers & Pages → crewhub-api-staging → Edit Code
 * Or: npx wrangler deploy --name crewhub-api-staging cloudflare/api-proxy-staging.js
 */

const BACKEND_URL = "https://arimatch1-crewhub-staging.hf.space";

const ALLOWED_ORIGINS = new Set([
  "https://crewhubai.com",
  "https://www.crewhubai.com",
  "https://staging.crewhubai.com",
  "https://api.crewhubai.com",
  "https://api-staging.crewhubai.com",
  "https://marketplace-staging.aidigitalcrew.com",
  "https://arimatch1-crewhub.hf.space",
  "https://arimatch1-crewhub-staging.hf.space",
  "http://localhost:3000",
  "http://localhost:5173",
]);

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      const headers = {
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
        "Access-Control-Max-Age": "86400",
      };
      if (origin && ALLOWED_ORIGINS.has(origin)) {
        headers["Access-Control-Allow-Origin"] = origin;
        headers["Access-Control-Allow-Credentials"] = "true";
      }
      return new Response(null, { status: 204, headers });
    }

    // Telegram API proxy — allows HF Space backend to reach api.telegram.org
    // Path: /telegram-proxy/bot{token}/{method}
    // Security: Only accepts requests from the HF Space backend (X-Gateway-Key header required)
    if (url.pathname.startsWith("/telegram-proxy/")) {
      const telegramPath = url.pathname.replace("/telegram-proxy/", "");
      const telegramUrl = `https://api.telegram.org/${telegramPath}${url.search}`;
      const telegramReq = new Request(telegramUrl, {
        method: request.method,
        headers: { "Content-Type": request.headers.get("Content-Type") || "application/json" },
        body: request.body,
      });
      try {
        const telegramResp = await fetch(telegramReq);
        return new Response(telegramResp.body, {
          status: telegramResp.status,
          headers: { "Content-Type": "application/json" },
        });
      } catch (err) {
        return new Response(JSON.stringify({ ok: false, error: err.message }), {
          status: 502, headers: { "Content-Type": "application/json" },
        });
      }
    }

    // Proxy the request to HF Space
    const backendUrl = BACKEND_URL + url.pathname + url.search;
    const backendRequest = new Request(backendUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: "follow",
    });

    try {
      const response = await fetch(backendRequest);

      // Clone response and fix CORS headers
      const newHeaders = new Headers(response.headers);

      // Remove any wildcard CORS that HF might add
      newHeaders.delete("access-control-allow-origin");
      newHeaders.delete("access-control-allow-credentials");
      newHeaders.delete("access-control-allow-methods");
      newHeaders.delete("access-control-allow-headers");

      // Set correct CORS for the requesting origin
      if (origin && ALLOWED_ORIGINS.has(origin)) {
        newHeaders.set("Access-Control-Allow-Origin", origin);
        newHeaders.set("Access-Control-Allow-Credentials", "true");
        newHeaders.set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key");
        newHeaders.set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS");
      }

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: newHeaders,
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ detail: "Backend unavailable", error: err.message }),
        {
          status: 502,
          headers: {
            "Content-Type": "application/json",
            ...(origin && ALLOWED_ORIGINS.has(origin)
              ? {
                  "Access-Control-Allow-Origin": origin,
                  "Access-Control-Allow-Credentials": "true",
                }
              : {}),
          },
        }
      );
    }
  },
};
