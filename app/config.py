"""
CCI Calculator Configuration

This module contains configuration settings for the CCI Calculator application.
"""
from pydantic import BaseSettings
from typing import Dict, Any, Optional, List
import os
import json
import logging
from pathlib import Path

# Configure basic logging until proper configuration is loaded
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class Settings(BaseSettings):
    """
    Application settings loaded from environment variables with defaults.
    """
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CCI Calculator API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "API for calculating Charlson Comorbidity Index (CCI) scores from ICD-10 codes"
    
    # CORS settings
    CORS_ORIGINS: str = "*"  # Comma-separated list of origins or "*" for all
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # Number of requests
    RATE_LIMIT_PERIOD: int = 60  # Period in seconds
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: Dict[str, str] = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "json": "application/json"
    }
    
    # Processing settings
    BATCH_SIZE: int = 1000  # Number of records to process in a batch
    MAX_WORKERS: int = 4  # Number of worker processes for parallel processing
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DIR: str = "logs"
    LOG_CONFIG_PATH: str = "config/logging.json"
    
    # Temporary file storage
    TEMP_DIR: str = "temp"
    
    # Results storage (temporary, not persistent)
    RESULTS_TTL: int = 3600  # Time to live for results in seconds (1 hour)
    
    # Configuration paths
    CONFIG_DIR: str = "config"
    MAPPING_CONFIG_PATH: str = "config/mapping.json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


def load_json_config(file_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        file_path: Path to the JSON configuration file
        
    Returns:
        Dictionary containing the configuration
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Configuration file not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in configuration file: {file_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading configuration file {file_path}: {str(e)}")
        return {}


def configure_logging(settings: Settings) -> None:
    """
    Configure logging based on the logging.json configuration file.
    
    Args:
        settings: Application settings
    """
    try:
        if os.path.exists(settings.LOG_CONFIG_PATH):
            with open(settings.LOG_CONFIG_PATH, 'r') as f:
                log_config = json.load(f)
                
            # Update file paths to use the configured log directory
            for handler in log_config.get('handlers', {}).values():
                if 'filename' in handler:
                    # Replace /app/logs with the actual log directory
                    handler['filename'] = handler['filename'].replace('/app/logs', settings.LOG_DIR)
            
            logging.config.dictConfig(log_config)
            logger.info(f"Logging configured from {settings.LOG_CONFIG_PATH}")
        else:
            logger.info(f"Logging configuration file not found: {settings.LOG_CONFIG_PATH}. Using default configuration.")
    except Exception as e:
        logger.error(f"Error configuring logging: {str(e)}")


# Create settings instance
settings = Settings()

# Ensure required directories exist
os.makedirs(settings.LOG_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)
os.makedirs(settings.CONFIG_DIR, exist_ok=True)

# Load mapping configuration
mapping_config = load_json_config(settings.MAPPING_CONFIG_PATH)
if mapping_config:
    logger.info(f"Loaded mapping configuration from {settings.MAPPING_CONFIG_PATH}")
else:
    logger.warning(f"No mapping configuration found at {settings.MAPPING_CONFIG_PATH}")

# Import logging.config here to avoid circular imports
import logging.config

# Configure logging
configure_logging(settings)