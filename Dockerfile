# Multi-stage Dockerfile for Arbitrator AI
# Educational AI agent system with clean, documented stages

# =============================================================================
# STAGE 1: DEPENDENCY BUILDER
# Purpose: Install Python dependencies in isolated environment
# =============================================================================
FROM python:3.11-slim as builder

# Set environment variables for Python optimization
ENV PYTHONDONTWRITEBYTECODE=1 \    # Prevent Python from writing .pyc files
    PYTHONUNBUFFERED=1 \           # Ensure stdout/stderr are not buffered
    PIP_NO_CACHE_DIR=1 \           # Disable pip cache to reduce image size
    PIP_DISABLE_PIP_VERSION_CHECK=1 # Disable pip version check for faster builds

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \              # Compiler tools for building packages
    curl \                         # For health checks and downloads
    && rm -rf /var/lib/apt/lists/* # Clean up package lists to reduce image size

# Set working directory
WORKDIR /app

# Copy requirements file first (Docker layer caching optimization)
COPY requirements.txt .

# Install Python dependencies
# Using --user flag to install in user directory for better security
RUN pip install --user --no-cache-dir -r requirements.txt

# =============================================================================
# STAGE 2: PRODUCTION RUNTIME
# Purpose: Minimal runtime environment with only necessary components
# =============================================================================
FROM python:3.11-slim as production

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \              # Add app directory to Python path
    API_HOST=0.0.0.0 \             # Listen on all interfaces
    API_PORT=8000                  # Default API port

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \                         # For health checks
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r arbitrator \    # Create non-root group
    && useradd -r -g arbitrator arbitrator  # Create non-root user

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
# This copies only the installed packages, not the build tools
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code with proper ownership
COPY --chown=arbitrator:arbitrator app/ ./app/
COPY --chown=arbitrator:arbitrator data/ ./data/
COPY --chown=arbitrator:arbitrator .env* ./

# Create necessary directories with proper permissions
RUN mkdir -p /app/data/chroma_db \     # Vector database storage
    /app/data/contracts \              # Contract documents
    /app/data/temp \                   # Temporary file processing
    /app/logs \                        # Application logs
    && chown -R arbitrator:arbitrator /app  # Set ownership to non-root user

# Switch to non-root user for security
USER arbitrator

# Health check to ensure application is running
# Checks the health endpoint every 30 seconds
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose the application port
EXPOSE 8000

# Run the application
# Uses Python module execution for better path handling
CMD ["python", "-m", "app.api.main"]

# =============================================================================
# STAGE 3: DEVELOPMENT ENVIRONMENT
# Purpose: Development environment with additional tools and hot reload
# =============================================================================
FROM production as development

# Switch back to root for installing development tools
USER root

# Install development system packages
RUN apt-get update && apt-get install -y \
    vim \                          # Text editor for debugging
    htop \                         # Process monitoring
    git \                          # Version control
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    pytest \                       # Testing framework
    pytest-asyncio \               # Async testing support
    pytest-cov \                   # Coverage reporting
    black \                        # Code formatting
    isort \                        # Import sorting
    flake8 \                       # Code linting
    mypy \                         # Type checking
    pre-commit                     # Git hooks for code quality

# Copy test files and configuration
COPY --chown=arbitrator:arbitrator tests/ ./tests/
COPY --chown=arbitrator:arbitrator pytest.ini .
COPY --chown=arbitrator:arbitrator .pre-commit-config.yaml .

# Switch back to non-root user
USER arbitrator

# Development command with hot reload
CMD ["python", "-m", "app.api.main", "--reload"]

# =============================================================================
# BUILD INSTRUCTIONS
# =============================================================================
# 
# Production build:
#   docker build --target production -t arbitrator-ai:latest .
# 
# Development build:
#   docker build --target development -t arbitrator-ai:dev .
# 
# Run production container:
#   docker run -p 8000:8000 --env-file .env arbitrator-ai:latest
# 
# Run development container with volume mounting:
#   docker run -p 8000:8000 -v $(pwd):/app --env-file .env arbitrator-ai:dev
# 
# =============================================================================