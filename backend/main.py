#!/usr/bin/env python3
"""
Main CLI for Supervisor Votes system

Commands:
  init        - Initialize database and seed supervisors
  scrape      - Scrape documents from Legistar
  process     - Process scraped documents (ETL)
  run         - Run scrape + process pipeline
  serve       - Start API server
  reset       - Reset scraper state
  pdf2md      - Convert PDF to Markdown using PyMuPDF
"""


import argparse
import sys
from pathlib import Path


# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models.database import init_db, get_session, seed_officials, seed_example_data, Document
from sqlalchemy import select
from scrapers.legistar import LegistarScraper
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
    """Scrape documents and save to database"""
    print("Starting scraper...")

    # Initialize database
    engine = init_db(args.database)
    session = get_session(engine)

    scraper = LegistarScraper(
        state_dir=args.state_dir,
        headless=not args.show_browser,
        convert_with_ai=args.convert_with_ai
    )

    # Scrape and save documents
    count = 0
    for doc in scraper.scrape(
        limit=args.limit,
        incremental=not args.full,
        force=args.force,
        session=session
    ):
        try:
            # Add to database
            statement = select(Document).where(Document.url == doc.url).limit(1)
            obj = session.execute(statement).scalar_one_or_none()

            if obj:
                print(f"  Already in database: {doc.url}")
                if args.full:
                    doc.id = obj.id
                else:
                    continue

            session.merge(doc)
            session.commit()
            count += 1
            print(f"✓ Saved document: {doc.url}")
        except Exception as e:
            print(f"✗ Error saving document {doc.url}: {e}")
            session.rollback()

    session.close()
    print(f"✓ Scraped and saved {count} documents to database")

    return count


def cmd_process(args):
    """Scrape documents and process with ETL pipeline"""
    print("Starting scrape + ETL pipeline...")

    # Initialize database and ETL
    engine = init_db(args.database)
    session = get_session(engine)
    etl = ETLPipeline(engine)

    # Scrape documents
    scraper = LegistarScraper(
        state_dir=args.state_dir,
        headless=not args.show_browser,
        convert_with_ai=args.convert_with_ai
    )

    count = 0
    for doc in scraper.scrape(
        limit=args.limit,
        incremental=not args.full,
        force=args.force,
        session=session
    ):
        try:
            # Add to database
            statement = session.query(Document).where(Document.url == doc.url).count(1)
            obj = session.execute(statement)
            if obj:
                print(f"  Already in database: {doc.url}")
                if args.full:
                    doc.id = obj.id
                else:
                    continue

            session.merge(doc)
            session.commit()

            # Process with ETL
            etl.process_document(doc)
            count += 1
            print(f"✓ Processed document: {doc.url}")
        except Exception as e:
            print(f"✗ Error processing {doc.url}: {e}")
            session.rollback()
            if args.verbose:
                import traceback
                traceback.print_exc()

    session.close()
    etl.close()
    print(f"✓ Scraped and processed {count} documents")


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
    scraper = LegistarScraper(state_dir=args.state_dir)
    scraper.reset_state()
    print("✓ Scraper state reset")


def cmd_stats(args):
    """Show statistics"""
    engine = init_db(args.database)
    session = get_session(engine)

    from models.database import Meeting, Legislation, Action, Official
    from sqlalchemy import func

    print("\n=== Database Statistics ===")
    print(f"Meetings:     {session.query(func.count(Meeting.id)).scalar()}")
    print(f"Legislation:  {session.query(func.count(Legislation.id)).scalar()}")
    print(f"Actions:      {session.query(func.count(Action.id)).scalar()}")
    print(f"Officials:    {session.query(func.count(Official.id)).scalar()}")

    # Latest meeting
    latest = session.query(Meeting).order_by(Meeting.meeting_date.desc()).first()
    if latest:
        print(f"Latest meeting: {latest.meeting_date}")

    session.close()


def cmd_pdf2md(args):
    """Convert PDF to Markdown using PyMuPDF"""
    import pymupdf.layout
    import pymupdf4llm
    from pathlib import Path

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return

    if not input_path.suffix.lower() == '.pdf':
        print(f"Error: Input file must be a PDF")
        return

    print(f"Converting {input_path} to Markdown...")

    try:
        # Convert PDF to markdown
        md_text = pymupdf4llm.to_markdown(str(input_path))

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.with_suffix('.md')

        # Write markdown to file
        output_path.write_text(md_text, encoding='utf-8')

        print(f"✓ Converted to: {output_path}")
        print(f"  Size: {len(md_text):,} characters")

        # Show preview if requested
        if args.preview:
            lines = md_text.split('\n')
            preview_lines = min(args.preview, len(lines))
            print(f"\n--- Preview (first {preview_lines} lines) ---")
            print('\n'.join(lines[:preview_lines]))
            print("---")

    except Exception as e:
        print(f"Error converting PDF: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()


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
    parser_scrape.add_argument('--show-browser', action='store_true', help='Show browser (not headless)')
    parser_scrape.add_argument('--convert-with-ai', action='store_true', help='Convert documents with AI (default: no)')
    parser_scrape.set_defaults(func=cmd_scrape)
    
    # process
    parser_process = subparsers.add_parser('process', help='Process documents with ETL')
    parser_process.add_argument('--limit', type=int, help='Limit number of documents')
    parser_process.add_argument('--full', action='store_true', help='Full processing')
    parser_process.add_argument('--force', action='store_true', help='Force re-process')
    parser_process.add_argument('--show-browser', action='store_true', help='Show browser (not headless)')
    parser_process.add_argument('--convert-with-ai', action='store_true', help='Convert documents with AI (default: no)')
    parser_process.set_defaults(func=cmd_process)
    
    # run
    parser_run = subparsers.add_parser('run', help='Run full pipeline')
    parser_run.add_argument('--limit', type=int, help='Limit number of documents')
    parser_run.add_argument('--full', action='store_true', help='Full pipeline')
    parser_run.add_argument('--force', action='store_true', help='Force re-process')
    parser_run.add_argument('--show-browser', action='store_true', help='Show browser (not headless)')
    parser_run.add_argument('--convert-with-ai', action='store_true', help='Convert documents with AI (default: no)')
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

    # pdf2md
    parser_pdf2md = subparsers.add_parser('pdf2md', help='Convert PDF to Markdown')
    parser_pdf2md.add_argument('input', help='Input PDF file path')
    parser_pdf2md.add_argument('-o', '--output', help='Output markdown file path (default: same name as input with .md extension)')
    parser_pdf2md.add_argument('-p', '--preview', type=int, metavar='N', help='Show first N lines of output')
    parser_pdf2md.set_defaults(func=cmd_pdf2md)

    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Run command
    args.func(args)


if __name__ == "__main__":
    main()
