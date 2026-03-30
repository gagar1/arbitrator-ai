"""Enterprise-grade security utilities and middleware."""

import os
import time
import hashlib
import secrets
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from functools import wraps
import logging
from collections import defaultdict, deque
import re

from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from cryptography.fernet import Fernet
import ipaddress

logger = logging.getLogger('arbitrator_ai.security')


class RateLimiter:
    """Thread-safe rate limiter with sliding window."""
    
    def __init__(self, max_requests: int = 100, window_minutes: int = 1, burst_size: int = 20):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.burst_size = burst_size
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._burst_count: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for given identifier."""
        async with self._lock:
            now = time.time()
            requests = self._requests[identifier]
            
            # Remove old requests outside the window
            while requests and requests[0] <= now - self.window_seconds:
                requests.popleft()
            
            # Check burst limit
            if self._burst_count[identifier] >= self.burst_size:
                # Reset burst count if enough time has passed
                if not requests or now - requests[-1] > 60:  # 1 minute burst window
                    self._burst_count[identifier] = 0
                else:
                    return False
            
            # Check rate limit
            if len(requests) >= self.max_requests:
                return False
            
            # Allow request
            requests.append(now)
            self._burst_count[identifier] += 1
            return True
    
    async def get_reset_time(self, identifier: str) -> int:
        """Get time until rate limit resets."""
        async with self._lock:
            requests = self._requests[identifier]
            if not requests:
                return 0
            
            oldest_request = requests[0]
            reset_time = oldest_request + self.window_seconds
            return max(0, int(reset_time - time.time()))


class SecurityValidator:
    """Input validation and sanitization utilities."""
    
    # Dangerous patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"('|(\-\-)|(;)|(\||\|)|(\*|\*))",
        r"(union|select|insert|delete|update|drop|create|alter|exec|execute)",
        r"(script|javascript|vbscript|onload|onerror|onclick)"
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>"
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e%5c"
    ]
    
    @classmethod
    def validate_input(cls, data: str, max_length: int = 1000) -> bool:
        """Validate input data for security threats."""
        if not data or len(data) > max_length:
            return False
        
        data_lower = data.lower()
        
        # Check for SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, data_lower, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                return False
        
        # Check for XSS
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, data_lower, re.IGNORECASE):
                logger.warning(f"Potential XSS detected: {pattern}")
                return False
        
        # Check for path traversal
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, data_lower, re.IGNORECASE):
                logger.warning(f"Potential path traversal detected: {pattern}")
                return False
        
        return True
    
    @classmethod
    def sanitize_input(cls, data: str) -> str:
        """Sanitize input data by removing dangerous characters."""
        if not data:
            return ""
        
        # Remove null bytes
        data = data.replace('\x00', '')
        
        # Remove control characters except whitespace
        data = ''.join(char for char in data if ord(char) >= 32 or char in '\t\n\r')
        
        # Escape HTML entities
        data = data.replace('&', '&')
        data = data.replace('<', '<')
        data = data.replace('>', '>')
        data = data.replace('"', '"')
        data = data.replace("'", ''')
        
        return data
    
    @classmethod
    def validate_file_path(cls, file_path: str, allowed_dirs: List[str]) -> bool:
        """Validate file path is within allowed directories."""
        try:
            # Normalize the path
            normalized_path = os.path.normpath(os.path.abspath(file_path))
            
            # Check if path is within allowed directories
            for allowed_dir in allowed_dirs:
                allowed_abs = os.path.normpath(os.path.abspath(allowed_dir))
                if normalized_path.startswith(allowed_abs):
                    return True
            
            return False
        except Exception:
            return False


class AuthenticationManager:
    """JWT-based authentication manager."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 30):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._revoked_tokens: set = set()
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.expire_minutes)
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16)  # JWT ID for revocation
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti in self._revoked_tokens:
                logger.warning(f"Revoked token used: {jti}")
                return None
            
            return payload
        except JWTError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def revoke_token(self, token: str):
        """Revoke a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            jti = payload.get("jti")
            if jti:
                self._revoked_tokens.add(jti)
                logger.info(f"Token revoked: {jti}")
        except JWTError:
            pass
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)


class IPWhitelist:
    """IP address whitelist manager."""
    
    def __init__(self, allowed_ips: List[str] = None):
        self.allowed_networks = []
        if allowed_ips:
            for ip in allowed_ips:
                try:
                    self.allowed_networks.append(ipaddress.ip_network(ip, strict=False))
                except ValueError as e:
                    logger.error(f"Invalid IP address/network: {ip} - {e}")
    
    def is_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed."""
        if not self.allowed_networks:
            return True  # No restrictions if no whitelist configured
        
        try:
            ip = ipaddress.ip_address(ip_address)
            return any(ip in network for network in self.allowed_networks)
        except ValueError:
            logger.warning(f"Invalid IP address: {ip_address}")
            return False


class SecurityHeaders:
    """Security headers middleware."""
    
    @staticmethod
    def add_security_headers(response: Response, csp_enabled: bool = True, hsts_max_age: int = 31536000):
        """Add security headers to response."""
        # HSTS (HTTP Strict Transport Security)
        response.headers["Strict-Transport-Security"] = f"max-age={hsts_max_age}; includeSubDomains"
        
        # Content Security Policy
        if csp_enabled:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            )
            response.headers["Content-Security-Policy"] = csp
        
        # Other security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Remove server information
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)


class AuditLogger:
    """Security audit logging."""
    
    def __init__(self):
        self.logger = logging.getLogger('arbitrator_ai.security.audit')
    
    def log_authentication_attempt(self, username: str, ip_address: str, success: bool, user_agent: str = None):
        """Log authentication attempt."""
        self.logger.info({
            "event": "authentication_attempt",
            "username": username,
            "ip_address": ip_address,
            "success": success,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_rate_limit_exceeded(self, identifier: str, ip_address: str, endpoint: str):
        """Log rate limit exceeded."""
        self.logger.warning({
            "event": "rate_limit_exceeded",
            "identifier": identifier,
            "ip_address": ip_address,
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_security_violation(self, violation_type: str, details: Dict[str, Any], ip_address: str = None):
        """Log security violation."""
        self.logger.error({
            "event": "security_violation",
            "violation_type": violation_type,
            "details": details,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_data_access(self, user_id: str, resource: str, action: str, ip_address: str = None):
        """Log data access for compliance."""
        self.logger.info({
            "event": "data_access",
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        })


def require_api_key(api_key: str):
    """Decorator for API key authentication."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                raise HTTPException(status_code=500, detail="Request object not found")
            
            # Check API key
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
            
            token = auth_header.split(" ")[1]
            if not secrets.compare_digest(token, api_key):
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit(rate_limiter: RateLimiter, identifier_func: Callable[[Request], str] = None):
    """Decorator for rate limiting."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                raise HTTPException(status_code=500, detail="Request object not found")
            
            # Get identifier
            if identifier_func:
                identifier = identifier_func(request)
            else:
                identifier = request.client.host if request.client else "unknown"
            
            # Check rate limit
            if not await rate_limiter.is_allowed(identifier):
                reset_time = await rate_limiter.get_reset_time(identifier)
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(reset_time)}
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Global instances
rate_limiter = RateLimiter()
security_validator = SecurityValidator()
audit_logger = AuditLogger()