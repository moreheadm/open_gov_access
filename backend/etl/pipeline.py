"""
ETL Pipeline for processing scraped documents.

Converts PDFs to text/markdown and extracts structured voting data.
"""

import io
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pdfplumber
from sqlalchemy.orm import Session

from models.database import (
    Action,
    ActionType,
    Document,
    Legislation,
    LegislationStatus,
    Meeting,
    MeetingType,
    Official,
    OfficialType,
    VoteType,
)
from scrapers.base import ScrapedDocument


class VoteParser:
    """
    Parser for extracting voting data from meeting minutes.

    Looks for patterns like:
    - "File No. 250210 - Title"
    - "8 ayes, 3 noes"
    - "Supervisor Preston voted aye"
    - Roll call format: "Ayes: Chan, Peskin, ..."
    """

    # Official name patterns (for matching in text)
    OFFICIAL_NAMES = [
        "Chan", "Stefani", "Peskin", "Engardio", "Preston",
        "Dorsey", "Melgar", "Mandelman", "Ronen", "Walton", "Safai"
    ]

    def __init__(self, session: Session):
        self.session = session

    def extract_legislation(self, text: str, meeting_id: int) -> List[Legislation]:
        """
        Extract voting items from meeting minutes text.
        
        Args:
            text: Meeting minutes text
            meeting_id: Database ID of the meeting
            
        Returns:
            List of Item objects
        """
        items = []
        
        # Pattern for file numbers: "File No. 250210" or "File #250210"
        file_pattern = r'File\s+(?:No\.|#)\s*(\d+)'
        
        # Split text into sections by file number
        sections = re.split(file_pattern, text, flags=re.I)
        
        for i in range(1, len(sections), 2):
            if i + 1 >= len(sections):
                break
            
            file_number = sections[i].strip()
            section_text = sections[i + 1]
            
            # Extract title (usually the next line after file number)
            title_match = re.search(r'^[^\n]{10,200}', section_text.strip())
            title = title_match.group(0).strip() if title_match else f"Item {file_number}"
            
            # Extract vote counts
            vote_counts = self._extract_vote_counts(section_text)
            
            # Extract result
            result = self._extract_result(section_text)
            
            # Create legislation
            legislation = Legislation(
                file_number=file_number,
                title=title,
                status=result if result else LegislationStatus.PENDING,
                metadata={
                    'vote_counts': vote_counts,
                    'meeting_id': meeting_id
                }
            )

            items.append(legislation)

        return items
    
    def _extract_vote_counts(self, text: str) -> Dict[str, int]:
        """Extract vote counts from text"""
        counts = {}
        
        # Pattern: "8 ayes, 3 noes"
        aye_match = re.search(r'(\d+)\s+ayes?', text, re.I)
        no_match = re.search(r'(\d+)\s+no(?:es)?', text, re.I)
        abstain_match = re.search(r'(\d+)\s+abstain', text, re.I)
        absent_match = re.search(r'(\d+)\s+absent', text, re.I)
        
        if aye_match:
            counts['aye'] = int(aye_match.group(1))
        if no_match:
            counts['no'] = int(no_match.group(1))
        if abstain_match:
            counts['abstain'] = int(abstain_match.group(1))
        if absent_match:
            counts['absent'] = int(absent_match.group(1))
        
        return counts
    
    def _extract_result(self, text: str) -> Optional[LegislationStatus]:
        """Extract vote result from text"""
        text_lower = text.lower()

        if 'approved' in text_lower or 'passed' in text_lower:
            return LegislationStatus.APPROVED
        elif 'rejected' in text_lower or 'failed' in text_lower:
            return LegislationStatus.REJECTED
        elif 'continued' in text_lower:
            return LegislationStatus.PENDING
        elif 'withdrawn' in text_lower:
            return LegislationStatus.PENDING

        return LegislationStatus.PENDING
    
    def extract_votes(self, text: str, legislation: Legislation) -> List[Action]:
        """
        Extract individual official votes.

        Args:
            text: Section of text for this legislation
            legislation: Legislation object

        Returns:
            List of Action objects
        """
        actions = []

        # Get all supervisors from database
        officials = {o.name: o for o in self.session.query(Official).filter(
            Official.official_type == OfficialType.SUPERVISOR
        ).all()}

        # Pattern 1: Roll call format
        # "Ayes: Chan, Peskin, Preston"
        # "Noes: Stefani, Dorsey"
        actions.extend(self._extract_roll_call_votes(text, legislation, officials))

        # Pattern 2: Individual mentions
        # "Supervisor Preston voted aye"
        actions.extend(self._extract_individual_votes(text, legislation, officials))

        return actions
    
    def _extract_roll_call_votes(
        self, text: str, legislation: Legislation, officials: Dict[str, Official]
    ) -> List[Action]:
        """Extract votes from roll call format"""
        actions = []

        # Find roll call sections
        for vote_type_str in ['ayes?', 'no(?:es)?', 'abstain', 'absent', 'excused']:
            pattern = rf'{vote_type_str}:\s*([^.;]+)'
            match = re.search(pattern, text, re.I)

            if match:
                names_text = match.group(1)
                vote_type = self._normalize_vote_type(vote_type_str)

                # Extract official names
                for official_name, official in officials.items():
                    if official_name.lower() in names_text.lower():
                        action = Action(
                            legislation_id=legislation.id,
                            official_id=official.id,
                            action_type=ActionType.VOTE,
                            vote=vote_type
                        )
                        actions.append(action)

        return actions
    
    def _extract_individual_votes(
        self, text: str, legislation: Legislation, officials: Dict[str, Official]
    ) -> List[Action]:
        """Extract votes from individual mentions"""
        actions = []

        for official_name, official in officials.items():
            # Pattern: "Supervisor Preston voted aye"
            pattern = rf'(?:Supervisor\s+)?{official_name}\s+(?:voted\s+)?(\w+)'
            match = re.search(pattern, text, re.I)

            if match:
                vote_str = match.group(1).lower()
                if vote_str in ['aye', 'yes']:
                    vote_type = VoteType.AYE
                elif vote_str in ['no', 'nay']:
                    vote_type = VoteType.NO
                elif vote_str in ['abstain']:
                    vote_type = VoteType.ABSTAIN
                elif vote_str in ['absent']:
                    vote_type = VoteType.ABSENT
                else:
                    continue

                action = Action(
                    legislation_id=legislation.id,
                    official_id=official.id,
                    action_type=ActionType.VOTE,
                    vote=vote_type
                )
                actions.append(action)

        return actions
    
    def _normalize_vote_type(self, vote_str: str) -> VoteType:
        """Normalize vote type string to VoteType enum"""
        vote_str = vote_str.lower().replace('?', '')
        
        if vote_str in ['ayes', 'aye']:
            return VoteType.AYE
        elif vote_str in ['noes', 'no']:
            return VoteType.NO
        elif vote_str == 'abstain':
            return VoteType.ABSTAIN
        elif vote_str == 'absent':
            return VoteType.ABSENT
        elif vote_str == 'excused':
            return VoteType.EXCUSED
        
        return VoteType.ABSENT


class ETLPipeline:
    """
    ETL Pipeline for processing scraped documents.
    
    Steps:
    1. Convert PDF to text
    2. Convert PDF to markdown
    3. Extract voting items and votes
    4. Load into database
    """
    
    def __init__(self, engine):
        """
        Initialize ETL pipeline.
        
        Args:
            engine: SQLAlchemy engine
        """
        self.engine = engine
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=engine)
        self.session = SessionLocal()
        self.vote_parser = VoteParser(self.session)
    
    def pdf_to_text(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF.

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            Extracted text
        """
        try:
            pdf_file = io.BytesIO(pdf_content)
            text_parts = []

            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

            return '\n\n'.join(text_parts)

        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def pdf_to_markdown(self, pdf_content: bytes) -> str:
        """
        Convert PDF to markdown format.

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            Markdown formatted text
        """
        # For now, just extract text and add basic markdown formatting
        text = self.pdf_to_text(pdf_content)

        # Add markdown headers for sections
        lines = text.split('\n')
        markdown_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                markdown_lines.append('')
                continue

            # Detect headers (all caps, short lines)
            if line.isupper() and len(line) < 100:
                markdown_lines.append(f"## {line}")
            # Detect file numbers
            elif re.match(r'File\s+(?:No\.|#)\s*\d+', line, re.I):
                markdown_lines.append(f"### {line}")
            else:
                markdown_lines.append(line)

        return '\n'.join(markdown_lines)

    def process_document(self, doc: ScrapedDocument) -> Optional[Document]:
        """
        Process a scraped document through the ETL pipeline.

        Args:
            doc: Scraped document

        Returns:
            Database Document object or None if processing failed
        """
        try:
            # 1. Get or create meeting
            meeting = self._get_or_create_meeting(doc.meeting_date)

            # 2. Check if document already exists
            existing_doc = self.session.query(Document).filter_by(doc_id=doc.doc_id).first()
            if existing_doc:
                print(f"Document {doc.doc_id} already exists, skipping")
                return existing_doc

            # 3. Convert PDF to text and markdown
            print(f"Converting PDF to text/markdown...")
            text_content = self.pdf_to_text(doc.raw_content)
            markdown_content = self.pdf_to_markdown(doc.raw_content)

            # 4. Create document record
            db_doc = Document(
                doc_id=doc.doc_id,
                meeting_id=meeting.id,
                source=doc.source,
                doc_type=DocumentType(doc.doc_type),
                url=doc.url,
                raw_content=text_content,  # Store extracted text instead of binary
                markdown_content=markdown_content,
            )
            self.session.add(db_doc)
            self.session.flush()

            # 5. Extract voting data (only from minutes)
            if doc.doc_type == 'minutes':
                print(f"Extracting voting data...")
                legislation_items = self.vote_parser.extract_legislation(text_content, meeting.id)

                for legislation in legislation_items:
                    self.session.add(legislation)
                    self.session.flush()

                    # Extract individual votes
                    # Find the section of text for this legislation
                    item_pattern = rf'File\s+(?:No\.|#)\s*{legislation.file_number}(.*?)(?=File\s+(?:No\.|#)|$)'
                    item_match = re.search(item_pattern, text_content, re.I | re.DOTALL)

                    if item_match:
                        item_text = item_match.group(1)
                        actions = self.vote_parser.extract_votes(item_text, legislation)

                        for action in actions:
                            self.session.add(action)

                print(f"Extracted {len(legislation_items)} legislation items")

            # 6. Commit transaction
            self.session.commit()
            print(f"✓ Processed document {doc.doc_id}")

            return db_doc

        except Exception as e:
            self.session.rollback()
            print(f"Error processing document {doc.doc_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_or_create_meeting(self, meeting_date: datetime) -> Meeting:
        """Get or create a meeting record"""
        # Normalize to date only (remove time)
        meeting_date = meeting_date.replace(hour=0, minute=0, second=0, microsecond=0)

        meeting = self.session.query(Meeting).filter_by(meeting_date=meeting_date).first()

        if not meeting:
            meeting = Meeting(
                meeting_date=meeting_date,
                meeting_type=MeetingType.REGULAR
            )
            self.session.add(meeting)
            self.session.flush()

        return meeting

    def close(self):
        """Close database session"""
        self.session.close()

