"""
FastAPI application for SF Board of Supervisors voting records.

Provides REST API endpoints for querying supervisors, votes, items, and statistics.
"""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from models.database import (
    Document,
    Item,
    ItemResult,
    Meeting,
    Supervisor,
    Vote,
    VoteType,
)

# Initialize FastAPI app
app = FastAPI(
    title="SF Board of Supervisors Voting Records API",
    description="API for querying SF Board of Supervisors voting records and meeting data",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/open_gov_access")
engine = create_engine(DATABASE_URL)


def get_db():
    """Dependency for database session"""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models for API responses

class SupervisorBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    district: Optional[int]
    is_active: bool


class VoteBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    vote: VoteType
    supervisor: SupervisorBase


class ItemBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    file_number: Optional[str]
    title: str
    result: Optional[ItemResult]
    vote_count_aye: int
    vote_count_no: int
    vote_count_abstain: int
    vote_count_absent: int


class ItemDetail(ItemBase):
    model_config = ConfigDict(from_attributes=True)
    
    description: Optional[str]
    meeting_date: datetime
    votes: List[VoteBase]


class SupervisorStats(BaseModel):
    supervisor: SupervisorBase
    total_votes: int
    aye_count: int
    no_count: int
    abstain_count: int
    absent_count: int
    aye_percentage: float


class MeetingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    meeting_date: datetime
    meeting_type: str


class OverviewStats(BaseModel):
    total_meetings: int
    total_items: int
    total_votes: int
    latest_meeting_date: Optional[datetime]
    active_supervisors: int


# API Endpoints

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "SF Board of Supervisors Voting Records API",
        "docs": "/docs",
        "version": "0.1.0"
    }


@app.get("/api/supervisors", response_model=List[SupervisorBase])
def get_supervisors(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get list of supervisors.
    
    Args:
        active_only: Only return active supervisors
    """
    query = db.query(Supervisor)
    
    if active_only:
        query = query.filter(Supervisor.is_active == True)
    
    supervisors = query.order_by(Supervisor.district).all()
    return supervisors


@app.get("/api/supervisors/{supervisor_id}", response_model=SupervisorBase)
def get_supervisor(
    supervisor_id: int,
    db: Session = Depends(get_db)
):
    """Get supervisor details"""
    supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    return supervisor


@app.get("/api/supervisors/{supervisor_id}/votes", response_model=List[ItemBase])
def get_supervisor_votes(
    supervisor_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get voting history for a supervisor.
    
    Args:
        supervisor_id: Supervisor ID
        limit: Maximum number of results
        offset: Offset for pagination
    """
    supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    # Get items this supervisor voted on
    items = (
        db.query(Item)
        .join(Vote)
        .filter(Vote.supervisor_id == supervisor_id)
        .order_by(Item.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    return items


@app.get("/api/supervisors/{supervisor_id}/stats", response_model=SupervisorStats)
def get_supervisor_stats(
    supervisor_id: int,
    db: Session = Depends(get_db)
):
    """
    Get voting statistics for a supervisor.
    
    Args:
        supervisor_id: Supervisor ID
    """
    supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    # Count votes by type
    votes = db.query(Vote).filter(Vote.supervisor_id == supervisor_id).all()
    
    total_votes = len(votes)
    aye_count = sum(1 for v in votes if v.vote == VoteType.AYE)
    no_count = sum(1 for v in votes if v.vote == VoteType.NO)
    abstain_count = sum(1 for v in votes if v.vote == VoteType.ABSTAIN)
    absent_count = sum(1 for v in votes if v.vote == VoteType.ABSENT)
    
    aye_percentage = (aye_count / total_votes * 100) if total_votes > 0 else 0.0
    
    return SupervisorStats(
        supervisor=supervisor,
        total_votes=total_votes,
        aye_count=aye_count,
        no_count=no_count,
        abstain_count=abstain_count,
        absent_count=absent_count,
        aye_percentage=round(aye_percentage, 2)
    )


@app.get("/api/items", response_model=List[ItemBase])
def get_items(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of voting items.
    
    Args:
        limit: Maximum number of results
        offset: Offset for pagination
        search: Search query for title
    """
    query = db.query(Item)
    
    if search:
        query = query.filter(Item.title.ilike(f"%{search}%"))
    
    items = query.order_by(Item.id.desc()).limit(limit).offset(offset).all()
    return items


@app.get("/api/items/{item_id}", response_model=ItemDetail)
def get_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Get item details with all votes.
    
    Args:
        item_id: Item ID
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Get meeting date
    meeting = db.query(Meeting).filter(Meeting.id == item.meeting_id).first()
    
    # Create response with meeting date
    item_dict = {
        "id": item.id,
        "file_number": item.file_number,
        "title": item.title,
        "description": item.description,
        "result": item.result,
        "vote_count_aye": item.vote_count_aye,
        "vote_count_no": item.vote_count_no,
        "vote_count_abstain": item.vote_count_abstain,
        "vote_count_absent": item.vote_count_absent,
        "meeting_date": meeting.meeting_date if meeting else None,
        "votes": item.votes
    }
    
    return item_dict


@app.get("/api/meetings", response_model=List[MeetingBase])
def get_meetings(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get list of meetings.
    
    Args:
        limit: Maximum number of results
    """
    meetings = (
        db.query(Meeting)
        .order_by(Meeting.meeting_date.desc())
        .limit(limit)
        .all()
    )
    return meetings


@app.get("/api/stats/overview", response_model=OverviewStats)
def get_overview_stats(db: Session = Depends(get_db)):
    """Get overview statistics"""
    total_meetings = db.query(func.count(Meeting.id)).scalar()
    total_items = db.query(func.count(Item.id)).scalar()
    total_votes = db.query(func.count(Vote.id)).scalar()
    active_supervisors = db.query(func.count(Supervisor.id)).filter(
        Supervisor.is_active == True
    ).scalar()
    
    latest_meeting = db.query(Meeting).order_by(Meeting.meeting_date.desc()).first()
    latest_meeting_date = latest_meeting.meeting_date if latest_meeting else None
    
    return OverviewStats(
        total_meetings=total_meetings or 0,
        total_items=total_items or 0,
        total_votes=total_votes or 0,
        latest_meeting_date=latest_meeting_date,
        active_supervisors=active_supervisors or 0
    )

