from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    # App settings
    app_name: str = "Glasgow GitOps API"
    app_version: str = "0.1.0"
    debug: bool = False

    # PostgreSQL settings
    postgres_host: str = Field(..., description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(..., description="PostgreSQL username")
    postgres_password: str = Field(..., description="PostgreSQL password")
    postgres_db: str = Field(..., description="PostgreSQL database name")

    # MinIO settings
    minio_endpoint: str = Field(..., description="MinIO endpoint")
    minio_access_key: str = Field(..., description="MinIO access key")
    minio_secret_key: str = Field(..., description="MinIO secret key")
    minio_secure: bool = Field(default=False, description="Use HTTPS for MinIO")

    @property
    def postgres_dsn(self) -> str:
        """Build PostgreSQL connection string."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def postgres_admin_dsn(self) -> str:
        """Build PostgreSQL admin connection string (connects to postgres db)."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/postgres"


# Global settings instance
settings = Settings()


# Optional: Log configuration source for debugging
def log_config_info():
    """Log configuration information for debugging."""
    import os

    config_source = (
        "environment variables" if os.getenv("POSTGRES_HOST") else ".env file"
    )
    return f"Configuration loaded from: {config_source}"
