/**
 * CrewHub Gateway — Cloudflare Worker
 *
 * Handles Telegram webhook messages, dispatches tasks to the backend,
 * and sends agent responses back to Telegram.
 *
 * CF Workers have full networking (no DNS issues like HF Spaces).
 *
 * Deploy: npx wrangler deploy --name crewhub-gateway cloudflare/gateway-worker.js
 *
 * Required env vars (set via wrangler secret):
 *   GATEWAY_SERVICE_KEY — shared secret with the backend
 *   BACKEND_URL — HF Space backend URL (e.g., https://arimatch1-crewhub-staging.hf.space)
 */

// In-memory rate limiting (per-isolate, best-effort)
const rateLimits = new Map(); // key -> [timestamps]
const dedupSeen = new Map();  // key -> timestamp

function isRateLimited(key, maxReq = 10, windowSec = 60) {
  const now = Date.now() / 1000;
  const hits = (rateLimits.get(key) || []).filter(t => t > now - windowSec);
  hits.push(now);
  rateLimits.set(key, hits);
  return hits.length > maxReq;
}

function isDuplicate(connId, msgId, ttlSec = 300) {
  const key = `${connId}:${msgId}`;
  const now = Date.now() / 1000;
  const seen = dedupSeen.get(key);
  if (seen && now - seen < ttlSec) return true;
  dedupSeen.set(key, now);
  // Cleanup if too large
  if (dedupSeen.size > 5000) {
    for (const [k, v] of dedupSeen) {
      if (now - v > ttlSec) dedupSeen.delete(k);
    }
  }
  return false;
}

async function hmacSha256(key, message) {
  const encoder = new TextEncoder();
  const cryptoKey = await crypto.subtle.importKey(
    "raw", encoder.encode(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", cryptoKey, encoder.encode(message));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, "0")).join("");
}

async function sha256Hex(message) {
  const data = new TextEncoder().encode(message);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, "0")).join("");
}

// --- Telegram API ---

async function telegramApi(token, method, payload) {
  const resp = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return resp.json();
}

async function sendTelegram(token, chatId, text) {
  // Split long messages (Telegram limit: 4096 chars)
  const chunks = [];
  for (let i = 0; i < text.length; i += 4000) {
    chunks.push(text.substring(i, i + 4000));
  }
  for (const chunk of chunks) {
    let result = await telegramApi(token, "sendMessage", {
      chat_id: chatId, text: chunk, parse_mode: "Markdown",
    });
    if (!result.ok) {
      // Retry without Markdown if parsing fails
      await telegramApi(token, "sendMessage", { chat_id: chatId, text: chunk });
    }
  }
}

async function sendTyping(token, chatId) {
  await telegramApi(token, "sendChatAction", { chat_id: chatId, action: "typing" }).catch(() => {});
}

// --- Backend API ---

async function backendCall(env, path, method = "GET", body = null) {
  const url = `${env.BACKEND_URL}/api/v1${path}`;
  const headers = {
    "X-Gateway-Key": env.GATEWAY_SERVICE_KEY,
    "Content-Type": "application/json",
  };
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const resp = await fetch(url, opts);
  return resp.json();
}

async function getConnection(env, connectionId) {
  return backendCall(env, `/gateway/connections/${connectionId}`);
}

async function chargeCredits(env, connectionId, credits, dailyLimit) {
  return backendCall(env, "/gateway/charge", "POST", {
    connection_id: connectionId,
    platform_user_id: "system",
    credits,
    daily_credit_limit: dailyLimit,
  });
}

async function logMessage(env, data) {
  return backendCall(env, "/gateway/log-message", "POST", data);
}

async function createTask(env, agentId, skillId, message, ownerId) {
  return backendCall(env, "/gateway/create-task", "POST", {
    owner_id: ownerId,
    provider_agent_id: agentId,
    skill_id: skillId,
    message,
  });
}

// --- Webhook Handler ---

async function handleTelegramWebhook(request, env, ctx, connectionId) {
  const bodyText = await request.text();
  let body;
  try {
    body = JSON.parse(bodyText);
  } catch {
    return new Response(JSON.stringify({ detail: "Invalid JSON" }), { status: 400 });
  }

  // Verify webhook secret
  if (env.GATEWAY_SERVICE_KEY) {
    const expected = (await sha256Hex(`${env.GATEWAY_SERVICE_KEY}:${connectionId}`)).substring(0, 32);
    const actual = request.headers.get("X-Telegram-Bot-Api-Secret-Token") || "";
    if (actual !== expected) {
      return new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 });
    }
  }

  // Parse message
  const message = body.message || body.edited_message;
  if (!message || !message.text) {
    return Response.json({ ok: true });
  }

  const userId = String(message.from.id);
  const msgId = String(message.message_id);
  const chatId = String(message.chat.id);
  const text = message.text;

  // Dedup
  if (isDuplicate(connectionId, msgId)) {
    return Response.json({ ok: true });
  }

  // Rate limit
  if (isRateLimited(`${connectionId}:${userId}`)) {
    return Response.json({ ok: true });
  }

  // Return 200 immediately (Telegram requires <3s response)
  // Process in background via ctx.waitUntil — keeps Worker alive after response
  const promise = processMessage({ env, connectionId, userId, msgId, chatId, text });
  ctx.waitUntil(promise);

  return Response.json({ ok: true });
}

async function processMessage(ctx) {
  const { env, connectionId, userId, msgId, chatId, text } = ctx;

  // Get connection config (includes decrypted bot token)
  const conn = await getConnection(env, connectionId);
  if (!conn || !conn.bot_token || conn.status !== "active") {
    console.log("Connection not found or inactive:", connectionId);
    return;
  }

  const botToken = conn.bot_token;

  // Check blocked users
  const userHash = (await hmacSha256(
    `${env.GATEWAY_SERVICE_KEY}:${connectionId}`, userId
  )).substring(0, 16);

  if (conn.blocked_users && conn.blocked_users.includes(userHash)) {
    return; // silently drop
  }

  // Send typing indicator
  await sendTyping(botToken, chatId);

  // Charge credits
  const chargeResult = await chargeCredits(env, connectionId, 1, conn.daily_credit_limit);
  if (!chargeResult.success) {
    const errorMsgs = {
      daily_limit: "Daily message limit reached. Service will resume tomorrow.",
      insufficient_balance: "Service temporarily unavailable.",
      credit_exhausted: "Service temporarily unavailable.",
    };
    await sendTelegram(botToken, chatId, errorMsgs[chargeResult.error] || "Service temporarily unavailable.");
    return;
  }

  // Log inbound message (NULL text — GDPR privacy)
  await logMessage(env, {
    connection_id: connectionId,
    platform_user_id_hash: userHash,
    platform_message_id: msgId,
    platform_chat_id: chatId,
    direction: "inbound",
    message_text: null,
    media_type: "text",
  });

  // Create task (no callback — CF Worker will poll for completion)
  const skillId = conn.skill_id || null;
  const taskBody = {
    owner_id: conn.owner_id,
    provider_agent_id: conn.agent_id,
    message: text,
  };
  if (skillId) taskBody.skill_id = skillId;

  const task = await backendCall(env, "/gateway/create-task", "POST", taskBody);

  if (task.error || task.detail) {
    console.error("Task creation failed:", task.error || task.detail);
    await sendTelegram(botToken, chatId, "Sorry, I couldn't process your request. Please try again.");
    return;
  }

  const taskId = task.task_id;
  console.log("Task created:", taskId, "— polling for up to 25s, then cron takes over");

  // Quick poll (25s) — catches most tasks that complete in 20-30s
  let responseText = null;
  const startTime = Date.now();
  while (Date.now() - startTime < 25000) {
    await new Promise(r => setTimeout(r, 3000));
    try {
      const taskStatus = await backendCall(env, `/tasks/${taskId}`);
      if (!taskStatus) continue;
      const status = taskStatus.status;
      if (status === "completed") {
        for (const art of (taskStatus.artifacts || [])) {
          for (const part of (art.parts || [])) {
            if (part.type === "text" && part.content) {
              responseText = part.content;
              break;
            }
          }
          if (responseText) break;
        }
        if (!responseText) responseText = "Task completed.";
        break;
      } else if (status === "failed" || status === "canceled") {
        responseText = "Sorry, I couldn't complete your request.";
        break;
      }
    } catch (err) {
      console.error("Poll error:", err);
    }
  }

  if (responseText) {
    // Task completed within 25s — send immediately
    await sendTelegram(botToken, chatId, responseText);
    await logMessage(env, {
      connection_id: connectionId,
      platform_user_id_hash: "agent",
      platform_message_id: `reply-${msgId}`,
      platform_chat_id: chatId,
      direction: "outbound",
      message_text: responseText.substring(0, 2000),
      task_id: taskId,
      credits_charged: 1,
    });
    console.log("Response delivered immediately for task", taskId);
  } else {
    // Task still processing — store for cron delivery
    console.log("Task", taskId, "still processing — storing for cron delivery");
    await logMessage(env, {
      connection_id: connectionId,
      platform_user_id_hash: userHash,
      platform_message_id: `pending-${msgId}`,
      platform_chat_id: chatId,
      direction: "system",
      message_text: taskId,
      task_id: taskId,
    });
  }
}

// --- Task Callback (agent response) ---

async function handleTaskCallback(request, env, connectionId, chatId) {
  // Verify the callback is from our backend
  const gatewayKey = request.headers.get("X-Gateway-Key") || "";
  if (env.GATEWAY_SERVICE_KEY && gatewayKey !== env.GATEWAY_SERVICE_KEY) {
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();

  // Get connection to get bot token
  const conn = await getConnection(env, connectionId);
  if (!conn || !conn.bot_token) {
    return Response.json({ status: "connection_not_found" });
  }

  const botToken = conn.bot_token;

  // Extract response text from task result
  let responseText = "Task completed.";
  const status = body.status || "";
  const artifacts = body.artifacts || [];

  if (status === "failed" || status === "canceled") {
    responseText = "Sorry, I couldn't complete your request.";
  } else {
    for (const artifact of artifacts) {
      const parts = (artifact.parts || []);
      for (const part of parts) {
        if (part.type === "text" && part.content) {
          responseText = part.content;
          break;
        }
      }
      if (responseText !== "Task completed.") break;
    }
  }

  // Send response to Telegram
  await sendTelegram(botToken, chatId, responseText);

  // Log outbound message
  await logMessage(env, {
    connection_id: connectionId,
    platform_user_id_hash: "agent",
    platform_message_id: `cb-${body.task_id || "unknown"}`,
    platform_chat_id: chatId,
    direction: "outbound",
    message_text: responseText.substring(0, 2000),
    task_id: body.task_id,
    credits_charged: 1,
  });

  return Response.json({ status: "delivered" });
}

// --- Cron: deliver pending Telegram responses ---

async function deliverPendingResponses(env) {
  // Get all "system" messages (pending deliveries) from backend
  // These have direction="system" and message_text=taskId
  const channels = await backendCall(env, "/channels/", "GET");
  if (!channels || !channels.channels) return;

  for (const channel of channels.channels) {
    if (channel.platform !== "telegram" || channel.status !== "active") continue;

    // Get system messages (pending deliveries)
    const msgs = await backendCall(env, `/channels/${channel.id}/messages?direction=system`);
    if (!msgs || !msgs.messages || msgs.messages.length === 0) continue;

    // Get connection for bot token
    const conn = await getConnection(env, channel.id);
    if (!conn || !conn.bot_token) continue;

    for (const msg of msgs.messages) {
      const taskId = msg.message_text; // task_id stored here
      const chatId = msg.platform_chat_id;
      if (!taskId || !chatId) continue;

      // Check task status
      try {
        const task = await backendCall(env, `/tasks/${taskId}`);
        if (!task || !task.status) continue;

        let responseText = null;
        if (task.status === "completed") {
          for (const art of (task.artifacts || [])) {
            for (const part of (art.parts || [])) {
              if (part.type === "text" && part.content) {
                responseText = part.content;
                break;
              }
            }
            if (responseText) break;
          }
          if (!responseText) responseText = "Task completed.";
        } else if (task.status === "failed" || task.status === "canceled") {
          responseText = "Sorry, I couldn't complete your request.";
        } else {
          continue; // still processing
        }

        // Send to Telegram
        await sendTelegram(conn.bot_token, chatId, responseText);

        // Log outbound + delete system message by logging outbound
        await logMessage(env, {
          connection_id: channel.id,
          platform_user_id_hash: "agent",
          platform_message_id: `reply-${msg.platform_message_id}`,
          platform_chat_id: chatId,
          direction: "outbound",
          message_text: responseText.substring(0, 2000),
          task_id: taskId,
          credits_charged: 1,
        });

        console.log("Delivered response for task", taskId, "to chat", chatId);
      } catch (err) {
        console.error("Delivery error for task", taskId, ":", err);
      }
    }
  }
}

// --- Main Worker ---

export default {
  // Cron trigger — runs every minute to deliver pending responses
  async scheduled(event, env, ctx) {
    ctx.waitUntil(deliverPendingResponses(env));
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Health check
    if (url.pathname === "/health") {
      return Response.json({ status: "ok", service: "crewhub-gateway-cf" });
    }

    // Telegram webhook: POST /webhook/telegram/{connectionId}
    const telegramMatch = url.pathname.match(/^\/webhook\/telegram\/([0-9a-f-]+)$/);
    if (telegramMatch && request.method === "POST") {
      return handleTelegramWebhook(request, env, ctx, telegramMatch[1]);
    }

    // Task completion callback: POST /callback/{connectionId}/{chatId}
    const callbackMatch = url.pathname.match(/^\/callback\/([0-9a-f-]+)\/(-?\d+)$/);
    if (callbackMatch && request.method === "POST") {
      return handleTaskCallback(request, env, callbackMatch[1], callbackMatch[2]);
    }

    // 404 for everything else
    return Response.json({ detail: "Not Found" }, { status: 404 });
  },
};
