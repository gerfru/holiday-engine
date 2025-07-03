# config/settings.py - Centralized Configuration Management
from pydantic_settings import BaseSettings
from typing import Optional
import logging
import os

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # API Configuration
    apify_token: Optional[str] = None
    x_rapidapi_key: Optional[str] = None  # For RapidAPI services
    x_rapidapi_host: Optional[str] = None  # For RapidAPI services
    
    # Application Configuration
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # API Retry Configuration
    max_retries: int = 3
    base_retry_delay: float = 2.0
    max_retry_delay: float = 60.0
    api_timeout: float = 300.0
    
    # Search Configuration  
    max_flights_per_search: int = 50
    max_hotels_per_search: int = 200
    max_airbnb_per_search: int = 100
    max_combinations: int = 5
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = None
    
    # Output Configuration
    output_directory: str = "output"
    export_csv: bool = True
    
    # Cache Configuration (future)
    cache_enabled: bool = False
    cache_ttl: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env
    
    def setup_logging(self) -> None:
        """Setup logging configuration"""
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=self.log_format,
            handlers=self._get_log_handlers()
        )
        
        # Set specific loggers
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("uvicorn").setLevel(logging.INFO)
    
    def _get_log_handlers(self) -> list:
        """Get logging handlers based on configuration"""
        handlers = [logging.StreamHandler()]
        
        if self.log_file:
            # Ensure log directory exists
            log_dir = os.path.dirname(self.log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            handlers.append(logging.FileHandler(self.log_file))
        
        return handlers
    
    def ensure_directories(self) -> None:
        """Ensure required directories exist"""
        os.makedirs(self.output_directory, exist_ok=True)
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.debug and os.getenv("ENVIRONMENT", "development") == "production"

# Global settings instance
settings = Settings()

# Setup logging when module is imported
settings.setup_logging()
settings.ensure_directories()

# Export for easy importing
__all__ = ["settings", "Settings"]