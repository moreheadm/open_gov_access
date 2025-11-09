#!/usr/bin/env python3
"""
HTML to Markdown Converter
Converts HTML documents (like meeting transcripts) to Markdown format
without using AI - uses rule-based parsing only.
"""

import html2text
import argparse
from pathlib import Path


def convert_html_to_markdown(html_content, options=None):
    """
    Convert HTML content to Markdown format.

    Args:
        html_content: String containing HTML content
        options: Dictionary of html2text options (optional)

    Returns:
        String containing Markdown formatted text
    """
    # Create html2text converter instance
    h = html2text.HTML2Text()

    # Configure converter options
    if options:
        for key, value in options.items():
            setattr(h, key, value)
    else:
        # Default configuration
        h.ignore_links = False  # Keep links
        h.ignore_images = False  # Keep images
        h.ignore_emphasis = False  # Keep bold/italic
        h.body_width = 0  # Don't wrap text
        h.unicode_snob = True  # Use unicode characters
        h.ignore_tables = False  # Keep tables
        h.single_line_break = False  # Use double line breaks for paragraphs

    # Convert HTML to Markdown
    markdown_content = h.handle(html_content)

    return markdown_content


def convert_html_file_to_markdown(input_file, output_file=None, options=None):
    """
    Convert an HTML file to a Markdown file.

    Args:
        input_file: Path to input HTML file
        output_file: Path to output Markdown file (optional, will auto-generate if not provided)
        options: Dictionary of html2text options (optional)

    Returns:
        Path to the created Markdown file
    """
    input_path = Path(input_file)

    # Read HTML content
    with open(input_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Convert to Markdown
    markdown_content = convert_html_to_markdown(html_content, options)

    # Determine output file path
    if output_file is None:
        output_file = input_path.with_suffix('.md')
    else:
        output_file = Path(output_file)

    # Write Markdown content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"✓ Successfully converted {input_file} to {output_file}")
    return output_file


def main():
    """Command line interface for HTML to Markdown conversion."""
    parser = argparse.ArgumentParser(
        description='Convert HTML documents to Markdown format without AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single file
  python html_to_markdown.py transcript.html

  # Convert with custom output name
  python html_to_markdown.py transcript.html -o output.md

  # Convert with custom options
  python html_to_markdown.py transcript.html --no-links --wrap-width 80
        """
    )

    parser.add_argument('input_file', help='Path to input HTML file')
    parser.add_argument('-o', '--output', help='Path to output Markdown file (default: input_file.md)')
    parser.add_argument('--no-links', action='store_true', help='Ignore links in conversion')
    parser.add_argument('--no-images', action='store_true', help='Ignore images in conversion')
    parser.add_argument('--wrap-width', type=int, default=0, help='Line wrap width (0 = no wrap)')
    parser.add_argument('--single-line-break', action='store_true', help='Use single line breaks instead of double')

    args = parser.parse_args()

    # Build options dictionary
    options = {
        'ignore_links': args.no_links,
        'ignore_images': args.no_images,
        'body_width': args.wrap_width,
        'unicode_snob': True,
        'single_line_break': args.single_line_break,
    }

    # Convert file
    convert_html_file_to_markdown(args.input_file, args.output, options)


if __name__ == '__main__':
    main()
