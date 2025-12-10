"""
Application settings configuration using Pydantic Settings.

This module defines all application configuration parameters that can be
loaded from environment variables. It provides type validation and default
values for all settings.
"""

import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings loaded from environment variables.

    All settings can be overridden via environment variables with the same name.
    Uses .env file if present for local development, or .env.dev/.env.prod based on APP_ENV.
    """

    # App Environment - determines which .env file to load
    app_env: str = Field(
        default="dev",
        description="Application environment: dev|prod (controls .env file loading)"
    )

    # Dynamically set env_file based on APP_ENV
    @property
    def env_file_path(self) -> str:
        """Get the appropriate .env file path based on APP_ENV."""
        if self.app_env == "prod":
            return ".env.prod"
        elif self.app_env == "dev":
            return ".env.dev"
        else:
            return ".env"

    model_config = SettingsConfigDict(
        env_file=None,  # Will be set dynamically
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        # Load APP_ENV first to determine which .env file to use
        app_env = os.getenv("APP_ENV", "dev")

        # Set the env_file based on APP_ENV
        env_file_path = ".env.prod" if app_env == "prod" else ".env.dev"

        # Update model_config with the correct env_file
        self.__class__.model_config = SettingsConfigDict(
            env_file=env_file_path if os.path.exists(env_file_path) else ".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore"
        )

        super().__init__(**kwargs)
    
    # Database Configuration
    db_dsn: str = Field(
        default="mssql+pyodbc://user:pass@SERVER/DB?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes",
        description="MSSQL database connection string with pyodbc driver"
    )
    
    # Optional Cedule Database (Mill Test certificates)
    cedule_db_dsn: Optional[str] = Field(
        default=None,
        description="Override MSSQL+pyodbc DSN for Cedule database (Mill Test certificates)"
    )
    cedule_sql_server: Optional[str] = Field(
        default=None,
        description="SQL Server host for Cedule database (e.g., server\\instance)"
    )
    cedule_sql_database: Optional[str] = Field(
        default=None,
        description="Cedule database name"
    )
    cedule_sql_username: Optional[str] = Field(
        default=None,
        description="Cedule database username"
    )
    cedule_sql_password: Optional[str] = Field(
        default=None,
        description="Cedule database password"
    )
    cedule_sql_driver: str = Field(
        default="ODBC Driver 18 for SQL Server",
        description="ODBC driver to use for Cedule SQL connections"
    )

    fastems1_autopilot_db_dsn: Optional[str] = Field(
        default=None,
        description="Override MSSQL DSN for Fastems1 Autopilot tables (if different from DB_DSN)"
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
    bc_explorer_api_base_url: Optional[str] = Field(
        default="https://bc.gilbert-tech.com:7063/ProductionBCBasic/api/GITECH/Explorateur/beta/",
        description="Base URL for Business Central Explorer API used for custom endpoints like easyPDFAddress"
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

    # Fastems1 Autopilot configuration
    fastems1_autopilot_enabled: bool = Field(
        default=False,
        description="Enable Fastems1 Autopilot endpoints and services"
    )
    fastems1_production_api_base_url: Optional[str] = Field(
        default="https://api.gilbert-tech.com:7776/api/v1",
        description="Base URL for Fastems1 production/WorkOrder API"
    )
    fastems1_production_requester_id: Optional[str] = Field(
        default=None,
        description="RequesterUserID header value for Fastems1 production API"
    )
    fastems1_tooling_api_base_url: Optional[str] = Field(
        default="https://api.gilbert-tech.com:7776/api/v1",
        description="Base URL for CNCTooling machine tools API"
    )
    fastems1_nc_program_tool_base_url: Optional[str] = Field(
        default="http://lpgadoc03:8585/fastems1",
        description="Base URL for NC program tool metadata"
    )
    fastems1_material_api_base_url: Optional[str] = Field(
        default="http://lpgadoc03:8585/fastems1",
        description="Base URL for Fastems1 material pallet inventory (dy_storage)"
    )
    fastems1_pallet_route_api_base_url: Optional[str] = Field(
        default="http://lpgadoc03:8585/fastems1",
        description="Base URL for Fastems1 pallet route status (dy_pallet_routes)"
    )
    fastems1_default_shift_timezone: str = Field(
        default="America/Toronto",
        description="IANA timezone for shift-window evaluation"
    )
    fastems1_ignore_ttl_hours: int = Field(
        default=24,
        ge=1,
        description="Default number of hours to ignore a refused job"
    )
    fastems1_plan_jobs_per_machine: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional cap on planned jobs per machine (None = plan everything)"
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for AI-powered features"
    )

    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouter API key for alternative LLM providers"
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
    
    # ClickUp Configuration
    clickup_api_base_url: str = Field(
        default="https://api.clickup.com/api/v2",
        description="Base URL for ClickUp API"
    )

    clickup_api_key: Optional[str] = Field(
        default=None,
        description="ClickUp API token for authentication"
    )

    clickup_sav_folder_id: Optional[str] = Field(
        default=None,
        description="ClickUp folder ID for SAV (Service Après Vente) tasks"
    )

    clickup_rabotage_list_id: Optional[str] = Field(
        default=None,
        description="ClickUp list ID for Rabotage (Regrinding) tasks"
    )

    # Zendesk Configuration
    zendesk_api_base_url: str = Field(
        default="https://api.zendesk.com",
        description="Base URL for Zendesk API"
    )

    zendesk_subdomain: Optional[str] = Field(
        default=None,
        description="Zendesk subdomain (e.g., 'company' for company.zendesk.com)"
    )

    zendesk_api_key: Optional[str] = Field(
        default=None,
        description="Zendesk API token for authentication"
    )

    zendesk_username: Optional[str] = Field(
        default=None,
        description="Zendesk username (email) for authentication"
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

    @field_validator("fastems1_plan_jobs_per_machine", mode="before")
    @classmethod
    def normalize_plan_limit(cls, value):
        """
        Treat blank/zero values as 'no limit' so planners can schedule every job.
        """
        if value is None:
            return None
        if isinstance(value, str):
            lowered = value.strip().lower()
            if not lowered or lowered in {"none", "null"}:
                return None
            try:
                numeric = int(lowered)
            except ValueError:
                return value
        else:
            try:
                numeric = int(value)
            except (TypeError, ValueError):
                return value
        if numeric <= 0:
            return None
        return numeric
    
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
