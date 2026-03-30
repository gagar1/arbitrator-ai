"""Enterprise-grade FastAPI main application for the Arbitrator AI system.

This is the central hub of the Arbitrator AI application - the "front door" that:
- Receives HTTP requests from users and other systems
- Routes requests to appropriate AI agents and services
- Handles authentication, security, and monitoring
- Manages the application lifecycle (startup, shutdown, health checks)
- Provides comprehensive logging and metrics for production operations

Think of this as the "conductor" of an orchestra, coordinating all the different
components (agents, RAG engine, security, monitoring) to work together harmoniously.

Key Features:
🔐 Enterprise Security: JWT authentication, rate limiting, IP whitelisting
📊 Comprehensive Monitoring: Prometheus metrics, structured logging, health checks
🚀 Production Ready: Async operations, error handling, graceful startup/shutdown
🛡️ Security Headers: CORS, CSP, HSTS, and other security protections
"""

# Core Python libraries for async operations and utilities
import asyncio  # For async/await and concurrent operations
import time  # For timing and performance measurement
import uuid  # For generating unique request IDs
from contextlib import asynccontextmanager  # For managing application lifecycle
from typing import Dict, Any, List, Optional  # For type hints and better code documentation

# FastAPI framework components - the web server that handles HTTP requests
from fastapi import FastAPI, HTTPException, Depends, Security, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware  # Cross-Origin Resource Sharing
from fastapi.middleware.trustedhost import TrustedHostMiddleware  # Host validation
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # Authentication
from fastapi.responses import JSONResponse  # JSON response formatting

# Monitoring and metrics - essential for production systems
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import logging  # For application logging

# Import our application modules - the actual business logic
from .routes import agents, documents, analysis, health  # API route handlers
from ..core.config import config  # Configuration management
from ..core.rag_engine import RAGEngine  # The "knowledge brain" for document search
from ..core.document_processor import DocumentProcessor  # Handles PDF, DOCX, and other file formats

# Logging infrastructure - critical for debugging and monitoring
from ..core.logging_config import (
    logging_config,  # Sets up structured JSON logging
    get_logger,  # Gets logger instances
    set_request_id,  # Tracks individual requests
    set_correlation_id,  # Tracks requests across services
    generate_request_id  # Creates unique request identifiers
)

# Security infrastructure - protects against attacks and unauthorized access
from ..core.security import (
    RateLimiter,  # Prevents abuse by limiting requests per minute
    SecurityValidator,  # Validates input for security threats
    AuthenticationManager,  # Handles JWT token authentication
    IPWhitelist,  # Restricts access to approved IP addresses
    SecurityHeaders,  # Adds security headers to responses
    AuditLogger,  # Logs security events for compliance
    rate_limiter,  # Global rate limiter instance
    security_validator,  # Global security validator instance
    audit_logger  # Global audit logger instance
)

# Initialize enterprise logging system
# This sets up structured JSON logging that's essential for production monitoring
logging_config.setup_logging()
logger = get_logger('api.main')  # Get a logger specifically for this module

# Prometheus metrics - these track application performance and health
# Prometheus is the industry standard for monitoring microservices

# Track total HTTP requests by method, endpoint, and response status
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests received by the API',
    ['method', 'endpoint', 'status_code']  # Labels for filtering and grouping
)

# Track how long requests take to process (performance monitoring)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request processing time in seconds',
    ['method', 'endpoint']  # Group by HTTP method and endpoint
)

# Track errors for alerting and debugging
ERROR_COUNT = Counter(
    'http_errors_total',
    'Total HTTP errors encountered',
    ['endpoint', 'error_type']  # Track which endpoints fail and why
)

# Track RAG engine operations (document search, indexing, etc.)
RAG_OPERATIONS = Counter(
    'rag_operations_total',
    'Total RAG engine operations performed',
    ['operation_type', 'status']  # Track operation types and success/failure
)

# Track AI model usage (important for cost monitoring and rate limiting)
AI_MODEL_REQUESTS = Counter(
    'ai_model_requests_total',
    'Total requests made to AI model providers',
    ['provider', 'model', 'status']  # Track which providers/models are used
)

# Global instances - these are shared across all requests
# We use global variables here because these components are expensive to create
# and should be reused across requests for performance
rag_engine = None  # The RAG engine for document search
document_processor = None  # Processes PDF, DOCX, and other files
authentication_manager = None  # Handles JWT authentication
ip_whitelist = None  # Manages IP address restrictions
security = HTTPBearer(auto_error=False)  # HTTP Bearer token security scheme

# Thread safety lock for initialization
# This prevents race conditions when multiple requests try to initialize
# the same components simultaneously during startup
_initialization_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enterprise application lifespan manager - handles startup and shutdown.

    This function manages the complete lifecycle of the Arbitrator AI application:

    📋 **Startup Phase**:
    1. Validates configuration settings
    2. Initializes security components (authentication, rate limiting)
    3. Sets up the RAG engine for document search
    4. Loads the document processor for file handling
    5. Pre-loads any existing documents into the knowledge base

    🔄 **Runtime Phase**:
    - Yields control to FastAPI to handle requests
    - All components are ready and available

    🛑 **Shutdown Phase**:
    - Gracefully closes connections
    - Cleans up resources
    - Ensures no data loss

    This pattern ensures that expensive initialization only happens once,
    and resources are properly managed throughout the application lifecycle.
    """
    global rag_engine, document_processor, authentication_manager, ip_whitelist

    # === STARTUP PHASE ===
    startup_start_time = time.time()  # Track how long startup takes
    correlation_id = str(uuid.uuid4())  # Unique ID to track startup logs
    set_correlation_id(correlation_id)

    # Log startup initiation with key context
    logger.info("🚀 Starting Arbitrator AI enterprise system...", extra={
        "startup_correlation_id": correlation_id,
        "environment": config.environment,  # development, staging, production
        "service_version": config.service_version,  # Version for tracking deployments
        "startup_timestamp": startup_start_time
    })


try:
    # Use the initialization lock to prevent race conditions
    # This ensures only one thread can initialize the system at a time
    async with _initialization_lock:
        # Step 1: Validate configuration before proceeding
        # This catches configuration errors early, before we start expensive operations
        logger.info("🔍 Validating system configuration...")
        config_validation = config.validate_config()

        if not config_validation["valid"]:
            logger.error("❌ Configuration validation failed", extra={
                "issues": config_validation["issues"],
                "warnings": config_validation["warnings"]
            })

            # In production, we're strict about configuration
            if config.environment == "production":
                raise ValueError("Invalid configuration for production environment")

        logger.info("✅ Configuration validation passed")

        # Step 2: Initialize security components
        # Security is initialized first because it protects all other operations
        logger.info("🔐 Initializing security components...")

        # Set up JWT authentication if a secret key is configured
        if config.api_config.jwt_secret_key:
            authentication_manager = AuthenticationManager(
                secret_key=config.api_config.jwt_secret_key,
                expire_minutes=config.api_config.jwt_expire_minutes
            )
            logger.info("✅ JWT authentication manager initialized")
        else:
            logger.warning("⚠️ No JWT secret key configured - JWT authentication disabled")

        # Set up IP whitelist for network-level access control
        allowed_ips = config.api_config.cors_origins  # Could be extended to separate IP config
        if allowed_ips:
            ip_whitelist = IPWhitelist(allowed_ips)
            logger.info(f"✅ IP whitelist initialized with {len(allowed_ips)} allowed addresses")
        else:
            logger.info("ℹ️ No IP whitelist configured - all IPs allowed")

            # Step 3: Initialize RAG engine with retry logic
            # The RAG engine is critical for document search, so we retry if it fails
            logger.info("🧠 Initializing RAG engine (the knowledge brain)...")
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    # Create RAG engine with configuration from settings
                    rag_engine = RAGEngine(
                        collection_name=config.rag_config.collection_name,  # Name of document collection
                        embedding_model=config.rag_config.embedding_model,  # AI model for text-to-vector conversion
                        persist_directory=config.rag_config.persist_directory  # Where to store vector data
                    )

                    # Initialize the engine (loads models, connects to database)
                    await rag_engine.initialize()

                    # Record successful initialization in metrics
                    RAG_OPERATIONS.labels(operation_type="initialization", status="success").inc()
                    logger.info("✅ RAG engine initialized successfully")
                    break  # Success - exit the retry loop

                except Exception as e:
                    # Record failed initialization attempt
                    RAG_OPERATIONS.labels(operation_type="initialization", status="error").inc()

                    # If this was our last attempt, give up
                    if attempt == max_retries - 1:
                        logger.error(f"❌ Failed to initialize RAG engine after {max_retries} attempts: {e}")
                        raise

                    # Log the failure and wait before retrying
                    logger.warning(f"⚠️ RAG engine initialization attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s

                # Step 4: Initialize document processor
                # This component handles PDF, DOCX, and other file formats
                logger.info("📄 Initializing document processor...")
                document_processor = DocumentProcessor(
                    chunk_size=config.rag_config.chunk_size,  # How big each text chunk should be
                    chunk_overlap=config.rag_config.chunk_overlap  # Overlap between chunks for context
                )
                logger.info("✅ Document processor initialized successfully")

                # Step 5: Process initial documents with progress tracking
                # Load any existing documents into the RAG engine's knowledge base
                logger.info("📚 Loading initial documents into knowledge base...")

                if config.contracts_dir.exists():
                    try:
                        # Process all documents in the contracts directory
                        documents = await document_processor.process_directory(str(config.contracts_dir))

                        if documents:
                            # Add processed documents to the RAG engine
                            await rag_engine.add_documents(documents)
                            RAG_OPERATIONS.labels(operation_type="document_loading", status="success").inc()
                            logger.info(f"✅ Loaded {len(documents)} document chunks from contracts directory")
                        else:
                            logger.info("ℹ️ No documents found in contracts directory")

                    except Exception as e:
                        RAG_OPERATIONS.labels(operation_type="document_loading", status="error").inc()
                        logger.error(f"⚠️ Failed to load initial documents: {e}")
                        # Don't fail startup for document loading errors - the system can still work
                        # Users can upload documents later through the API
                else:
                    logger.info("ℹ️ Contracts directory does not exist - skipping initial document loading")

            # Calculate and log successful startup
            startup_duration = time.time() - startup_start_time
            logger.info("🎉 Arbitrator AI enterprise system started successfully!", extra={
                "startup_duration_seconds": round(startup_duration, 2),
                "config_summary": config_validation["config_summary"],
                "components_initialized": {
                    "rag_engine": rag_engine is not None,
                    "document_processor": document_processor is not None,
                    "authentication_manager": authentication_manager is not None,
                    "ip_whitelist": ip_whitelist is not None
                }
            })

except Exception as e:
    # Record startup failure in metrics
    ERROR_COUNT.labels(endpoint="startup", error_type=type(e).__name__).inc()

    # Log detailed error information
    logger.error(f"❌ Failed to start application: {str(e)}", extra={
        "error_type": type(e).__name__,
        "startup_correlation_id": correlation_id,
        "startup_duration_seconds": time.time() - startup_start_time
    })

    # Re-raise the exception to prevent the application from starting in a broken state
    raise

    # === RUNTIME PHASE ===
    # Yield control to FastAPI - the application is now ready to handle requests
    # All components are initialized and ready
yield

# === SHUTDOWN PHASE ===
logger.info("🛑 Shutting down Arbitrator AI enterprise system...", extra={
    "shutdown_correlation_id": correlation_id
})

# Cleanup resources gracefully
try:
    if rag_engine:
        # The RAG engine has its own cleanup method
        await rag_engine.cleanup()
        logger.info("✅ RAG engine cleanup completed")

    # Other components can be cleaned up here as needed
    logger.info("✅ System shutdown completed successfully")

except Exception as e:
    # Log shutdown errors but don't raise them (we're already shutting down)
    logger.error(f"⚠️ Error during shutdown: {e}")

# Create the main FastAPI application instance
# This is the core web application that handles all HTTP requests
app = FastAPI(
    title="Arbitrator AI Enterprise",
    description="Enterprise-grade multi-agent system for commercial dispute resolution with RAG capabilities",
    version=config.service_version,

    # Security consideration: Hide API docs in production
    # Docs are helpful for development but can expose internal structure in production
    docs_url="/docs" if config.environment != "production" else None,
    redoc_url="/redoc" if config.environment != "production" else None,
    openapi_url="/openapi.json" if config.environment != "production" else None,

    # Use our custom lifespan manager for startup/shutdown
    lifespan=lifespan,

    # Global dependencies that apply to all routes can be added here
    dependencies=[],  # Currently empty, but could include global auth, logging, etc.

    # Define standard HTTP response codes and their meanings
    # This helps with API documentation and client error handling
    responses={
        422: {"description": "Validation Error - Invalid input data"},
        429: {"description": "Rate Limit Exceeded - Too many requests"},
        500: {"description": "Internal Server Error - Something went wrong"},
        503: {"description": "Service Unavailable - System is starting up or overloaded"}
    }
)

# === SECURITY MIDDLEWARE STACK ===
# Middleware runs for every request, providing security and monitoring

# CORS (Cross-Origin Resource Sharing) - allows web browsers to access the API
if config.api_config.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api_config.cors_origins,  # Which domains can access the API
        allow_credentials=True,  # Allow cookies and auth headers
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Allowed HTTP methods
        allow_headers=[  # Headers the client can send
            "Authorization",  # For API keys and JWT tokens
            "Content-Type",  # For JSON, form data, etc.
            "X-Requested-With",  # Standard AJAX header
            "X-Request-ID",  # For request tracking
            "X-Correlation-ID",  # For distributed tracing
            "Accept",  # What response format the client wants
            "Origin"  # Where the request came from
        ],
        expose_headers=["X-Request-ID", "X-Correlation-ID", "X-Rate-Limit-Remaining"]  # Headers the client can read
    )

# Trusted Host Middleware - prevents Host header attacks in production
# This validates that requests are coming to the expected domain names
if config.environment == "production":
    allowed_hosts = ["localhost", "127.0.0.1"] + config.api_config.cors_origins
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts  # Only allow requests to these hostnames
    )


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Comprehensive security middleware that runs for every HTTP request.

    This middleware provides multiple layers of security and monitoring:
    1. Request tracking with unique IDs
    2. IP address validation and whitelisting
    3. Rate limiting to prevent abuse
    4. Request size validation
    5. Security headers on responses
    6. Performance metrics collection
    7. Error handling and logging

    Think of this as a "security checkpoint" that every request must pass through.
    """
    start_time = time.time()  # Start timing the request for performance metrics

    # Generate or extract request tracking IDs
    # These IDs help us trace requests through logs and across services
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

    # Set these IDs in thread-local storage so all logging includes them
    set_request_id(request_id)
    set_correlation_id(correlation_id)

    # Extract the real client IP address
    # This is tricky because requests might come through proxies or load balancers
    client_ip = request.client.host if request.client else "unknown"

    # If behind a proxy/load balancer, use the X-Forwarded-For header
    if "X-Forwarded-For" in request.headers:
        # X-Forwarded-For can contain multiple IPs, we want the first (original client)
        client_ip = request.headers["X-Forwarded-For"].split(",")[0].strip()

    # Security Check 1: IP Whitelist Validation
    # If IP whitelisting is enabled, block requests from unauthorized IPs
    if ip_whitelist and not ip_whitelist.is_allowed(client_ip):
        # Log the security violation for monitoring and investigation
        audit_logger.log_security_violation(
            "ip_not_whitelisted",
            {"ip_address": client_ip, "endpoint": str(request.url)},
            client_ip
        )

        # Return a 403 Forbidden response
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Access denied"}  # Generic message to avoid info disclosure
        )

    # Security Check 2: Rate Limiting
    # Prevent abuse by limiting how many requests each IP can make per minute
    if config.api_config.rate_limit_enabled:
        # Create a unique identifier for this client and endpoint
        identifier = f"{client_ip}:{request.url.path}"

        # Check if this client has exceeded their rate limit
        if not await rate_limiter.is_allowed(identifier):
            # Get when the rate limit will reset
            reset_time = await rate_limiter.get_reset_time(identifier)

            # Log the rate limit violation
            audit_logger.log_rate_limit_exceeded(identifier, client_ip, str(request.url.path))

            # Return a 429 Too Many Requests response
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(reset_time),  # Tell client when to retry
                    "X-Rate-Limit-Remaining": "0"  # No requests remaining
                }
            )

    # Security Check 3: Request Size Validation
    # Prevent denial-of-service attacks by limiting request size
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            # Convert bytes to megabytes for easier comparison
            size_mb = int(content_length) / (1024 * 1024)

            # Check if request exceeds maximum allowed size
            if size_mb > config.api_config.max_request_size_mb:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": f"Request too large. Max size: {config.api_config.max_request_size_mb}MB"}
                )
        except ValueError:
            # If content-length is not a valid number, ignore it
            # The request will be processed normally
            pass

    try:
        # All security checks passed - process the request
        response = await call_next(request)

        # Add security headers to the response
        # These headers help protect against various web attacks
        if config.api_config.security_headers_enabled:
            SecurityHeaders.add_security_headers(
                response,
                config.api_config.csp_enabled,  # Content Security Policy
                config.api_config.hsts_max_age  # HTTP Strict Transport Security
            )

        # Add request tracking headers so clients can reference specific requests
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        # Record performance metrics for monitoring
        duration = time.time() - start_time

        # Count this request by method, endpoint, and status code
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()

        # Record how long this request took to process
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response

    except Exception as e:
        # Something went wrong during request processing

        # Record error metrics for monitoring and alerting
        ERROR_COUNT.labels(
            endpoint=request.url.path,
            error_type=type(e).__name__
        ).inc()

        # Log detailed error information for debugging
        logger.error(f"Request processing error: {e}", extra={
            "request_id": request_id,
            "correlation_id": correlation_id,
            "client_ip": client_ip,
            "endpoint": str(request.url),
            "method": request.method,
            "error_type": type(e).__name__,
            "processing_time_seconds": time.time() - start_time
        })

        # Return a generic error response
        # Don't expose internal error details to clients for security
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
            headers={
                "X-Request-ID": request_id,  # Client can reference this for support
                "X-Correlation-ID": correlation_id  # For distributed tracing
            }
        )


# Enhanced authentication dependencies
async def verify_api_key(request: Request, credentials: HTTPAuthorizationCredentials = Security(security)):
    """Enhanced API key verification with security logging."""
    client_ip = request.client.host if request.client else "unknown"

    if config.api_config.api_key:
        if not credentials:
            audit_logger.log_authentication_attempt(
                "api_key", client_ip, False, request.headers.get("User-Agent")
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Use constant-time comparison to prevent timing attacks
        import secrets
        if not secrets.compare_digest(credentials.credentials, config.api_config.api_key):
            audit_logger.log_authentication_attempt(
                "api_key", client_ip, False, request.headers.get("User-Agent")
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"}
            )

        audit_logger.log_authentication_attempt(
            "api_key", client_ip, True, request.headers.get("User-Agent")
        )

    return True


async def verify_jwt_token(request: Request, credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token if authentication manager is configured."""
    if not authentication_manager:
        return None

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = authentication_manager.verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return payload


# Enhanced dependency providers with health checks
async def get_rag_engine() -> RAGEngine:
    """Get RAG engine instance with health check."""
    if rag_engine is None:
        logger.error("RAG engine not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG engine not initialized"
        )

    # Optional: Add health check for RAG engine
    try:
        stats = await rag_engine.get_collection_stats()
        if not stats:
            logger.warning("RAG engine health check failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG engine unhealthy"
            )
    except Exception as e:
        logger.error(f"RAG engine health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG engine health check failed"
        )

    return rag_engine


async def get_document_processor() -> DocumentProcessor:
    """Get document processor instance with validation."""
    if document_processor is None:
        logger.error("Document processor not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document processor not initialized"
        )
    return document_processor


def get_authentication_manager() -> Optional[AuthenticationManager]:
    """Get authentication manager instance."""
    return authentication_manager


# Include routers with enhanced security
app.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)

app.include_router(
    agents.router,
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["analysis"],
    dependencies=[Depends(verify_api_key)]
)


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root(request: Request):
    """Root endpoint with enhanced information."""
    return {
        "message": "Arbitrator AI Enterprise - Multi-agent dispute resolution system",
        "version": config.service_version,
        "environment": config.environment,
        "service_name": config.service_name,
        "docs": "/docs" if config.environment != "production" else None,
        "health": "/health",
        "metrics": "/metrics",
        "timestamp": time.time(),
        "request_id": request.headers.get("X-Request-ID"),
        "features": {
            "rag_enabled": rag_engine is not None,
            "document_processing": document_processor is not None,
            "authentication": authentication_manager is not None,
            "rate_limiting": config.api_config.rate_limit_enabled,
            "security_headers": config.api_config.security_headers_enabled
        }
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with enhanced logging."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}", extra={
        "status_code": exc.status_code,
        "detail": exc.detail,
        "endpoint": str(request.url),
        "method": request.method,
        "client_ip": request.client.host if request.client else "unknown"
    })

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "X-Request-ID": request.headers.get("X-Request-ID", "unknown"),
            "X-Correlation-ID": request.headers.get("X-Correlation-ID", "unknown")
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler with security considerations."""
    error_id = str(uuid.uuid4())

    logger.error(f"Unhandled exception: {exc}", extra={
        "error_id": error_id,
        "error_type": type(exc).__name__,
        "endpoint": str(request.url),
        "method": request.method,
        "client_ip": request.client.host if request.client else "unknown"
    }, exc_info=True)

    # Don't expose internal error details in production
    if config.environment == "production":
        detail = "Internal server error"
    else:
        detail = f"Internal server error: {str(exc)}"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": detail,
            "error_id": error_id
        },
        headers={
            "X-Request-ID": request.headers.get("X-Request-ID", "unknown"),
            "X-Correlation-ID": request.headers.get("X-Correlation-ID", "unknown")
        }
    )


if __name__ == "__main__":
    import uvicorn

    # Configure uvicorn with enterprise settings
    uvicorn_config = {
        "app": "app.api.main:app",
        "host": config.api_config.host,
        "port": config.api_config.port,
        "reload": config.api_config.debug and config.environment == "development",
        "log_config": None,  # Use our custom logging
        "access_log": True,
        "server_header": False,  # Don't expose server info
        "date_header": False,  # Don't expose date header
    }

    # Production-specific settings
    if config.environment == "production":
        uvicorn_config.update({
            "workers": int(os.getenv("WORKERS", "4")),
            "reload": False,
            "log_level": "warning",
            "proxy_headers": True,
            "forwarded_allow_ips": "*"
        })

    logger.info(f"Starting Arbitrator AI server on {config.api_config.host}:{config.api_config.port}")
    uvicorn.run(**uvicorn_config)
