# CrewHub Channel Setup Guide

Connect your AI agents to messaging platforms so your users can interact with them directly via Telegram, Slack, and Discord.

---

## How It Works

```
Your users on Telegram/Slack/Discord
    ↓ send message
CrewHub Gateway (Cloudflare Worker)
    ↓ creates task
Your AI Agent (HF Spaces)
    ↓ responds
CrewHub Gateway
    ↓ sends response
Your users see the reply
```

**Cost:** 1 credit per message. No platform fees for Telegram, Slack, Discord. WhatsApp charges 2 extra credits per message (Meta API fees).

---

## Telegram Setup (~2 minutes)

### Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a display name (e.g., "My Support Bot")
4. Choose a username ending in `bot` (e.g., `my_support_bot`)
5. BotFather gives you a **token** like `123456789:ABCdefGHI...` — copy it

### Step 2: Connect in CrewHub

1. Go to **crewhubai.com/dashboard/channels**
2. Click **Connect a Channel**
3. Select **Telegram**
4. Enter:
   - **Bot Display Name:** Your bot's name
   - **Bot Token:** Paste the token from BotFather
   - **Privacy Notice URL:** Link to your privacy policy
5. Click **Next**
6. Select the **AI agent** you want to power this bot
7. Set budget controls (daily credit limit, auto-pause)
8. Click **Create Channel**

### Step 3: Done!

The webhook is registered automatically. Your bot is live immediately.

**Test it:** Open Telegram, search for your bot's username, send a message. You should get an AI response within 10-15 seconds.

---

## Slack Setup (~10 minutes)

### Step 1: Create a Slack App

1. Go to **https://api.slack.com/apps**
2. Click **Create New App** → **From scratch**
3. Name: e.g., "CrewHub Agent"
4. Select your workspace → **Create App**

### Step 2: Configure Permissions

1. Go to **OAuth & Permissions** in the sidebar
2. Scroll to **Bot Token Scopes**
3. Add these scopes:
   - `chat:write` — send messages
   - `channels:history` — read messages in public channels
   - `channels:read` — see channel list
   - `app_mentions:read` — respond to @mentions (optional)
4. Click **Install to Workspace** → **Allow**
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 3: Get Signing Secret

1. Go to **Basic Information** in the sidebar
2. Under **App Credentials**, copy the **Signing Secret**

### Step 4: Connect in CrewHub

1. Go to **crewhubai.com/dashboard/channels**
2. Click **Connect a Channel**
3. Select **Slack**
4. Enter:
   - **Bot Display Name:** Your bot's name
   - **Bot Token:** Paste the `xoxb-...` token
   - **Signing Secret:** Paste the signing secret
   - **Privacy Notice URL:** Link to your privacy policy
5. Click **Next**
6. Select your **AI agent** and set budget controls
7. Click **Create Channel**
8. You'll see a **webhook URL** — copy it

### Step 5: Enable Event Subscriptions

1. Go back to your Slack app settings → **Event Subscriptions**
2. Toggle **Enable Events** to ON
3. In **Request URL**, paste the webhook URL from CrewHub
4. Slack will send a verification request — it should show ✅ **Verified**
5. Under **Subscribe to bot events**, click **Add Bot User Event** and add:
   - `message.channels` — messages in public channels
   - `message.im` — direct messages to the bot
6. Click **Save Changes**
7. If prompted, **reinstall the app** to your workspace

### Step 6: Invite the Bot

1. Go to any Slack channel where you want the bot
2. Type `/invite @YourBotName` (replace with your bot's actual name)
3. Send a message in the channel — the bot should respond within 10-15 seconds

### Troubleshooting

| Issue | Fix |
|-------|-----|
| Bot doesn't respond | Check Event Subscriptions → verify webhook URL shows ✅ |
| "not_in_channel" error | Invite the bot with `/invite @BotName` |
| "missing_scope" error | Add required scopes in OAuth & Permissions → reinstall app |
| Channel shows "Pending" | The bot auto-activates on first verified event. Send a message to trigger it. |

---

## Discord Setup (~5 minutes)

### Step 1: Create a Discord Application

1. Go to **https://discord.com/developers/applications**
2. Click **New Application** → name it (e.g., "CrewHub Agent") → **Create**
3. On the **General Information** page, note:
   - **Application ID** — copy it
   - **Public Key** — copy it (needed for webhook verification)

### Step 2: Create the Bot

1. Go to **Bot** in the sidebar
2. Click **Reset Token** → copy the **Bot Token**
3. Under **Privileged Gateway Intents**, enable:
   - **Message Content Intent** (required to read messages)

### Step 3: Invite the Bot to Your Server

1. Go to **OAuth2** → **URL Generator**
2. Select scopes: `bot`, `applications.commands`
3. Select bot permissions: `Send Messages`, `Read Message History`
4. Copy the generated URL → open it → select your server → **Authorize**

### Step 4: Connect in CrewHub

1. Go to **crewhubai.com/dashboard/channels**
2. Click **Connect a Channel**
3. Select **Discord**
4. Enter:
   - **Bot Display Name:** Your bot's name
   - **Bot Token:** Paste the bot token
   - **Application ID:** Paste the Application ID
   - **Public Key:** Paste the Public Key
   - **Privacy Notice URL:** Link to your privacy policy
5. Click **Next**
6. Select your **AI agent** and set budget controls
7. Click **Create Channel**
8. The `/ask` slash command is registered automatically

### Step 5: Set Interactions Endpoint

1. Go back to Discord Developer Portal → your app → **General Information**
2. In **Interactions Endpoint URL**, paste the webhook URL shown by CrewHub
3. Click **Save Changes** — Discord will send a PING to verify the endpoint (should show ✅)

### Step 6: Test

In any channel where the bot is present, type `/ask message:Hello!` and press Enter. The bot should show "thinking..." and respond within 10-15 seconds.

**How it works:** Discord interactions use the `/ask` slash command. When you type `/ask`, Discord sends the message to CrewHub's gateway, which dispatches it to your AI agent and edits the response back into the "thinking..." message.

### Troubleshooting

| Issue | Fix |
|-------|-----|
| "Interactions Endpoint URL" fails to save | Make sure the webhook URL is correct and the channel exists in CrewHub |
| `/ask` command doesn't appear | Wait 1-2 minutes — global commands take up to 1 hour to propagate. Try restarting Discord |
| Bot shows "thinking..." but never responds | Check agent health in CrewHub dashboard. The agent may be sleeping (HF Spaces free tier). |
| "This interaction failed" | Check that the channel is active in CrewHub and you have credits |

---

## Budget Controls

Every channel has configurable budget controls:

| Setting | Default | Description |
|---------|---------|-------------|
| **Daily Credit Limit** | 100 | Max credits per day. Bot auto-pauses when reached. |
| **Low Balance Alert** | 20 | Notification when your account credits drop below this. |
| **Auto-Pause on Limit** | On | Automatically pause the bot when daily limit is hit. |

You can change these anytime in the channel detail page → Settings tab.

---

## Managing Channels

### Channel Detail Page

Click **Configure** on any channel card to see:

- **Overview** — messages today, active contacts, credits used
- **Contacts** — end-users who messaged your bot (pseudonymized)
- **Messages** — message log (inbound text not stored for privacy)
- **Analytics** — daily message/credit charts
- **Settings** — budget controls, token rotation, delete

### Blocking Users

If an end-user is abusive, you can block them:
1. Go to channel detail → Contacts tab
2. Click **Block** next to the user
3. The bot will silently ignore their future messages

### Rotating Bot Token

If your bot token is compromised:
1. Go to channel detail → Settings tab
2. Click **Rotate Token**
3. Enter the new token from your platform (BotFather, Slack API, etc.)

### GDPR: Deleting User Data

To comply with a data deletion request:
1. Go to channel detail → Contacts tab
2. Click **Delete Data** next to the user
3. All messages from that user are permanently deleted

---

## Security & Privacy

| Feature | How It Works |
|---------|-------------|
| **Inbound messages** | Text is NOT stored — only metadata (timestamp, direction, credits) |
| **Outbound messages** | Agent responses are encrypted at rest (Fernet AES-128) |
| **User identity** | Pseudonymized via HMAC-SHA256 — raw platform IDs never stored |
| **Bot tokens** | Encrypted at rest in the database |
| **Webhook verification** | Platform-specific signature verification on every event |
| **Data retention** | Messages auto-purged after 90 days |
| **HIPAA** | Channels must not be used for Protected Health Information without a BAA |

---

## FAQ

**Q: How much does it cost?**
A: 1 credit per message (both inbound processing + outbound response). No platform fees for Telegram, Slack, Discord. WhatsApp adds 2 credits per message.

**Q: Can I connect the same bot to multiple agents?**
A: Each channel connection maps to one agent. Create multiple channels with the same bot token but different agents if needed.

**Q: What happens when I run out of credits?**
A: The bot sends "Service temporarily unavailable" and auto-pauses. Buy more credits at crewhubai.com/dashboard/credits.

**Q: Does the bot work 24/7?**
A: Yes. The gateway runs on Cloudflare Workers (global edge, 99.99% uptime). Agent availability depends on HF Spaces uptime.

**Q: Can end-users send images/files?**
A: Not yet. Only text messages are supported in v1. Media support is planned.

**Q: How fast is the response?**
A: Typically 10-15 seconds. The time includes: webhook processing (<1s) + agent AI processing (5-30s) + response delivery (<1s).
