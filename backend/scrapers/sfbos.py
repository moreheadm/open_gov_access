"""
SF Board of Supervisors scraper.

Scrapes meeting agendas and minutes from https://sfbos.org/meetings
"""

import re
from datetime import datetime
from typing import Generator, Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from .base import Scraper
from models.database import Document, ContentFormat


class SFBOSScraper(Scraper):
    """
    Scraper for SF Board of Supervisors meeting documents.

    Scrapes from: https://sfbos.org/meetings/full-board-meetings
    """

    BASE_URL = "https://sfbos.org"
    MEETINGS_URL = "https://sfbos.org/meetings/full-board-meetings"

    def source_name(self) -> str:
        return "sfbos"

    def scrape(
        self,
        limit: Optional[int] = None,
        incremental: bool = True,
        force: bool = False,
        session: Optional[Session] = None
    ) -> Generator[Document, None, None]:
        """
        Main scraping method.

        Discovers documents, filters based on database, and yields Document models.

        Args:
            limit: Maximum number of documents to scrape
            incremental: Only scrape new documents (not already in database)
            force: Force re-scrape even if already in database
            session: SQLAlchemy session for checking existing URLs

        Yields:
            Document models (not yet persisted to database)
        """
        print(f"[{self.source_name()}] Discovering documents...")

        # Discover documents from the website
        try:
            response = requests.get(self.MEETINGS_URL, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[{self.source_name()}] Error fetching meetings page: {e}")
            return

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find meeting entries
        meeting_sections = soup.find_all(['div', 'article', 'section'], class_=re.compile(r'meeting|event', re.I))
        if not meeting_sections:
            meeting_sections = [soup]

        count = 0
        for section in meeting_sections:
            if limit and count >= limit:
                break

            # Find PDF links (agendas and minutes)
            pdf_links = section.find_all('a', href=re.compile(r'\.pdf$', re.I))

            for link in pdf_links:
                if limit and count >= limit:
                    break

                url = link.get('href', '')
                if not url:
                    continue

                # Make URL absolute
                if url.startswith('/'):
                    url = self.BASE_URL + url
                elif not url.startswith('http'):
                    continue

                # Check if already in database (incremental by default)
                if incremental and not force and session:
                    existing = session.query(Document).filter_by(url=url).first()
                    if existing:
                        print(f"[{self.source_name()}] Skipping (already in database): {url}")
                        continue

                # Extract document type and date
                link_text = link.get_text(strip=True).lower()

                # Determine document type
                if 'agenda' in link_text or 'agenda' in url.lower():
                    doc_type = 'agenda'
                elif 'minute' in link_text or 'minute' in url.lower():
                    doc_type = 'minutes'
                else:
                    doc_type = 'other'

                # Try to extract date
                meeting_date = self._extract_date(url, link_text, section.get_text())

                # Fetch the document
                try:
                    print(f"[{self.source_name()}] Fetching: {url}")
                    response = requests.get(url, timeout=60)
                    response.raise_for_status()

                    # Create Document model
                    doc = Document(
                        source=self.source_name(),
                        url=url,
                        raw_content=response.content.decode('latin-1', errors='ignore'),
                        content_format=ContentFormat.PDF
                    )

                    count += 1
                    yield doc

                except Exception as e:
                    print(f"[{self.source_name()}] Error fetching {url}: {e}")
                    continue

        print(f"[{self.source_name()}] Successfully scraped {count} documents")


    
    def _extract_date(self, url: str, link_text: str, context: str) -> Optional[datetime]:
        """
        Extract meeting date from URL, link text, or surrounding context.
        
        Args:
            url: Document URL
            link_text: Link text
            context: Surrounding text context
            
        Returns:
            Parsed datetime or None
        """
        # Common date patterns
        patterns = [
            r'(\d{4})[_-](\d{2})[_-](\d{2})',  # YYYY-MM-DD or YYYY_MM_DD
            r'(\d{2})[_-](\d{2})[_-](\d{4})',  # MM-DD-YYYY or MM_DD_YYYY
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # M/D/YYYY
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})',  # Month DD, YYYY
        ]
        
        # Try URL first
        for pattern in patterns:
            match = re.search(pattern, url, re.I)
            if match:
                date = self._parse_date_match(match, pattern)
                if date:
                    return date
        
        # Try link text
        for pattern in patterns:
            match = re.search(pattern, link_text, re.I)
            if match:
                date = self._parse_date_match(match, pattern)
                if date:
                    return date
        
        # Try context
        for pattern in patterns:
            match = re.search(pattern, context, re.I)
            if match:
                date = self._parse_date_match(match, pattern)
                if date:
                    return date
        
        # Default to current date if no date found (not ideal, but prevents errors)
        return datetime.now()
    
    def _parse_date_match(self, match, pattern: str) -> Optional[datetime]:
        """Parse date from regex match"""
        try:
            groups = match.groups()
            
            if 'january|february' in pattern:  # Month name pattern
                month_names = {
                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                    'september': 9, 'october': 10, 'november': 11, 'december': 12
                }
                month = month_names[groups[0].lower()]
                day = int(groups[1])
                year = int(groups[2])
                return datetime(year, month, day)
            
            elif pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                return datetime(year, month, day)
            
            elif pattern.startswith(r'(\d{2})[_-](\d{2})[_-](\d{4})'):  # MM-DD-YYYY
                month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                return datetime(year, month, day)
            
            elif pattern.startswith(r'(\d{1,2})[/-]'):  # M/D/YYYY
                month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                return datetime(year, month, day)
        
        except (ValueError, IndexError):
            return None
        
        return None
    


