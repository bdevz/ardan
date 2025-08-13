"""
Enhanced logging middleware for production monitoring.
"""
import json
import time
import uuid
from typing import Callable, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from shared.config import config


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if config.monitoring.log_format == "json" else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced logging middleware for API requests and responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Start timing
        start_time = time.time()
        
        # Log request
        await self._log_request(request, correlation_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            await self._log_response(request, response, correlation_id, process_time)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as exc:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log error
            await self._log_error(request, exc, correlation_id, process_time)
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "correlation_id": correlation_id,
                    "timestamp": time.time()
                },
                headers={"X-Correlation-ID": correlation_id}
            )
    
    async def _log_request(self, request: Request, correlation_id: str):
        """Log incoming request details."""
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Get request body for POST/PUT requests
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Try to parse as JSON, fallback to string
                    try:
                        body = json.loads(body.decode())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        body = body.decode()[:1000]  # Limit body size in logs
            except Exception:
                body = "<unable to read body>"
        
        logger.info(
            "Request received",
            correlation_id=correlation_id,
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=dict(request.query_params),
            headers=dict(request.headers),
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
            body=body,
            timestamp=time.time()
        )
    
    async def _log_response(self, request: Request, response: Response, 
                          correlation_id: str, process_time: float):
        """Log response details."""
        logger.info(
            "Request completed",
            correlation_id=correlation_id,
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            status_code=response.status_code,
            process_time=process_time,
            response_headers=dict(response.headers),
            timestamp=time.time()
        )
    
    async def _log_error(self, request: Request, exc: Exception, 
                        correlation_id: str, process_time: float):
        """Log error details."""
        logger.error(
            "Request failed",
            correlation_id=correlation_id,
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            error_type=type(exc).__name__,
            error_message=str(exc),
            process_time=process_time,
            timestamp=time.time(),
            exc_info=True
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting application metrics."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = {}
        self.request_duration = {}
        self.error_count = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Track request
        path = request.url.path
        method = request.method
        key = f"{method}:{path}"
        
        self.request_count[key] = self.request_count.get(key, 0) + 1
        
        try:
            response = await call_next(request)
            
            # Track duration
            duration = time.time() - start_time
            if key not in self.request_duration:
                self.request_duration[key] = []
            self.request_duration[key].append(duration)
            
            # Track errors
            if response.status_code >= 400:
                error_key = f"{key}:{response.status_code}"
                self.error_count[error_key] = self.error_count.get(error_key, 0) + 1
            
            return response
            
        except Exception as exc:
            # Track errors
            error_key = f"{key}:500"
            self.error_count[error_key] = self.error_count.get(error_key, 0) + 1
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return {
            "request_count": self.request_count,
            "request_duration": {
                k: {
                    "count": len(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0
                }
                for k, v in self.request_duration.items()
            },
            "error_count": self.error_count
        }


# Global metrics instance
metrics_middleware = None


def get_metrics_middleware() -> MetricsMiddleware:
    """Get global metrics middleware instance."""
    global metrics_middleware
    if metrics_middleware is None:
        metrics_middleware = MetricsMiddleware(None)
    return metrics_middleware