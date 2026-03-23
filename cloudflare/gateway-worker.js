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

// --- Platform APIs ---

// Telegram
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

// Slack
async function sendSlack(token, channelId, text) {
  const chunks = [];
  for (let i = 0; i < text.length; i += 3000) {
    chunks.push(text.substring(i, i + 3000));
  }
  for (const chunk of chunks) {
    await fetch("https://slack.com/api/chat.postMessage", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ channel: channelId, text: chunk }),
    });
  }
}

async function slackTyping(token, channelId) {
  // Slack doesn't have a typing indicator API for bots
  // Best effort: no-op
}

async function verifySlackSignature(body, headers, signingSecret) {
  const timestamp = headers.get("x-slack-request-timestamp") || "";
  const slackSig = headers.get("x-slack-signature") || "";
  if (!timestamp || !slackSig) return false;

  // Reject if timestamp is older than 5 minutes (replay protection)
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - Number(timestamp)) > 300) return false;

  const baseString = `v0:${timestamp}:${body}`;
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw", encoder.encode(signingSecret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(baseString));
  const computed = "v0=" + Array.from(new Uint8Array(sig))
    .map(b => b.toString(16).padStart(2, "0")).join("");

  // Timing-safe comparison via double-hash
  const h1 = await sha256Hex(computed);
  const h2 = await sha256Hex(slackSig);
  return h1 === h2;
}

// Discord
async function sendDiscord(token, channelId, text) {
  const chunks = [];
  for (let i = 0; i < text.length; i += 2000) {
    chunks.push(text.substring(i, i + 2000));
  }
  for (const chunk of chunks) {
    await fetch(`https://discord.com/api/v10/channels/${channelId}/messages`, {
      method: "POST",
      headers: {
        "Authorization": `Bot ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content: chunk }),
    });
  }
}

// Discord interaction followup — edit deferred response
async function sendDiscordInteractionFollowup(applicationId, interactionToken, text) {
  const chunks = [];
  for (let i = 0; i < text.length; i += 2000) {
    chunks.push(text.substring(i, i + 2000));
  }
  // Edit the original deferred response
  await fetch(
    `https://discord.com/api/v10/webhooks/${applicationId}/${interactionToken}/messages/@original`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: chunks[0] }),
    }
  );
  // Send additional chunks as followup messages
  for (let i = 1; i < chunks.length; i++) {
    await fetch(
      `https://discord.com/api/v10/webhooks/${applicationId}/${interactionToken}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: chunks[i] }),
      }
    );
  }
}

async function discordTyping(token, channelId) {
  await fetch(`https://discord.com/api/v10/channels/${channelId}/typing`, {
    method: "POST",
    headers: { "Authorization": `Bot ${token}` },
  }).catch(() => {});
}

// Discord Ed25519 signature verification (CF Workers compatible)
async function verifyDiscordSignature(publicKeyHex, signature, timestamp, body) {
  try {
    // Convert hex strings to Uint8Array
    const hexToBytes = (hex) => new Uint8Array(
      hex.match(/.{1,2}/g).map(b => parseInt(b, 16))
    );
    const pubKeyBytes = hexToBytes(publicKeyHex);
    const sigBytes = hexToBytes(signature);
    const message = new TextEncoder().encode(timestamp + body);

    // CF Workers require namedCurve for Ed25519
    const cryptoKey = await crypto.subtle.importKey(
      "raw", pubKeyBytes,
      { name: "Ed25519", namedCurve: "Ed25519" },
      false, ["verify"]
    );
    return await crypto.subtle.verify(
      { name: "Ed25519" }, cryptoKey, sigBytes, message
    );
  } catch (err) {
    console.error("Ed25519 verification error:", err.message || err);
    return false;
  }
}

// --- Platform dispatcher ---

function getPlatformSender(platform) {
  switch (platform) {
    case "telegram": return { send: sendTelegram, typing: sendTyping };
    case "slack": return { send: sendSlack, typing: slackTyping };
    case "discord": return { send: sendDiscord, typing: discordTyping };
    default: return null;
  }
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

  // Verify webhook secret (timing-safe comparison)
  if (!env.GATEWAY_SERVICE_KEY) {
    return new Response(JSON.stringify({ detail: "Gateway not configured" }), { status: 503 });
  }
  const expected = (await sha256Hex(`${env.GATEWAY_SERVICE_KEY}:${connectionId}`)).substring(0, 32);
  const actual = request.headers.get("X-Telegram-Bot-Api-Secret-Token") || "";
  // Timing-safe: compare HMAC digests instead of raw strings
  const expectedHash = await sha256Hex(expected);
  const actualHash = await sha256Hex(actual);
  if (expectedHash !== actualHash) {
    return new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 });
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

// --- Slack Webhook Handler ---

async function handleSlackWebhook(request, env, ctx, connectionId) {
  const bodyText = await request.text();

  // Slack URL verification challenge (first-time setup)
  try {
    const body = JSON.parse(bodyText);
    if (body.type === "url_verification") {
      return Response.json({ challenge: body.challenge });
    }
  } catch {}

  // Get connection to get signing secret
  const conn = await getConnection(env, connectionId);
  if (!conn) {
    return Response.json({ ok: true });
  }
  // Auto-activate pending channels on first verified event
  if (conn.status === "pending") {
    await backendCall(env, "/gateway/heartbeat", "POST", {
      connections: [{ connection_id: connectionId, status: "active" }],
    });
    conn.status = "active";
  }
  if (conn.status !== "active") {
    return Response.json({ ok: true });
  }

  // Verify Slack signature using the webhook_secret (signing secret)
  const signingSecret = conn.webhook_secret || "";
  if (signingSecret) {
    const valid = await verifySlackSignature(bodyText, request.headers, signingSecret);
    if (!valid) {
      return new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 });
    }
  }

  let body;
  try { body = JSON.parse(bodyText); } catch {
    return new Response(JSON.stringify({ detail: "Invalid JSON" }), { status: 400 });
  }

  // Parse Slack Events API message
  const event = body.event;
  if (!event || event.type !== "message" || event.subtype || event.bot_id) {
    return Response.json({ ok: true }); // ignore non-message events, edits, bot messages
  }

  const userId = event.user || "";
  const msgId = event.client_msg_id || event.ts || "";
  const chatId = event.channel || "";
  const text = event.text || "";
  if (!text || !chatId) return Response.json({ ok: true });

  if (isDuplicate(connectionId, msgId)) return Response.json({ ok: true });
  if (isRateLimited(`${connectionId}:${userId}`)) return Response.json({ ok: true });

  ctx.waitUntil(processMessage({ env, connectionId, userId, msgId, chatId, text, platform: "slack" }));
  return Response.json({ ok: true });
}

// --- Discord Webhook Handler ---

async function handleDiscordWebhook(request, env, ctx, connectionId) {
  const bodyText = await request.text();
  const signature = request.headers.get("x-signature-ed25519") || request.headers.get("X-Signature-Ed25519") || "";
  const timestamp = request.headers.get("x-signature-timestamp") || request.headers.get("X-Signature-Timestamp") || "";

  // Discord sends interactions as JSON
  let body;
  try { body = JSON.parse(bodyText); } catch {
    return new Response(JSON.stringify({ detail: "Invalid JSON" }), { status: 400 });
  }

  // Get connection to retrieve the Discord public key for verification
  const conn = await getConnection(env, connectionId);
  const publicKey = conn?.config?.public_key || "";

  // Verify Ed25519 signature (required for ALL Discord interactions including PING)
  if (signature && timestamp) {
    if (!publicKey) {
      console.error("Discord: no public_key in config for connection", connectionId,
        "conn found:", !!conn, "config keys:", conn?.config ? Object.keys(conn.config) : "none");
      // Cannot verify — reject to be safe (Discord will show this as endpoint failure)
      return new Response("Server missing public key", { status: 401 });
    }
    const valid = await verifyDiscordSignature(publicKey, signature, timestamp, bodyText);
    if (!valid) {
      console.error("Discord: Ed25519 verification failed for connection", connectionId,
        "pubkey length:", publicKey.length, "sig length:", signature.length);
      return new Response("Invalid request signature", { status: 401 });
    }
    console.log("Discord: Ed25519 verification passed for", connectionId);
  }

  // Discord PING verification (required for Interactions endpoint setup)
  if (body.type === 1) {
    return Response.json({ type: 1 }); // PONG — signature already verified above
  }

  // Handle slash commands (type 2 = APPLICATION_COMMAND)
  if (body.type === 2) {
    const userId = body.member?.user?.id || body.user?.id || "";
    const msgId = body.id || "";
    const chatId = body.channel_id || "";
    const applicationId = body.application_id || conn?.config?.application_id || "";
    const interactionToken = body.token || "";
    const text = body.data?.options?.[0]?.value || body.data?.name || "";
    if (!text || !chatId) {
      return Response.json({ type: 4, data: { content: "Please provide a message." } });
    }

    if (isDuplicate(connectionId, msgId)) {
      return Response.json({ type: 5 });
    }

    // Process in background with interaction context for followup
    ctx.waitUntil(processDiscordInteraction({
      env, connectionId, userId, msgId, chatId, text,
      applicationId, interactionToken,
    }));

    // Respond with "thinking" indicator — Discord requires immediate response
    return Response.json({ type: 5 });
  }

  return Response.json({ ok: true });
}

// Discord interaction processor — uses interaction webhook for responses
async function processDiscordInteraction(ctx) {
  const { env, connectionId, userId, msgId, chatId, text, applicationId, interactionToken } = ctx;

  const conn = await getConnection(env, connectionId);
  if (!conn || !conn.bot_token) {
    console.log("Connection not found:", connectionId);
    if (applicationId && interactionToken) {
      await sendDiscordInteractionFollowup(applicationId, interactionToken,
        "Sorry, this channel is not configured correctly.");
    }
    return;
  }

  // Auto-activate pending channels
  if (conn.status === "pending") {
    await backendCall(env, "/gateway/heartbeat", "POST", {
      connections: [{ connection_id: connectionId, status: "active" }],
    });
  }
  if (conn.status !== "active" && conn.status !== "pending") {
    console.log("Connection inactive:", connectionId, conn.status);
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

  // Charge credits
  const chargeResult = await chargeCredits(env, connectionId, 1, conn.daily_credit_limit);
  if (!chargeResult.success) {
    const errorMsgs = {
      daily_limit: "Daily message limit reached. Service will resume tomorrow.",
      insufficient_balance: "Service temporarily unavailable.",
      credit_exhausted: "Service temporarily unavailable.",
    };
    await sendDiscordInteractionFollowup(applicationId, interactionToken,
      errorMsgs[chargeResult.error] || "Service temporarily unavailable.");
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

  // Create task
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
    await sendDiscordInteractionFollowup(applicationId, interactionToken,
      "Sorry, I couldn't process your request. Please try again.");
    return;
  }

  const taskId = task.task_id;
  console.log("Discord task created:", taskId, "— polling for up to 25s");

  // Quick poll (25s)
  let responseText = null;
  const startTime = Date.now();
  while (Date.now() - startTime < 25000) {
    await new Promise(r => setTimeout(r, 3000));
    try {
      const taskStatus = await backendCall(env, `/gateway/task-status/${taskId}`);
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

  if (!responseText) {
    responseText = "Your request is taking longer than expected. Please try again in a moment.";
  }

  // Send response via interaction webhook (edits the deferred "thinking..." message)
  await sendDiscordInteractionFollowup(applicationId, interactionToken, responseText);

  // Log outbound message
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

  console.log("Discord response delivered for task", taskId);
}

// --- Generic Message Processor ---

async function processMessage(ctx) {
  const { env, connectionId, userId, msgId, chatId, text, platform: platformOverride } = ctx;

  // Get connection config (includes decrypted bot token)
  const conn = await getConnection(env, connectionId);
  if (!conn || !conn.bot_token) {
    console.log("Connection not found:", connectionId);
    return;
  }
  // Auto-activate pending channels
  if (conn.status === "pending") {
    await backendCall(env, "/gateway/heartbeat", "POST", {
      connections: [{ connection_id: connectionId, status: "active" }],
    });
  }
  if (conn.status !== "active" && conn.status !== "pending") {
    console.log("Connection inactive:", connectionId, conn.status);
    return;
  }

  const botToken = conn.bot_token;
  const platform = platformOverride || conn.platform || "telegram";
  const sender = getPlatformSender(platform);
  if (!sender) {
    console.error("Unsupported platform:", platform);
    return;
  }

  // Check blocked users
  const userHash = (await hmacSha256(
    `${env.GATEWAY_SERVICE_KEY}:${connectionId}`, userId
  )).substring(0, 16);

  if (conn.blocked_users && conn.blocked_users.includes(userHash)) {
    return; // silently drop
  }

  // Send typing indicator
  await sender.typing(botToken, chatId);

  // Charge credits
  const chargeResult = await chargeCredits(env, connectionId, 1, conn.daily_credit_limit);
  if (!chargeResult.success) {
    const errorMsgs = {
      daily_limit: "Daily message limit reached. Service will resume tomorrow.",
      insufficient_balance: "Service temporarily unavailable.",
      credit_exhausted: "Service temporarily unavailable.",
    };
    await sender.send(botToken, chatId, errorMsgs[chargeResult.error] || "Service temporarily unavailable.");
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
    await sender.send(botToken, chatId, "Sorry, I couldn't process your request. Please try again.");
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
      const taskStatus = await backendCall(env, `/gateway/task-status/${taskId}`);
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
    await sender.send(botToken, chatId, responseText);
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
  // Verify the callback is from our backend (mandatory, timing-safe)
  if (!env.GATEWAY_SERVICE_KEY) {
    return Response.json({ detail: "Gateway not configured" }, { status: 503 });
  }
  const gatewayKey = request.headers.get("X-Gateway-Key") || "";
  const expectedKeyHash = await sha256Hex(env.GATEWAY_SERVICE_KEY);
  const actualKeyHash = await sha256Hex(gatewayKey);
  if (expectedKeyHash !== actualKeyHash) {
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

  // Send response to platform
  const callbackSender = getPlatformSender(conn.platform || "telegram");
  if (callbackSender) {
    await callbackSender.send(botToken, chatId, responseText);
  }

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
    if (channel.status !== "active") continue;
    // Skip Discord — interactions use webhook followup, not cron delivery
    if (channel.platform === "discord") continue;

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

        // Send to platform
        const cronSender = getPlatformSender(channel.platform || "telegram");
        if (cronSender) {
          await cronSender.send(conn.bot_token, chatId, responseText);
        }

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

// --- CORS helpers ---

const ALLOWED_ORIGINS = [
  "https://crewhubai.com",
  "https://www.crewhubai.com",
  "https://marketplace-staging.aidigitalcrew.com",
  "http://localhost:3000",
];

function corsHeaders(origin) {
  const headers = {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
  if (origin && ALLOWED_ORIGINS.includes(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
  }
  return headers;
}

function addCorsHeaders(response, origin) {
  if (!origin || !ALLOWED_ORIGINS.includes(origin)) return response;
  const newResp = new Response(response.body, response);
  newResp.headers.set("Access-Control-Allow-Origin", origin);
  return newResp;
}

// --- Main Worker ---

export default {
  // Cron trigger — runs every minute to deliver pending responses
  async scheduled(event, env, ctx) {
    ctx.waitUntil(deliverPendingResponses(env));
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";

    // CORS preflight for /auto-register
    if (request.method === "OPTIONS" && url.pathname === "/auto-register") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    // Health check
    if (url.pathname === "/health") {
      return Response.json({ status: "ok", service: "crewhub-gateway-cf" });
    }

    // Platform webhooks: POST /webhook/{platform}/{connectionId}
    const telegramMatch = url.pathname.match(/^\/webhook\/telegram\/([0-9a-f-]+)$/);
    if (telegramMatch && request.method === "POST") {
      return handleTelegramWebhook(request, env, ctx, telegramMatch[1]);
    }

    const slackMatch = url.pathname.match(/^\/webhook\/slack\/([0-9a-f-]+)$/);
    if (slackMatch && request.method === "POST") {
      return handleSlackWebhook(request, env, ctx, slackMatch[1]);
    }

    const discordMatch = url.pathname.match(/^\/webhook\/discord\/([0-9a-f-]+)$/);
    if (discordMatch && request.method === "POST") {
      return handleDiscordWebhook(request, env, ctx, discordMatch[1]);
    }

    // Task completion callback: POST /callback/{connectionId}/{chatId}
    const callbackMatch = url.pathname.match(/^\/callback\/([0-9a-f-]+)\/(-?\d+)$/);
    if (callbackMatch && request.method === "POST") {
      return handleTaskCallback(request, env, callbackMatch[1], callbackMatch[2]);
    }

    // Token validation: POST /validate-token (called by backend)
    if (url.pathname === "/validate-token" && request.method === "POST") {
      const body = await request.json();
      const gatewayKey = request.headers.get("X-Gateway-Key") || "";
      if (!env.GATEWAY_SERVICE_KEY) return Response.json({ detail: "Not configured" }, { status: 503 });
      const ek = await sha256Hex(env.GATEWAY_SERVICE_KEY);
      const ak = await sha256Hex(gatewayKey);
      if (ek !== ak) return Response.json({ detail: "Unauthorized" }, { status: 401 });

      const { platform, bot_token } = body;
      if (platform === "telegram" && bot_token) {
        const result = await telegramApi(bot_token, "getMe", {});
        if (result && result.ok) {
          return Response.json({
            valid: true,
            platform_bot_id: String(result.result.id),
            bot_name: result.result.username || result.result.first_name,
          });
        }
        return Response.json({ valid: false, error: "Invalid Telegram bot token" });
      }
      if (platform === "discord" && bot_token) {
        const result = await fetch("https://discord.com/api/v10/users/@me", {
          headers: { "Authorization": `Bot ${bot_token}` },
        });
        if (result.ok) {
          const user = await result.json();
          return Response.json({
            valid: true,
            platform_bot_id: user.id,
            bot_name: user.username,
          });
        }
        return Response.json({ valid: false, error: "Invalid Discord bot token" });
      }
      return Response.json({ valid: false, error: "Unsupported platform" });
    }

    // Webhook registration: POST /register-webhook (called by backend)
    if (url.pathname === "/register-webhook" && request.method === "POST") {
      const body = await request.json();
      const gatewayKey = request.headers.get("X-Gateway-Key") || "";
      if (!env.GATEWAY_SERVICE_KEY) return Response.json({ detail: "Not configured" }, { status: 503 });
      const ek = await sha256Hex(env.GATEWAY_SERVICE_KEY);
      const ak = await sha256Hex(gatewayKey);
      if (ek !== ak) return Response.json({ detail: "Unauthorized" }, { status: 401 });

      const { bot_token, connection_id, webhook_secret } = body;
      const workerUrl = url.origin;
      const webhookUrl = `${workerUrl}/webhook/telegram/${connection_id}`;

      const payload = {
        url: webhookUrl,
        allowed_updates: ["message", "edited_message"],
        drop_pending_updates: true,
      };
      if (webhook_secret) payload.secret_token = webhook_secret;

      const result = await telegramApi(bot_token, "setWebhook", payload);
      return Response.json({
        ok: result && result.ok,
        webhook_url: webhookUrl,
        error: result && !result.ok ? result.description : null,
      });
    }

    // Browser-safe webhook registration: POST /auto-register
    // Auth: validates bot_token via Telegram getMe (token IS the credential)
    // Called by frontend after channel creation — browser has full DNS
    if (url.pathname === "/auto-register" && request.method === "POST") {
      const body = await request.json();
      const { bot_token, connection_id } = body;
      if (!bot_token || !connection_id) {
        return addCorsHeaders(
          Response.json({ ok: false, error: "bot_token and connection_id required" }, { status: 400 }),
          origin
        );
      }

      // Validate token by calling Telegram (proof of ownership)
      const me = await telegramApi(bot_token, "getMe", {});
      if (!me || !me.ok) {
        return addCorsHeaders(
          Response.json({ ok: false, error: "Invalid bot token" }, { status: 401 }),
          origin
        );
      }

      // Derive webhook secret
      let webhookSecret = "";
      if (env.GATEWAY_SERVICE_KEY) {
        webhookSecret = (await sha256Hex(`${env.GATEWAY_SERVICE_KEY}:${connection_id}`)).substring(0, 32);
      }

      const workerUrl = url.origin;
      const webhookUrl = `${workerUrl}/webhook/telegram/${connection_id}`;

      const result = await telegramApi(bot_token, "setWebhook", {
        url: webhookUrl,
        secret_token: webhookSecret || undefined,
        allowed_updates: ["message", "edited_message"],
        drop_pending_updates: false,
      });

      return addCorsHeaders(
        Response.json({
          ok: result && result.ok,
          webhook_url: webhookUrl,
          bot_username: me.result?.username,
          error: result && !result.ok ? result.description : null,
        }),
        origin
      );
    }

    // Discord auto-register: POST /auto-register-discord
    // Registers /ask slash command + returns webhook URL for Interactions Endpoint
    if (url.pathname === "/auto-register-discord" && request.method === "POST") {
      const body = await request.json();
      const { bot_token, application_id, connection_id } = body;
      if (!bot_token || !application_id || !connection_id) {
        return addCorsHeaders(
          Response.json({ ok: false, error: "bot_token, application_id, and connection_id required" }, { status: 400 }),
          origin
        );
      }

      // Validate token by calling Discord
      const meResp = await fetch("https://discord.com/api/v10/users/@me", {
        headers: { "Authorization": `Bot ${bot_token}` },
      });
      if (!meResp.ok) {
        return addCorsHeaders(
          Response.json({ ok: false, error: "Invalid bot token" }, { status: 401 }),
          origin
        );
      }

      // Register /ask slash command globally
      const cmdResp = await fetch(
        `https://discord.com/api/v10/applications/${application_id}/commands`,
        {
          method: "POST",
          headers: {
            "Authorization": `Bot ${bot_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: "ask",
            description: "Ask the AI agent a question",
            type: 1, // CHAT_INPUT
            options: [{
              name: "message",
              description: "Your question or message",
              type: 3, // STRING
              required: true,
            }],
          }),
        }
      );

      const workerUrl = url.origin;
      const webhookUrl = `${workerUrl}/webhook/discord/${connection_id}`;

      return addCorsHeaders(
        Response.json({
          ok: cmdResp.ok,
          webhook_url: webhookUrl,
          slash_command: cmdResp.ok ? "/ask" : null,
          error: !cmdResp.ok ? `Failed to register slash command: ${cmdResp.status}` : null,
          instructions: "Paste this webhook URL as the Interactions Endpoint URL in your Discord app's General Information page.",
        }),
        origin
      );
    }

    // CORS preflight for /auto-register-discord
    if (request.method === "OPTIONS" && url.pathname === "/auto-register-discord") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    // 404 for everything else
    return Response.json({ detail: "Not Found" }, { status: 404 });
  },
};
