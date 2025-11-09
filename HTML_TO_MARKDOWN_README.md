# HTML to Markdown Converter

Two Python scripts for converting HTML documents to Markdown format **without using AI**. These tools use rule-based parsing only.

## Files

1. **`html_to_markdown.py`** - General-purpose HTML to Markdown converter using the `html2text` library
2. **`transcript_to_markdown.py`** - Specialized converter for meeting transcript HTML files using BeautifulSoup

## Installation

Install required dependencies:

```bash
pip install -r requirements_html2md.txt
```

Or install individually:

```bash
pip install html2text beautifulsoup4 lxml
```

## Usage

### General HTML Conversion (html_to_markdown.py)

**Basic usage:**
```bash
python html_to_markdown.py input.html
```

**Specify output file:**
```bash
python html_to_markdown.py input.html -o output.md
```

**Advanced options:**
```bash
# Ignore links during conversion
python html_to_markdown.py input.html --no-links

# Ignore images
python html_to_markdown.py input.html --no-images

# Set line wrap width (0 = no wrap)
python html_to_markdown.py input.html --wrap-width 80

# Use single line breaks
python html_to_markdown.py input.html --single-line-break
```

### Transcript Conversion (transcript_to_markdown.py)

This script is optimized for meeting transcripts with timestamps.

**Basic usage (clean mode):**
```bash
python transcript_to_markdown.py transcript.html
```

**Structured mode (preserves timestamps):**
```bash
python transcript_to_markdown.py transcript.html --mode structured
```

**Specify output file:**
```bash
python transcript_to_markdown.py transcript.html -o meeting_notes.md
```

## Programmatic Usage

You can also import these modules in your Python code:

### Using html_to_markdown

```python
from html_to_markdown import convert_html_to_markdown, convert_html_file_to_markdown

# Convert HTML string
html_content = "<h1>Title</h1><p>Paragraph</p>"
markdown = convert_html_to_markdown(html_content)
print(markdown)

# Convert HTML file
output_path = convert_html_file_to_markdown("input.html", "output.md")
```

### Using transcript_to_markdown

```python
from transcript_to_markdown import convert_transcript_html_to_markdown

# Convert transcript file (clean mode)
output_path = convert_transcript_html_to_markdown("transcript.html")

# Convert with structured timestamp parsing
output_path = convert_transcript_html_to_markdown(
    "transcript.html",
    "output.md",
    mode='structured'
)
```

## Conversion Methods

### html2text Library (General HTML)

The `html_to_markdown.py` script uses the `html2text` library which:
- Converts HTML tags to Markdown equivalents
- Preserves formatting (bold, italic, links, etc.)
- Handles tables, lists, and other complex structures
- Is completely rule-based (no AI involved)

### BeautifulSoup (Transcript Specific)

The `transcript_to_markdown.py` script uses BeautifulSoup which:
- Parses HTML DOM structure
- Extracts specific elements (timestamps, speaker text)
- Provides more control over output format
- Better for structured data extraction

## Examples

### Example 1: Converting a simple HTML file

```bash
echo "<h1>Meeting Notes</h1><p>Discussion about project timeline.</p>" > test.html
python html_to_markdown.py test.html
cat test.md
```

Output:
```markdown
# Meeting Notes

Discussion about project timeline.
```

### Example 2: Converting a transcript

Given a transcript HTML like:
```html
<div id="divTranscript">
<span id="00:00:00"><font style="color: Gray">00:00:10</font></span>
Welcome to the meeting.
<br>
<span id="00:00:15"><font style="color: Gray">00:00:15</font></span>
Today we will discuss the budget.
</div>
```

Run:
```bash
python transcript_to_markdown.py transcript.html --mode structured
```

Output:
```markdown
# Meeting Transcript

**[00:00:10]** Welcome to the meeting.

**[00:00:15]** Today we will discuss the budget.
```

## Customization

### Customize html_to_markdown Options

Modify the `options` dictionary in your code:

```python
options = {
    'ignore_links': False,
    'ignore_images': False,
    'body_width': 0,  # No line wrapping
    'unicode_snob': True,
    'single_line_break': False,
    'ignore_tables': False,
    'mark_code': True,
}

markdown = convert_html_to_markdown(html_content, options)
```

### Customize transcript_to_markdown Parser

Edit the `extract_transcript_content()` or `clean_transcript_text()` functions to match your specific HTML structure.

## Limitations

- **html2text**: Works best with well-formed HTML; may struggle with heavily nested or malformed HTML
- **transcript_to_markdown**: Currently optimized for San Francisco meeting transcript format; may need customization for other formats

## Technical Details

### How It Works (No AI)

Both scripts use **rule-based parsing**:

1. **html2text** uses regex patterns and HTML parsing rules to convert tags to Markdown
2. **BeautifulSoup** builds a DOM tree and traverses it based on predefined rules
3. No machine learning, no neural networks, no AI models - just traditional programming logic

### Dependencies

- `html2text`: MIT licensed, rule-based HTML to Markdown converter
- `beautifulsoup4`: MIT licensed, HTML/XML parser
- `lxml`: BSD licensed, fast HTML/XML processing library

## License

These scripts are provided as-is for converting HTML to Markdown without AI assistance.

## Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'html2text'`
- **Solution**: Run `pip install html2text`

**Issue**: Output Markdown has too many line breaks
- **Solution**: Use `--single-line-break` flag with html_to_markdown.py

**Issue**: Transcript timestamps not being extracted
- **Solution**: The HTML structure may differ; edit the `extract_transcript_content()` function to match your HTML format

**Issue**: Unicode characters not displaying correctly
- **Solution**: Ensure you're using UTF-8 encoding when reading/writing files
