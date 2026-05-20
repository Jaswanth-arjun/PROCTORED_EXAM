import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4o-mini"
    API_PROVIDER: str = os.getenv("API_PROVIDER", "openai")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv(
        "OPENROUTER_MODEL", "google/gemini-2.5-flash"
    )
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_MODEL: str = os.getenv(
        "NVIDIA_MODEL", "meta/llama-3.2-90b-vision-instruct"
    )
    TESSERACT_PATH: str = os.getenv(
        "TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )
    DATABASE_PATH: str = "mcq_assistant.db"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]
    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10MB
    OCR_CONFIDENCE_THRESHOLD: float = 60.0

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
