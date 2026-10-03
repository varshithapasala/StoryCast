from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StoryCast"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./storycast.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    hf_token: str = ""
    tts_provider: str = "huggingface"
    hf_tts_provider: str = "auto"
    hf_tts_model: str = "hexgrad/Kokoro-82M"
    kokoro_voice_en: str = "af_heart"
    kokoro_voice_hi: str = "hf_alpha"
    video_provider: str = "huggingface"
    hf_video_provider: str = "fal-ai"
    hf_video_model: str = "Wan-AI/Wan2.2-TI2V-5B"
    hf_video_frames: int = 81
    hf_video_inference_steps: int = 30
    hf_video_guidance_scale: float = 5.0
    hf_video_negative_prompt: str = "text, subtitles, logo, watermark, distorted, blurry, low quality, identifiable public figure, fake news footage"
    output_width: int = 1080
    output_height: int = 1920
    output_fps: int = 30
    storage_root: Path = Path("storage")
    storage_provider: str = "local"
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    aws_region: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    cors_origins: str = "http://localhost:3000"
    allow_mock_media: bool = False
    source_user_agent: str = "StoryCast/0.1"
    source_timeout_seconds: float = 15.0
    max_article_bytes: int = 2_000_000
    crawl_delay_seconds: float = 0.5
    freshness_hours: int = 72
    model_input_cost_per_million: float = 0.0
    model_output_cost_per_million: float = 0.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
