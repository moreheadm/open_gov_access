# Mission Local Civic Data Platform

A platform for scraping, processing, and analyzing San Francisco civic data to supercharge investigative journalism.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCES LAYER                       │
│  SF Board Meetings | Campaign Finance | Permits | etc.      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    INGESTION PIPELINE                        │
│  • Scrapers (download original documents)                   │
│  • Parsers (PDF → Text/Markdown)                            │
│  • Validators (data quality checks)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      STORAGE LAYER                           │
│  • PostgreSQL (structured metadata & relationships)          │
│  • Object Storage (original PDFs, documents)                │
│  • Vector DB (embeddings for semantic search)               │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    PROCESSING LAYER                          │
│  • ETL Pipeline (data transformation)                       │
│  • Search Indexer (full-text + semantic)                    │
│  • Analyzer (pattern detection, anomalies)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                        API LAYER                             │
│  • REST API (web interface)                                 │
│  • MCP Server (AI tool access)                              │
│  • WebSocket (real-time alerts)                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      FRONTEND LAYER                          │
│  • Search Interface (find documents by entity/address)      │
│  • Analytics Dashboard (patterns, trends)                   │
│  • Alert Management (notifications)                         │
└─────────────────────────────────────────────────────────────┘
```

## Core Concepts

### Data Source
A pipeline that imports data from a specific source (e.g., Board meetings, permits) into a standardized format. Each data source:
- Scrapes/downloads original documents
- Converts to text/markdown
- Stores original + processed versions
- Maintains link to original source
- Tracks metadata (date, source, type, entities)

### Document Model
Every document in the system has:
- **Original**: The raw file (PDF, HTML, etc.)
- **Processed**: Text/markdown version
- **Metadata**: Date, source, type, entities mentioned
- **Source URL**: Link back to original
- **Relationships**: Links to addresses, people, organizations mentioned

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

### 2. Run the SF Board Meetings Scraper

```bash
python sfbos_scraper.py
```

This will:
1. Scrape the most recent 5 meetings from https://sfbos.org/meetings/full-board-meetings
2. Download agendas and minutes (PDFs)
3. Convert PDFs to text
4. Save everything in structured folders:
   - `data/sfbos_meetings/raw/` - Original PDFs
   - `data/sfbos_meetings/text/` - Converted text files
   - `data/sfbos_meetings/metadata/` - JSON metadata

### 3. Output Structure

```
data/sfbos_meetings/
├── raw/
│   ├── 01-14-2025_agenda.pdf
│   ├── 01-14-2025_minutes.pdf
│   └── ...
├── text/
│   ├── 01-14-2025_agenda.txt
│   ├── 01-14-2025_minutes.txt
│   └── ...
└── metadata/
    ├── 01-14-2025_agenda.json
    ├── 01-14-2025_minutes.json
    └── ...
```

## Next Steps

### Phase 1: Core Data Pipeline ✅ (Current)
- [x] Board meetings scraper
- [ ] Database schema design
- [ ] ETL pipeline to load into PostgreSQL
- [ ] Add more data sources (permits, campaign finance)

### Phase 2: Search & Analysis
- [ ] Set up vector database (Pinecone/Weaviate/Qdrant)
- [ ] Entity extraction (addresses, names, organizations)
- [ ] Full-text search API
- [ ] Semantic search with embeddings

### Phase 3: API Layer
- [ ] REST API for data access
- [ ] MCP server implementation
- [ ] WebSocket for real-time updates

### Phase 4: Frontend
- [ ] Search interface
- [ ] Entity profile pages (all docs for an address)
- [ ] Pattern visualization
- [ ] Alert management

### Phase 5: Advanced Features
- [ ] Anomaly detection
- [ ] Cross-dataset correlation
- [ ] Real-time monitoring
- [ ] Journalist collaboration features

## Database Schema (Proposed)

See `schema.sql` for the full PostgreSQL schema design.

Key tables:
- **data_sources**: Registry of all data sources
- **documents**: All processed documents
- **entities**: Extracted entities (addresses, people, orgs)
- **document_entities**: Many-to-many relationships
- **alerts**: Configurable alerts for journalists

## Technology Stack

- **Scraping**: Python, requests, BeautifulSoup, pdfplumber
- **Database**: PostgreSQL (structured data) + pgvector (embeddings)
- **Search**: Elasticsearch or Typesense
- **Backend**: FastAPI (Python) or Node.js/Express
- **MCP**: Python MCP SDK
- **Frontend**: React/Next.js or Vue.js
- **Deployment**: Docker + Docker Compose

## Contributing

This is a hackathon project for Mission Local. Key priorities:
1. **Accuracy**: Civic data must be reliable
2. **Attribution**: Always link back to original sources
3. **Usability**: Journalists need tools, not complexity
4. **Speed**: Enable real-time reporting

## License

[Choose appropriate license]
