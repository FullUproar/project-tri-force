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

    # API Authentication
    api_key: SecretStr = SecretStr("dev-key-change-me")

    # Stripe Billing
    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")
    stripe_price_id: str = ""  # Price ID for the $299/month ASC plan

    # Data Retention
    data_retention_days: int = 90  # Auto-purge completed jobs older than this

    # Application
    log_level: str = "INFO"
    allowed_origins: list[str] = ["http://localhost:3000"]
    max_upload_size_mb: int = 500


settings = Settings()
