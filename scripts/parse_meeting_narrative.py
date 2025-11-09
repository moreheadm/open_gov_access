#!/usr/bin/env python3
"""
Parse meeting narrative XML from board-mayor-topics-summary-xml command
and convert to JSON for downstream consumption.
"""

import xml.etree.ElementTree as ET
import json
import sys
from typing import Dict, List, Any


def parse_meeting_narrative(xml_str: str) -> Dict[str, Any]:
    """
    Parse meetingNarrative XML and return as a Python dict.
    
    Args:
        xml_str: XML string from board-mayor-topics-summary-xml command
        
    Returns:
        Dict with meeting path and list of narrative topics
    """
    root = ET.fromstring(xml_str)
    
    topics = []
    for topic in root.findall("topic"):
        topic_id = topic.get("id")
        headline = (topic.findtext("headline") or "").strip()
        summary = (topic.findtext("summary") or "").strip()
        timestamps_str = (topic.findtext("timestamps") or "").strip()
        
        # Parse timestamps into a list
        timestamps = [ts.strip() for ts in timestamps_str.split(",") if ts.strip()]
        
        topics.append({
            "id": topic_id,
            "headline": headline,
            "summary": summary,
            "timestamps": timestamps,
        })
    
    return {
        "meeting": root.get("meeting"),
        "topics": topics,
    }


def format_for_display(data: Dict[str, Any]) -> str:
    """
    Format parsed data as human-readable narrative (similar to sample format).
    
    Args:
        data: Parsed meeting narrative dict
        
    Returns:
        Formatted string for display
    """
    lines = []
    lines.append(f"Meeting: {data['meeting']}\n")
    
    for topic in data["topics"]:
        lines.append(f"({topic['headline']})")
        lines.append(topic['summary'])
        if topic['timestamps']:
            lines.append(f"[{', '.join(topic['timestamps'])}]")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Read XML from stdin or file argument
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            xml_input = f.read()
    else:
        xml_input = sys.stdin.read()
    
    # Parse and output as JSON
    parsed = parse_meeting_narrative(xml_input)
    print(json.dumps(parsed, indent=2))

