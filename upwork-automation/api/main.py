"""
FastAPI main application for Upwork Automation System
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import uvicorn

from shared.config import settings, validate_config
from shared.utils import setup_logging
from database.connection import init_db, close_db
from routers import jobs, proposals, applications, browser, system, metrics, workflows, queue, n8n_webhooks, slack, safety, websocket
from middleware.error_handling import add_error_handlers
from middleware.logging import RequestLoggingMiddleware
from services.websocket_service import websocket_service

# Setup logging
logger = setup_logging("upwork-automation-api", settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Upwork Automation API...")
    
    try:
        # Validate configuration
        validate_config()
        logger.info("Configuration validated successfully")
        
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Initialize WebSocket service
        from routers.websocket import manager
        websocket_service.initialize(manager)
        logger.info("WebSocket service initialized")
        
        # Start health monitoring
        from services.health_monitoring_service import health_monitoring_service
        await health_monitoring_service.start_monitoring()
        logger.info("Health monitoring started")
        
        logger.info("API startup complete")
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    # Shutdown
    logger.info("Shutting down Upwork Automation API...")
    
    # Stop health monitoring
    from services.health_monitoring_service import health_monitoring_service
    await health_monitoring_service.stop_monitoring()
    logger.info("Health monitoring stopped")
    
    await close_db()
    logger.info("API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Upwork Automation API",
    description="Automated job application system for Salesforce Agentforce Developer positions",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware, log_body=settings.debug)

# Add error handlers
add_error_handlers(app)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "ardan-automation-api"}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Upwork Automation API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else None,
        "health": "/health",
        "status": "operational"
    }


# Custom OpenAPI schema
def custom_openapi():
    """Custom OpenAPI schema with additional information"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Upwork Automation API",
        version="1.0.0",
        description="""
        Automated job application system for Salesforce Agentforce Developer positions.
        
        ## Features
        
        * **Job Discovery**: Automated job search and filtering
        * **Proposal Generation**: AI-powered proposal creation
        * **Application Submission**: Automated application submission
        * **Browser Automation**: Intelligent browser control with Stagehand
        * **Performance Metrics**: Comprehensive analytics and reporting
        * **System Management**: Configuration and monitoring
        
        ## Authentication
        
        API endpoints require authentication via Bearer token in the Authorization header.
        In development mode, authentication is optional.
        
        ## Rate Limiting
        
        API requests are rate limited to prevent abuse. Authenticated users have higher limits.
        """,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Include routers
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(proposals.router, prefix="/api/proposals", tags=["proposals"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(browser.router, prefix="/api/browser", tags=["browser"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(queue.router, tags=["queue"])
app.include_router(n8n_webhooks.router, prefix="/api/n8n", tags=["n8n-webhooks"])
app.include_router(slack.router, prefix="/api/slack", tags=["slack"])
app.include_router(safety.router, tags=["safety"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])

# Import and include health router
from routers import health
app.include_router(health.router, tags=["health"])


# API versioning endpoint
@app.get("/api/version")
async def get_api_version():
    """Get API version information"""
    return {
        "version": "1.0.0",
        "build_date": "2024-01-01",
        "environment": "development" if settings.debug else "production",
        "features": {
            "job_discovery": True,
            "proposal_generation": True,
            "application_submission": True,
            "browser_automation": True,
            "metrics": True,
            "authentication": True
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )