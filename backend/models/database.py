"""
Database models for SF Board of Supervisors voting records.

Models:
- Document: Scraped documents (centerpiece for raw data)
- Supervisor: Board members
- Legislation: Bills, ordinances, resolutions
- Meeting: Board meetings
- Action: Votes or proposals by supervisors on legislation
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker
import enum


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class OfficialType(str, enum.Enum):
    """Types of officials"""
    SUPERVISOR = "supervisor"
    MAYOR = "mayor"


class ActionType(str, enum.Enum):
    """Types of actions an official can take"""
    VOTE = "vote"
    SPONSOR = "sponsor"
    CO_SPONSOR = "co_sponsor"
    PROPOSE = "propose"


class VoteType(str, enum.Enum):
    """Types of votes a supervisor can cast"""
    AYE = "aye"
    NO = "no"
    ABSTAIN = "abstain"
    ABSENT = "absent"
    EXCUSED = "excused"


class ContentFormat(str, enum.Enum):
    """Format of document content"""
    PDF = "pdf"
    HTML = "html"
    CSV = "csv"
    TEXT = "text"


class MeetingType(str, enum.Enum):
    """Types of meetings"""
    REGULAR = "regular"
    SPECIAL = "special"
    COMMITTEE = "committee"


class LegislationStatus(str, enum.Enum):
    """Result of voting on legislation"""
    APPROVED = "approved"
    REJECTED = "rejected"
    CONTINUED = "continued"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"


class Document(Base):
    """
    Scraped document - centerpiece for raw data storage.
    Documents are independent of meetings and contain raw scraped content.
    Optionally linked to a meeting if the document is associated with a specific meeting.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    source = Column(String(255), nullable=False, index=True)  # e.g., "sfbos", "permits"
    url = Column(String(1024), nullable=False, unique=True, index=True)
    raw_content = Column(Text, nullable=True)  # File dump - original content
    content_format = Column(Enum(ContentFormat), nullable=False)  # pdf, html, csv, etc.
    converted_content = Column(Text, nullable=True)  # Content as markdown text
    doc_metadata = Column(JSON, nullable=True)  # Additional metadata (e.g., link text, source info)

    # Optional foreign key to link document to a meeting
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True, index=True)

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    meeting = relationship("Meeting", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, source={self.source}, format={self.content_format})>"


class Official(Base):
    """SF elected official (Supervisor or Mayor)"""
    __tablename__ = "officials"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    official_type = Column(Enum(OfficialType), nullable=False, default=OfficialType.SUPERVISOR)
    district = Column(Integer, nullable=True)  # 1-11 for supervisors, None for mayor
    initials = Column(String(10), nullable=True)  # e.g., "CC" for Connie Chan
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    actions = relationship("Action", back_populates="official", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Official(name={self.name}, type={self.official_type}, district={self.district})>"


class Legislation(Base):
    """Bills, ordinances, resolutions, and other legislation"""
    __tablename__ = "legislation"

    id = Column(Integer, primary_key=True)
    file_number = Column(String(255), nullable=True, index=True)  # e.g., "250657"
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    legislation_type = Column(String(100), nullable=True)  # "Ordinance", "Resolution", etc.
    category = Column(String(100), nullable=True)  # "Housing", "Transportation", etc.
    status = Column(Enum(LegislationStatus), nullable=True)
    url = Column(String(1024), nullable=True)  # Link to legislation detail page

    # Additional metadata stored as JSON
    # Contains: dates (introduced, final_action), committee (name, members), etc.
    extra_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    actions = relationship("Action", back_populates="legislation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Legislation(file_number={self.file_number}, title={self.title[:50]})>"


class Meeting(Base):
    """Board of Supervisors meeting"""
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    meeting_file_number = Column(String(255), nullable=True, index=True)  # e.g., "250657"
    meeting_datetime = Column(DateTime, nullable=False, index=True)
    meeting_type = Column(String(255), nullable=False, default=MeetingType.REGULAR)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    actions = relationship("Action", back_populates="meeting", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="meeting", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Meeting(date={self.meeting_date}, type={self.meeting_type})>"


class Action(Base):
    """
    Represents a vote or proposal by an official on legislation.
    Many actions belong to one legislation.
    Many actions belong to one official.
    Many actions belong to one meeting.
    """
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True)

    # Foreign keys
    legislation_id = Column(Integer, ForeignKey("legislation.id"), nullable=False, index=True)
    official_id = Column(Integer, ForeignKey("officials.id"), nullable=False, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True, index=True)

    # Action details
    action_type = Column(Enum(ActionType), nullable=False, default=ActionType.VOTE)
    vote = Column(Enum(VoteType), nullable=True)  # Only for VOTE action_type
    notes = Column(Text, nullable=True)  # Additional context

    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    legislation = relationship("Legislation", back_populates="actions")
    official = relationship("Official", back_populates="actions")
    meeting = relationship("Meeting", back_populates="actions")

    def __repr__(self):
        return f"<Action(official_id={self.official_id}, type={self.action_type}, vote={self.vote})>"


# Database initialization and utilities

def init_db(database_url: str = "postgresql://opengov:opengov@localhost:5432/open_gov_access"):
    """
    Initialize database and create all tables.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        SQLAlchemy engine
    """
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine) -> Session:
    """
    Create a new database session.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        SQLAlchemy session
    """
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def seed_officials(session: Session):
    """
    Seed database with current SF elected officials (as of 2025).

    Args:
        session: SQLAlchemy session
    """
    # Current officials (2025)
    officials_data = [
        # Mayor
        {"name": "Daniel Lurie", "official_type": OfficialType.MAYOR, "district": None, "initials": "DL", "is_active": True},
        # Supervisors
        {"name": "Connie Chan", "official_type": OfficialType.SUPERVISOR, "district": 1, "initials": "CC", "is_active": True},
        {"name": "Catherine Stefani", "official_type": OfficialType.SUPERVISOR, "district": 2, "initials": "CS", "is_active": True},
        {"name": "Aaron Peskin", "official_type": OfficialType.SUPERVISOR, "district": 3, "initials": "AP", "is_active": True},
        {"name": "Joel Engardio", "official_type": OfficialType.SUPERVISOR, "district": 4, "initials": "JE", "is_active": True},
        {"name": "Dean Preston", "official_type": OfficialType.SUPERVISOR, "district": 5, "initials": "DP", "is_active": True},
        {"name": "Matt Dorsey", "official_type": OfficialType.SUPERVISOR, "district": 6, "initials": "MD", "is_active": True},
        {"name": "Myrna Melgar", "official_type": OfficialType.SUPERVISOR, "district": 7, "initials": "MM", "is_active": True},
        {"name": "Rafael Mandelman", "official_type": OfficialType.SUPERVISOR, "district": 8, "initials": "RM", "is_active": True},
        {"name": "Hillary Ronen", "official_type": OfficialType.SUPERVISOR, "district": 9, "initials": "HR", "is_active": True},
        {"name": "Shamann Walton", "official_type": OfficialType.SUPERVISOR, "district": 10, "initials": "SW", "is_active": True},
        {"name": "Ahsha Safai", "official_type": OfficialType.SUPERVISOR, "district": 11, "initials": "AS", "is_active": True},
    ]

    for official_data in officials_data:
        # Check if official already exists
        existing = session.query(Official).filter_by(
            name=official_data["name"]
        ).first()

        if not existing:
            official = Official(**official_data)
            session.add(official)

    session.commit()
    print(f"✓ Seeded {len(officials_data)} officials (1 mayor + 11 supervisors)")


def seed_example_data(session: Session):
    """
    Seed database with example legislation and voting data.
    Based on SF File #250804 - Property Exchange Agreement.

    Args:
        session: SQLAlchemy session
    """
    # Check if example data already exists
    existing = session.query(Legislation).filter_by(file_number="250804").first()
    if existing:
        print("✓ Example data already exists")
        return

    # Create example legislation
    legislation = Legislation(
        file_number="250804",
        title="Amended and Restated Conditional Property Exchange Agreement - EQX Jackson SQ Holdco LLC - 530 Sansome Street and 447 Battery Street",
        description="Ordinance approving an Amended and Restated Conditional Property Exchange Agreement between the City and County of San Francisco and EQX Jackson SQ Holdco LLC for the exchange of 530 Sansome Street and 447 Battery Street and the construction of a new fire station on 447 Battery Street; affirming exempt surplus property finding declaration; waiving the appraisal requirements of Administrative Code, Chapter 23; ratifying past actions and authorizing future actions in furtherance of this Ordinance, as defined herein; adopting findings under the California Environmental Quality Act; and making findings of consistency with the General Plan, and the eight priority policies of Planning Code, Section 101.1.",
        legislation_type="Ordinance",
        category="Real Estate",
        status=LegislationStatus.APPROVED,
        url="https://sfgov.legistar.com/LegislationDetail.aspx?ID=7501529&GUID=557EC678-D34A-49CD-AEA0-5E681ADD5806",
        extra_data={
            "introduced_date": "2025-07-29",
            "final_action_date": "2025-10-27",
            "enactment_date": "2025-10-27",
            "enactment_number": "203-25",
            "version": 1,
            "in_control": "Clerk of the Board",
            "related_files": ["250803"],
            "attachments": [
                "Leg Ver1", "Leg Dig Ver1", "DRAFT Agrmt 092325",
                "PC Reso No 21775 071725", "MYR Cover Ltr 072925",
                "Form 126", "Comm Pkt 092925", "OEWD Presentation 092925",
                "Board Pkt 100725", "Comment Ltrs", "Board Pkt 102125",
                "Leg Final", "Form 126 Final"
            ]
        }
    )
    session.add(legislation)
    session.flush()  # Get the ID

    # Get Mayor as sponsor
    mayor = session.query(Official).filter_by(official_type=OfficialType.MAYOR, is_active=True).first()
    if not mayor:
        print("Warning: No active mayor found for example data")
        return

    # Get Danny Sauter as co-sponsor (create if doesn't exist)
    danny_sauter = session.query(Official).filter_by(name="Danny Sauter").first()
    if not danny_sauter:
        danny_sauter = Official(
            name="Danny Sauter",
            official_type=OfficialType.SUPERVISOR,
            district=None,
            is_active=True
        )
        session.add(danny_sauter)
        session.flush()

    # Add sponsor actions
    sponsor_action = Action(
        legislation_id=legislation.id,
        official_id=mayor.id,
        action_type=ActionType.SPONSOR,
        notes="Primary sponsor"
    )
    session.add(sponsor_action)

    co_sponsor_action = Action(
        legislation_id=legislation.id,
        official_id=danny_sauter.id,
        action_type=ActionType.CO_SPONSOR,
        notes="Co-sponsor"
    )
    session.add(co_sponsor_action)

    # Create meetings for the legislative history
    meeting_dates = [
        ("2025-07-29", MeetingType.REGULAR, "ASSIGNED UNDER 30 DAY RULE"),
        ("2025-09-29", MeetingType.COMMITTEE, "RECOMMENDED"),
        ("2025-10-07", MeetingType.REGULAR, "PASSED, ON FIRST READING"),
        ("2025-10-21", MeetingType.REGULAR, "FINALLY PASSED"),
        ("2025-10-27", MeetingType.REGULAR, "APPROVED"),
    ]

    meetings = []
    for date_str, meeting_type, action_desc in meeting_dates:
        meeting_date = datetime.strptime(date_str, "%Y-%m-%d")
        meeting = session.query(Meeting).filter_by(meeting_date=meeting_date).first()
        if not meeting:
            meeting = Meeting(meeting_date=meeting_date, meeting_type=meeting_type)
            session.add(meeting)
            session.flush()
        meetings.append((meeting, action_desc))

    # Add example votes for the final passage (10/21/2025)
    # Simulate a vote where most supervisors voted yes
    final_meeting = meetings[3][0]  # 10/21/2025 - FINALLY PASSED

    # Get all active supervisors (not mayor)
    supervisors = session.query(Official).filter_by(
        is_active=True,
        official_type=OfficialType.SUPERVISOR
    ).all()

    # Example vote distribution (11 supervisors)
    vote_pattern = [
        VoteType.AYE, VoteType.AYE, VoteType.AYE, VoteType.AYE,
        VoteType.AYE, VoteType.AYE, VoteType.AYE, VoteType.NO,
        VoteType.AYE, VoteType.AYE, VoteType.ABSTAIN
    ]

    for i, supervisor in enumerate(supervisors[:len(vote_pattern)]):
        vote_action = Action(
            legislation_id=legislation.id,
            official_id=supervisor.id,
            meeting_id=final_meeting.id,
            action_type=ActionType.VOTE,
            vote=vote_pattern[i],
            notes=f"Vote on final passage"
        )
        session.add(vote_action)

    session.commit()
    print(f"✓ Seeded example legislation (File #250804) with {len(vote_pattern)} votes")

