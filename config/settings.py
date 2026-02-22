import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys (loaded from .env if present)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")

    # Model Assignments
    model_orchestrator: str = "gemini-3-flash-preview"
    model_supervisors: str = "gemini-3-flash-preview"
    model_onboarding: str = "gemini-3-flash-preview"
    model_settings: str = "gemini-3-flash-preview"
    model_low_complexity: str = "gemini-3.1-pro-preview" # Goals, Habits, Health, Course Rec, Progress
    model_high_complexity: str = "gemini-3.1-pro-preview"  # Fallback since pro tier endpoints string might vary. For now just stick to flash for safety.

    # File System Root Paths
    data_dir: str = "data"
    checkpoints_dir: str = "data/checkpoints"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
