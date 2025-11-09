#!/usr/bin/env python3
"""
Example: Orchestrate both meeting summary commands and convert to JSON.
This shows how another service can invoke the commands and consume the output.
"""

import subprocess
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any


def run_command(command: str, transcript_path: str) -> str:
    """
    Run an .augment command and return its XML output.
    
    Args:
        command: Command name (e.g., "board-mayor-topics-summary-xml")
        transcript_path: Path to transcript file
        
    Returns:
        XML string from command stdout
    """
    # In real usage, this would invoke the Augment agent
    # For now, this is a placeholder showing the interface
    result = subprocess.run(
        [command, transcript_path],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout


def parse_meeting_narrative(xml_str: str) -> Dict[str, Any]:
    """Parse meetingNarrative XML to dict."""
    root = ET.fromstring(xml_str)
    topics = []
    for topic in root.findall("topic"):
        timestamps = [ts.strip() for ts in 
                     (topic.findtext("timestamps") or "").split(",") 
                     if ts.strip()]
        topics.append({
            "id": topic.get("id"),
            "headline": (topic.findtext("headline") or "").strip(),
            "summary": (topic.findtext("summary") or "").strip(),
            "timestamps": timestamps,
        })
    return {"meeting": root.get("meeting"), "topics": topics}


def parse_public_comments(xml_str: str) -> Dict[str, Any]:
    """Parse publicComments XML to dict."""
    root = ET.fromstring(xml_str)
    items = []
    for item in root.findall("item"):
        totals = item.find("totals").attrib if item.find("totals") is not None else {}
        comments = []
        for comment in (item.find("comments") or []).findall("comment"):
            comments.append({
                "index": comment.get("index"),
                "speaker": comment.get("speaker"),
                "position": comment.get("position"),
                "timestamp": comment.get("timestamp"),
                "text": "".join(comment.itertext()).strip(),
            })
        items.append({
            "id": item.get("id"),
            "description": (item.findtext("description") or "").strip(),
            "totals": totals,
            "comments": comments,
        })
    return {"meeting": root.get("meeting"), "items": items}


def main(transcript_path: str):
    """
    Orchestrate both commands and produce combined JSON output.
    """
    print(f"Processing: {transcript_path}\n")
    
    # Run board-mayor command
    print("1. Fetching board/mayor narrative...")
    narrative_xml = run_command("board-mayor-topics-summary-xml", transcript_path)
    narrative_data = parse_meeting_narrative(narrative_xml)
    
    # Run public-comments command
    print("2. Fetching public comments summary...")
    comments_xml = run_command("public-comments-summary-xml", transcript_path)
    comments_data = parse_public_comments(comments_xml)
    
    # Combine into single payload
    payload = {
        "meeting": transcript_path,
        "narrative": narrative_data,
        "publicComments": comments_data,
    }
    
    # Output as JSON
    print("\n3. Combined output (JSON):")
    print(json.dumps(payload, indent=2))
    
    return payload


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python example_automation_flow.py <transcript_path>")
        sys.exit(1)
    main(sys.argv[1])

