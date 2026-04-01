from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TF_", env_file=".env")

    # Database
    database_url: str = "postgresql+asyncpg://triforce:triforce@localhost:5432/triforce"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "triforce-uploads"
    minio_use_ssl: bool = False

    # LLM API Key (Anthropic only)
    anthropic_api_key: SecretStr = SecretStr("")

    # Application
    log_level: str = "INFO"
    allowed_origins: list[str] = ["http://localhost:3000"]
    max_upload_size_mb: int = 500


settings = Settings()
