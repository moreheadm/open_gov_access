"""
Admin routes for SF Board of Supervisors API.

Provides endpoints for administrative operations like database initialization and scraping.
All endpoints are under /api/admin and require authentication.

Authentication Strategy (Not Implemented):
- Simple API Key: Store a secret key in environment variable (ADMIN_API_KEY)
  - Client sends: Authorization: Bearer <api_key>
  - Verify in dependency: check if key matches ADMIN_API_KEY
  
- Alternative: JWT Token
  - Issue short-lived JWT tokens on login
  - Verify token signature and expiration on each request
  
- Alternative: OAuth2 with Password Flow
  - Use FastAPI's built-in OAuth2PasswordBearer
  - Verify username/password against admin credentials
  
Recommended: Start with simple API Key for MVP, upgrade to JWT for production.
"""

import os
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import init_db, get_session, seed_officials, seed_example_data, Document
from scrapers.legistar import LegistarScraper
from etl.pipeline import ETLPipeline
from config import settings


# Create router for admin endpoints
router = APIRouter(prefix="/api/admin", tags=["admin"])


# Pydantic models for admin responses

class InitResponse(BaseModel):
    """Response from database initialization"""
    status: str
    message: str
    timestamp: datetime
    with_examples: bool


class ScrapeResponse(BaseModel):
    """Response from scrape operation"""
    status: str
    message: str
    documents_scraped: int
    timestamp: datetime
    convert_with_ai: bool
    incremental: bool


class ScrapeStatusResponse(BaseModel):
    """Status of current scrape operation"""
    status: str  # "running", "completed", "failed"
    documents_processed: int
    documents_total: Optional[int]
    current_url: Optional[str]
    error: Optional[str]


# Authentication dependency (placeholder - not implemented)
async def verify_admin_key(authorization: Optional[str] = None) -> bool:
    """
    Verify admin API key.
    
    TODO: Implement one of the authentication strategies:
    1. Simple API Key: Compare with ADMIN_API_KEY env var
    2. JWT Token: Verify signature and expiration
    3. OAuth2: Use FastAPI's OAuth2PasswordBearer
    
    For now, this is a placeholder that always returns True.
    """
    # Placeholder implementation
    # In production, implement actual authentication:
    # 
    # if not authorization:
    #     raise HTTPException(status_code=401, detail="Missing authorization header")
    # 
    # scheme, credentials = authorization.split()
    # if scheme.lower() != "bearer":
    #     raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    # 
    # api_key = os.getenv("ADMIN_API_KEY")
    # if not api_key or credentials != api_key:
    #     raise HTTPException(status_code=403, detail="Invalid API key")
    # 
    # return True
    
    return True


@router.post("/init", response_model=InitResponse)
async def admin_init(
    with_examples: bool = False,
    database: Optional[str] = None,
    _: bool = Depends(verify_admin_key)
):
    """
    Initialize database and seed officials.
    
    Args:
        with_examples: Whether to seed example data
        database: Database URL (uses DATABASE_URL env var if not provided)
    
    Returns:
        InitResponse with status and message
    """
    try:
        db_url = database or settings.database_url
        print(f"[ADMIN] Initializing database: {db_url}")
        
        engine = init_db(db_url)
        print("[ADMIN] ✓ Database created")
        
        session = get_session(engine)
        seed_officials(session)
        print("[ADMIN] ✓ Officials seeded")
        
        if with_examples:
            seed_example_data(session)
            print("[ADMIN] ✓ Example data seeded")
        
        session.close()
        
        return InitResponse(
            status="success",
            message="Database initialized successfully",
            timestamp=datetime.now(),
            with_examples=with_examples
        )
    except Exception as e:
        print(f"[ADMIN] ✗ Error initializing database: {e}")
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")


@router.post("/scrape", response_model=ScrapeResponse)
async def admin_scrape(
    limit: Optional[int] = Query(None, description="Limit number of documents"),
    full: bool = Query(False, description="Full scrape (not incremental)"),
    convert_with_ai: bool = Query(False, description="Convert documents with AI"),
    show_browser: bool = Query(False, description="Show browser (not headless)"),
    database: Optional[str] = None,
    _: bool = Depends(verify_admin_key)
):
    """
    Scrape documents from Legistar and save to database.

    Args:
        limit: Maximum number of documents to scrape
        full: Disable incremental mode (scrape all)
        convert_with_ai: Convert documents with AI
        show_browser: Show browser window (not headless)
        database: Database URL (uses DATABASE_URL env var if not provided)

    Returns:
        ScrapeResponse with status and count
    """
    try:
        db_url = database or settings.database_url
        print(f"[ADMIN] Starting scrape: limit={limit}, full={full}, ai={convert_with_ai}")

        engine = init_db(db_url)
        session = get_session(engine)

        scraper = LegistarScraper(
            headless=not show_browser,
            convert_with_ai=convert_with_ai,
            limit=limit,
            incremental=not full
        )

        count = 0
        for obj in scraper.scrape(session=session):
            try:
                session.add(obj)
                session.commit()
                count += 1
                obj_type = type(obj).__name__
                obj_id = getattr(obj, 'url', getattr(obj, 'file_number', getattr(obj, 'name', 'unknown')))
                print(f"[ADMIN] ✓ Saved {obj_type} {count}: {obj_id}")
            except Exception as e:
                print(f"[ADMIN] ✗ Error saving object: {e}")
                session.rollback()

        session.close()

        return ScrapeResponse(
            status="success",
            message=f"Scraped and saved {count} objects",
            documents_scraped=count,
            timestamp=datetime.now(),
            convert_with_ai=convert_with_ai,
            incremental=not full
        )
    except Exception as e:
        print(f"[ADMIN] ✗ Error during scrape: {e}")
        raise HTTPException(status_code=500, detail=f"Scrape failed: {str(e)}")


@router.get("/status", response_model=dict)
async def admin_status(_: bool = Depends(verify_admin_key)):
    """
    Get admin status and system information.
    
    Returns:
        Status information including database connection and configuration
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(),
        "database_url": settings.database_url.split("@")[1] if "@" in settings.database_url else "unknown",
        "version": "0.1.0"
    }

