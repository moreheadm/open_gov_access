"""
FastAPI application for SF Board of Supervisors voting records.

Provides REST API endpoints for querying supervisors, votes, items, and statistics.
"""

import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from calendar import monthrange
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from models.database import (
    Action,
    ActionType,
    ContentFormat,
    Document,
    Legislation,
    LegislationStatus,
    Meeting,
    Official,
    OfficialType,
    VoteType,
)
from utils.transcript_parser import NonAITranscriptParser
from .admin import router as admin_router

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

# Include admin router
app.include_router(admin_router)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://opengov:opengov@localhost:5432/open_gov_access")
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

class SupervisorResponse(BaseModel):
    """Supervisor information for API responses"""
    model_config = ConfigDict(from_attributes=True)

    name: str
    district: Optional[int]
    initials: Optional[str]


class SponsorResponse(BaseModel):
    """Sponsor information including type (supervisor/mayor)"""
    name: str
    is_mayor: bool  # True if official_type is MAYOR


class CommitteeResponse(BaseModel):
    """Committee information"""
    name: Optional[str]
    members: Optional[List[str]]


class DatesResponse(BaseModel):
    """Legislation dates"""
    introduced: Optional[str]
    final_action: Optional[str]


class LegislationResponse(BaseModel):
    """Legislation detail response matching desired format"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    legislation_number: Optional[str]  # file_number
    title: str
    description: Optional[str]
    type: Optional[str]  # legislation_type
    category: Optional[str]
    status: Optional[str]
    dates: Optional[DatesResponse]
    sponsors: Optional[List[SponsorResponse]]
    committee: Optional[CommitteeResponse]
    legislation_url: Optional[str]  # url
    votes: Optional[dict]  # Dict[supervisor_name, vote_type]


class LegislationListResponse(BaseModel):
    """Response for legislation list endpoint"""
    legislation: List[LegislationResponse]
    supervisors: List[SupervisorResponse]


class SupervisorStats(BaseModel):
    supervisor: SupervisorResponse
    total_votes: int
    aye_count: int
    no_count: int
    abstain_count: int
    absent_count: int
    aye_percentage: float


class MeetingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_datetime: datetime
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


@app.get("/api/supervisors", response_model=List[SupervisorResponse])
def get_supervisors(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get list of supervisors (officials with type=SUPERVISOR).

    Args:
        active_only: Only return active supervisors
    """
    query = db.query(Official).filter(Official.official_type == OfficialType.SUPERVISOR)

    if active_only:
        query = query.filter(Official.is_active == True)

    supervisors = query.order_by(Official.district).all()
    return supervisors


@app.get("/api/supervisors/{supervisor_id}", response_model=SupervisorResponse)
def get_supervisor(
    supervisor_id: int,
    db: Session = Depends(get_db)
):
    """Get supervisor details"""
    supervisor = db.query(Official).filter(
        Official.id == supervisor_id,
        Official.official_type == OfficialType.SUPERVISOR
    ).first()

    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    return supervisor


@app.get("/api/supervisors/{supervisor_id}/actions")
def get_supervisor_actions(
    supervisor_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get action history for a supervisor.

    Args:
        supervisor_id: Supervisor ID
        limit: Maximum number of results
        offset: Offset for pagination
    """
    supervisor = db.query(Official).filter(
        Official.id == supervisor_id,
        Official.official_type == OfficialType.SUPERVISOR
    ).first()

    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    # Get legislation this supervisor acted on
    legislation = (
        db.query(Legislation)
        .join(Action)
        .filter(Action.official_id == supervisor_id)
        .order_by(Legislation.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return legislation


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
    supervisor = db.query(Official).filter(
        Official.id == supervisor_id,
        Official.official_type == OfficialType.SUPERVISOR
    ).first()

    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    # Count actions by type
    actions = db.query(Action).filter(Action.official_id == supervisor_id).all()

    total_votes = len([a for a in actions if a.action_type == ActionType.VOTE])
    aye_count = sum(1 for a in actions if a.vote == VoteType.AYE)
    no_count = sum(1 for a in actions if a.vote == VoteType.NO)
    abstain_count = sum(1 for a in actions if a.vote == VoteType.ABSTAIN)
    absent_count = sum(1 for a in actions if a.vote == VoteType.ABSENT)

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


@app.get("/api/legislation", response_model=LegislationListResponse)
def get_legislation(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of legislation with votes aggregated on demand.

    Args:
        limit: Maximum number of results
        offset: Offset for pagination
        search: Search query for title
    """
    query = db.query(Legislation)

    if search:
        query = query.filter(Legislation.title.ilike(f"%{search}%"))

    legislation_list = query.order_by(Legislation.id.desc()).limit(limit).offset(offset).all()

    # Get all supervisors
    supervisors = db.query(Official).filter(
        Official.is_active == True,
        Official.official_type == OfficialType.SUPERVISOR
    ).order_by(Official.district).all()

    # Build response
    legislation_responses = []
    for leg in legislation_list:
        # Get all vote actions for this legislation
        vote_actions = (
            db.query(Action, Official)
            .join(Official, Action.official_id == Official.id)
            .filter(Action.legislation_id == leg.id)
            .filter(Action.action_type == ActionType.VOTE)
            .all()
        )

        # Build votes dict
        votes_dict = {action.Official.name: action.Action.vote.value if action.Action.vote else None
                      for action in vote_actions}

        # Get sponsor actions
        sponsor_actions = (
            db.query(Action, Official)
            .join(Official, Action.official_id == Official.id)
            .filter(Action.legislation_id == leg.id)
            .filter(Action.action_type.in_([ActionType.SPONSOR, ActionType.CO_SPONSOR]))
            .all()
        )

        sponsors = [
            SponsorResponse(
                name=action.Official.name,
                is_mayor=(action.Official.official_type == OfficialType.MAYOR)
            )
            for action in sponsor_actions
        ]

        # Parse metadata for dates and committee
        dates = None
        committee = None
        if leg.metadata:
            if 'dates' in leg.metadata:
                dates = DatesResponse(**leg.metadata['dates'])
            if 'committee' in leg.metadata:
                committee = CommitteeResponse(**leg.metadata['committee'])

        legislation_responses.append(
            LegislationResponse(
                id=leg.id,
                legislation_number=leg.file_number,
                title=leg.title,
                description=leg.description,
                type=leg.legislation_type,
                category=leg.category,
                status=leg.status.value if leg.status else None,
                dates=dates,
                sponsors=sponsors if sponsors else None,
                committee=committee,
                legislation_url=leg.url,
                votes=votes_dict if votes_dict else None
            )
        )

    supervisor_responses = [
        SupervisorResponse(name=s.name, district=s.district, initials=s.initials)
        for s in supervisors
    ]

    return LegislationListResponse(
        legislation=legislation_responses,
        supervisors=supervisor_responses
    )


@app.get("/api/legislation/{legislation_id}", response_model=LegislationResponse)
def get_legislation_detail(
    legislation_id: int,
    db: Session = Depends(get_db)
):
    """
    Get legislation details with all votes aggregated on demand.

    Args:
        legislation_id: Legislation ID
    """
    leg = db.query(Legislation).filter(Legislation.id == legislation_id).first()

    if not leg:
        raise HTTPException(status_code=404, detail="Legislation not found")

    # Get all vote actions for this legislation
    vote_actions = (
        db.query(Action, Official)
        .join(Official, Action.official_id == Official.id)
        .filter(Action.legislation_id == leg.id)
        .filter(Action.action_type == ActionType.VOTE)
        .all()
    )

    # Build votes dict
    votes_dict = {action.Official.name: action.Action.vote.value if action.Action.vote else None
                  for action in vote_actions}

    # Get sponsor actions
    sponsor_actions = (
        db.query(Action, Official)
        .join(Official, Action.official_id == Official.id)
        .filter(Action.legislation_id == leg.id)
        .filter(Action.action_type.in_([ActionType.SPONSOR, ActionType.CO_SPONSOR]))
        .all()
    )

    sponsors = [
        SponsorResponse(
            name=action.Official.name,
            is_mayor=(action.Official.official_type == OfficialType.MAYOR)
        )
        for action in sponsor_actions
    ]

    # Parse metadata for dates and committee
    dates = None
    committee = None
    if leg.metadata:
        if 'dates' in leg.metadata:
            dates = DatesResponse(**leg.metadata['dates'])
        if 'committee' in leg.metadata:
            committee = CommitteeResponse(**leg.metadata['committee'])

    return LegislationResponse(
        id=leg.id,
        legislation_number=leg.file_number,
        title=leg.title,
        description=leg.description,
        type=leg.legislation_type,
        category=leg.category,
        status=leg.status.value if leg.status else None,
        dates=dates,
        sponsors=sponsors if sponsors else None,
        committee=committee,
        legislation_url=leg.url,
        votes=votes_dict if votes_dict else None
    )


@app.get("/api/meetings", response_model=List[MeetingBase])
def get_meetings(
    limit: int = Query(100, ge=1, le=200),
    month: Optional[str] = Query(None, description="Filter by month in YYYY-MM format, or 'all' for all meetings"),
    db: Session = Depends(get_db)
):
    """
    Get list of meetings, optionally filtered by month.

    Args:
        limit: Maximum number of results
        month: Optional month filter in YYYY-MM format (e.g., '2025-01'), or 'all' for all meetings
    """
    query = db.query(Meeting)

    # Apply month filter if provided and not 'all'
    if month and month != 'all':
        try:
            # Parse the month string (YYYY-MM)
            year, month_num = month.split('-')
            year_int = int(year)
            month_int = int(month_num)

            # Create start and end dates for the month
            start_date = datetime(year_int, month_int, 1)
            last_day = monthrange(year_int, month_int)[1]
            end_date = datetime(year_int, month_int, last_day, 23, 59, 59)

            query = query.filter(
                Meeting.meeting_datetime >= start_date,
                Meeting.meeting_datetime <= end_date
            )
        except (ValueError, AttributeError):
            # Invalid month format, ignore filter
            pass

    meetings = (
        query
        .order_by(Meeting.meeting_datetime.desc())
        .limit(limit)
        .all()
    )
    return meetings

@app.get("/api/stats/overview", response_model=OverviewStats)
def get_overview_stats(db: Session = Depends(get_db)):
    """Get overview statistics"""
    total_meetings = db.query(func.count(Meeting.id)).scalar()
    total_legislation = db.query(func.count(Legislation.id)).scalar()
    total_actions = db.query(func.count(Action.id)).scalar()
    active_supervisors = db.query(func.count(Official.id)).filter(
        Official.is_active == True,
        Official.official_type == OfficialType.SUPERVISOR
    ).scalar()

    latest_meeting = db.query(Meeting).order_by(Meeting.meeting_date.desc()).first()
    latest_meeting_date = latest_meeting.meeting_date if latest_meeting else None

    return OverviewStats(
        total_meetings=total_meetings or 0,
        total_items=total_legislation or 0,
        total_votes=total_actions or 0,
        latest_meeting_date=latest_meeting_date,
        active_supervisors=active_supervisors or 0
    )


# Meeting Summary Models and Endpoint

class MomentSummary(BaseModel):
    """Summary of a single moment/statement by an official"""
    id: str
    headline: str
    summary: str
    timestamps: str


class PersonSummary(BaseModel):
    """Summary of an official's contributions in a meeting"""
    name: str
    role: str  # "supervisor" or "mayor"
    moments: List[MomentSummary]


class MeetingSummaryResponse(BaseModel):
    """Response model for meeting summary endpoint"""
    meeting_id: int
    meeting_datetime: datetime
    people: List[PersonSummary]


@app.get("/api/meetings/{meeting_id}/summary", response_model=MeetingSummaryResponse)
def get_meeting_summary(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """
    Get AI-generated summary of meeting topics from transcript.

    This endpoint:
    1. Fetches the meeting by ID
    2. Finds the associated transcript document
    3. Runs the Auggie CLI command to generate XML summary
    4. Parses the XML and returns structured topic summaries

    Args:
        meeting_id: Meeting ID

    Returns:
        MeetingSummaryResponse with topics and summaries
    """
    # Get meeting
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Find transcript document for this meeting
    # For now, we'll look for the first HTML transcript document from legistar source
    # TODO: In the future, link meetings to documents via a foreign key or metadata field
    transcript_doc = (
        db.query(Document)
        .filter(Document.source == "legistar")
        .filter(Document.content_format == ContentFormat.HTML)
        .filter(Document.url.contains("Transcript"))
        .first()
    )

    if not transcript_doc:
        raise HTTPException(
            status_code=404,
            detail=f"No transcript found for meeting {meeting_id}"
        )

    # Extract transcript text from HTML
    if transcript_doc.converted_content:
        # Use converted markdown content if available
        transcript_text = transcript_doc.converted_content
    elif transcript_doc.raw_content:
        # Parse HTML to extract text
        parser = NonAITranscriptParser()
        segments = parser.extract_segments(transcript_doc.raw_content)
        transcript_text = parser.to_markdown(segments, include_timestamps=True)
    else:
        raise HTTPException(
            status_code=500,
            detail="Transcript document has no content"
        )

    # Write transcript to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as transcript_file:
        transcript_file.write(transcript_text)
        transcript_path = transcript_file.name

    # Create temporary output file path
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as output_file:
        output_path = output_file.name

    # Create officials JSON with current supervisors and mayor
    officials_data = {
        "supervisors": [
            "Beya Alcaraz",
            "Bilal Mahmood",
            "Chyanne Chen",
            "Connie Chan",
            "Danny Sauter",
            "Jackie Fielder",
            "Matt Dorsey",
            "Myrna Melgar",
            "Rafael Mandelman",
            "Shamann Walton",
            "Stephen Sherrill"
        ],
        "mayor": "Daniel Lurie"
    }

    # Write officials JSON to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as officials_file:
        json.dump(officials_data, officials_file)
        officials_path = officials_file.name

    try:
        # Run auggie command with officials list
        # auggie --print command board-mayor-topics-summary-xml <transcript_path> <output_path> <officials_json>
        result = subprocess.run(
            ['auggie', '--print', 'command', 'board-mayor-topics-summary-xml', transcript_path, output_path, officials_path],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Auggie command failed: {result.stderr}"
            )

        # Read and parse XML output
        if not Path(output_path).exists():
            raise HTTPException(
                status_code=500,
                detail="Auggie command did not produce output file"
            )

        with open(output_path, 'r') as f:
            xml_content = f.read()

        # Parse XML
        root = ET.fromstring(xml_content)

        # Extract people and their moments
        people = []
        for person_elem in root.findall('person'):
            person_name = person_elem.get('name', '')
            person_role = person_elem.get('role', '')

            # Extract moments for this person
            moments = []
            for moment_elem in person_elem.findall('moment'):
                moment_id = moment_elem.get('id', '')
                headline_elem = moment_elem.find('headline')
                summary_elem = moment_elem.find('summary')
                timestamps_elem = moment_elem.find('timestamps')

                headline = headline_elem.text if headline_elem is not None else ''

                # Extract CDATA content from summary
                summary = ''
                if summary_elem is not None:
                    summary = ''.join(summary_elem.itertext()).strip()

                timestamps = timestamps_elem.text if timestamps_elem is not None else ''

                moments.append(MomentSummary(
                    id=moment_id,
                    headline=headline,
                    summary=summary,
                    timestamps=timestamps
                ))

            people.append(PersonSummary(
                name=person_name,
                role=person_role,
                moments=moments
            ))

        return MeetingSummaryResponse(
            meeting_id=meeting.id,
            meeting_datetime=meeting.meeting_datetime,
            people=people
        )

    finally:
        # Clean up temporary files
        try:
            Path(transcript_path).unlink()
            Path(output_path).unlink()
            Path(officials_path).unlink()
        except Exception:
            pass  # Ignore cleanup errors

