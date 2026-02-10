"""
Application settings configuration using Pydantic Settings.

This module defines all application configuration parameters that can be
loaded from environment variables. It provides type validation and default
values for all settings.
"""

import os
from typing import Optional
from pydantic import AliasChoices, Field, field_validator
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
        # Load from .env first, then override with environment-specific file if it exists
        env_files = [".env"]  # Always load from .env first

        app_env = os.getenv("APP_ENV", "dev")
        env_specific_file = ".env.prod" if app_env == "prod" else ".env.dev"

        if os.path.exists(env_specific_file):
            env_files.append(env_specific_file)  # Override with environment-specific file

        # Update model_config with the correct env_file list
        self.__class__.model_config = SettingsConfigDict(
            env_file=env_files,
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore"
        )

        super().__init__(**kwargs)

    # Server Configuration
    port: int = Field(
        default=7003,
        description="Port to run the FastAPI server on"
    )

    # Database Configuration
    db_dsn: str = Field(
        default="mssql+pyodbc://user:pass@SERVER/DB?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes",
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

    # Business Central SQL Server (for Continia CDC tables)
    bc_sql_server: Optional[str] = Field(
        default=None,
        description="SQL Server host for Business Central database (e.g., server\\instance)",
    )
    bc_sql_database: Optional[str] = Field(
        default=None,
        description="Business Central database name",
    )
    bc_sql_username: Optional[str] = Field(
        default=None,
        description="Business Central SQL username",
    )
    bc_sql_password: Optional[str] = Field(
        default=None,
        description="Business Central SQL password",
    )
    bc_sql_driver: str = Field(
        default="ODBC Driver 18 for SQL Server",
        description="ODBC driver to use for Business Central SQL connections",
    )

    # Windchill SQL Server (for KPI queries)
    windchill_db_dsn: Optional[str] = Field(
        default=None,
        description="Override MSSQL+pyodbc DSN for Windchill analytics database"
    )
    windchill_sql_server: Optional[str] = Field(
        default=None,
        description="SQL Server host for Windchill database (e.g., server\\instance)",
    )
    windchill_sql_database: Optional[str] = Field(
        default=None,
        description="Windchill database name",
    )
    windchill_sql_username: Optional[str] = Field(
        default=None,
        description="Windchill SQL username",
    )
    windchill_sql_password: Optional[str] = Field(
        default=None,
        description="Windchill SQL password",
    )
    windchill_sql_driver: str = Field(
        default="ODBC Driver 18 for SQL Server",
        description="ODBC driver to use for Windchill SQL connections",
    )

    fastems1_autopilot_db_dsn: Optional[str] = Field(
        default=None,
        description="Override MSSQL DSN for Fastems1 Autopilot tables (if different from DB_DSN)"
    )

    @staticmethod
    def _normalize_odbc_driver_17_to_18(value: str) -> str:
        """
        Enforce ODBC Driver 18 usage.

        We historically had references to ODBC Driver 17 in env files/DSNs.
        Since our containers install msodbcsql18, normalize any 17 references to 18.
        """
        return (
            value.replace("ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server")
            .replace("ODBC+Driver+17+for+SQL+Server", "ODBC+Driver+18+for+SQL+Server")
            .replace("{ODBC Driver 17 for SQL Server}", "{ODBC Driver 18 for SQL Server}")
        )

    @field_validator(
        "db_dsn",
        "cedule_db_dsn",
        "fastems1_autopilot_db_dsn",
        "cedule_sql_driver",
        "bc_sql_driver",
        "windchill_db_dsn",
        "windchill_sql_driver",
        mode="before",
    )
    @classmethod
    def _enforce_odbc_driver_18(cls, v):
        if v is None:
            return v
        if not isinstance(v, str):
            return v
        return cls._normalize_odbc_driver_17_to_18(v)

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

    front_accounting_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "FRONT_ACCOUNTING_API_KEY",
            "FrontApp_Accounting_API_KEY",
            "FRONTAPP_ACCOUNTING_API_KEY",
        ),
        description="Front API access token used for accounting/receivables outbound email",
    )

    front_purchasing_channel_id: Optional[str] = Field(
        default=None,
        description="Front channel ID for the purchasing inbox default channel"
    )

    front_receivables_inbox_id: Optional[str] = Field(
        default="inb_cunq0",
        validation_alias=AliasChoices(
            "FRONT_RECEIVABLES_INBOX_ID",
            "FRONT_ACCOUNTING_INBOX_ID",
        ),
        description="Front inbox ID for receivables outbound email",
    )

    front_receivables_channel_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "FRONT_RECEIVABLES_CHANNEL_ID",
            "FRONT_ACCOUNTING_CHANNEL_ID",
        ),
        description="Optional fixed Front channel ID for receivables outbound email",
    )

    toolkit_base_url: str = Field(
        default="https://api.gilbert-tech.com:7778",
        description="Base URL for Gilbert Tech internal toolkit services"
    )

    # File Share (HTTP API)
    file_share_base_url: str = Field(
        default="https://api.gilbert-tech.com:7776/api/v1",
        description="Base URL for Gilbert Tech file share API"
    )

    file_share_requester_id: Optional[str] = Field(
        default=None,
        description="Requester user identifier for file share API calls"
    )

    # File Share (SMB/NTFS)
    file_share_enabled: bool = Field(
        default=False,
        description="Enable direct SMB file share access"
    )
    file_share_server: Optional[str] = Field(
        default=None,
        description="Hostname or IP of the SMB file server"
    )
    file_share_share: Optional[str] = Field(
        default=None,
        description="Name of the SMB share (e.g., 'commun')"
    )
    file_share_base_path: str = Field(
        default="/",
        description="Base path inside the SMB share to scope file operations"
    )
    file_share_username: Optional[str] = Field(
        default=None,
        description="SMB username for the file share"
    )
    file_share_password: Optional[str] = Field(
        default=None,
        description="SMB password for the file share"
    )
    file_share_domain: Optional[str] = Field(
        default=None,
        description="Domain for SMB authentication"
    )
    file_share_port: int = Field(
        default=445,
        description="TCP port for SMB (usually 445)"
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

    openrouter_ocr_model: str = Field(
        default="openrouter/auto",
        description="OpenRouter model to use for OCR fallback"
    )

    ocr_primary_provider: str = Field(
        default="openrouter",
        description="Primary OCR provider: openrouter (default) or openai"
    )

    google_api_key: Optional[str] = Field(
        default=None,
        description="Google API key for geocoding"
    )

    google_geocode_cache_ttl_days: int = Field(
        default=7,
        ge=1,
        description="Days to keep cached customer geocodes"
    )

    google_geocode_max_concurrency: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Max concurrent Google geocoding requests"
    )

    google_geocode_block_on_miss: bool = Field(
        default=False,
        description="Block /bc/customers responses until missing geocodes are fetched"
    )

    google_geocode_block_timeout_seconds: int = Field(
        default=15,
        ge=0,
        description="Max seconds to wait for geocoding before returning partial results"
    )

    bc_ship_to_timeout_seconds: int = Field(
        default=8,
        ge=1,
        description="Max seconds to wait for ShipToAddress lookups per customer"
    )

    google_geocode_persist_enabled: bool = Field(
        default=True,
        description="Persist geocode cache to disk between container restarts"
    )

    google_geocode_cache_db_path: str = Field(
        default="/app/data/geocode_cache.sqlite",
        description="SQLite path for persisted geocode cache"
    )

    google_geocode_cache_source: str = Field(
        default="ship_to_address_v2",
        description="Cache namespace to invalidate when address source changes"
    )

    planner_kpi_cache_db_path: str = Field(
        default="/app/data/planner_kpi_cache.sqlite",
        description="SQLite path for persisted planner KPI cache",
    )
    planner_kpi_cache_retention_days: int = Field(
        default=90,
        description="Days to keep cached planner KPI history",
    )
    planner_daily_report_cache_retention_days: int = Field(
        default=30,
        description="Days to keep cached planner daily reports",
    )

    sales_stats_cache_db_path: str = Field(
        default="/app/data/sales_stats_cache.sqlite",
        description="SQLite path for persisted sales stats KPI snapshots",
    )
    sales_stats_cache_retention_days: int = Field(
        default=120,
        description="Days to keep sales stats daily snapshots",
    )

    cashflow_projection_cache_db_path: str = Field(
        default="/app/data/cashflow_projection_cache.sqlite",
        description="SQLite path for persisted finance cashflow projection cache",
    )
    cashflow_projection_cache_retention_days: int = Field(
        default=30,
        description="Days to keep daily cashflow projection cache entries",
    )
    cashflow_refresh_hour: int = Field(
        default=5,
        ge=0,
        le=23,
        description="Hour (0-23) to refresh default cashflow projection cache",
    )
    cashflow_refresh_minute: int = Field(
        default=0,
        ge=0,
        le=59,
        description="Minute (0-59) to refresh default cashflow projection cache",
    )

    jobs_snapshot_cache_db_path: str = Field(
        default="/app/data/jobs_snapshot_cache.sqlite",
        description="SQLite path for persisted jobs KPI snapshots",
    )
    jobs_snapshot_cache_retention_days: int = Field(
        default=180,
        description="Days to keep jobs daily snapshots",
    )

    payables_stats_cache_db_path: str = Field(
        default="/app/data/payables_stats_cache.sqlite",
        description="SQLite path for persisted payables invoice KPI snapshots",
    )
    payables_stats_cache_retention_days: int = Field(
        default=30,
        description="Days to keep payables invoice daily snapshots",
    )

    purchasing_stats_cache_db_path: str = Field(
        default="/app/data/purchasing_stats_cache.sqlite",
        description="SQLite path for persisted purchasing KPI snapshots",
    )
    purchasing_stats_cache_retention_days: int = Field(
        default=30,
        description="Days to keep purchasing KPI snapshots",
    )
    
    openai_model: str = Field(
        default="gpt-5-2025-08-07",
        description="OpenAI model to use for AI operations"
    )
    
    ocr_llm_model: str = Field(
        default="gpt-4.1-mini",
        description="OpenAI model to use for OCR document extraction (responses API capable)"
    )
    
    local_agent_base_url: Optional[str] = Field(
        default=None,
        description="Base URL for local AI agent service"
    )
    
    ocr_service_url: Optional[str] = Field(
        default=None,
        description="URL for OCR service (Tesseract/Azure)"
    )

    # Dynamics 365 CRM (Dataverse) Configuration
    crm_web_api_endpoint: Optional[str] = Field(
        default=None,
        description="Dynamics 365 Web API endpoint, e.g. https://<org>.api.crm3.dynamics.com/api/data/v9.2",
    )
    crm_discovery_endpoint: Optional[str] = Field(
        default="https://globaldisco.crm3.dynamics.com/api/discovery/v2.0/Instances",
        description="Dynamics 365 discovery endpoint",
    )
    crm_tenant_id: Optional[str] = Field(
        default=None,
        description="Microsoft Entra tenant ID used for CRM authentication",
    )
    crm_client_id: Optional[str] = Field(
        default=None,
        description="Microsoft Entra application (client) ID for CRM integration",
    )
    crm_client_secret: Optional[str] = Field(
        default=None,
        description="Microsoft Entra client secret for CRM integration",
    )
    crm_environment_id: Optional[str] = Field(
        default=None,
        description="Dynamics environment ID",
    )
    crm_environment_unique_name: Optional[str] = Field(
        default=None,
        description="Dynamics environment unique name",
    )
    crm_organization_id: Optional[str] = Field(
        default=None,
        description="Dynamics organization ID",
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

    clickup_access_token: Optional[str] = Field(
        default=None,
        description="ClickUp OAuth access token for authentication"
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

    # Sandvik API Configuration
    sandvik_api_enabled: bool = Field(
        default=False,
        description="Enable Sandvik API integration"
    )

    sandvik_base_url: str = Field(
        default="https://machininginsights.sandvikcoromant.com",
        description="Base URL for Sandvik Machining Insights API"
    )

    sandvik_username: Optional[str] = Field(
        default=None,
        description="Sandvik API username"
    )

    sandvik_password: Optional[str] = Field(
        default=None,
        description="Sandvik API password"
    )

    sandvik_client_id: Optional[str] = Field(
        default=None,
        description="Sandvik API client ID"
    )

    sandvik_client_secret: Optional[str] = Field(
        default=None,
        description="Sandvik API client secret"
    )

    sandvik_tenant: str = Field(
        default="produitsgilbert",
        description="Sandvik tenant identifier"
    )

    sandvik_api_timeout: int = Field(
        default=30,
        ge=1,
        description="Timeout for Sandvik API requests in seconds"
    )

    sandvik_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for Sandvik API requests"
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
        description="Allowed CORS origins (comma list, JSON array, or '*')"
    )
    cors_origin_regex: Optional[str] = Field(
        default=r"https?://.*",
        description="Regex pattern for allowed origins (applied when set)"
    )

    @field_validator("cors_origins", mode="before")
    def parse_cors_origins(cls, v):
        """Accept JSON array, comma-separated string, or '*' for all."""
        if v is None:
            return []

        if isinstance(v, str):
            raw = v.strip()
            if raw == "":
                return []
            if raw == "*":
                return ["*"]

            # JSON array input
            if raw.startswith("["):
                import json
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass  # Fallback to comma split below

            # Comma-separated list
            return [item.strip() for item in raw.split(",") if item.strip()]

        return v
    
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
    
    scheduler_timezone: str = Field(
        default="UTC",
        description="Timezone for scheduled jobs (e.g. America/New_York)"
    )

    planner_daily_report_refresh_hour: int = Field(
        default=1,
        ge=0,
        le=23,
        description="Hour (0-23) to refresh planner daily report cache"
    )

    planner_daily_report_refresh_minute: int = Field(
        default=0,
        ge=0,
        le=59,
        description="Minute (0-59) to refresh planner daily report cache"
    )

    sales_stats_refresh_hour: int = Field(
        default=2,
        ge=0,
        le=23,
        description="Hour (0-23) to refresh KPI sales stats snapshots",
    )

    sales_stats_refresh_minute: int = Field(
        default=30,
        ge=0,
        le=59,
        description="Minute (0-59) to refresh KPI sales stats snapshots",
    )

    jobs_snapshot_refresh_hour: int = Field(
        default=3,
        ge=0,
        le=23,
        description="Hour (0-23) to refresh KPI jobs snapshots",
    )

    jobs_snapshot_refresh_minute: int = Field(
        default=0,
        ge=0,
        le=59,
        description="Minute (0-59) to refresh KPI jobs snapshots",
    )

    payables_stats_refresh_hour: int = Field(
        default=4,
        ge=0,
        le=23,
        description="Hour (0-23) to refresh KPI payables invoice snapshots",
    )

    payables_stats_refresh_minute: int = Field(
        default=0,
        ge=0,
        le=59,
        description="Minute (0-59) to refresh KPI payables invoice snapshots",
    )

    ar_open_invoices_cache_path: str = Field(
        default="/app/data/ar_open_invoices_cache.sqlite",
        description="SQLite file path for AR open invoices cache"
    )

    ar_open_invoices_refresh_hour: int = Field(
        default=8,
        ge=0,
        le=23,
        description="Hour (0-23) to refresh AR open invoices cache"
    )

    ar_open_invoices_refresh_minute: int = Field(
        default=0,
        ge=0,
        le=59,
        description="Minute (0-59) to refresh AR open invoices cache"
    )

    ar_payment_stats_refresh_day: str = Field(
        default="mon-sun",
        description="Day of week for AR payment stats refresh (cron format)"
    )

    ar_payment_stats_refresh_hour: int = Field(
        default=2,
        ge=0,
        le=23,
        description="UTC hour for AR payment stats refresh"
    )

    ar_payment_stats_refresh_minute: int = Field(
        default=0,
        ge=0,
        le=59,
        description="UTC minute for AR payment stats refresh"
    )

    ar_payment_stats_lookback_days: int = Field(
        default=730,
        ge=30,
        le=3650,
        description="How many days of closed invoices to include when computing AR payment stats",
    )

    ar_payment_stats_max_invoices: int = Field(
        default=10000,
        ge=100,
        le=200000,
        description="Maximum number of closed invoices to load per AR payment stats refresh run",
    )
    
    enable_ocr: bool = Field(
        default=False,
        description="Enable OCR processing features"
    )
    
    enable_ai_assistance: bool = Field(
        default=False,
        description="Enable AI-powered assistance features"
    )

    enable_docs: bool = Field(
        default=False,
        description="Expose OpenAPI/Swagger docs endpoints even in production"
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
