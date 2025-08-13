"""
Environment-specific configuration management for Upwork Automation System.
"""
import os
from typing import Optional, List
from pydantic import BaseSettings, Field
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    url: str = Field(..., env="DATABASE_URL")
    pool_size: int = Field(10, env="DB_POOL_SIZE")
    max_overflow: int = Field(20, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(3600, env="DB_POOL_RECYCLE")
    echo: bool = Field(False, env="DB_ECHO")


class RedisConfig(BaseSettings):
    """Redis configuration settings."""
    url: str = Field(..., env="REDIS_URL")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    max_connections: int = Field(20, env="REDIS_MAX_CONNECTIONS")
    retry_on_timeout: bool = Field(True, env="REDIS_RETRY_ON_TIMEOUT")
    socket_timeout: int = Field(5, env="REDIS_SOCKET_TIMEOUT")


class BrowserbaseConfig(BaseSettings):
    """Browserbase configuration settings."""
    api_key: str = Field(..., env="BROWSERBASE_API_KEY")
    project_id: str = Field("upwork-automation", env="BROWSERBASE_PROJECT_ID")
    max_sessions: int = Field(5, env="MAX_BROWSER_SESSIONS")
    session_timeout: int = Field(3600, env="BROWSER_SESSION_TIMEOUT")
    stealth_mode: bool = Field(True, env="BROWSER_STEALTH_MODE")
    proxy_enabled: bool = Field(True, env="BROWSER_PROXY_ENABLED")


class OpenAIConfig(BaseSettings):
    """OpenAI configuration settings."""
    api_key: str = Field(..., env="OPENAI_API_KEY")
    model: str = Field("gpt-4", env="OPENAI_MODEL")
    max_tokens: int = Field(2000, env="OPENAI_MAX_TOKENS")
    temperature: float = Field(0.7, env="OPENAI_TEMPERATURE")
    timeout: int = Field(60, env="OPENAI_TIMEOUT")


class GoogleConfig(BaseSettings):
    """Google Services configuration settings."""
    credentials_path: str = Field(..., env="GOOGLE_CREDENTIALS_PATH")
    drive_folder_id: Optional[str] = Field(None, env="GOOGLE_DRIVE_FOLDER_ID")
    docs_template_id: Optional[str] = Field(None, env="GOOGLE_DOCS_TEMPLATE_ID")
    sheets_id: Optional[str] = Field(None, env="GOOGLE_SHEETS_ID")


class SlackConfig(BaseSettings):
    """Slack configuration settings."""
    bot_token: str = Field(..., env="SLACK_BOT_TOKEN")
    channel: str = Field("#upwork-automation", env="SLACK_CHANNEL")
    alert_channel: str = Field("#upwork-alerts", env="SLACK_ALERT_CHANNEL")
    webhook_url: Optional[str] = Field(None, env="SLACK_WEBHOOK_URL")


class N8NConfig(BaseSettings):
    """n8n configuration settings."""
    webhook_url: str = Field(..., env="N8N_WEBHOOK_URL")
    api_key: Optional[str] = Field(None, env="N8N_API_KEY")
    timeout: int = Field(30, env="N8N_TIMEOUT")


class SecurityConfig(BaseSettings):
    """Security configuration settings."""
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration: int = Field(3600, env="JWT_EXPIRATION")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    allowed_origins: List[str] = Field(["http://localhost:3000"], env="ALLOWED_ORIGINS")


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration settings."""
    enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    max_requests_per_minute: int = Field(60, env="MAX_REQUESTS_PER_MINUTE")
    max_daily_applications: int = Field(30, env="MAX_DAILY_APPLICATIONS")
    min_delay_between_applications: int = Field(300, env="MIN_DELAY_BETWEEN_APPLICATIONS")  # 5 minutes
    max_delay_between_applications: int = Field(1800, env="MAX_DELAY_BETWEEN_APPLICATIONS")  # 30 minutes


class JobFilterConfig(BaseSettings):
    """Job filtering configuration settings."""
    min_hourly_rate: float = Field(50.0, env="MIN_HOURLY_RATE")
    target_hourly_rate: float = Field(75.0, env="TARGET_HOURLY_RATE")
    min_client_rating: float = Field(4.0, env="MIN_CLIENT_RATING")
    min_hire_rate: float = Field(0.5, env="MIN_HIRE_RATE")
    required_keywords: List[str] = Field(
        ["Salesforce", "Agentforce", "Einstein", "AI"],
        env="REQUIRED_KEYWORDS"
    )
    excluded_keywords: List[str] = Field(
        ["adult", "gambling", "crypto"],
        env="EXCLUDED_KEYWORDS"
    )


class MonitoringConfig(BaseSettings):
    """Monitoring and logging configuration settings."""
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")
    health_check_interval: int = Field(30, env="HEALTH_CHECK_INTERVAL")
    prometheus_port: int = Field(9090, env="PROMETHEUS_PORT")
    grafana_port: int = Field(3001, env="GRAFANA_PORT")


class BackupConfig(BaseSettings):
    """Backup configuration settings."""
    enabled: bool = Field(True, env="BACKUP_ENABLED")
    schedule: str = Field("0 2 * * *", env="BACKUP_SCHEDULE")  # Daily at 2 AM
    retention_days: int = Field(30, env="BACKUP_RETENTION_DAYS")
    postgres_backup_path: str = Field("/backups/postgres", env="POSTGRES_BACKUP_PATH")
    redis_backup_path: str = Field("/backups/redis", env="REDIS_BACKUP_PATH")
    session_backup_path: str = Field("/backups/sessions", env="SESSION_BACKUP_PATH")


class Config(BaseSettings):
    """Main configuration class that combines all configuration sections."""
    
    # Environment
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # Configuration sections
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    browserbase: BrowserbaseConfig = BrowserbaseConfig()
    openai: OpenAIConfig = OpenAIConfig()
    google: GoogleConfig = GoogleConfig()
    slack: SlackConfig = SlackConfig()
    n8n: N8NConfig = N8NConfig()
    security: SecurityConfig = SecurityConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    job_filter: JobFilterConfig = JobFilterConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    backup: BackupConfig = BackupConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING


def get_config() -> Config:
    """Get configuration instance based on environment."""
    env = os.getenv("ENVIRONMENT", "development")
    
    # Load environment-specific .env file
    env_file = f".env.{env}"
    if os.path.exists(env_file):
        return Config(_env_file=env_file)
    
    return Config()


# Global configuration instance
config = get_config()