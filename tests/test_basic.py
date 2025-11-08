"""
Basic tests to verify the system is set up correctly.
"""

import pytest
from datetime import datetime


def test_imports():
    """Test that all modules can be imported"""
    from models.database import (
        Meeting, Document, Supervisor, Item, Vote,
        VoteType, DocumentType, MeetingType, ItemResult
    )
    from scrapers.base import Scraper, DocumentMetadata, ScrapedDocument
    from scrapers.sfbos import SFBOSScraper
    from etl.pipeline import ETLPipeline, VoteParser
    from api.main import app
    
    assert Meeting is not None
    assert Scraper is not None
    assert SFBOSScraper is not None
    assert ETLPipeline is not None
    assert app is not None


def test_document_metadata():
    """Test DocumentMetadata creation"""
    from scrapers.base import DocumentMetadata
    
    meta = DocumentMetadata(
        url="https://example.com/doc.pdf",
        doc_type="agenda",
        meeting_date=datetime(2025, 1, 1),
        source="test",
        title="Test Document"
    )
    
    assert meta.url == "https://example.com/doc.pdf"
    assert meta.doc_type == "agenda"
    assert meta.source == "test"
    assert len(meta.doc_id) == 16  # SHA256 hash truncated to 16 chars


def test_vote_types():
    """Test VoteType enum"""
    from models.database import VoteType
    
    assert VoteType.AYE.value == "aye"
    assert VoteType.NO.value == "no"
    assert VoteType.ABSTAIN.value == "abstain"
    assert VoteType.ABSENT.value == "absent"
    assert VoteType.EXCUSED.value == "excused"


def test_scraper_state():
    """Test ScraperState functionality"""
    from scrapers.base import ScraperState
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        state = ScraperState(tmpdir, "test_scraper")
        
        # Test marking as scraped
        assert not state.is_scraped("doc123")
        state.mark_scraped("doc123")
        assert state.is_scraped("doc123")
        
        # Test metadata
        state.set_metadata("test_key", "test_value")
        assert state.get_metadata("test_key") == "test_value"
        
        # Test reset
        state.reset()
        assert not state.is_scraped("doc123")


def test_api_root():
    """Test API root endpoint"""
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "SF Board of Supervisors" in data["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

