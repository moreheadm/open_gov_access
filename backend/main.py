#!/usr/bin/env python3
"""
Main CLI for Supervisor Votes system

Commands:
  init        - Initialize database and seed supervisors
  scrape      - Scrape documents from SF BOS website
  process     - Process scraped documents (ETL)
  run         - Run scrape + process pipeline
  serve       - Start API server
  reset       - Reset scraper state
"""

import argparse
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models.database import init_db, get_session, seed_officials, seed_example_data
from scrapers.sfbos import SFBOSScraper
from etl.pipeline import ETLPipeline
from config import settings


def cmd_init(args):
    """Initialize database"""
    print("Initializing database...")
    engine = init_db(args.database)
    print("✓ Database created")

    session = get_session(engine)
    seed_officials(session)

    # Seed example data if requested
    if args.with_examples:
        seed_example_data(session)

    session.close()

    print("✓ Database initialized")


def cmd_scrape(args):
    """Scrape documents"""
    print("Starting scraper...")
    
    scraper = SFBOSScraper(state_dir=args.state_dir)
    
    documents = scraper.scrape(
        limit=args.limit,
        incremental=not args.full,
        force=args.force
    )
    
    if documents and args.save:
        # Save scraped documents
        save_dir = Path(args.save)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        for doc in documents:
            filename = f"{doc.doc_id}.pdf"
            filepath = save_dir / filename
            filepath.write_bytes(doc.raw_content)
        
        print(f"✓ Saved {len(documents)} documents to {save_dir}")
    
    return documents


def cmd_process(args):
    """Process scraped documents with ETL pipeline"""
    print("Starting ETL pipeline...")
    
    # Initialize database and ETL
    engine = init_db(args.database)
    etl = ETLPipeline(engine)
    
    # Scrape documents
    scraper = SFBOSScraper(state_dir=args.state_dir)
    documents = scraper.scrape(
        limit=args.limit,
        incremental=not args.full,
        force=args.force
    )
    
    # Process each document
    for doc in documents:
        try:
            etl.process_document(doc)
        except Exception as e:
            print(f"Error processing {doc.doc_id}: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    etl.close()
    print("✓ ETL complete")


def cmd_run(args):
    """Run full pipeline: scrape + process"""
    cmd_process(args)


def cmd_serve(args):
    """Start API server"""
    import uvicorn
    from api.main import app

    print(f"Starting API server on http://{args.host}:{args.port}")
    print(f"Docs available at http://{args.host}:{args.port}/docs")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


def cmd_reset(args):
    """Reset scraper state"""
    scraper = SFBOSScraper(state_dir=args.state_dir)
    scraper.reset_state()
    print("✓ Scraper state reset")


def cmd_stats(args):
    """Show statistics"""
    engine = init_db(args.database)
    session = get_session(engine)

    from models.database import Meeting, Item, Vote, Supervisor
    from sqlalchemy import func
    
    print("\n=== Database Statistics ===")
    print(f"Meetings:     {session.query(func.count(Meeting.id)).scalar()}")
    print(f"Items:        {session.query(func.count(Item.id)).scalar()}")
    print(f"Votes:        {session.query(func.count(Vote.id)).scalar()}")
    print(f"Supervisors:  {session.query(func.count(Supervisor.id)).scalar()}")
    
    # Latest meeting
    latest = session.query(Meeting).order_by(Meeting.meeting_date.desc()).first()
    if latest:
        print(f"Latest meeting: {latest.meeting_date}")
    
    session.close()


def main():
    parser = argparse.ArgumentParser(
        description="SF Board of Supervisors Voting Records System"
    )
    
    # Global arguments
    parser.add_argument(
        '--database',
        default=settings.database_url,
        help='Database URL'
    )
    parser.add_argument(
        '--state-dir',
        default='data/state',
        help='Directory for scraper state'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # init
    parser_init = subparsers.add_parser('init', help='Initialize database')
    parser_init.add_argument('--with-examples', action='store_true', help='Seed with example data')
    parser_init.set_defaults(func=cmd_init)
    
    # scrape
    parser_scrape = subparsers.add_parser('scrape', help='Scrape documents')
    parser_scrape.add_argument('--limit', type=int, help='Limit number of documents')
    parser_scrape.add_argument('--full', action='store_true', help='Full scrape (not incremental)')
    parser_scrape.add_argument('--force', action='store_true', help='Force re-scrape')
    parser_scrape.add_argument('--save', help='Save PDFs to directory')
    parser_scrape.set_defaults(func=cmd_scrape)
    
    # process
    parser_process = subparsers.add_parser('process', help='Process documents with ETL')
    parser_process.add_argument('--limit', type=int, help='Limit number of documents')
    parser_process.add_argument('--full', action='store_true', help='Full processing')
    parser_process.add_argument('--force', action='store_true', help='Force re-process')
    parser_process.set_defaults(func=cmd_process)
    
    # run
    parser_run = subparsers.add_parser('run', help='Run full pipeline')
    parser_run.add_argument('--limit', type=int, help='Limit number of documents')
    parser_run.add_argument('--full', action='store_true', help='Full pipeline')
    parser_run.add_argument('--force', action='store_true', help='Force re-process')
    parser_run.set_defaults(func=cmd_run)
    
    # serve
    parser_serve = subparsers.add_parser('serve', help='Start API server')
    parser_serve.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser_serve.add_argument('--port', type=int, default=8000, help='Port to bind')
    parser_serve.add_argument('--reload', action='store_true', help='Auto-reload on changes')
    parser_serve.set_defaults(func=cmd_serve)
    
    # reset
    parser_reset = subparsers.add_parser('reset', help='Reset scraper state')
    parser_reset.set_defaults(func=cmd_reset)
    
    # stats
    parser_stats = subparsers.add_parser('stats', help='Show statistics')
    parser_stats.set_defaults(func=cmd_stats)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Run command
    args.func(args)


if __name__ == "__main__":
    main()
