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


class ActionType(str, enum.Enum):
    """Types of actions a supervisor can take"""
    VOTE = "vote"
    SPONSOR = "sponsor"
    CO_SPONSOR = "co_sponsor"
    PROPOSE = "propose"


class VoteType(str, enum.Enum):
    """Types of votes a supervisor can cast"""
    YES = "yes"
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
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    source = Column(String(255), nullable=False, index=True)  # e.g., "sfbos", "permits"
    url = Column(String(1024), nullable=False, unique=True, index=True)
    raw_content = Column(Text, nullable=True)  # File dump - original content
    content_format = Column(Enum(ContentFormat), nullable=False)  # pdf, html, csv, etc.
    converted_content = Column(Text, nullable=True)  # Content as markdown text
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Document(id={self.id}, source={self.source}, format={self.content_format})>"


class Supervisor(Base):
    """SF Board of Supervisors member"""
    __tablename__ = "supervisors"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    district = Column(Integer, nullable=True)  # 1-11, or None for at-large
    is_active = Column(Boolean, nullable=False, default=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    actions = relationship("Action", back_populates="supervisor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Supervisor(name={self.name}, district={self.district})>"


class Legislation(Base):
    """Bills, ordinances, resolutions, and other legislation"""
    __tablename__ = "legislation"

    id = Column(Integer, primary_key=True)
    file_number = Column(String(255), nullable=True, index=True)  # e.g., "250210"
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    legislation_type = Column(String(100), nullable=True)  # "Ordinance", "Resolution", etc.
    status = Column(Enum(LegislationStatus), nullable=True)

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
    meeting_date = Column(DateTime, nullable=False, unique=True, index=True)
    meeting_type = Column(Enum(MeetingType), nullable=False, default=MeetingType.REGULAR)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    actions = relationship("Action", back_populates="meeting", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Meeting(date={self.meeting_date}, type={self.meeting_type})>"


class Action(Base):
    """
    Represents a vote or proposal by a supervisor on legislation.
    Many actions belong to one legislation.
    Many actions belong to one supervisor.
    Many actions belong to one meeting.
    """
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True)

    # Foreign keys
    legislation_id = Column(Integer, ForeignKey("legislation.id"), nullable=False, index=True)
    supervisor_id = Column(Integer, ForeignKey("supervisors.id"), nullable=False, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True, index=True)

    # Action details
    action_type = Column(Enum(ActionType), nullable=False, default=ActionType.VOTE)
    vote = Column(Enum(VoteType), nullable=True)  # Only for VOTE action_type
    notes = Column(Text, nullable=True)  # Additional context

    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    legislation = relationship("Legislation", back_populates="actions")
    supervisor = relationship("Supervisor", back_populates="actions")
    meeting = relationship("Meeting", back_populates="actions")

    def __repr__(self):
        return f"<Action(supervisor_id={self.supervisor_id}, type={self.action_type}, vote={self.vote})>"


# Database initialization and utilities

def init_db(database_url: str = "postgresql://localhost/open_gov_access"):
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


def seed_supervisors(session: Session):
    """
    Seed database with current SF Board of Supervisors members (as of 2025).
    
    Args:
        session: SQLAlchemy session
    """
    # Current supervisors (2025)
    supervisors_data = [
        {"name": "Connie Chan", "district": 1, "is_active": True},
        {"name": "Catherine Stefani", "district": 2, "is_active": True},
        {"name": "Aaron Peskin", "district": 3, "is_active": True},
        {"name": "Joel Engardio", "district": 4, "is_active": True},
        {"name": "Dean Preston", "district": 5, "is_active": True},
        {"name": "Matt Dorsey", "district": 6, "is_active": True},
        {"name": "Myrna Melgar", "district": 7, "is_active": True},
        {"name": "Rafael Mandelman", "district": 8, "is_active": True},
        {"name": "Hillary Ronen", "district": 9, "is_active": True},
        {"name": "Shamann Walton", "district": 10, "is_active": True},
        {"name": "Ahsha Safai", "district": 11, "is_active": True},
    ]
    
    for sup_data in supervisors_data:
        # Check if supervisor already exists
        existing = session.query(Supervisor).filter_by(
            name=sup_data["name"],
            district=sup_data["district"]
        ).first()
        
        if not existing:
            supervisor = Supervisor(**sup_data)
            session.add(supervisor)
    
    session.commit()
    print(f"✓ Seeded {len(supervisors_data)} supervisors")

