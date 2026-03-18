"""Gateway configuration."""
import os

CREWHUB_API_URL = os.environ.get("CREWHUB_API_URL", "https://api.crewhubai.com")
CREWHUB_SERVICE_KEY = os.environ.get("CREWHUB_SERVICE_KEY", "")  # service account API key
GATEWAY_URL = os.environ.get("GATEWAY_URL", "")  # public URL of this gateway
PORT = int(os.environ.get("PORT", "7860"))
