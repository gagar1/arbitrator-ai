"""Enterprise-grade configuration management for the arbitrator-ai system."""

import os
import secrets
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import logging
from functools import lru_cache
from cryptography.fernet import Fernet
import base64
import json


@dataclass
class ModelConfig:
    """Configuration for AI models with security validation."""
    provider: str  # 'anthropic', 'openai', 'gemini'
    model_name: str
    api_key: str
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 1.0

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.api_key or self.api_key in ['', 'your_api_key_here', 'placeholder']:
            raise ValueError(f"Invalid API key for {self.provider}. Please set a valid API key.")

        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {self.temperature}")

        if not (1 <= self.max_tokens <= 100000):
            raise ValueError(f"Max tokens must be between 1 and 100000, got {self.max_tokens}")

        if not (1 <= self.timeout <= 300):
            raise ValueError(f"Timeout must be between 1 and 300 seconds, got {self.timeout}")

    @property
    def masked_api_key(self) -> str:
        """Return masked API key for logging."""
        if len(self.api_key) <= 8:
            return '***'
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"


@dataclass
class RAGConfig:
    """Configuration for RAG engine with validation."""
    collection_name: str = "arbitrator_docs"
    embedding_model: str = "all-MiniLM-L6-v2"
    persist_directory: str = "./data/chroma_db"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_results: int = 5
    similarity_threshold: float = 0.7
    max_document_size_mb: int = 50
    max_batch_size: int = 100
    processing_timeout: int = 300

    def __post_init__(self):
        """Validate RAG configuration."""
        if not (100 <= self.chunk_size <= 10000):
            raise ValueError(f"Chunk size must be between 100 and 10000, got {self.chunk_size}")

        if not (0 <= self.chunk_overlap < self.chunk_size):
            raise ValueError(f"Chunk overlap must be between 0 and chunk_size-1, got {self.chunk_overlap}")

        if not (1 <= self.top_k_results <= 100):
            raise ValueError(f"Top K results must be between 1 and 100, got {self.top_k_results}")

        if not (0.0 <= self.similarity_threshold <= 1.0):
            raise ValueError(f"Similarity threshold must be between 0.0 and 1.0, got {self.similarity_threshold}")


@dataclass
class APIConfig:
    """Configuration for FastAPI server with security."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = field(default_factory=list)
    api_key: Optional[str] = None
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 100
    rate_limit_burst: int = 20
    max_request_size_mb: int = 10
    security_headers_enabled: bool = True
    hsts_max_age: int = 31536000
    csp_enabled: bool = True

    def __post_init__(self):
        """Validate API configuration."""
        if not (1024 <= self.port <= 65535):
            raise ValueError(f"Port must be between 1024 and 65535, got {self.port}")

        if self.jwt_secret_key and len(self.jwt_secret_key) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")

        if not (1 <= self.jwt_expire_minutes <= 1440):  # Max 24 hours
            raise ValueError(f"JWT expire minutes must be between 1 and 1440, got {self.jwt_expire_minutes}")

    def generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret key."""
        return secrets.token_urlsafe(32)


@dataclass
class SecurityConfig:
    """Security configuration."""
    encryption_key: Optional[str] = None
    password_min_length: int = 12
    password_require_special: bool = True
    session_timeout_minutes: int = 60
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    def __post_init__(self):
        """Validate security configuration."""
        if self.encryption_key and len(base64.urlsafe_b64decode(self.encryption_key.encode())) != 32:
            raise ValueError("Encryption key must be 32 bytes when base64 decoded")

    def generate_encryption_key(self) -> str:
        """Generate a new encryption key."""
        return base64.urlsafe_b64encode(Fernet.generate_key()).decode()


class Config:
    """Enterprise-grade configuration class for the arbitrator-ai system."""

    def __init__(self):
        self._logger = logging.getLogger('arbitrator_ai.config')
        self._encryption_cipher = None
        self.load_from_env()
        self.validate_critical_config()

    def load_from_env(self):
        """Load configuration from environment variables with validation."""

        try:
            # Model configurations with validation
            self.anthropic_config = ModelConfig(
                provider="anthropic",
                model_name=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                api_key=self._get_secure_env("ANTHROPIC_API_KEY", ""),
                temperature=self._get_float_env("ANTHROPIC_TEMPERATURE", 0.7),
                max_tokens=self._get_int_env("ANTHROPIC_MAX_TOKENS", 4000),
                timeout=self._get_int_env("ANTHROPIC_TIMEOUT", 30)
            )
        except ValueError as e:
            self._logger.error(f"Invalid Anthropic configuration: {e}")
            raise

        try:
            self.openai_config = ModelConfig(
                provider="openai",
                model_name=os.getenv("OPENAI_MODEL", "gpt-4"),
                api_key=self._get_secure_env("OPENAI_API_KEY", ""),
                temperature=self._get_float_env("OPENAI_TEMPERATURE", 0.7),
                max_tokens=self._get_int_env("OPENAI_MAX_TOKENS", 4000),
                timeout=self._get_int_env("OPENAI_TIMEOUT", 30)
            )
        except ValueError as e:
            self._logger.error(f"Invalid OpenAI configuration: {e}")
            raise

        try:
            self.gemini_config = ModelConfig(
                provider="gemini",
                model_name=os.getenv("GEMINI_MODEL", "gemini-pro"),
                api_key=self._get_secure_env("GEMINI_API_KEY", ""),
                temperature=self._get_float_env("GEMINI_TEMPERATURE", 0.7),
                max_tokens=self._get_int_env("GEMINI_MAX_TOKENS", 4000),
                timeout=self._get_int_env("GEMINI_TIMEOUT", 30)
            )
        except ValueError as e:
            self._logger.error(f"Invalid Gemini configuration: {e}")
            raise

        # RAG configuration with validation
        try:
            self.rag_config = RAGConfig(
                collection_name=os.getenv("RAG_COLLECTION_NAME", "arbitrator_docs"),
                embedding_model=os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
                persist_directory=os.getenv("RAG_PERSIST_DIR", "./data/chroma_db"),
                chunk_size=self._get_int_env("RAG_CHUNK_SIZE", 1000),
                chunk_overlap=self._get_int_env("RAG_CHUNK_OVERLAP", 200),
                top_k_results=self._get_int_env("RAG_TOP_K", 5),
                similarity_threshold=self._get_float_env("RAG_SIMILARITY_THRESHOLD", 0.7),
                max_document_size_mb=self._get_int_env("MAX_DOCUMENT_SIZE_MB", 50),
                max_batch_size=self._get_int_env("MAX_BATCH_SIZE", 100),
                processing_timeout=self._get_int_env("PROCESSING_TIMEOUT", 300)
            )
        except ValueError as e:
            self._logger.error(f"Invalid RAG configuration: {e}")
            raise

        # API configuration with security
        try:
            cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
            self.api_config = APIConfig(
                host=os.getenv("API_HOST", "0.0.0.0"),
                port=self._get_int_env("API_PORT", 8000),
                debug=self._get_bool_env("DEBUG", False),
                cors_origins=cors_origins.split(",") if cors_origins else [],
                api_key=self._get_secure_env("API_KEY"),
                jwt_secret_key=self._get_secure_env("JWT_SECRET_KEY"),
                jwt_expire_minutes=self._get_int_env("JWT_EXPIRE_MINUTES", 30),
                rate_limit_enabled=self._get_bool_env("RATE_LIMIT_ENABLED", True),
                rate_limit_requests_per_minute=self._get_int_env("RATE_LIMIT_REQUESTS_PER_MINUTE", 100),
                max_request_size_mb=self._get_int_env("MAX_REQUEST_SIZE_MB", 10),
                security_headers_enabled=self._get_bool_env("SECURITY_HEADERS_ENABLED", True)
            )
        except ValueError as e:
            self._logger.error(f"Invalid API configuration: {e}")
            raise

        # Security configuration
        try:
            self.security_config = SecurityConfig(
                encryption_key=self._get_secure_env("ENCRYPTION_KEY"),
                password_min_length=self._get_int_env("PASSWORD_MIN_LENGTH", 12),
                session_timeout_minutes=self._get_int_env("SESSION_TIMEOUT_MINUTES", 60),
                max_login_attempts=self._get_int_env("MAX_LOGIN_ATTEMPTS", 5)
            )
        except ValueError as e:
            self._logger.error(f"Invalid security configuration: {e}")
            raise

        # Data directories with secure permissions
        self.data_dir = Path(os.getenv("DATA_DIR", "./data"))
        self.contracts_dir = self.data_dir / "contracts"
        self.legal_docs_dir = self.data_dir / "legal_docs"
        self.temp_dir = self.data_dir / "temp"
        self.logs_dir = Path(os.getenv("LOG_FILE_PATH", "./logs")).parent

        # Create directories with secure permissions
        for directory in [self.data_dir, self.contracts_dir, self.legal_docs_dir, self.temp_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True, mode=0o750)

        # Environment and deployment info
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.service_name = os.getenv("OTEL_SERVICE_NAME", "arbitrator-ai")
        self.service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")

    def _get_secure_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable with security validation."""
        value = os.getenv(key, default)
        if value and value in ['', 'your_api_key_here', 'placeholder', 'changeme', 'default']:
            self._logger.warning(f"Potentially insecure value for {key}")
            return None
        return value

    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer environment variable with validation."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError as e:
            self._logger.error(f"Invalid integer value for {key}: {os.getenv(key)}")
            raise ValueError(f"Invalid integer value for {key}") from e

    def _get_float_env(self, key: str, default: float) -> float:
        """Get float environment variable with validation."""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError as e:
            self._logger.error(f"Invalid float value for {key}: {os.getenv(key)}")
            raise ValueError(f"Invalid float value for {key}") from e

    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with validation."""
        value = os.getenv(key, str(default)).lower()
        if value in ['true', '1', 'yes', 'on']:
            return True
        elif value in ['false', '0', 'no', 'off']:
            return False
        else:
            self._logger.error(f"Invalid boolean value for {key}: {value}")
            raise ValueError(f"Invalid boolean value for {key}: {value}")

    def get_model_config(self, provider: str) -> Optional[ModelConfig]:
        """Get model configuration for specified provider."""
        configs = {
            "anthropic": self.anthropic_config,
            "openai": self.openai_config,
            "gemini": self.gemini_config
        }
        return configs.get(provider)

    def get_encryption_cipher(self) -> Optional[Fernet]:
        """Get encryption cipher for sensitive data."""
        if not self._encryption_cipher and self.security_config.encryption_key:
            try:
                key = base64.urlsafe_b64decode(self.security_config.encryption_key.encode())
                self._encryption_cipher = Fernet(key)
            except Exception as e:
                self._logger.error(f"Failed to initialize encryption cipher: {e}")
        return self._encryption_cipher

    def encrypt_sensitive_data(self, data: str) -> Optional[str]:
        """Encrypt sensitive data."""
        cipher = self.get_encryption_cipher()
        if cipher:
            try:
                return cipher.encrypt(data.encode()).decode()
            except Exception as e:
                self._logger.error(f"Failed to encrypt data: {e}")
        return None

    def decrypt_sensitive_data(self, encrypted_data: str) -> Optional[str]:
        """Decrypt sensitive data."""
        cipher = self.get_encryption_cipher()
        if cipher:
            try:
                return cipher.decrypt(encrypted_data.encode()).decode()
            except Exception as e:
                self._logger.error(f"Failed to decrypt data: {e}")
        return None

    def validate_critical_config(self):
        """Validate critical configuration that could prevent startup."""
        critical_issues = []

        # Check for at least one valid AI provider
        valid_providers = 0
        for provider, config in [("anthropic", self.anthropic_config),
                                 ("openai", self.openai_config),
                                 ("gemini", self.gemini_config)]:
            if config.api_key and config.api_key not in ['', 'your_api_key_here']:
                valid_providers += 1

        if valid_providers == 0:
            critical_issues.append("No valid AI provider API keys configured")

        # Check JWT secret in production
        if self.environment == 'production' and not self.api_config.jwt_secret_key:
            critical_issues.append("JWT secret key required in production")

        # Check encryption key in production
        if self.environment == 'production' and not self.security_config.encryption_key:
            critical_issues.append("Encryption key required in production")

        if critical_issues:
            error_msg = "Critical configuration issues: " + "; ".join(critical_issues)
            self._logger.error(error_msg)
            raise ValueError(error_msg)

    def validate_config(self) -> Dict[str, Any]:
        """Comprehensive configuration validation."""
        issues = []
        warnings = []

        # Check API keys
        for provider, config in [("anthropic", self.anthropic_config),
                                 ("openai", self.openai_config),
                                 ("gemini", self.gemini_config)]:
            if not config.api_key:
                issues.append(f"{provider.upper()}_API_KEY not set")
            elif config.api_key in ['your_api_key_here', 'placeholder']:
                issues.append(f"{provider.upper()}_API_KEY contains placeholder value")

        # Check directories
        for dir_name, directory in [("data", self.data_dir), ("contracts", self.contracts_dir),
                                    ("legal_docs", self.legal_docs_dir), ("temp", self.temp_dir)]:
            if not directory.exists():
                warnings.append(f"{dir_name} directory does not exist: {directory}")
            elif not os.access(directory, os.R_OK | os.W_OK):
                issues.append(f"Insufficient permissions for {dir_name} directory: {directory}")

        # Security checks
        if self.environment == 'production':
            if self.api_config.debug:
                warnings.append("Debug mode enabled in production")
            if not self.api_config.security_headers_enabled:
                warnings.append("Security headers disabled in production")
            if not self.api_config.rate_limit_enabled:
                warnings.append("Rate limiting disabled in production")

        # Performance checks
        if self.rag_config.chunk_size > 2000:
            warnings.append(f"Large chunk size may impact performance: {self.rag_config.chunk_size}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "config_summary": {
                "environment": self.environment,
                "service_name": self.service_name,
                "service_version": self.service_version,
                "data_dir": str(self.data_dir),
                "api_port": self.api_config.port,
                "debug_mode": self.api_config.debug,
                "security_headers": self.api_config.security_headers_enabled,
                "rate_limiting": self.api_config.rate_limit_enabled,
                "rag_collection": self.rag_config.collection_name,
                "embedding_model": self.rag_config.embedding_model,
                "valid_ai_providers": [provider for provider, config in
                                       [("anthropic", self.anthropic_config),
                                        ("openai", self.openai_config),
                                        ("gemini", self.gemini_config)]
                                       if config.api_key and config.api_key not in ['', 'your_api_key_here']]
            }
        }

    @lru_cache(maxsize=1)
    def get_config_hash(self) -> str:
        """Get hash of current configuration for change detection."""
        import hashlib
        config_str = json.dumps({
            "api_port": self.api_config.port,
            "debug": self.api_config.debug,
            "environment": self.environment,
            "rag_collection": self.rag_config.collection_name,
            "embedding_model": self.rag_config.embedding_model
        }, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]


# Global configuration instance with error handling
try:
    config = Config()
except Exception as e:
    logging.error(f"Failed to initialize configuration: {e}")
    raise
