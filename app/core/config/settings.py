# Importing necessary modules for configuration management
import json
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv


# Lightweight bootstrap so import-time logs don't get swallowed before the
# structured logger is configured in app.core.logging.configure_logging.
logging.basicConfig(level=logging.INFO, format="%(message)s", force=False)
logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Application environment types.
    Defines the possible environments the application can run in:
    development, staging, production, and test.
    """
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


# Determine environment
def get_environment() -> Environment:
    """Get the current environment.
       Returns:
       Environment: The current environment (development, staging, production, or test)
    """
    match os.getenv("APP_ENV", "development").lower():
        case "production" | "prod":
            return Environment.PRODUCTION
        case "staging" | "stage":
            return Environment.STAGING
        case "test":
            return Environment.TEST
        case _:
            return Environment.DEVELOPMENT


# Load appropriate .env file based on environment
def load_env_file():
    """Load environment-specific .env file."""
    env = get_environment()
    logger.info("Loading environment: %s", env.value)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Define env files in priority order
    env_files = [
        os.path.join(base_dir, f".env.{env.value}.local"),
        os.path.join(base_dir, f".env.{env.value}"),
        os.path.join(base_dir, ".env.local"),
        os.path.join(base_dir, ".env"),
    ]
    # Load the first env file that exists
    for env_file in env_files:
        if os.path.isfile(env_file):
            load_dotenv(dotenv_path=env_file)
            logger.info("Loaded environment from %s", env_file)
            return env_file
    # Fall back to default if no env file found
    logger.warning(
        "No environment file found; relying on existing environment variables")
    return None


# Call the function to load the env file
ENV_FILE = load_env_file()


# Parse list values from environment variables
def parse_list_from_env(env_key, default=None):
    """Parse a comma-separated list from an environment variable."""
    value = os.getenv(env_key)
    if not value:
        return default or []

    # Remove quotes if they exist
    value = value.strip("\"'")

    # Handle single value case
    if "," not in value:
        return [value]

    # Split comma-separated values
    return [item.strip() for item in value.split(",") if item.strip()]

# Parse dict of lists from environment variables with prefix


def parse_dict_of_lists_from_env(prefix, default_dict=None):
    """Parse dictionary of lists from environment variables with a common prefix."""
    result = default_dict or {}

    # Look for all env vars with the given prefix
    for key, value in os.environ.items():
        if key.startswith(prefix):
            endpoint = key[len(prefix):].lower()  # Extract endpoint name

            # Parse the values for this endpoint
            if value:
                value = value.strip("\"'")
                if "," in value:
                    result[endpoint] = [item.strip()
                                        for item in value.split(",") if item.strip()]
                else:
                    result[endpoint] = [value]
    return result


class Settings:
    """
    Centralized application configuration.
    Loads from environment variables and applies defaults.
    """

    def __init__(self):
        # Set the current environment
        self.ENVIRONMENT = get_environment()

        # ==========================
        # Application Basics
        # ==========================
        self.PROJECT_NAME = os.getenv(
            "PROJECT_NAME", "FastAPI LangGraph Agent")
        self.VERSION = os.getenv("VERSION", "1.0.0")
        self.API_V1_STR = os.getenv("API_V1_STR", "/api/v1")
        self.DEBUG = os.getenv("DEBUG", "false").lower() in (
            "true", "1", "t", "yes")

        # Parse CORS origins using our helper
        self.ALLOWED_ORIGINS = parse_list_from_env("ALLOWED_ORIGINS", ["*"])

        # ==========================
        # LLM & LangGraph
        # ==========================

        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
        self.DEFAULT_LLM_TEMPERATURE = float(
            os.getenv("DEFAULT_LLM_TEMPERATURE", "0.2"))

        # Agent specific settings
        self.MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
        self.MAX_LLM_CALL_RETRIES = int(os.getenv("MAX_LLM_CALL_RETRIES", "3"))

        # ==========================
        # Observability (Langfuse)
        # ==========================
        self.LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self.LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
        self.LANGFUSE_HOST = os.getenv(
            "LANGFUSE_HOST", "https://cloud.langfuse.com")

        # ==========================
        # Database (PostgreSQL)
        # ==========================
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
        self.POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

        # Pool settings are critical for high-concurrency agents
        self.POSTGRES_POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", "20"))
        self.POSTGRES_MAX_OVERFLOW = int(
            os.getenv("POSTGRES_MAX_OVERFLOW", "10"))

        # LangGraph persistence tables
        self.CHECKPOINT_TABLES = ["checkpoint_blobs",
                                  "checkpoint_writes", "checkpoints"]

        # ==========================
        # Security (JWT)
        # ==========================
        self.JWT_SECRET_KEY = os.getenv(
            "JWT_SECRET_KEY", "unsafe-secret-for-dev")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRE_DAYS = int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_DAYS", "30"))

        # ==========================
        # Rate Limiting
        # ==========================
        self.RATE_LIMIT_DEFAULT = parse_list_from_env(
            "RATE_LIMIT_DEFAULT", ["200 per day", "50 per hour"])

        # Define endpoint specific limits
        self.RATE_LIMIT_ENDPOINTS = {
            "chat": parse_list_from_env("RATE_LIMIT_CHAT", ["30 per minute"]),
            "chat_stream": parse_list_from_env("RATE_LIMIT_CHAT_STREAM", ["20 per minute"]),
            "auth": parse_list_from_env("RATE_LIMIT_LOGIN", ["20 per minute"]),
            "root": parse_list_from_env("RATE_LIMIT_ROOT", ["10 per minute"]),
            "health": parse_list_from_env("RATE_LIMIT_HEALTH", ["20 per minute"]),
        }

        # Apply logic to override settings based on environment
        self.apply_environment_settings()

    def apply_environment_settings(self):
        """
        Apply rigorous overrides based on the active environment.
        This ensures production security even if .env is misconfigured.
        """
        if self.ENVIRONMENT == Environment.DEVELOPMENT:
            self.DEBUG = True
            self.LOG_LEVEL = "DEBUG"
            self.LOG_FORMAT = "console"
            # Relax rate limits for local development
            self.RATE_LIMIT_DEFAULT = ["1000 per day", "200 per hour"]

        elif self.ENVIRONMENT == Environment.PRODUCTION:
            self.DEBUG = False
            self.LOG_LEVEL = "WARNING"
            self.LOG_FORMAT = "json"
            # Stricter limits for production
            self.RATE_LIMIT_DEFAULT = ["200 per day", "50 per hour"]


# Initialize the global settings object
settings = Settings()
