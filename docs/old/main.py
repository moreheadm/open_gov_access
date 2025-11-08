"""
FastAPI backend for supervisor voting API
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import date
from pydantic import BaseModel

import sys
sys.path.append('..')
from models.database import (
    init_db, get_session,
    Meeting, Document, Item, Vote, Supervisor, VoteType
)


# Initialize FastAPI app
app = FastAPI(
    title="SF Supervisor Votes API",
    description="Track how San Francisco Board of Supervisors members vote",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency
engine = init_db()

def get_db():
    session = get_session(engine)
    try:
        yield session
    finally:
        session.close()


# Pydantic models for API responses
class SupervisorBase(BaseModel):
    id: int
    name: str
    district: int
    is_active: bool
    
    class Config:
        from_attributes = True


class VoteResponse(BaseModel):
    supervisor: SupervisorBase
    vote: str
    
    class Config:
        from_attributes = True


class ItemSummary(BaseModel):
    id: int
    file_number: str
    title: str
    result: Optional[str]
    meeting_date: date
    vote_count_aye: int
    vote_count_no: int
    
    class Config:
        from_attributes = True


class ItemDetail(BaseModel):
    id: int
    file_number: str
    title: str
    description: Optional[str]
    result: Optional[str]
    meeting_date: date
    vote_count_aye: int
    vote_count_no: int
    vote_count_abstain: int
    vote_count_absent: int
    votes: List[VoteResponse]
    
    class Config:
        from_attributes = True


class SupervisorVotingRecord(BaseModel):
    supervisor: SupervisorBase
    total_votes: int
    aye_count: int
    no_count: int
    abstain_count: int
    absent_count: int
    aye_percentage: float


# API Routes

@app.get("/")
def root():
    """API information"""
    return {
        "name": "SF Supervisor Votes API",
        "version": "1.0.0",
        "endpoints": {
            "supervisors": "/api/supervisors",
            "items": "/api/items",
            "votes": "/api/votes",
            "stats": "/api/stats"
        }
    }


@app.get("/api/supervisors", response_model=List[SupervisorBase])
def get_supervisors(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get list of supervisors"""
    query = db.query(Supervisor)
    
    if active_only:
        query = query.filter(Supervisor.is_active == True)
    
    supervisors = query.order_by(Supervisor.district).all()
    return supervisors


@app.get("/api/supervisors/{supervisor_id}", response_model=SupervisorBase)
def get_supervisor(supervisor_id: int, db: Session = Depends(get_db)):
    """Get supervisor details"""
    supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    return supervisor


@app.get("/api/supervisors/{supervisor_id}/votes", response_model=List[ItemSummary])
def get_supervisor_votes(
    supervisor_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get voting history for a supervisor"""
    # Join votes, items, and meetings
    query = db.query(Item).join(Vote).join(Meeting).filter(
        Vote.supervisor_id == supervisor_id
    ).order_by(desc(Meeting.meeting_date))
    
    items = query.offset(offset).limit(limit).all()
    
    # Format response
    result = []
    for item in items:
        result.append(ItemSummary(
            id=item.id,
            file_number=item.file_number,
            title=item.title,
            result=item.result,
            meeting_date=item.meeting.meeting_date,
            vote_count_aye=item.vote_count_aye or 0,
            vote_count_no=item.vote_count_no or 0
        ))
    
    return result


@app.get("/api/supervisors/{supervisor_id}/stats", response_model=SupervisorVotingRecord)
def get_supervisor_stats(supervisor_id: int, db: Session = Depends(get_db)):
    """Get voting statistics for a supervisor"""
    supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    # Count votes by type
    votes = db.query(Vote.vote, func.count(Vote.id)).filter(
        Vote.supervisor_id == supervisor_id
    ).group_by(Vote.vote).all()
    
    vote_counts = {
        'aye': 0,
        'no': 0,
        'abstain': 0,
        'absent': 0,
        'excused': 0
    }
    
    for vote_type, count in votes:
        vote_counts[vote_type.value] = count
    
    total = sum(vote_counts.values())
    aye_pct = (vote_counts['aye'] / total * 100) if total > 0 else 0
    
    return SupervisorVotingRecord(
        supervisor=SupervisorBase.from_orm(supervisor),
        total_votes=total,
        aye_count=vote_counts['aye'],
        no_count=vote_counts['no'],
        abstain_count=vote_counts['abstain'],
        absent_count=vote_counts['absent'],
        aye_percentage=round(aye_pct, 2)
    )


@app.get("/api/items", response_model=List[ItemSummary])
def get_items(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    file_number: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of voting items"""
    query = db.query(Item).join(Meeting)
    
    if file_number:
        query = query.filter(Item.file_number == file_number)
    
    if search:
        query = query.filter(Item.title.contains(search))
    
    query = query.order_by(desc(Meeting.meeting_date))
    items = query.offset(offset).limit(limit).all()
    
    result = []
    for item in items:
        result.append(ItemSummary(
            id=item.id,
            file_number=item.file_number,
            title=item.title,
            result=item.result,
            meeting_date=item.meeting.meeting_date,
            vote_count_aye=item.vote_count_aye or 0,
            vote_count_no=item.vote_count_no or 0
        ))
    
    return result


@app.get("/api/items/{item_id}", response_model=ItemDetail)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a voting item"""
    item = db.query(Item).options(
        joinedload(Item.votes).joinedload(Vote.supervisor),
        joinedload(Item.meeting)
    ).filter(Item.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Format votes
    votes_list = []
    for vote in item.votes:
        votes_list.append(VoteResponse(
            supervisor=SupervisorBase.from_orm(vote.supervisor),
            vote=vote.vote.value
        ))
    
    return ItemDetail(
        id=item.id,
        file_number=item.file_number,
        title=item.title,
        description=item.description,
        result=item.result,
        meeting_date=item.meeting.meeting_date,
        vote_count_aye=item.vote_count_aye or 0,
        vote_count_no=item.vote_count_no or 0,
        vote_count_abstain=item.vote_count_abstain or 0,
        vote_count_absent=item.vote_count_absent or 0,
        votes=votes_list
    )


@app.get("/api/meetings")
def get_meetings(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get list of meetings"""
    meetings = db.query(Meeting).order_by(
        desc(Meeting.meeting_date)
    ).limit(limit).all()
    
    return [
        {
            "id": m.id,
            "meeting_date": m.meeting_date,
            "meeting_type": m.meeting_type,
            "item_count": len(m.items)
        }
        for m in meetings
    ]


@app.get("/api/stats/overview")
def get_overview_stats(db: Session = Depends(get_db)):
    """Get overall statistics"""
    total_meetings = db.query(func.count(Meeting.id)).scalar()
    total_items = db.query(func.count(Item.id)).scalar()
    total_votes = db.query(func.count(Vote.id)).scalar()
    
    # Most recent meeting
    latest_meeting = db.query(Meeting).order_by(
        desc(Meeting.meeting_date)
    ).first()
    
    return {
        "total_meetings": total_meetings,
        "total_items": total_items,
        "total_votes": total_votes,
        "latest_meeting_date": latest_meeting.meeting_date if latest_meeting else None,
        "active_supervisors": db.query(func.count(Supervisor.id)).filter(
            Supervisor.is_active == True
        ).scalar()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
