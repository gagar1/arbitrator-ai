"""Enterprise-grade logging configuration with OpenTelemetry integration."""

import os
import sys
import json
import logging
import logging.config
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import traceback
import uuid
from contextvars import ContextVar

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')


class CorrelationFilter(logging.Filter):
    """Add correlation IDs to log records."""
    
    def filter(self, record):
        record.request_id = request_id_var.get('')
        record.user_id = user_id_var.get('')
        record.correlation_id = correlation_id_var.get('')
        record.trace_id = ''
        record.span_id = ''
        
        # Add OpenTelemetry trace information if available
        if OTEL_AVAILABLE and trace:
            span = trace.get_current_span()
            if span:
                span_context = span.get_span_context()
                record.trace_id = format(span_context.trace_id, '032x')
                record.span_id = format(span_context.span_id, '016x')
        
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.hostname = os.uname().nodename
        self.service_name = os.getenv('OTEL_SERVICE_NAME', 'arbitrator-ai')
        self.service_version = os.getenv('OTEL_SERVICE_VERSION', '1.0.0')
        self.environment = os.getenv('OTEL_ENVIRONMENT', 'development')
    
    def format(self, record):
        log_entry = {
            '@timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'service': {
                'name': self.service_name,
                'version': self.service_version,
                'environment': self.environment
            },
            'host': {
                'hostname': self.hostname
            },
            'process': {
                'pid': os.getpid(),
                'thread': record.thread,
                'thread_name': record.threadName
            },
            'source': {
                'file': record.pathname,
                'line': record.lineno,
                'function': record.funcName,
                'module': record.module
            }
        }
        
        # Add correlation IDs if available
        if hasattr(record, 'request_id') and record.request_id:
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'user_id') and record.user_id:
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'correlation_id') and record.correlation_id:
            log_entry['correlation_id'] = record.correlation_id
        
        # Add OpenTelemetry trace information
        if hasattr(record, 'trace_id') and record.trace_id:
            log_entry['trace'] = {
                'trace_id': record.trace_id,
                'span_id': record.span_id
            }
        
        # Add exception information
        if record.exc_info:
            log_entry['error'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'stack_trace': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'exc_info', 'exc_text',
                'stack_info', 'request_id', 'user_id', 'correlation_id',
                'trace_id', 'span_id'
            }:
                log_entry['extra'] = log_entry.get('extra', {})
                log_entry['extra'][key] = value
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class SecurityFilter(logging.Filter):
    """Filter sensitive information from logs."""
    
    SENSITIVE_PATTERNS = [
        'password', 'token', 'key', 'secret', 'credential',
        'authorization', 'auth', 'api_key', 'access_token',
        'refresh_token', 'jwt', 'bearer', 'session'
    ]
    
    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            message = record.msg.lower()
            for pattern in self.SENSITIVE_PATTERNS:
                if pattern in message:
                    # Redact sensitive information
                    record.msg = record.msg.replace(
                        record.msg[message.find(pattern):message.find(pattern) + 50],
                        f'{pattern}=***REDACTED***'
                    )
        return True


class PerformanceFilter(logging.Filter):
    """Add performance metrics to log records."""
    
    def filter(self, record):
        # Add memory usage if available
        try:
            import psutil
            process = psutil.Process()
            record.memory_mb = round(process.memory_info().rss / 1024 / 1024, 2)
            record.cpu_percent = process.cpu_percent()
        except ImportError:
            pass
        
        return True


class LoggingConfig:
    """Enterprise logging configuration manager."""
    
    def __init__(self):
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.log_format = os.getenv('LOG_FORMAT', 'json').lower()
        self.log_file_path = os.getenv('LOG_FILE_PATH', './logs/arbitrator-ai.log')
        self.log_max_size_mb = int(os.getenv('LOG_MAX_SIZE_MB', '100'))
        self.log_backup_count = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        # Create logs directory
        log_dir = Path(self.log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration dictionary."""
        
        formatters = {
            'json': {
                '()': JSONFormatter,
            },
            'detailed': {
                'format': (
                    '%(asctime)s - %(name)s - %(levelname)s - '
                    '[%(request_id)s] [%(correlation_id)s] - '
                    '%(pathname)s:%(lineno)d - %(funcName)s - %(message)s'
                ),
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(asctime)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        }
        
        handlers = {
            'console': {
                'class': 'logging.StreamHandler',
                'level': self.log_level,
                'formatter': self.log_format if self.log_format in formatters else 'json',
                'stream': 'ext://sys.stdout',
                'filters': ['correlation', 'security', 'performance']
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': self.log_level,
                'formatter': self.log_format if self.log_format in formatters else 'json',
                'filename': self.log_file_path,
                'maxBytes': self.log_max_size_mb * 1024 * 1024,
                'backupCount': self.log_backup_count,
                'encoding': 'utf-8',
                'filters': ['correlation', 'security', 'performance']
            }
        }
        
        # Add error file handler for production
        if self.environment == 'production':
            error_log_path = self.log_file_path.replace('.log', '-error.log')
            handlers['error_file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'json',
                'filename': error_log_path,
                'maxBytes': self.log_max_size_mb * 1024 * 1024,
                'backupCount': self.log_backup_count,
                'encoding': 'utf-8',
                'filters': ['correlation', 'security', 'performance']
            }
        
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': formatters,
            'filters': {
                'correlation': {
                    '()': CorrelationFilter,
                },
                'security': {
                    '()': SecurityFilter,
                },
                'performance': {
                    '()': PerformanceFilter,
                }
            },
            'handlers': handlers,
            'loggers': {
                'arbitrator_ai': {
                    'level': self.log_level,
                    'handlers': ['console', 'file'],
                    'propagate': False
                },
                'uvicorn': {
                    'level': 'INFO',
                    'handlers': ['console', 'file'],
                    'propagate': False
                },
                'uvicorn.access': {
                    'level': 'INFO',
                    'handlers': ['console', 'file'],
                    'propagate': False
                },
                'fastapi': {
                    'level': 'INFO',
                    'handlers': ['console', 'file'],
                    'propagate': False
                }
            },
            'root': {
                'level': self.log_level,
                'handlers': ['console', 'file']
            }
        }
        
        # Add error file handler to loggers in production
        if self.environment == 'production':
            for logger_config in config['loggers'].values():
                logger_config['handlers'].append('error_file')
            config['root']['handlers'].append('error_file')
        
        return config
    
    def setup_logging(self):
        """Setup logging configuration."""
        config = self.get_logging_config()
        logging.config.dictConfig(config)
        
        # Setup OpenTelemetry if available
        if OTEL_AVAILABLE and os.getenv('OTEL_ENABLED', 'false').lower() == 'true':
            self.setup_opentelemetry()
    
    def setup_opentelemetry(self):
        """Setup OpenTelemetry tracing and instrumentation."""
        if not OTEL_AVAILABLE:
            logging.warning("OpenTelemetry not available. Install with: pip install opentelemetry-api opentelemetry-sdk")
            return
        
        # Create resource
        resource = Resource.create({
            "service.name": os.getenv('OTEL_SERVICE_NAME', 'arbitrator-ai'),
            "service.version": os.getenv('OTEL_SERVICE_VERSION', '1.0.0'),
            "deployment.environment": os.getenv('OTEL_ENVIRONMENT', 'development')
        })
        
        # Setup tracer provider
        trace.set_tracer_provider(TracerProvider(resource=resource))
        
        # Setup Jaeger exporter
        jaeger_endpoint = os.getenv('JAEGER_ENDPOINT')
        if jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name=os.getenv('JAEGER_AGENT_HOST', 'localhost'),
                agent_port=int(os.getenv('JAEGER_AGENT_PORT', '6831')),
                collector_endpoint=jaeger_endpoint
            )
            
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
        
        # Auto-instrument libraries
        FastAPIInstrumentor.instrument()
        RequestsInstrumentor.instrument()
        LoggingInstrumentor.instrument(set_logging_format=True)
        
        logging.info("OpenTelemetry instrumentation configured")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(f'arbitrator_ai.{name}')


def set_request_id(request_id: str):
    """Set request ID for current context."""
    request_id_var.set(request_id)


def set_user_id(user_id: str):
    """Set user ID for current context."""
    user_id_var.set(user_id)


def set_correlation_id(correlation_id: str):
    """Set correlation ID for current context."""
    correlation_id_var.set(correlation_id)


def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


# Initialize logging configuration
logging_config = LoggingConfig()