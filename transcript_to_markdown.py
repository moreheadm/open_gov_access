#!/usr/bin/env python3
"""
Transcript HTML to Markdown Converter
Specialized converter for meeting transcript HTML files.
Extracts timestamps and speaker text, formatting them cleanly in Markdown.
"""

from bs4 import BeautifulSoup
import argparse
from pathlib import Path
import re


def extract_transcript_content(html_content):
    """
    Extract transcript content from HTML, focusing on timestamped text.

    Args:
        html_content: String containing HTML content

    Returns:
        String containing formatted Markdown transcript
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Try to find the main transcript div
    transcript_div = soup.find('div', {'id': 'divTranscript'})

    if not transcript_div:
        # Fallback: try to find any div with transcript-like content
        transcript_div = soup.find('div', style=re.compile(r'font-family'))

    if not transcript_div:
        # If no specific div found, use the body
        transcript_div = soup.find('body')

    if not transcript_div:
        return "# Error: No transcript content found\n"

    markdown_lines = []
    markdown_lines.append("# Meeting Transcript\n")

    # Get title if available
    title = soup.find('title')
    if title and title.string:
        markdown_lines.append(f"**Title:** {title.string.strip()}\n")

    markdown_lines.append("---\n")

    # Process the transcript content
    # Look for spans with timestamps and text
    current_time = None

    for element in transcript_div.descendants:
        if element.name == 'span':
            # Check if this is a timestamp
            span_id = element.get('id', '')
            if span_id.startswith('00:'):
                # This is a timestamp marker
                continue

            # Check for font elements with timestamps
            font = element.find('font', style=re.compile(r'color:\s*Gray'))
            if font:
                current_time = font.get_text().strip()

        elif element.name == 'br':
            continue

        elif isinstance(element, str):
            text = element.strip()
            if text and text not in ['', '\n']:
                # Clean up the text
                text = re.sub(r'\s+', ' ', text).strip()
                if len(text) > 3:  # Ignore very short fragments
                    if current_time:
                        markdown_lines.append(f"**[{current_time}]** {text}\n\n")
                        current_time = None
                    else:
                        markdown_lines.append(f"{text}\n\n")

    return ''.join(markdown_lines)


def clean_transcript_text(html_content):
    """
    Simple clean extraction of all text from transcript.

    Args:
        html_content: String containing HTML content

    Returns:
        String containing clean transcript text
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove script and style elements
    for script in soup(['script', 'style']):
        script.decompose()

    # Get title
    title = soup.find('title')
    title_text = title.string.strip() if title else "Transcript"

    # Find transcript div
    transcript_div = soup.find('div', {'id': 'divTranscript'})
    if not transcript_div:
        transcript_div = soup.find('body')

    markdown_lines = [f"# {title_text}\n\n---\n\n"]

    # Get all text, preserving line breaks
    if transcript_div:
        lines = transcript_div.get_text(separator='\n').split('\n')

        for line in lines:
            line = line.strip()
            if line:
                # Check if line starts with timestamp
                if re.match(r'^\d{2}:\d{2}:\d{2}', line):
                    markdown_lines.append(f"**{line}**\n\n")
                else:
                    markdown_lines.append(f"{line}\n\n")

    return ''.join(markdown_lines)


def convert_transcript_html_to_markdown(input_file, output_file=None, mode='clean'):
    """
    Convert transcript HTML file to Markdown.

    Args:
        input_file: Path to input HTML file
        output_file: Path to output Markdown file (optional)
        mode: 'clean' for simple text extraction, 'structured' for timestamp parsing

    Returns:
        Path to the created Markdown file
    """
    input_path = Path(input_file)

    # Read HTML content
    with open(input_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Convert based on mode
    if mode == 'structured':
        markdown_content = extract_transcript_content(html_content)
    else:
        markdown_content = clean_transcript_text(html_content)

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
    """Command line interface for transcript HTML to Markdown conversion."""
    parser = argparse.ArgumentParser(
        description='Convert meeting transcript HTML to Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert with clean text extraction (default)
  python transcript_to_markdown.py transcript.html

  # Convert with structured timestamp parsing
  python transcript_to_markdown.py transcript.html --mode structured

  # Specify output file
  python transcript_to_markdown.py transcript.html -o meeting_notes.md
        """
    )

    parser.add_argument('input_file', help='Path to input HTML transcript file')
    parser.add_argument('-o', '--output', help='Path to output Markdown file')
    parser.add_argument('--mode', choices=['clean', 'structured'], default='clean',
                       help='Conversion mode (default: clean)')

    args = parser.parse_args()

    # Convert file
    convert_transcript_html_to_markdown(args.input_file, args.output, args.mode)


if __name__ == '__main__':
    main()
