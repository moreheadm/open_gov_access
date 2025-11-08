# Running the Open Government Access Backend

This guide provides step-by-step instructions for running the backend API.

## Prerequisites

- **Python 3.11+** installed
- **uv** package manager (recommended) or pip
- **Docker** (for PostgreSQL) or a PostgreSQL instance
- **Git** (to clone the repository)

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
./setup.sh
```

This script will:
1. Install uv if needed
2. Install all dependencies
3. Start PostgreSQL with Docker
4. Initialize the database
5. Optionally scrape sample data

### Option 2: Manual Setup

#### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. Install Dependencies

```bash
cd backend
uv sync
```

This creates a virtual environment at `backend/.venv` and installs all dependencies.

#### 3. Start PostgreSQL

**Using Docker (recommended):**
```bash
# From the project root
docker-compose up -d
```

**Or use an existing PostgreSQL instance:**
- Make sure PostgreSQL is running
- Create a database: `createdb supervisor_votes`
- Update `.env` with your connection string

#### 4. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` if needed (default settings work with Docker setup):
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/supervisor_votes
```

#### 5. Initialize Database

```bash
cd backend
python main.py init
```

This will:
- Create all database tables
- Seed the database with current SF supervisors

#### 6. Scrape Data (Optional)

```bash
python main.py run --limit 5
```

This scrapes and processes 5 recent Board of Supervisors meetings.

#### 7. Start the API Server

```bash
python main.py serve
```

The API will be available at:
- **API:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Using the CLI

The backend includes a comprehensive CLI tool. All commands should be run from the `backend/` directory using `uv run`.

### Available Commands

```bash
cd backend

# Initialize database (create tables, seed supervisors)
uv run python main.py init

# Scrape documents only (no processing)
uv run python main.py scrape --limit 10

# Process already-scraped documents
uv run python main.py process

# Full pipeline: scrape + process
uv run python main.py run --limit 5

# Start API server
uv run python main.py serve

# Show database statistics
uv run python main.py stats

# Reset scraper state (re-scrape everything)
uv run python main.py reset
```

### Command Options

**Scraping options:**
```bash
# Limit number of documents
uv run python main.py run --limit 10

# Full scrape (not incremental)
uv run python main.py run --full

# Force re-process existing documents
uv run python main.py process --force

# Custom database URL
uv run python main.py run --database postgresql://user:pass@host:5432/dbname

# Verbose output
uv run python main.py run --verbose
```

**Server options:**
```bash
# Custom host and port
uv run python main.py serve --host 0.0.0.0 --port 8080

# Enable auto-reload (development)
uv run python main.py serve --reload
```

### Alternative: Activate Virtual Environment

If you prefer, you can activate the virtual environment and run commands directly:

```bash
cd backend

# Activate virtual environment
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate     # On Windows

# Now you can run commands without 'uv run'
python main.py init
python main.py serve
```

## Using the Makefile

From the project root, you can use make commands:

```bash
# Install dependencies
make install

# Start PostgreSQL
make db-start

# Stop PostgreSQL
make db-stop

# Initialize database
make init

# Scrape and process data
make scrape

# Start API server
make serve

# Run tests
make test

# Clean up
make clean

# Complete setup (install + db + init + scrape)
make setup
```

## API Endpoints

Once the server is running, you can access these endpoints:

### Supervisors
- `GET /api/supervisors` - List all supervisors
- `GET /api/supervisors/{id}` - Get supervisor details
- `GET /api/supervisors/{id}/votes` - Get voting history
- `GET /api/supervisors/{id}/stats` - Get voting statistics

### Items (Legislation)
- `GET /api/items` - List items (supports `?search=query`)
- `GET /api/items/{id}` - Get item with all votes

### Meetings
- `GET /api/meetings` - List meetings

### Statistics
- `GET /api/stats/overview` - System overview

### Examples

```bash
# List all supervisors
curl http://localhost:8000/api/supervisors

# Get voting history for supervisor #1
curl http://localhost:8000/api/supervisors/1/votes

# Search for housing-related items
curl "http://localhost:8000/api/items?search=housing"

# Get system statistics
curl http://localhost:8000/api/stats/overview
```

## Project Structure

```
open_gov_access/
├── backend/                    # Backend project (self-contained)
│   ├── .venv/                 # Virtual environment (created by uv)
│   ├── api/                   # FastAPI application
│   │   └── main.py
│   ├── etl/                   # ETL pipeline
│   │   └── pipeline.py
│   ├── models/                # Database models
│   │   └── database.py
│   ├── scrapers/              # Scraper framework
│   │   ├── base.py           # Abstract base class
│   │   └── sfbos.py          # SF BOS implementation
│   ├── config.py              # Configuration
│   ├── main.py                # CLI entry point
│   ├── pyproject.toml         # Dependencies (uv)
│   ├── .python-version        # Python version
│   └── README.md
├── tests/                     # Tests
├── docs/                      # Documentation
├── docker-compose.yml         # PostgreSQL setup
├── Makefile                   # Common commands
├── setup.sh                   # Automated setup script
└── RUNNING.md                 # This file
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:
```bash
python main.py serve --port 8080
```

### PostgreSQL Connection Error

1. Check if PostgreSQL is running:
   ```bash
   docker-compose ps
   ```

2. Check the connection string in `.env`

3. Restart PostgreSQL:
   ```bash
   docker-compose restart
   ```

### Import Errors

Make sure you're in the `backend/` directory when running commands:
```bash
cd backend
python main.py serve
```

### Virtual Environment Issues

If you have issues with the virtual environment:
```bash
cd backend
rm -rf .venv
uv sync
```

## Development

### Running Tests

```bash
# From project root
pytest tests/ -v

# Or using make
make test
```

### Code Formatting

```bash
cd backend

# Format code
uv run black .

# Lint code
uv run ruff check .

# Type checking
uv run mypy .
```

### Adding Dependencies

```bash
cd backend

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name
```

## Next Steps

1. **Explore the API:** Visit http://localhost:8000/docs for interactive documentation
2. **Run Tests:** `pytest tests/ -v`
3. **Scrape More Data:** `python main.py run --limit 20`
4. **Build Frontend:** The backend is ready for a frontend to be added at the root level

## Support

For more information, see:
- `README.md` - Full project documentation
- `QUICKSTART.md` - 5-minute quick start guide
- `docs/` - Additional documentation
- API Docs - http://localhost:8000/docs (when server is running)

