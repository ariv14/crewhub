---
title: CrewHub Gateway
emoji: 🔗
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
---

# CrewHub Multi-Channel Gateway

Messaging gateway that connects CrewHub AI agents to Telegram, Slack, Discord, Teams, and WhatsApp.

## Environment Variables

- `CREWHUB_API_URL` — CrewHub API base URL (default: https://api.crewhubai.com)
- `CREWHUB_SERVICE_KEY` — Service account API key for CrewHub
- `GATEWAY_URL` — Public URL of this gateway (for webhook registration)
