import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Sports Analyzer AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS Origins
    CORS_ORIGINS: List[str] = ["*"]
    
    # Storage and paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    MODELS_DIR: str = os.path.join(BASE_DIR, "models")
    RULES_DIR: str = os.path.join(BASE_DIR, "rules")
    UPLOADS_DIR: str = os.path.join(DATA_DIR, "uploads")
    MATCHES_DIR: str = os.path.join(DATA_DIR, "matches")
    
    # Database
    DATABASE_URL: str = f"sqlite:///{os.path.join(DATA_DIR, 'sports_analyzer.db')}"
    
    # Vision & Detection Settings
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.40
    DEFAULT_IOU_THRESHOLD: float = 0.45
    DEFAULT_MODEL_NAME: str = "yolov8n.pt"
    MAX_PATH_HISTORY_LENGTH: int = 60  # number of frames to store for player trail
    TRACKER_MAX_AGE: int = 30  # max frames to keep lost track before deleting
    TRACKER_MIN_HITS: int = 3   # minimum hits before confirming a track

    # AI / Gemini API — set GEMINI_API_KEY in .env to enable cloud chatbot
    GEMINI_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()

# Ensure directories exist
for path in [settings.DATA_DIR, settings.MODELS_DIR, settings.RULES_DIR, settings.UPLOADS_DIR, settings.MATCHES_DIR]:
    os.makedirs(path, exist_ok=True)
