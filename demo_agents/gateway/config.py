from pydantic_settings import BaseSettings

class GatewaySettings(BaseSettings):
    crewhub_api_url: str = "https://api-staging.crewhubai.com/api/v1"
    gateway_service_key: str = ""
    gateway_public_url: str = ""  # this gateway's public URL (for callback URLs)
    port: int = 7860
    model_config = {"env_file": ".env", "extra": "ignore"}

settings = GatewaySettings()
