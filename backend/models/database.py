"""
Database models for SF Board of Supervisors voting records.

Models:
- Meeting: Board meetings
- Document: Meeting documents (agendas, minutes)
- Supervisor: Board members
- Item: Legislation items voted on
- Vote: Individual supervisor votes on items
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


class VoteType(str, enum.Enum):
    """Types of votes a supervisor can cast"""
    AYE = "aye"
    NO = "no"
    ABSTAIN = "abstain"
    ABSENT = "absent"
    EXCUSED = "excused"


class DocumentType(str, enum.Enum):
    """Types of documents"""
    AGENDA = "agenda"
    MINUTES = "minutes"
    OTHER = "other"


class MeetingType(str, enum.Enum):
    """Types of meetings"""
    REGULAR = "regular"
    SPECIAL = "special"
    COMMITTEE = "committee"


class ItemResult(str, enum.Enum):
    """Result of voting on an item"""
    APPROVED = "approved"
    REJECTED = "rejected"
    CONTINUED = "continued"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"


class Meeting(Base):
    """Board of Supervisors meeting"""
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    meeting_date = Column(DateTime, nullable=False, unique=True, index=True)
    meeting_type = Column(Enum(MeetingType), nullable=False, default=MeetingType.REGULAR)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    documents = relationship("Document", back_populates="meeting", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="meeting", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Meeting(date={self.meeting_date}, type={self.meeting_type})>"


class Document(Base):
    """Meeting document (agenda, minutes, etc.)"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    doc_id = Column(String(255), nullable=False, unique=True, index=True)  # Hash of url+date
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, index=True)
    source = Column(String(255), nullable=False)  # e.g., "sfbos"
    doc_type = Column(Enum(DocumentType), nullable=False)
    url = Column(String(1024), nullable=False)
    raw_content = Column(Text, nullable=True)  # Original PDF/HTML content
    markdown_content = Column(Text, nullable=True)  # Converted to markdown
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    meeting = relationship("Meeting", back_populates="documents")

    def __repr__(self):
        return f"<Document(doc_id={self.doc_id}, type={self.doc_type})>"


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
    votes = relationship("Vote", back_populates="supervisor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Supervisor(name={self.name}, district={self.district})>"


class Item(Base):
    """Legislation item voted on at a meeting"""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, index=True)
    file_number = Column(String(255), nullable=True, index=True)  # e.g., "250210"
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    result = Column(Enum(ItemResult), nullable=True)
    
    # Vote counts
    vote_count_aye = Column(Integer, nullable=False, default=0)
    vote_count_no = Column(Integer, nullable=False, default=0)
    vote_count_abstain = Column(Integer, nullable=False, default=0)
    vote_count_absent = Column(Integer, nullable=False, default=0)
    vote_count_excused = Column(Integer, nullable=False, default=0)
    
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    meeting = relationship("Meeting", back_populates="items")
    votes = relationship("Vote", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item(file_number={self.file_number}, title={self.title[:50]})>"


class Vote(Base):
    """Individual supervisor vote on an item"""
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    supervisor_id = Column(Integer, ForeignKey("supervisors.id"), nullable=False, index=True)
    vote = Column(Enum(VoteType), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    item = relationship("Item", back_populates="votes")
    supervisor = relationship("Supervisor", back_populates="votes")

    def __repr__(self):
        return f"<Vote(supervisor_id={self.supervisor_id}, vote={self.vote})>"


# Database initialization and utilities

def init_db(database_url: str = "postgresql://localhost/supervisor_votes"):
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

