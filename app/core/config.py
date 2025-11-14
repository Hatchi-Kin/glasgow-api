from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")
    
    # App settings
    app_name: str = Field(default="Glasgow GitOps API", description="Application name")
    app_version: str = Field(default="1.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    
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
    
    # Navidrome settings
    music_folder_path: str = Field(default="/music", description="Path to music folder")
    allowed_music_extensions: set[str] = Field(
        default={'.mp3', '.flac', '.ogg', '.m4a', '.wav', '.aac'},
        description="Allowed music file extensions"
    )
    
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
    config_source = "environment variables" if os.getenv("POSTGRES_HOST") else ".env file"
    return f"Configuration loaded from: {config_source}"