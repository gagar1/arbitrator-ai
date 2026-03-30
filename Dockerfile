# Multi-stage build for Arbitrator AI
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    API_HOST=0.0.0.0 \
    API_PORT=8000

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r arbitrator \
    && useradd -r -g arbitrator arbitrator

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY data/ ./data/
COPY .env* ./

# Create necessary directories
RUN mkdir -p /app/data/chroma_db \
    && mkdir -p /app/data/contracts \
    && mkdir -p /app/data/legal_docs \
    && mkdir -p /app/data/temp \
    && mkdir -p /app/logs \
    && chown -R arbitrator:arbitrator /app

# Switch to non-root user
USER arbitrator

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "app.api.main"]

# Development stage
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy \
    pre-commit

# Copy test files
COPY tests/ ./tests/
COPY pytest.ini .
COPY .pre-commit-config.yaml .

# Set ownership
RUN chown -R arbitrator:arbitrator /app

# Switch back to non-root user
USER arbitrator

# Development command
CMD ["python", "-m", "app.api.main", "--reload"]

# Testing stage
FROM development as testing

# Run tests
RUN python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# Lint and format check
RUN black --check app/ tests/ && \
    isort --check-only app/ tests/ && \
    flake8 app/ tests/ && \
    mypy app/

CMD ["pytest"]