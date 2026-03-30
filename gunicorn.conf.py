# Enterprise Gunicorn Configuration
# Production-ready WSGI server configuration with monitoring and security

import os
import multiprocessing
from pathlib import Path

# =============================================================================
# SERVER SOCKET
# =============================================================================
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = int(os.getenv('GUNICORN_BACKLOG', '2048'))

# =============================================================================
# WORKER PROCESSES
# =============================================================================
# Calculate workers based on CPU cores and environment
cpu_count = multiprocessing.cpu_count()
default_workers = min(cpu_count * 2 + 1, 8)  # Cap at 8 workers
workers = int(os.getenv('GUNICORN_WORKERS', str(default_workers)))

# Worker class for async support
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'uvicorn.workers.UvicornWorker')

# Worker connections (for async workers)
worker_connections = int(os.getenv('GUNICORN_WORKER_CONNECTIONS', '1000'))

# Worker timeout settings
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', '5'))
graceful_timeout = int(os.getenv('GUNICORN_GRACEFUL_TIMEOUT', '30'))

# Worker lifecycle settings
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '100'))
preload_app = os.getenv('GUNICORN_PRELOAD_APP', 'true').lower() == 'true'

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
# Disable Gunicorn's default logging to use our custom logging
disable_redirect_access_to_syslog = True
capture_output = False
enable_stdio_inheritance = True

# Log levels
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

# Log files
log_dir = Path(os.getenv('LOG_FILE_PATH', './logs')).parent
log_dir.mkdir(parents=True, exist_ok=True)

accesslog = str(log_dir / 'gunicorn-access.log')
errorlog = str(log_dir / 'gunicorn-error.log')

# Access log format with detailed information
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" %(L)s %(D)s '
    'request_id="%({X-Request-ID}i)s" '
    'correlation_id="%({X-Correlation-ID}i)s"'
)

# =============================================================================
# SECURITY SETTINGS
# =============================================================================
# Limit request line size to prevent attacks
limit_request_line = int(os.getenv('GUNICORN_LIMIT_REQUEST_LINE', '4096'))
limit_request_fields = int(os.getenv('GUNICORN_LIMIT_REQUEST_FIELDS', '100'))
limit_request_field_size = int(os.getenv('GUNICORN_LIMIT_REQUEST_FIELD_SIZE', '8190'))

# SSL settings (if SSL is enabled)
if os.getenv('SSL_ENABLED', 'false').lower() == 'true':
    keyfile = os.getenv('SSL_KEY_PATH', './certs/key.pem')
    certfile = os.getenv('SSL_CERT_PATH', './certs/cert.pem')
    ssl_version = 2  # TLS 1.2+
    ciphers = 'ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS'

# =============================================================================
# PERFORMANCE TUNING
# =============================================================================
# Thread settings for sync workers
threads = int(os.getenv('GUNICORN_THREADS', '1'))

# Memory management
max_requests_jitter = max_requests // 10  # 10% jitter

# Process naming
proc_name = os.getenv('GUNICORN_PROC_NAME', 'arbitrator-ai')

# =============================================================================
# MONITORING HOOKS
# =============================================================================

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Arbitrator AI server is ready. Listening on: %s", server.address)
    server.log.info("Worker processes: %d", server.cfg.workers)
    server.log.info("Worker class: %s", server.cfg.worker_class)
    server.log.info("Environment: %s", os.getenv('ENVIRONMENT', 'unknown'))

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Arbitrator AI server...")
    server.log.info("Gunicorn version: %s", server.version)
    
    # Log configuration summary
    server.log.info("Configuration summary:")
    server.log.info("  Workers: %d", server.cfg.workers)
    server.log.info("  Worker class: %s", server.cfg.worker_class)
    server.log.info("  Timeout: %ds", server.cfg.timeout)
    server.log.info("  Keepalive: %ds", server.cfg.keepalive)
    server.log.info("  Max requests: %d", server.cfg.max_requests)
    server.log.info("  Preload app: %s", server.cfg.preload_app)

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Arbitrator AI server...")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker %s interrupted", worker.pid)

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.debug("Worker %s about to be forked", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker %s forked successfully", worker.pid)
    
    # Set worker process title
    import setproctitle
    setproctitle.setproctitle(f"arbitrator-ai: worker [{worker.age}]")

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Worker %s initialized", worker.pid)

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.error("Worker %s aborted", worker.pid)

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    worker.log.debug("%s %s", req.method, req.path)

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    # Log slow requests
    if hasattr(req, 'start_time'):
        duration = time.time() - req.start_time
        if duration > 5.0:  # Log requests taking more than 5 seconds
            worker.log.warning(
                "Slow request: %s %s - %d - %.3fs",
                req.method, req.path, resp.status_code, duration
            )

def child_exit(server, worker):
    """Called just after a worker has been exited, in the master process."""
    server.log.info("Worker %s exited", worker.pid)

def worker_exit(server, worker):
    """Called just after a worker has been exited, in the worker process."""
    worker.log.info("Worker %s shutting down", worker.pid)

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    server.log.info("Number of workers changed from %s to %s", old_value, new_value)

def on_exit(server):
    """Called just before exiting."""
    server.log.info("Arbitrator AI server shutting down...")

# =============================================================================
# CUSTOM REQUEST HANDLING
# =============================================================================

def default_proc_name(name):
    """Return the default process name."""
    return f"arbitrator-ai: {name}"

# =============================================================================
# ENVIRONMENT-SPECIFIC OVERRIDES
# =============================================================================

if os.getenv('ENVIRONMENT') == 'development':
    # Development settings
    reload = True
    reload_extra_files = ['app/']
    loglevel = 'debug'
    workers = 1
    timeout = 0  # No timeout in development
    
elif os.getenv('ENVIRONMENT') == 'production':
    # Production settings
    reload = False
    preload_app = True
    worker_tmp_dir = '/dev/shm'  # Use memory for worker tmp files
    
    # Enhanced security in production
    limit_request_line = 2048
    limit_request_fields = 50
    limit_request_field_size = 4096
    
    # Performance optimizations
    if os.path.exists('/dev/shm'):
        worker_tmp_dir = '/dev/shm'
    
    # Enable detailed access logging in production
    access_log_format = (
        '{"timestamp": "%(t)s", '
        '"remote_addr": "%(h)s", '
        '"method": "%(m)s", '
        '"url": "%(U)s", '
        '"query_string": "%(q)s", '
        '"status": %(s)s, '
        '"response_length": %(b)s, '
        '"referer": "%(f)s", '
        '"user_agent": "%(a)s", '
        '"request_time": %(L)s, '
        '"response_time": %(D)s, '
        '"request_id": "%({X-Request-ID}i)s", '
        '"correlation_id": "%({X-Correlation-ID}i)s"}'
    )

# =============================================================================
# HEALTH CHECK CONFIGURATION
# =============================================================================

# Custom application check
def check_config(config):
    """Check configuration validity."""
    # Validate worker count
    if config.workers <= 0:
        raise ValueError("Worker count must be positive")
    
    # Validate timeout settings
    if config.timeout <= 0:
        raise ValueError("Timeout must be positive")
    
    # Check log directory permissions
    log_dir = Path(config.errorlog).parent
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise ValueError(f"Cannot create log directory: {log_dir}")
    
    return True

# =============================================================================
# RUNTIME IMPORTS
# =============================================================================

import time
import setproctitle

# =============================================================================
# CONFIGURATION SUMMARY
# =============================================================================

print(f"""\n=== Gunicorn Configuration Summary ===
Bind: {bind}
Workers: {workers}
Worker Class: {worker_class}
Timeout: {timeout}s
Max Requests: {max_requests}
Preload App: {preload_app}
Log Level: {loglevel}
Environment: {os.getenv('ENVIRONMENT', 'unknown')}
======================================\n""")