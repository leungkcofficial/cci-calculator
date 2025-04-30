"""
CCI Calculator API

This package contains API endpoints for the CCI Calculator application.

Modules:
- endpoints: API endpoint implementations
"""

from fastapi import APIRouter

api_router = APIRouter()

from app.api.endpoints import router as endpoints_router
api_router.include_router(endpoints_router)