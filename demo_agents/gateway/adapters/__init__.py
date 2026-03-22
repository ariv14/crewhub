from .telegram import TelegramAdapter

ADAPTERS = {
    "telegram": TelegramAdapter(),
}

def get_adapter(platform: str):
    adapter = ADAPTERS.get(platform)
    if not adapter:
        raise ValueError(f"Unsupported platform: {platform}")
    return adapter
