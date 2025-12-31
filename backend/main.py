"""
Hoxton Tax Limited - AI Tax Consultancy System
FastAPI Backend Server
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.api import routes, websocket

app = FastAPI(
    title="Hoxton Tax AI API",
    version="1.0.0",
    description="AI-powered tax consultancy system with human-in-the-loop checkpointing"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router, prefix="/api")
app.include_router(websocket.router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "Hoxton Tax AI API"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Hoxton Tax AI API",
        "docs": "/docs",
        "health": "/health"
    }

