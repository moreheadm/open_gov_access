#!/usr/bin/env python3
"""
Demo script showing how to use the HTML to Markdown converters
"""

from html_to_markdown import convert_html_to_markdown
from transcript_to_markdown import clean_transcript_text
from pathlib import Path


def demo_basic_conversion():
    """Demonstrate basic HTML to Markdown conversion"""
    print("=" * 60)
    print("Demo 1: Basic HTML to Markdown Conversion")
    print("=" * 60)

    html_sample = """
    <html>
    <head><title>Sample Document</title></head>
    <body>
        <h1>Meeting Minutes</h1>
        <h2>October 20, 2025</h2>

        <p>The meeting was called to order at <strong>10:00 AM</strong>.</p>

        <h3>Attendees:</h3>
        <ul>
            <li>John Doe</li>
            <li>Jane Smith</li>
            <li>Bob Johnson</li>
        </ul>

        <h3>Discussion Points:</h3>
        <ol>
            <li>Budget review</li>
            <li>Project timeline</li>
            <li>Resource allocation</li>
        </ol>

        <p>For more information, visit <a href="https://example.com">our website</a>.</p>

        <blockquote>
        Important: All action items must be completed by next Friday.
        </blockquote>
    </body>
    </html>
    """

    markdown = convert_html_to_markdown(html_sample)
    print("\nInput HTML:")
    print("-" * 60)
    print(html_sample[:200] + "...")
    print("\nOutput Markdown:")
    print("-" * 60)
    print(markdown)


def demo_transcript_conversion():
    """Demonstrate transcript HTML to Markdown conversion"""
    print("\n" + "=" * 60)
    print("Demo 2: Transcript HTML to Markdown Conversion")
    print("=" * 60)

    transcript_html = """
    <html>
    <head><title>City Council Meeting - Transcript</title></head>
    <body>
        <div id="divTranscript" style="font-family: Tahoma; font-size: 10pt;">
            <span id="00:00:00">
                <span id="00:00:10">
                    <font style="color: Gray">00:00:10</font>
                </span>
            </span>
            Good morning everyone and welcome to today's meeting.
            <br>
            <span id="00:00:15">
                <font style="color: Gray">00:00:15</font>
            </span>
            We have several important items on the agenda.
            <br>
            <span id="00:00:20">
                <font style="color: Gray">00:00:20</font>
            </span>
            First, we will discuss the proposed budget.
            <br>
            <span id="00:01:00">
                <font style="color: Gray">00:01:00</font>
            </span>
            Second, we will review the infrastructure plan.
        </div>
    </body>
    </html>
    """

    markdown = clean_transcript_text(transcript_html)
    print("\nInput HTML (excerpt):")
    print("-" * 60)
    print(transcript_html[:300] + "...")
    print("\nOutput Markdown:")
    print("-" * 60)
    print(markdown)


def demo_table_conversion():
    """Demonstrate table conversion to Markdown"""
    print("\n" + "=" * 60)
    print("Demo 3: Table HTML to Markdown Conversion")
    print("=" * 60)

    table_html = """
    <html>
    <body>
        <h2>Budget Summary</h2>
        <table border="1">
            <thead>
                <tr>
                    <th>Department</th>
                    <th>Q1</th>
                    <th>Q2</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Engineering</td>
                    <td>$50,000</td>
                    <td>$55,000</td>
                    <td>$105,000</td>
                </tr>
                <tr>
                    <td>Marketing</td>
                    <td>$30,000</td>
                    <td>$35,000</td>
                    <td>$65,000</td>
                </tr>
                <tr>
                    <td><strong>Total</strong></td>
                    <td><strong>$80,000</strong></td>
                    <td><strong>$90,000</strong></td>
                    <td><strong>$170,000</strong></td>
                </tr>
            </tbody>
        </table>
    </body>
    </html>
    """

    markdown = convert_html_to_markdown(table_html)
    print("\nInput HTML:")
    print("-" * 60)
    print(table_html)
    print("\nOutput Markdown:")
    print("-" * 60)
    print(markdown)


def demo_custom_options():
    """Demonstrate conversion with custom options"""
    print("\n" + "=" * 60)
    print("Demo 4: Conversion with Custom Options")
    print("=" * 60)

    html_with_links = """
    <html>
    <body>
        <h1>Resources</h1>
        <p>Check out these links:</p>
        <ul>
            <li><a href="https://github.com">GitHub</a> - Code hosting</li>
            <li><a href="https://stackoverflow.com">Stack Overflow</a> - Q&A</li>
        </ul>
        <img src="logo.png" alt="Company Logo">
    </body>
    </html>
    """

    print("\nOriginal HTML:")
    print("-" * 60)
    print(html_with_links)

    print("\n\nOption 1: Default (keep links and images)")
    print("-" * 60)
    markdown1 = convert_html_to_markdown(html_with_links)
    print(markdown1)

    print("\nOption 2: Ignore links")
    print("-" * 60)
    markdown2 = convert_html_to_markdown(html_with_links, {'ignore_links': True})
    print(markdown2)

    print("\nOption 3: Ignore both links and images")
    print("-" * 60)
    markdown3 = convert_html_to_markdown(html_with_links, {
        'ignore_links': True,
        'ignore_images': True
    })
    print(markdown3)


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "HTML to Markdown Converter Demos" + " " * 16 + "║")
    print("╚" + "═" * 58 + "╝")
    print("\nThese demos show rule-based HTML to Markdown conversion")
    print("No AI is used - only traditional parsing algorithms\n")

    demo_basic_conversion()
    demo_transcript_conversion()
    demo_table_conversion()
    demo_custom_options()

    print("\n" + "=" * 60)
    print("All demos completed!")
    print("=" * 60)
    print("\nTo convert your own files:")
    print("  python html_to_markdown.py your_file.html")
    print("  python transcript_to_markdown.py your_transcript.html")
    print("\nFor more options, see HTML_TO_MARKDOWN_README.md")
    print()


if __name__ == '__main__':
    main()
