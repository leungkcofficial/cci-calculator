"""
CCI Calculator Main Application

This module provides the FastAPI application and endpoints for the CCI Calculator.
"""

import logging
import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from datetime import datetime

from app.api import api_router
from app.config import settings

# Get logger
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add rate limiting middleware
if settings.RATE_LIMIT_ENABLED:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_REQUESTS} requests per {settings.RATE_LIMIT_PERIOD} seconds")


# Add request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add a unique request ID to each request."""
    request_id = f"{int(time.time())}-{os.urandom(4).hex()}"
    request.state.request_id = request_id
    
    # Add request ID to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing information."""
    start_time = time.time()
    
    # Get client IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = forwarded_for.split(",")[0] if forwarded_for else request.client.host
    
    # Log request
    logger.info(f"Request started: {request.method} {request.url.path} from {client_ip}")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log response
        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"status={response.status_code} duration={process_time:.2f}ms"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        
        return response
    except Exception as e:
        # Log exception
        process_time = (time.time() - start_time) * 1000
        logger.error(
            f"Request failed: {request.method} {request.url.path} "
            f"error={str(e)} duration={process_time:.2f}ms"
        )
        
        # Re-raise exception
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_type": "server_error",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# Include API router
app.include_router(api_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint that serves the frontend application."""
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Perform startup tasks."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Create required directories
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.TEMP_DIR, "results"), exist_ok=True)
    
    # Log configuration
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info(f"Max upload size: {settings.MAX_UPLOAD_SIZE / (1024 * 1024):.1f} MB")
    logger.info(f"Batch size: {settings.BATCH_SIZE}")
    logger.info(f"Max workers: {settings.MAX_WORKERS}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Perform shutdown tasks."""
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )