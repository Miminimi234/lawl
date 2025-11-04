"""
AI Judge Companion - Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api import cases, documents, analysis, research, feed
from app.db.database import engine, create_tables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting AI Judge Companion...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Legal Domain: {settings.LEGAL_DOMAIN}")
    logger.info(f"Jurisdiction: {settings.JURISDICTION}")
    
    # Create database tables
    create_tables()
    logger.info("Database tables created")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Judge Companion...")


app = FastAPI(
    title="AI Judge Companion",
    description="Legal case analysis and judgment recommendation system",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(feed.router, prefix="/api/feed", tags=["feed"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Judge Companion API",
        "version": "0.1.0",
        "jurisdiction": settings.JURISDICTION,
        "legal_domain": settings.LEGAL_DOMAIN,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )







