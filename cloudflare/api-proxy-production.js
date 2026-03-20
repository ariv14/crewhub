/**
 * Cloudflare Worker — API proxy for CrewHub production
 *
 * Proxies requests from api.crewhubai.com to the HF Space backend.
 * Passes through the backend's CORS headers (does NOT add its own).
 *
 * Deploy: npx wrangler deploy --name <worker-name> cloudflare/api-proxy-production.js
 */

const BACKEND_URL = "https://arimatch1-crewhub.hf.space";

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
