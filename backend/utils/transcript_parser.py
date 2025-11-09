"""
Non-AI transcript parsing utilities for extracting text from HTML transcripts.

This module provides fast, deterministic parsing of HTML transcripts without
requiring LLM API calls. It extracts text content and timestamps from the
structured HTML format used by Legistar transcripts.
"""

import re
from typing import List, Tuple, Optional
from html import unescape
from bs4 import BeautifulSoup


class TranscriptSegment:
    """Represents a segment of transcript with optional timestamp."""
    
    def __init__(self, text: str, timestamp: Optional[str] = None):
        self.text = text.strip()
        self.timestamp = timestamp
    
    def __repr__(self):
        if self.timestamp:
            return f"[{self.timestamp}] {self.text}"
        return self.text


class NonAITranscriptParser:
    """
    Parse HTML transcripts without AI/LLM.
    
    Handles the Legistar transcript format with:
    - Timestamps in <span id="HH:MM:SS"> elements
    - Text content between <br> tags
    - HTML entities and formatting tags
    """
    
    # Regex to extract timestamp from span id
    TIMESTAMP_PATTERN = re.compile(r'(\d{2}:\d{2}:\d{2})')
    
    def extract_segments(self, html_content: str) -> List[TranscriptSegment]:
        """
        Extract transcript segments with timestamps from HTML.

        Args:
            html_content: HTML content (full page or just divTranscript)

        Returns:
            List of TranscriptSegment objects
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find the transcript div if it exists
        transcript_div = soup.find('div', id='divTranscript')
        if transcript_div:
            soup = transcript_div

        segments = []

        # Find all <br> tags and process text between them
        br_tags = soup.find_all('br')

        for i, br_tag in enumerate(br_tags):
            # Get the next <br> tag (or end of content)
            next_br = br_tags[i + 1] if i + 1 < len(br_tags) else None

            # Extract timestamp and text between this br and the next
            timestamp = None
            text_parts = []

            current = br_tag.next_sibling
            while current and current != next_br:
                if isinstance(current, str):
                    text = current.strip()
                    if text:
                        text_parts.append(text)
                elif hasattr(current, 'name'):
                    if current.name == 'span':
                        span_id = current.get('id', '')
                        if NonAITranscriptParser.TIMESTAMP_PATTERN.match(span_id):
                            timestamp = span_id
                        else:
                            # Get text from span
                            nested_text = current.get_text(strip=True)
                            if nested_text and not NonAITranscriptParser.TIMESTAMP_PATTERN.match(nested_text):
                                text_parts.append(nested_text)
                    elif current.name == 'font':
                        nested_text = current.get_text(strip=True)
                        if nested_text and not NonAITranscriptParser.TIMESTAMP_PATTERN.match(nested_text):
                            text_parts.append(nested_text)

                current = current.next_sibling

            # Create segment if we have text
            text = ' '.join(text_parts)
            text = unescape(text)
            text = re.sub(r'\s+', ' ', text).strip()

            if text:
                segments.append(TranscriptSegment(text, timestamp))

        return segments

    
    def to_markdown(self, segments: List[TranscriptSegment], include_timestamps: bool = False) -> str:
        """
        Convert transcript segments to markdown format.
        
        Args:
            segments: List of TranscriptSegment objects
            
        Returns:
            Markdown formatted transcript
        """
        lines = []
        footnotes = {}
        
        for segment in segments:
            if segment.text:
                if segment.timestamp and include_timestamps:
                    # Create footnote reference
                    footnote_key = segment.timestamp.replace(':', '-')
                    lines.append(f"{segment.text}[^{footnote_key}]")
                    footnotes[footnote_key] = segment.timestamp
                else:
                    lines.append(segment.text)
        
        # Add footnotes at the end
        if footnotes:
            lines.append("\n---\n")
            for key in sorted(footnotes.keys()):
                lines.append(f"[^{key}]: {footnotes[key]}")
        
        return '\n\n'.join(lines)
    
    def convert(self, html_content: str, include_timestamps: bool = False) -> str:
        """
        Parse HTML transcript and return plain text.
        
        Args:
            html_content: HTML content to parse
            include_timestamps: Whether to include timestamps in output
            
        Returns:
            Plain text transcript
        """
        segments = self.extract_segments(html_content)

        self.to_markdown(segments, include_timestamps=include_timestamps)


