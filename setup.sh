#!/bin/bash
# Quick setup script for Open Government Access

set -e

echo "🚀 Open Government Access - Setup Script"
echo "=========================================="
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "✓ Found uv"
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker not found. You'll need to install PostgreSQL manually."
    echo "   Visit: https://www.postgresql.org/download/"
    USE_DOCKER=false
else
    echo "✓ Found Docker"
    USE_DOCKER=true
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
cd backend
uv sync
cd ..

# Start PostgreSQL
if [ "$USE_DOCKER" = true ]; then
    echo ""
    echo "🐘 Starting PostgreSQL with Docker..."
    docker-compose up -d
    
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 5
    
    # Check if PostgreSQL is ready
    until docker-compose exec -T postgres pg_isready -U opengov &> /dev/null; do
        echo "   Still waiting..."
        sleep 2
    done
    
    echo "✓ PostgreSQL is ready"
else
    echo ""
    echo "⚠️  Please ensure PostgreSQL is running and create a database:"
    echo "   createdb open_gov_access"
    echo ""
    read -p "Press Enter when ready to continue..."
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✓ Created .env file"
fi

# Initialize database
echo ""
echo "🗄️  Initializing database..."
cd backend
python main.py init
cd ..

# Ask if user wants to scrape data
echo ""
read -p "📥 Do you want to scrape sample data now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔍 Scraping 5 recent meetings..."
    cd backend
    python main.py run --limit 5
    cd ..
fi

# Show statistics
echo ""
echo "📊 Database statistics:"
cd backend
python main.py stats
cd ..

# Success message
echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Start the API server:"
echo "     cd backend && python main.py serve"
echo ""
echo "  2. Open the API docs:"
echo "     http://localhost:8000/docs"
echo ""
echo "  3. Try some API endpoints:"
echo "     curl http://localhost:8000/api/supervisors"
echo "     curl http://localhost:8000/api/stats/overview"
echo ""
echo "For more information, see README.md and QUICKSTART.md"
echo ""

