# Open Government Access

> Aggregate and analyze SF Board of Supervisors votes and meeting data

A hackathon project for Mission Local's challenge to supercharge civic data investigations. This system scrapes, processes, and exposes SF Board of Supervisors voting records through a REST API.

## 🎯 Project Goals

- **Aggregate** Board of Supervisors votes and meeting events
- **Standardize** data from multiple sources via a generic scraping framework
- **Expose** data through a REST API for journalists and civic applications
- **Enable** quick lookups like "find all votes related to a particular property"

## 🏗️ Architecture

```
┌─────────────────┐
│  SF BOS Website │  (sfbos.org)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Scraper        │  Generic framework with incremental scraping
│  (SF BOS impl)  │  State management for efficiency
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ETL Pipeline   │  PDF → Text → Markdown
│                 │  Extract voting data
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL DB  │  Meetings, Documents, Supervisors, Items, Votes
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │  REST API with auto-generated docs
│  (port 8000)    │  Query supervisors, votes, items, stats
└─────────────────┘
```

## 🚀 Quick Start

**Get up and running in 3 commands:**

```bash
# 1. Install dependencies
cd backend && uv sync

# 2. Start PostgreSQL (requires Docker)
cd .. && docker-compose up -d

# 3. Initialize and run
cd backend && uv run python main.py init && uv run python main.py serve
```

Then visit http://localhost:8000/docs to explore the API!

For detailed instructions, see [RUNNING.md](RUNNING.md).

### Prerequisites

- Python 3.11+
- uv package manager
- PostgreSQL (or Docker)
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### 1. Install Dependencies

Using `uv` (recommended):
```bash
cd backend
uv sync
```

Or using pip:
```bash
cd backend
pip install -e .
```

### 2. Set Up Database

Create a PostgreSQL database:
```bash
createdb supervisor_votes
```

Set the database URL (optional, defaults to localhost):
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/supervisor_votes"
```

### 3. Initialize Database

```bash
cd backend
python main.py init
```

This creates tables and seeds the database with current supervisors.

### 4. Run the Pipeline

Scrape and process recent meetings:
```bash
python main.py run --limit 5
```

### 5. Start the API Server

```bash
python main.py serve
```

API available at: http://localhost:8000  
Interactive docs: http://localhost:8000/docs

## 📚 CLI Commands

### Initialize Database
```bash
python backend/main.py init
```

### Scrape Documents
```bash
# Scrape 10 most recent meetings
python backend/main.py scrape --limit 10

# Full scrape (not incremental)
python backend/main.py scrape --full

# Save PDFs to directory
python backend/main.py scrape --save ./pdfs
```

### Process Documents (ETL)
```bash
# Process 5 documents
python backend/main.py process --limit 5

# Force re-process
python backend/main.py process --force
```

### Run Full Pipeline
```bash
# Scrape + process in one command
python backend/main.py run --limit 10
```

### Start API Server
```bash
# Default (port 8000)
python backend/main.py serve

# Custom port
python backend/main.py serve --port 3000

# Auto-reload on code changes
python backend/main.py serve --reload
```

### View Statistics
```bash
python backend/main.py stats
```

### Reset Scraper State
```bash
python backend/main.py reset
```

## 🔌 API Endpoints

### Supervisors

**Get all supervisors**
```http
GET /api/supervisors
```

**Get supervisor details**
```http
GET /api/supervisors/{id}
```

**Get supervisor's voting history**
```http
GET /api/supervisors/{id}/votes?limit=50&offset=0
```

**Get supervisor's statistics**
```http
GET /api/supervisors/{id}/stats
```

Response:
```json
{
  "supervisor": {
    "id": 1,
    "name": "Connie Chan",
    "district": 1,
    "is_active": true
  },
  "total_votes": 150,
  "aye_count": 120,
  "no_count": 25,
  "abstain_count": 3,
  "absent_count": 2,
  "aye_percentage": 80.0
}
```

### Items (Legislation)

**Get voting items**
```http
GET /api/items?limit=50&search=housing
```

**Get item details with all votes**
```http
GET /api/items/{id}
```

### Meetings

**Get meetings**
```http
GET /api/meetings?limit=20
```

### Statistics

**Get overview stats**
```http
GET /api/stats/overview
```

## 🗄️ Database Schema

### Tables

- **meetings** - Board meetings
- **documents** - Meeting documents (agendas, minutes)
- **supervisors** - Board members
- **items** - Legislation items voted on
- **votes** - Individual supervisor votes on items

### Key Features

- **Incremental scraping** - Only processes new documents
- **State management** - Tracks what's been scraped
- **Generic framework** - Easy to add new data sources
- **Type safety** - Pydantic models and SQLAlchemy
- **Auto-generated API docs** - FastAPI Swagger UI

## 🔧 Development

### Project Structure

```
open_gov_access/
├── backend/
│   ├── api/
│   │   └── main.py          # FastAPI application
│   ├── etl/
│   │   └── pipeline.py      # ETL pipeline
│   ├── models/
│   │   └── database.py      # SQLAlchemy models
│   ├── scrapers/
│   │   ├── base.py          # Generic scraper framework
│   │   └── sfbos.py         # SF BOS implementation
│   ├── config.py            # Configuration
│   └── main.py              # CLI entry point
├── docs/                    # Documentation
├── pyproject.toml           # Project dependencies
└── README.md
```

### Adding a New Data Source

1. Create a new scraper class extending `Scraper`:

```python
from backend.scrapers.base import Scraper, DocumentMetadata, ScrapedDocument

class MySourceScraper(Scraper):
    def source_name(self) -> str:
        return "my_source"
    
    def discover(self, limit=None):
        # Return list of DocumentMetadata
        pass
    
    def fetch(self, doc_meta):
        # Download and return ScrapedDocument
        pass
```

2. Use it:

```python
scraper = MySourceScraper()
documents = scraper.scrape(limit=10)
```

### Environment Variables

Create a `.env` file:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/supervisor_votes
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

## 📖 Documentation

See the `docs/` directory for detailed documentation:

- `ARCHITECTURE.txt` - System architecture
- `PROJECT_GUIDE.md` - Development guide
- Mission Local challenge documents

## 🤝 Contributing

This is a hackathon project. Contributions welcome!

## 📄 License

MIT License

## 🙏 Credits

Built for Mission Local's Social Impact Hackathon 2025 challenge to improve civic data accessibility.

