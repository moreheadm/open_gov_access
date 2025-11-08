"""
SF Board of Supervisors scraper.

Scrapes meeting agendas and minutes from https://sfbos.org/meetings
"""

import re
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .base import DocumentMetadata, Scraper, ScrapedDocument


class SFBOSScraper(Scraper):
    """
    Scraper for SF Board of Supervisors meeting documents.
    
    Scrapes from: https://sfbos.org/meetings/full-board-meetings
    """
    
    BASE_URL = "https://sfbos.org"
    MEETINGS_URL = "https://sfbos.org/meetings/full-board-meetings"
    
    def source_name(self) -> str:
        return "sfbos"
    
    def discover(self, limit: Optional[int] = None) -> List[DocumentMetadata]:
        """
        Discover meeting documents from SF BOS website.
        
        Scrapes the meetings page to find agendas and minutes.
        
        Args:
            limit: Maximum number of meetings to discover
            
        Returns:
            List of document metadata
        """
        try:
            response = requests.get(self.MEETINGS_URL, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching meetings page: {e}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        documents = []
        
        # Find meeting entries
        # The SF BOS website structure may vary, so we'll look for common patterns
        meeting_sections = soup.find_all(['div', 'article', 'section'], class_=re.compile(r'meeting|event', re.I))
        
        if not meeting_sections:
            # Fallback: look for links to PDFs
            meeting_sections = [soup]
        
        meetings_found = 0
        for section in meeting_sections:
            if limit and meetings_found >= limit:
                break
            
            # Find PDF links (agendas and minutes)
            pdf_links = section.find_all('a', href=re.compile(r'\.pdf$', re.I))
            
            for link in pdf_links:
                if limit and meetings_found >= limit:
                    break
                
                url = link.get('href', '')
                if not url:
                    continue
                
                # Make URL absolute
                if url.startswith('/'):
                    url = self.BASE_URL + url
                elif not url.startswith('http'):
                    continue
                
                # Extract document type and date from URL or link text
                link_text = link.get_text(strip=True).lower()
                
                # Determine document type
                if 'agenda' in link_text or 'agenda' in url.lower():
                    doc_type = 'agenda'
                elif 'minute' in link_text or 'minute' in url.lower():
                    doc_type = 'minutes'
                else:
                    doc_type = 'other'
                
                # Try to extract date from URL or text
                meeting_date = self._extract_date(url, link_text, section.get_text())
                
                if meeting_date:
                    doc_meta = DocumentMetadata(
                        url=url,
                        doc_type=doc_type,
                        meeting_date=meeting_date,
                        source=self.source_name(),
                        title=link_text
                    )
                    documents.append(doc_meta)
                    meetings_found += 1
        
        # Sort by date (most recent first)
        documents.sort(key=lambda x: x.meeting_date, reverse=True)
        
        return documents[:limit] if limit else documents
    
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
    
    def fetch(self, doc_meta: DocumentMetadata) -> ScrapedDocument:
        """
        Fetch a document (PDF).
        
        Args:
            doc_meta: Document metadata
            
        Returns:
            Scraped document with PDF content
        """
        try:
            response = requests.get(doc_meta.url, timeout=60)
            response.raise_for_status()
            
            return ScrapedDocument(
                doc_id=doc_meta.doc_id,
                url=doc_meta.url,
                doc_type=doc_meta.doc_type,
                meeting_date=doc_meta.meeting_date,
                source=doc_meta.source,
                raw_content=response.content,
                title=doc_meta.title,
                metadata={
                    'content_type': response.headers.get('content-type'),
                    'content_length': len(response.content)
                }
            )
        
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch document: {e}")

