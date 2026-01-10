"""
Configuration module for KlingBot.
Loads environment variables using pydantic-settings.
"""

from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Telegram Bot
    bot_token: str
    webhook_url: str = ""
    
    # Supabase
    supabase_url: str
    supabase_service_key: str
    
    # Kling API
    kling_api_key: str
    kling_api_base_url: str = "https://api.kie.ai/api/v1"
    
    # Hub Bot (payments)
    hub_bot_username: str = "aiverse_hub_bot"
    hub_allowed_amounts: str = "50,120,300,800"
    hub_allowed_star_amounts: str = "10,20,50,100"
    
    # Cloudflare R2 (video storage)
    r2_video_account_id: str = ""
    r2_video_access_key_id: str = ""
    r2_video_secret_access_key: str = ""
    r2_bucket_video_refs: str = "video-refs"
    r2_public_url_video_refs: str = ""
    
    @property
    def allowed_amounts(self) -> List[int]:
        return [int(x) for x in self.hub_allowed_amounts.split(",")]
    
    @property
    def allowed_star_amounts(self) -> List[int]:
        return [int(x) for x in self.hub_allowed_star_amounts.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
