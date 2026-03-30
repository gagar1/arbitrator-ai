"""Configuration management for Arbitrator AI.

This module handles all configuration settings for the application,
including AI model settings, database connections, and security parameters.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from functools import lru_cache

# Configure logging for this module
logger = logging.getLogger(__name__)


class ModelConfig:
    """Configuration for AI model providers.
    
    This class stores settings for different AI providers like Anthropic Claude,
    OpenAI GPT, and Google Gemini. Each provider needs an API key and has
    customizable parameters for response generation.
    """
    
    def __init__(self, provider: str, model_name: str, api_key: str, 
                 temperature: float = 0.7, max_tokens: int = 2000):
        """Initialize model configuration.
        
        Args:
            provider: Name of the AI provider (e.g., 'anthropic', 'openai')
            model_name: Specific model to use (e.g., 'claude-3-sonnet')
            api_key: API key for authentication
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens in response
        """
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Validate configuration
        if not api_key or api_key in ['your_api_key_here', 'placeholder']:
            logger.warning(f"Invalid API key for {provider}")
        
        if not (0.0 <= temperature <= 2.0):
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {temperature}")
    
    @property
    def masked_api_key(self) -> str:
        """Return masked API key for safe logging.
        
        Shows only first 4 and last 4 characters of the API key,
        replacing the middle with asterisks for security.
        """
        if len(self.api_key) <= 8:
            return '***'
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"


class RAGConfig:
    """Configuration for the RAG (Retrieval-Augmented Generation) engine.
    
    This class manages settings for document processing, vector storage,
    and semantic search functionality.
    """
    
    def __init__(self):
        """Initialize RAG configuration with default values."""
        # Vector database settings
        self.collection_name = os.getenv("RAG_COLLECTION_NAME", "arbitrator_docs")
        self.embedding_model = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.persist_directory = os.getenv("RAG_PERSIST_DIR", "./data/chroma_db")
        
        # Document processing settings
        self.chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "1000"))  # Characters per chunk
        self.chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))  # Overlap between chunks
        
        # Search settings
        self.top_k_results = int(os.getenv("RAG_TOP_K", "5"))  # Number of results to return
        self.similarity_threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7"))
        
        # File processing limits
        self.max_document_size_mb = int(os.getenv("MAX_DOCUMENT_SIZE_MB", "50"))
        
        # Validate configuration
        if not (100 <= self.chunk_size <= 10000):
            raise ValueError(f"Chunk size must be between 100 and 10000, got {self.chunk_size}")
        
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")


class APIConfig:
    """Configuration for the FastAPI web server.
    
    This class manages HTTP server settings, security parameters,
    and API behavior configuration.
    """
    
    def __init__(self):
        """Initialize API configuration from environment variables."""
        # Server settings
        self.host = os.getenv("API_HOST", "0.0.0.0")  # Listen on all interfaces
        self.port = int(os.getenv("API_PORT", "8000"))  # Default HTTP port
        self.debug = os.getenv("DEBUG", "False").lower() == "true"
        
        # CORS (Cross-Origin Resource Sharing) settings
        cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        self.cors_origins = cors_origins.split(",") if cors_origins else []
        
        # Security settings
        self.api_key = os.getenv("API_KEY")  # Optional API key for authentication
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY")  # Secret for JWT tokens
        self.jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
        
        # Rate limiting
        self.rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
        self.rate_limit_requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100"))
        
        # Request size limits
        self.max_request_size_mb = int(os.getenv("MAX_REQUEST_SIZE_MB", "10"))
        
        # Validate port number
        if not (1024 <= self.port <= 65535):
            raise ValueError(f"Port must be between 1024 and 65535, got {self.port}")


class DatabaseConfig:
    """Configuration for database connections.
    
    This class manages PostgreSQL and Redis connection settings.
    """
    
    def __init__(self):
        """Initialize database configuration."""
        # PostgreSQL settings
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://arbitrator:arbitrator_password@localhost:5432/arbitrator_ai"
        )
        
        # Redis settings
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Connection pool settings
        self.db_pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
        self.db_max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        
        # Connection timeouts
        self.db_timeout = int(os.getenv("DB_TIMEOUT", "30"))
        self.redis_timeout = int(os.getenv("REDIS_TIMEOUT", "5"))


class MonitoringConfig:
    """Configuration for monitoring and observability.
    
    This class manages settings for logging, metrics, and tracing.
    """
    
    def __init__(self):
        """Initialize monitoring configuration."""
        # Logging settings
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "json")  # 'json' or 'text'
        self.log_file_path = os.getenv("LOG_FILE_PATH", "./logs/arbitrator-ai.log")
        
        # OpenTelemetry settings
        self.otel_enabled = os.getenv("OTEL_ENABLED", "False").lower() == "true"
        self.otel_service_name = os.getenv("OTEL_SERVICE_NAME", "arbitrator-ai")
        self.otel_service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
        self.jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces")
        
        # Prometheus metrics
        self.prometheus_enabled = os.getenv("PROMETHEUS_ENABLED", "True").lower() == "true"
        self.metrics_port = int(os.getenv("METRICS_PORT", "9090"))


class Config:
    """Main configuration class for Arbitrator AI.
    
    This class brings together all configuration components and provides
    a single interface for accessing application settings.
    """
    
    def __init__(self):
        """Initialize the complete application configuration."""
        logger.info("Loading application configuration...")
        
        # Load all configuration sections
        self.api = APIConfig()
        self.database = DatabaseConfig()
        self.rag = RAGConfig()
        self.monitoring = MonitoringConfig()
        
        # Initialize AI model configurations
        self._init_model_configs()
        
        # Set up data directories
        self._init_directories()
        
        # Environment information
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.service_name = self.monitoring.otel_service_name
        self.service_version = self.monitoring.otel_service_version
        
        # Validate critical configuration
        self._validate_config()
        
        logger.info(f"Configuration loaded successfully for environment: {self.environment}")
    
    def _init_model_configs(self):
        """Initialize AI model configurations for all providers."""
        # Anthropic Claude configuration
        self.anthropic = ModelConfig(
            provider="anthropic",
            model_name=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "2000"))
        )
        
        # OpenAI GPT configuration
        self.openai = ModelConfig(
            provider="openai",
            model_name=os.getenv("OPENAI_MODEL", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
        )
        
        # Google Gemini configuration
        self.gemini = ModelConfig(
            provider="gemini",
            model_name=os.getenv("GEMINI_MODEL", "gemini-pro"),
            api_key=os.getenv("GEMINI_API_KEY", ""),
            temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "2000"))
        )
    
    def _init_directories(self):
        """Create and configure data directories."""
        # Main data directory
        self.data_dir = Path(os.getenv("DATA_DIR", "./data"))
        
        # Subdirectories for different types of data
        self.contracts_dir = self.data_dir / "contracts"  # Contract documents
        self.legal_docs_dir = self.data_dir / "legal_docs"  # Legal precedents
        self.temp_dir = self.data_dir / "temp"  # Temporary file processing
        self.logs_dir = Path(self.monitoring.log_file_path).parent  # Log files
        
        # Create directories if they don't exist
        for directory in [self.data_dir, self.contracts_dir, self.legal_docs_dir, 
                         self.temp_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def _validate_config(self):
        """Validate critical configuration settings."""
        issues = []
        
        # Check for at least one valid AI provider
        valid_providers = 0
        for provider_name, config in [("Anthropic", self.anthropic), 
                                     ("OpenAI", self.openai), 
                                     ("Gemini", self.gemini)]:
            if config.api_key and config.api_key not in ['', 'your_api_key_here']:
                valid_providers += 1
                logger.info(f"{provider_name} API key configured: {config.masked_api_key}")
            else:
                logger.warning(f"{provider_name} API key not configured")
        
        if valid_providers == 0:
            issues.append("No valid AI provider API keys configured")
        
        # Check production-specific requirements
        if self.environment == 'production':
            if self.api.debug:
                issues.append("Debug mode should not be enabled in production")
            
            if not self.api.jwt_secret_key:
                issues.append("JWT secret key is required in production")
        
        # Log any configuration issues
        if issues:
            error_msg = "Configuration issues found: " + "; ".join(issues)
            logger.error(error_msg)
            if self.environment == 'production':
                raise ValueError(error_msg)
            else:
                logger.warning("Continuing with configuration issues in development mode")
    
    def get_model_config(self, provider: str) -> Optional[ModelConfig]:
        """Get model configuration for a specific provider.
        
        Args:
            provider: Name of the AI provider ('anthropic', 'openai', 'gemini')
            
        Returns:
            ModelConfig object if provider exists, None otherwise
        """
        provider_map = {
            "anthropic": self.anthropic,
            "openai": self.openai,
            "gemini": self.gemini
        }
        return provider_map.get(provider.lower())
    
    def get_available_providers(self) -> list[str]:
        """Get list of AI providers with valid API keys.
        
        Returns:
            List of provider names that have valid API keys configured
        """
        available = []
        for provider_name, config in [("anthropic", self.anthropic), 
                                     ("openai", self.openai), 
                                     ("gemini", self.gemini)]:
            if config.api_key and config.api_key not in ['', 'your_api_key_here']:
                available.append(provider_name)
        return available
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration for debugging.
        
        Returns:
            Dictionary containing key configuration information
        """
        return {
            "environment": self.environment,
            "service_name": self.service_name,
            "service_version": self.service_version,
            "api_host": self.api.host,
            "api_port": self.api.port,
            "debug_mode": self.api.debug,
            "data_directory": str(self.data_dir),
            "rag_collection": self.rag.collection_name,
            "embedding_model": self.rag.embedding_model,
            "available_ai_providers": self.get_available_providers(),
            "monitoring_enabled": self.monitoring.otel_enabled,
            "log_level": self.monitoring.log_level
        }


# Create global configuration instance
# This is loaded once when the module is imported
try:
    config = Config()
except Exception as e:
    logger.error(f"Failed to initialize configuration: {e}")
    raise


# Convenience function for getting configuration
@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get the global configuration instance.
    
    This function is cached to ensure we always return the same
    configuration object throughout the application lifecycle.
    
    Returns:
        The global Config instance
    """
    return config