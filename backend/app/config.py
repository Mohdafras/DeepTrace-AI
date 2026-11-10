"""Environment-backed application configuration."""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime settings loaded from backend/.env when present."""
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")
    cors_origins_raw: str = Field(
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173", validation_alias="CORS_ORIGINS"
    )
    max_upload_size_bytes: int = 10 * 1024 * 1024
    database_path: str = "data/detections.db"
    model_path: str = "model/deepfake_model.keras"
    threshold_path: str = "model/threshold.json"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    def resolve(self, path: str) -> Path:
        return (BASE_DIR / path).resolve()


settings = Settings()
