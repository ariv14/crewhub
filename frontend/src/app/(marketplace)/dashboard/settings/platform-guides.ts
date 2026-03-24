// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.

export const PLATFORM_GUIDES = {
  telegram: {
    name: "Telegram",
    icon: "Send",
    credentials: [
      { key: "bot_token", label: "Bot Token", placeholder: "123456789:ABC...", type: "password" as const },
    ],
    steps: [
      "Open Telegram and search for @BotFather",
      "Send /newbot and follow the prompts",
      "Choose a name and username (ending in 'bot')",
      "Copy the HTTP API token",
    ],
    externalUrl: "https://t.me/BotFather",
    externalLabel: "Open @BotFather",
    webhookManagement: "automatic" as const,
    creditCost: 0,
  },
  slack: {
    name: "Slack",
    icon: "Hash",
    credentials: [
      { key: "bot_token", label: "Bot Token (xoxb-...)", placeholder: "xoxb-...", type: "password" as const },
      { key: "signing_secret", label: "Signing Secret", placeholder: "0a22dc0c...", type: "password" as const },
    ],
    steps: [
      "Go to api.slack.com/apps → Create New App → From scratch",
      "Go to OAuth & Permissions → add Bot Token Scopes: chat:write, channels:history, channels:read",
      "Click Install to Workspace → Allow → copy Bot User OAuth Token (xoxb-...)",
      "Go to Basic Information → copy Signing Secret",
      "After creating the channel below, go to Event Subscriptions → toggle ON",
      "Paste the webhook URL shown on the next step as the Request URL",
      "Under Subscribe to bot events, add: message.channels, message.im",
      "Click Save Changes → invite bot to a channel: /invite @YourBotName",
    ],
    externalUrl: "https://api.slack.com/apps",
    externalLabel: "Open Slack API",
    webhookManagement: "manual" as const,
    creditCost: 0,
  },
  discord: {
    name: "Discord",
    icon: "Gamepad2",
    credentials: [
      { key: "bot_token", label: "Bot Token", placeholder: "MTk...", type: "password" as const },
    ],
    steps: [
      'Open the Discord Developer Portal and click "New Application"',
      "Give your app a name (e.g. CrewHub Agent) and click Create",
      'Go to the "Bot" tab in the left sidebar',
      'Click "Reset Token" → Yes, do it! → Copy the token (save it — you can\'t see it again)',
      'Scroll down and enable "Message Content Intent" under Privileged Gateway Intents',
      'Go to "Installation" tab → under Guild Install, add both "bot" and "applications.commands" scopes',
    ],
    externalUrl: "https://discord.com/developers/applications",
    externalLabel: "Open Discord Developer Portal",
    webhookManagement: "discord" as const,
    creditCost: 0,
  },
  teams: {
    name: "Teams",
    icon: "Users",
    credentials: [
      { key: "app_id", label: "App ID", placeholder: "xxxxxxxx-xxxx-...", type: "text" as const },
      { key: "app_password", label: "App Password", placeholder: "...", type: "password" as const },
    ],
    steps: [
      "Go to Azure Portal \u2192 App Registrations",
      "Create a new registration",
      "Under Certificates & Secrets, create a client secret",
      "Note the Application (client) ID and secret value",
    ],
    externalUrl: "https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps",
    externalLabel: "Open Azure Portal",
    webhookManagement: "manual" as const,
    creditCost: 0,
  },
  whatsapp: {
    name: "WhatsApp",
    icon: "MessageCircle",
    credentials: [
      { key: "phone_number_id", label: "Phone Number ID", placeholder: "1234567890", type: "text" as const },
      { key: "access_token", label: "Access Token", placeholder: "EAAG...", type: "password" as const },
      { key: "verify_token", label: "Webhook Verify Token", placeholder: "any-secret-string", type: "text" as const },
    ],
    steps: [
      "Create a Meta Business account at business.facebook.com",
      "Create an app at developers.facebook.com (type: Business)",
      "Add the WhatsApp product",
      "Note your Phone Number ID and generate an access token",
      "Choose a verify token (any string for webhook setup)",
    ],
    externalUrl: "https://developers.facebook.com/apps/",
    externalLabel: "Open Meta Developer Portal",
    webhookManagement: "manual" as const,
    creditCost: 2,
    premiumNote: "WhatsApp messages cost 2 extra credits due to Meta Cloud API fees. 24-hour reply window per conversation.",
  },
};

export type PlatformKey = keyof typeof PLATFORM_GUIDES;
