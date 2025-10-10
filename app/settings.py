"""
Application settings configuration using Pydantic Settings.

This module defines all application configuration parameters that can be
loaded from environment variables. It provides type validation and default
values for all settings.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings loaded from environment variables.
    
    All settings can be overridden via environment variables with the same name.
    Uses .env file if present for local development.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database Configuration
    db_dsn: str = Field(
        default="mssql+pyodbc://user:pass@SERVER/DB?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes",
        description="MSSQL database connection string with pyodbc driver"
    )
    
    # Business Central API Configuration
    erp_base_url: str = Field(
        description="Base URL for Business Central OData API"
    )
    
    # Business Central API Credentials
    bc_api_username: Optional[str] = Field(
        default=None,
        description="Business Central API username"
    )
    
    bc_api_password: Optional[str] = Field(
        default=None,
        description="Business Central API password"
    )
    
    # External Services Configuration
    logfire_api_key: Optional[str] = Field(
        default=None,
        description="API key for Logfire observability platform"
    )

    front_api_base_url: str = Field(
        default="https://api2.frontapp.com",
        description="Base URL for Front API"
    )

    front_api_key: Optional[str] = Field(
        default=None,
        description="Front API access token"
    )

    toolkit_base_url: str = Field(
        default="https://api.gilbert-tech.com:7778",
        description="Base URL for Gilbert Tech internal toolkit services"
    )

    file_share_base_url: str = Field(
        default="https://api.gilbert-tech.com:7776/api/v1",
        description="Base URL for Gilbert Tech file share API"
    )

    file_share_requester_id: Optional[str] = Field(
        default=None,
        description="Requester user identifier for file share API calls"
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for AI-powered features"
    )
    
    openai_model: str = Field(
        default="gpt-5-2025-08-07",
        description="OpenAI model to use for AI operations"
    )
    
    ocr_llm_model: str = Field(
        default="gpt-4.1-mini",
        description="OpenAI model to use for OCR document extraction"
    )
    
    local_agent_base_url: Optional[str] = Field(
        default=None,
        description="Base URL for local AI agent service"
    )
    
    ocr_service_url: Optional[str] = Field(
        default=None,
        description="URL for OCR service (Tesseract/Azure)"
    )
    
    # Application Configuration
    app_name: str = Field(
        default="LPG Core Platform API",
        description="Application name for logging and identification"
    )
    
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    
    environment: str = Field(
        default="development",
        description="Deployment environment: development|staging|production"
    )
    
    debug: bool = Field(
        default=False,
        description="Enable debug mode (verbose logging, detailed errors)"
    )
    
    # API Configuration
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="API v1 route prefix"
    )
    
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    
    # Performance Configuration
    db_pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Database connection pool size"
    )
    
    db_pool_overflow: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Maximum overflow connections for database pool"
    )
    
    db_pool_timeout: int = Field(
        default=30,
        ge=1,
        description="Database connection timeout in seconds"
    )
    
    request_timeout: int = Field(
        default=60,
        ge=1,
        description="Default timeout for external HTTP requests in seconds"
    )
    
    # Retry Configuration
    max_retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed operations"
    )
    
    retry_max_wait: int = Field(
        default=60,
        ge=1,
        description="Maximum wait time between retries in seconds"
    )
    
    # Feature Flags
    enable_scheduler: bool = Field(
        default=False,
        description="Enable APScheduler for background jobs"
    )
    
    enable_ocr: bool = Field(
        default=False,
        description="Enable OCR processing features"
    )
    
    enable_ai_assistance: bool = Field(
        default=False,
        description="Enable AI-powered assistance features"
    )
    
    # Idempotency Configuration
    idempotency_ttl_hours: int = Field(
        default=24,
        ge=1,
        description="TTL for idempotency keys in hours"
    )
    
    # Audit Configuration
    audit_retention_days: int = Field(
        default=90,
        ge=1,
        description="Number of days to retain audit logs"
    )
    
    @field_validator("db_dsn")
    @classmethod
    def validate_db_dsn(cls, v: str) -> str:
        """
        Validate that the database DSN contains required MSSQL components.
        """
        if not v.startswith("mssql+pyodbc://"):
            raise ValueError("Database DSN must use mssql+pyodbc driver")
        if "driver=" not in v.lower():
            raise ValueError("Database DSN must specify ODBC driver")
        return v
    
    @field_validator("erp_base_url")
    @classmethod
    def validate_erp_url(cls, v: Optional[str], values) -> Optional[str]:
        """
        Validate ERP base URL is provided when using official mode.
        """
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("ERP base URL must start with http:// or https://")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    @property
    def use_legacy_erp(self) -> bool:
        """Check if using legacy ERP integration."""
        return self.erp_mode == ERPMode.LEGACY
    
    @property
    def use_official_erp(self) -> bool:
        """Check if using official ERP API."""
        return self.erp_mode == ERPMode.OFFICIAL
    
    @property
    def use_canary_erp(self) -> bool:
        """Check if using canary deployment for ERP."""
        return self.erp_mode == ERPMode.CANARY


# Global settings instance
settings = Settings()
